"""Claims Layer: machine-checkable evidence passports for claims.

The missing layer under public information: any consequential claim
-- a study result, a product spec, an AI summary, a benchmark number
-- ships with a passport that states what kind of claim it is
(announcement / model / measurement / hypothesis / inference), what
evidence stands behind it (SYNTHETIC / REPORTED / TARGET / UNRUN),
and which machine-runnable checks were run against it, with the
results. Statuses (VERIFIED / SUPPORTED / UNVERIFIED / REFUTED) are
assigned by the checks, never by the author. A passport seals only
when nothing is refuted and every measurement is verified.

Combined from the sparkainlp-x portfolio: the claim-kind taxonomy of
quantum-claims-passport, the manifest passport of evidence-passport,
the recompute-before-display verifier of sparkholo-coherence-agent,
the claims firewall of spark-iis-api, and the hash-sealing of
measurement-trail.

Honest boundary: a passport proves consistency and provenance --
that the claims match their cited records and the record is
unchanged. It does not prove the underlying data is true.
"""

from .model import Claim
from .checks import claim_status, run_check
from .firewall import FirewallViolation, screen_claim, screen_passport
from .passport import build_passport, render_html, save_passport

__all__ = [
    "Claim",
    "claim_status",
    "run_check",
    "screen_claim",
    "screen_passport",
    "FirewallViolation",
    "build_passport",
    "render_html",
    "save_passport",
]

__version__ = "0.1.0"
