"""Claim model: kinds, evidence tags, verification statuses.

Claim kinds (taxonomy from quantum-claims-passport -- most public
confusion comes from kinds being silently swapped: an announcement
quoted as if it were a measurement, a hypothesis as if it were a
result):

    ANNOUNCEMENT  someone said they will do / did something
    MODEL         output of a model or simulation
    MEASUREMENT   a number obtained from data by a stated method
    HYPOTHESIS    a proposed explanation, not yet tested
    INFERENCE     a conclusion drawn from other claims

Evidence tags (org-wide convention): SYNTHETIC, REPORTED, TARGET,
UNRUN. A claim's tag says what kind of evidence stands behind it;
the firewall (firewall.py) refuses combinations that lie -- e.g. a
SYNTHETIC claim whose text asserts a real-world measurement.

Verification statuses (assigned by checks, never by the author):

    VERIFIED    at least one strong check passed, none failed
    SUPPORTED   only weak checks (e.g. textual citation) passed
    UNVERIFIED  no checks attached, or checks could not run
    REFUTED     at least one check failed
"""

KINDS = ("ANNOUNCEMENT", "MODEL", "MEASUREMENT", "HYPOTHESIS", "INFERENCE")
TAGS = ("SYNTHETIC", "REPORTED", "TARGET", "UNRUN")
STATUSES = ("VERIFIED", "SUPPORTED", "UNVERIFIED", "REFUTED")


class Claim:
    """One claim, its kind, its evidence tag, and its checks.

    A check is a dict describing a machine-runnable verification
    (see checks.py). The author proposes; the checks dispose.
    """

    def __init__(self, claim_id, text, kind, tag, checks=None, sources=None):
        if kind not in KINDS:
            raise ValueError(f"unknown claim kind: {kind}")
        if tag not in TAGS:
            raise ValueError(f"unknown evidence tag: {tag}")
        self.id = claim_id
        self.text = text
        self.kind = kind
        self.tag = tag
        self.checks = checks or []
        self.sources = sources or []

    def to_dict(self):
        return {
            "id": self.id,
            "text": self.text,
            "kind": self.kind,
            "tag": self.tag,
            "checks": self.checks,
            "sources": self.sources,
        }
