"""Text normalisation and matching helpers for the claims firewall.

Steps: Unicode NFKC, casefold, apostrophes dropped (doesn't -> doesnt),
leetspeak digits mapped to letters inside tokens that contain a letter
(pr0v3n -> proven, while 100% stays 100%), hyphens/underscores/dots
between word characters removed (pro-ven -> proven, pr*ven -> prven),
zero-width and other format characters dropped, spelled-out letters
joined (p r o v e n -> proven),
production-ready -> productionready), "100 %" -> "100%". Text is split
into clauses at punctuation so negation stays clause-scoped.
"""

import re
import unicodedata

_LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"})
_CLAUSE = re.compile(r"[.;:!?,()\[\]\u2014\u2013\n]+|\s-{1,2}\s")
_TOKEN = re.compile(r"[a-z0-9%@$]+")


def _token_fix(tok):
    if any(ch.isalpha() for ch in tok):
        return tok.translate(_LEET)
    return tok


def clauses(text):
    """Return a list of clauses, each a list of normalised tokens."""
    t = unicodedata.normalize("NFKC", text).casefold()
    t = "".join(ch for ch in t if unicodedata.category(ch) != "Cf")  # zero-width etc.
    t = re.sub(r"(?<=[a-z0-9])[*#~^+](?=[a-z0-9])", "", t)
    t = re.sub(r"[\u2019'`]", "", t)
    t = re.sub(r"(?<=[\w@$])[-_.\u2010\u2011\u00ad](?=[\w@$])", "", t)
    t = re.sub(r"(\d)\s+%", r"\1%", t)
    out = []
    for part in _CLAUSE.split(t):
        toks = _join_spelled([_token_fix(x) for x in _TOKEN.findall(part)])
        if toks:
            out.append(toks)
    return out


def _join_spelled(toks):
    """Join runs of 3+ single-letter tokens: 'p r o v e n' -> 'proven'."""
    out, run = [], []
    for tok in toks + [""]:
        if len(tok) == 1 and tok.isalpha():
            run.append(tok)
            continue
        out.extend(["".join(run)] if len(run) >= 3 else run)
        run = []
        if tok:
            out.append(tok)
    return out


def edit_distance(a, b, limit=2):
    """Levenshtein distance, stopping early once it exceeds limit."""
    if abs(len(a) - len(b)) > limit:
        return limit + 1
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        if min(cur) > limit:
            return limit + 1
        prev = cur
    return prev[-1]
