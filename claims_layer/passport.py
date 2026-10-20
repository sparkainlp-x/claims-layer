"""Evidence passport for a set of claims: verify, seal, render.

Build procedure (fail-closed at every step):
  1. Screen all claims through the tag-consistency firewall.
     Any violation -> the passport is REFUSED (FirewallViolation).
  2. Run every claim's checks; assign each claim a status
     (VERIFIED / SUPPORTED / UNVERIFIED / REFUTED).
  3. Sealing rule: a passport may be SEALED only if no claim is
     REFUTED and every MEASUREMENT claim is VERIFIED. Otherwise it
     is issued UNSEALED with the reasons listed -- the document
     exists, but it does not carry the seal, and any reader (or
     platform) can see why at a glance.
     A claim whose text contains a number but is not VERIFIED also
     blocks the seal unless it is a HYPOTHESIS, so a number cannot dodge
     the rule by being labelled INFERENCE or ANNOUNCEMENT.
  4. The seal is SHA-256 over the canonical payload (title, subject,
     claims with statuses and check results, and the SHA-256 of every
     evidence file any check reads). No wall-clock time is included,
     so identical inputs give an identical seal. verify_passport()
     re-computes the seal and re-runs every check against the evidence.

The seal is an unkeyed hash, not a signature. It detects accidental or
careless change, but anyone who edits a passport can recompute it. Use
verify_passport() against the evidence, or sign the seal separately,
when the author may not be trusted.

What a seal does and does not mean -- printed on the passport itself:
it means every claim's stated checks were run and passed, and the
record has not changed since. It does NOT mean the underlying data
is true: a passport shows consistency and provenance, not ground
truth. Garbage data, honestly hashed, seals fine -- which is why
MEASUREMENT claims must trace to run records, and why the statuses
distinguish VERIFIED from merely SUPPORTED.
"""

import hashlib
import html
import json
import re

from .checks import claim_status, resolve_inside
from .firewall import FirewallViolation, screen_passport

PROTOCOL = "claims-layer/0.1.0"
_HAS_NUMBER = re.compile(r"\d")
SEAL_MEANING = (
    "Sealed: every claim's checks were run and passed, no claim is "
    "REFUTED, every MEASUREMENT claim and every non-hypothesis claim "
    "stating a number is VERIFIED. A seal shows consistency and "
    "provenance of this record, not the ground truth of the underlying "
    "data. It is an unkeyed hash, not a signature."
)


def build_passport(title, subject, claims, base_dir):
    """Verify claims and build the passport dict (sealed or not)."""
    violations = screen_passport(claims)
    if violations:
        raise FirewallViolation(f"claims firewall refused passport: {violations}")

    entries = []
    for c in claims:
        status, results = claim_status(c, base_dir)
        entries.append({**c.to_dict(), "status": status, "check_results": results})

    reasons = []
    for e in entries:
        if e["status"] == "REFUTED":
            reasons.append(f"{e['id']}: REFUTED")
        if e["kind"] == "MEASUREMENT" and e["status"] != "VERIFIED":
            reasons.append(f"{e['id']}: MEASUREMENT claim is {e['status']}, not VERIFIED")
        elif (e["kind"] != "HYPOTHESIS" and e["status"] not in ("VERIFIED", "REFUTED")
              and _HAS_NUMBER.search(e["text"])):
            reasons.append(f"{e['id']}: {e['kind']} claim states a number but is {e['status']}, not VERIFIED")
    sealed = not reasons

    payload = {
        "protocol": PROTOCOL,
        "title": title,
        "subject": subject,
        "claims": entries,
        "sealed": sealed,
        "unsealed_reasons": reasons,
        "evidence_sha256": _evidence_digests(claims, base_dir),
    }
    return {**payload, "seal_sha256": compute_seal(payload), "seal_meaning": SEAL_MEANING}


_SEALED_KEYS = ("protocol", "title", "subject", "claims", "sealed",
                "unsealed_reasons", "evidence_sha256")


