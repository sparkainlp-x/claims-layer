"""Tag-consistency firewall (pattern from spark-iis-api).

The claims firewall refuses claim/tag combinations that lie about
their own evidence, and claim text that overclaims in absolute
terms. It screens the passport at build time; a violation means the
passport is NOT built -- refused, not edited.

Rules:
  R1  A claim not tagged REPORTED may not assert a real-world measurement
      ("measured on real patients", "field data shows", ...).
  R2  A MEASUREMENT claim may not carry the UNRUN tag (a measurement
      that was never run is not a measurement).
  R3  Absolute overclaim phrases ("proves", "guaranteed",
      "100% accurate", "scientifically proven", "miracle") are
      refused in any claim, whatever its tag: the layer exists so
      that claims earn their strength from checks, not adverbs.
      The list also holds the org's banned terms (validated,
      production-ready, quantum advantage, real-world performance).

v0.2.0 detection (R3): text is normalised (normalize.py), then refused
for strong claim verbs in any inflection (prove, guarantee, validate),
their misspellings (edit distance 1, or 2 for long words, with an
allowlist of real words such as "probes"), weak verbs next to an
intensifier ("conclusively demonstrates", "definitively confirmed"),
certainty phrases ("beyond doubt", "no doubt", "settled science") and
banned compounds ("production ready", "quantum advantage", "real-world
performance"). A single negator in the three tokens before a match, in
the same clause, exempts it ("does not prove"), except "not only/just",
double negatives and certainty phrases. In doubt, it refuses.

Limits: this is still a word list. Sentences that assert certainty
without these words ("the effect is beyond question", "it works,
period") pass. Measured rates are in the README.
"""

import re

_R1_PATTERNS = [
    r"measured (on|in) (real|actual|field)",
    r"real[- ]world (data|results|measurements) (show|prove|confirm)",
    r"field (data|trial|test) (shows|proves|confirms)",
    r"patients (showed|improved|responded)",
]
from .normalize import clauses, edit_distance

# --- R3: overclaim detection (v0.2.0) ------------------------------------
# Strong claim verbs: refused on their own (unless negated in-clause).
_STRONG = re.compile(
    r"^(prove|proves|proved|proven|proving|guarantee|guarantees|guaranteed|guaranteeing|"
    r"validate|validates|validated|validating|validation)$")
# Weak verbs/nouns: refused only next to an intensifier.
_WEAK = re.compile(r"^(demonstrat\w*|establish\w*|confirm\w*|show\w*|settle\w*|proof|proofs|shown)$")
_INTENSIFIER = re.compile(
    r"^(conclusive\w*|definitive\w*|unequivocal\w*|clearly|irrefutabl\w*|undeniabl\w*|"
    r"indisputabl\w*|unquestionabl\w*|decisive\w*|categorical\w*|absolute\w*|certainly|"
    r"scientifically|clinically|extensively|incontrovertibl\w*|undoubtedly)$")
# Phrases refused regardless of negation (they are certainty claims).
_PHRASES = [
    r"\bbeyond (any |a |all |reasonable )?doubt\b", r"\bno doubt\b", r"\bno room for doubt\b",
    r"\bwithout (a |any )?doubt\b", r"\bcannot be (disproven|disproved|denied|refuted)\b",
    r"\b(nobody|no one) can deny\b", r"\bsettled science\b", r"\bsettles the question\b",
    r"\bonce and for all\b", r"\bit is certain\b", r"\b100% (accurate|certain|reliable|correct)\b",
    r"\bmiracle (of|cure|drug|cures)\b", r"\b(a|is|truly) miracle\b", r"\brevolutionary breakthrough\b",
    r"\b(undeniabl|irrefutabl|indisputabl|incontrovertibl)\w*",
]
# Compounds matched across 1-3 adjacent tokens with spaces/hyphens removed.
_COMPOUNDS = {"productionready", "quantumadvantage", "quantumsupremacy", "realworldperformance"}
# Misspelling targets (edit distance) and real words that must not match.
_FUZZY = ("proven", "proves", "proved", "guaranteed", "guarantee", "guarantees",
          "validated", "validation", "validates", "validate")
