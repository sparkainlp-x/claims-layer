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

Limits: this is a fixed phrase list. Paraphrases ("conclusively
demonstrates") and misspellings pass it. It is not negation-aware on
purpose: "not guaranteed" is refused too, which is the safe direction
(rephrase the disclaimer).
"""

import re

_R1_PATTERNS = [
    r"measured (on|in) (real|actual|field)",
    r"real[- ]world (data|results|measurements) (show|prove|confirm)",
    r"field (data|trial|test) (shows|proves|confirms)",
    r"patients (showed|improved|responded)",
]
_R3_PATTERNS = [
    r"\bproves\b", r"\bproven\b", r"guaranteed", r"100%\s*accurate",
    r"scientifically proven", r"miracle", r"revolutionary breakthrough",
    r"\bvalidated\b", r"production[- ]ready", r"quantum advantage",
    r"real[- ]world performance",
]


class FirewallViolation(Exception):
    pass


def screen_claim(claim):
    """Return the list of firewall violations for one claim ([] = clean)."""
    hits = []
    text = claim.text
    if claim.tag != "REPORTED":
        for pat in _R1_PATTERNS:
            if re.search(pat, text, flags=re.IGNORECASE):
                hits.append(f"R1 {claim.tag} claim asserts real measurement: /{pat}/")
    if claim.kind == "MEASUREMENT" and claim.tag == "UNRUN":
        hits.append("R2 MEASUREMENT claim tagged UNRUN")
    for pat in _R3_PATTERNS:
        if re.search(pat, text, flags=re.IGNORECASE):
            hits.append(f"R3 absolute overclaim phrase: /{pat}/")
    return hits


def screen_passport(claims):
    """All violations across a claim list, keyed by claim id."""
    out = {}
    for c in claims:
        v = screen_claim(c)
        if v:
            out[c.id] = v
    return out