def compute_seal(passport):
    """SHA-256 over the canonical sealed fields of a passport dict."""
    payload = {k: passport[k] for k in _SEALED_KEYS}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _evidence_digests(claims, base_dir):
    out = {}
    for c in claims:
        for chk in c.checks:
            rel = chk.get("path")
            if not isinstance(rel, str) or rel in out:
                continue
            try:
                out[rel] = hashlib.sha256(resolve_inside(base_dir, rel).read_bytes()).hexdigest()
            except Exception:
                out[rel] = None
    return out


def verify_passport(passport, base_dir):
    """Re-check a passport. Returns (ok, problems).

    1. The stored seal must match the sealed fields (detects edits made
       without recomputing the seal).
    2. Rebuilding the passport from its own claims against base_dir must
       reproduce the same seal (detects changed evidence files, and edits
       whose author recomputed the seal but not the check results).
    """
    from .model import Claim

    problems = []
    try:
        if compute_seal(passport) != passport.get("seal_sha256"):
            problems.append("seal does not match the passport contents")
        claims = [Claim(c["id"], c["text"], c["kind"], c["tag"], c.get("checks"), c.get("sources"))
                  for c in passport["claims"]]
        rebuilt = build_passport(passport["title"], passport["subject"], claims, base_dir)
        if rebuilt["seal_sha256"] != passport.get("seal_sha256"):
            for k in ("evidence_sha256", "claims", "sealed"):
                if rebuilt[k] != passport.get(k):
                    problems.append(f"re-run differs from passport in: {k}")
            if len(problems) == 0:
                problems.append("re-run seal differs")
    except Exception as exc:  # fail-closed
        problems.append(f"could not verify: {type(exc).__name__}: {exc}")
    return not problems, problems


def save_passport(passport, json_path, html_path=None):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(passport, f, indent=2, sort_keys=True)
    if html_path:
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(render_html(passport))


_STATUS_COLOR = {"VERIFIED": "#137333", "SUPPORTED": "#b06000",
                 "UNVERIFIED": "#5f6368", "REFUTED": "#a50e0e"}


def render_html(p):
    rows = []
    for c in p["claims"]:
        checks = "<br>".join(
            f"{'✓' if r['ok'] else '✗'} {html.escape(r['kind'])}: {html.escape(r['detail'])}"
            for r in c["check_results"]
        ) or "—"
        rows.append(
            f"<tr><td><b>{html.escape(c['id'])}</b></td>"
            f"<td>{html.escape(c['text'])}</td>"
            f"<td>{html.escape(c['kind'])}<br><small>{html.escape(c['tag'])}</small></td>"
            f"<td style='color:{_STATUS_COLOR[c['status']]}'><b>{c['status']}</b></td>"
            f"<td><small>{checks}</small></td></tr>"
        )
    seal_badge = ("SEALED" if p["sealed"] else "UNSEALED") + \
        f" — sha256 {p['seal_sha256'][:16]}…"
    reasons = "".join(f"<li>{html.escape(r)}</li>" for r in p["unsealed_reasons"])
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8">
<title>{html.escape(p['title'])} — Claims Passport</title>
<style>body{{font-family:system-ui,sans-serif;max-width:1000px;margin:2rem auto;padding:0 1rem}}
table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:.45rem;vertical-align:top}}
.badge{{display:inline-block;padding:.3rem .7rem;border:1px solid #333;border-radius:4px;font-weight:600}}
small{{color:#555}}</style></head><body>
<h1>{html.escape(p['title'])}</h1>
<p><b>Subject:</b> {html.escape(p['subject'])}</p>
<p><span class="badge">{seal_badge}</span></p>
{'<p><b>Unsealed because:</b></p><ul>' + reasons + '</ul>' if reasons else ''}
<table><tr><th>ID</th><th>Claim</th><th>Kind / Tag</th><th>Status</th><th>Checks</th></tr>
{''.join(rows)}</table>
<p><small>{html.escape(p['seal_meaning'])}</small></p>
<p><small>Protocol {html.escape(p['protocol'])} — Claims Layer (AGPL-3.0). Statuses are
assigned by machine-run checks, never by the claim's author.</small></p>
</body></html>"""