_ALLOW = {"probes", "probed", "prover", "provers", "proper", "provide", "provided", "provides",
          "provence", "improves", "approved", "valiant", "validity", "probing", "proving"}
_NEGATORS = {"not", "no", "never", "nothing", "cannot", "cant", "dont", "doesnt", "isnt", "arent",
             "wasnt", "werent", "wont", "didnt", "hasnt", "havent", "nor", "neither", "without"}
_NOT_NEGATING = {"only", "just", "merely", "simply"}
_NEG_WINDOW = 3


def _negated(toks, i):
    """Conservative clause-scoped negation: exactly one negator within the
    3 tokens before position i, not followed by 'only'/'just'/... ("not
    only proves" is a claim). Two negators ("never not guaranteed") count
    as no negation, i.e. the phrase is refused."""
    window = [j for j in range(max(0, i - _NEG_WINDOW), i) if toks[j] in _NEGATORS]
    if len(window) != 1:
        return False
    for j in window:
        if toks[j] in _NEGATORS:
            nxt = toks[j + 1] if j + 1 < len(toks) else ""
            if nxt in _NOT_NEGATING:
                return False
            return True
    return False


def _negative_prefix(tok):
    return any(tok.startswith(p) and _STRONG.match(tok[len(p):]) for p in ("un", "in", "dis"))


def _is_strong(tok):
    if _STRONG.match(tok):
        return True
    if len(tok) < 5 or tok in _ALLOW or _negative_prefix(tok):
        return False
    limit = 1 if len(tok) < 9 else 2
    return any(edit_distance(tok, f, limit) <= limit for f in _FUZZY)


def overclaims(text):
    """Return a list of R3 reasons for text ([] = clean)."""
    hits = []
    for toks in clauses(text):
        joined = " ".join(toks)
        for pat in _PHRASES:
            if re.search(pat, joined):
                hits.append(f"certainty phrase /{pat}/")
        for i, tok in enumerate(toks):
            for n in (1, 2, 3):
                if "".join(toks[i:i + n]) in _COMPOUNDS and not _negated(toks, i):
                    hits.append(f"banned term '{' '.join(toks[i:i + n])}'")
            if _is_strong(tok) and not _negated(toks, i):
                hits.append(f"claim verb '{tok}'")
            if _negative_prefix(tok) and _negated(toks, i):
                hits.append(f"double negation '{tok}'")
            if _WEAK.match(tok):
                near = toks[max(0, i - 2):i] + toks[i + 1:i + 3]
                if any(_INTENSIFIER.match(x) for x in near) and not _negated(toks, max(0, i - 2)):
                    hits.append(f"intensified claim '{tok}'")
            if _INTENSIFIER.match(tok) and i + 1 < len(toks) and _is_strong(toks[i + 1]):
                hits.append(f"intensified claim '{tok} {toks[i + 1]}'")
    return sorted(set(hits))


class FirewallViolation(Exception):
    pass


def screen_claim(claim):
    """Return the list of firewall violations for one claim ([] = clean)."""
    hits = []
    text = claim.text
    if claim.tag != "REPORTED":
        flat = " ".join(" ".join(c) for c in clauses(text))
        for pat in _R1_PATTERNS:
            if re.search(pat, text, flags=re.IGNORECASE) or re.search(pat.replace("[- ]", "[- ]?"), flat):
                hits.append(f"R1 {claim.tag} claim asserts real measurement: /{pat}/")
    if claim.kind == "MEASUREMENT" and claim.tag == "UNRUN":
        hits.append("R2 MEASUREMENT claim tagged UNRUN")
    for reason in overclaims(text):
        hits.append(f"R3 {reason}")
    return hits


def screen_passport(claims):
    """All violations across a claim list, keyed by claim id."""
    out = {}
    for c in claims:
        v = screen_claim(c)
        if v:
            out[c.id] = v
    return out
