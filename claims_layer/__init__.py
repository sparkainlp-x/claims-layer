"""Claims Layer: machine-checkable evidence passports for claims.

A small, standard-library reference implementation: any consequential claim
-- a study result, a product spec, an AI summary, a benchmark number
-- ships with a passport that states what kind of claim it is
(announcement / model / measurement / hypothesis / inference), what
evidence stands behind it (SYNTHETIC / REPORTED / TARGET / UNRUN),
and which machine-runnable checks were run against it, with the
results. Statuses (VERIFIED / SUPPORTED / UNVERIFIED / REFUTED) are
computed by running the checks, not typed in by the author (who does
still write the checks). A passport seals only
when nothing is refuted and every measurement is verified.

Combined from the sparkainlp-x portfolio: the claim-kind taxonomy of
quantum-claims-passport, the manifest passport of evidence-passport,
the recompute-before-display verifier of sparkholo-coherence-agent,
the claims firewall of spark-iis-api, and the hash-sealing of
measurement-trail.

Honest boundary: a passport shows consistency and provenance --
that the claims match their cited records and the record is
unchanged. It does not prove the underlying data is true.
"""

from .model import Claim
from .checks import claim_status, run_check
from .firewall import FirewallViolation, screen_claim, screen_passport
from .passport import (
    build_passport,
    compute_hmac,
    compute_seal,
    key_from_env,
    key_id,
    render_html,
    save_passport,
    verify_passport,
)

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
    "compute_seal",
    "verify_passport",
    "compute_hmac",
    "key_from_env",
    "key_id",
]

__version__ = "0.1.0"
