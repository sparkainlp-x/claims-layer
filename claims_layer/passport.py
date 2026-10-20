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
  4. The seal is SHA-256 over the canonical payload (title, subject,
     claims with statuses and check results). No wall-clock time is
     included: identical inputs give an identical seal, so a seal
     can be re-checked by anyone, forever.

What a seal does and does not mean -- printed on the passport itself:
it means every claim's stated checks were run and passed, and the
record has not changed since. It does NOT mean the underlying data
is true: a passport proves consistency and provenance, not ground
truth. Garbage data, honestly hashed, seals fine -- which is why
MEASUREMENT claims must trace to run records, and why the statuses
distinguish VERIFIED from merely SUPPORTED.
"""

import hashlib
import html
import json

from .checks import claim_status
from .firewall import FirewallViolation, screen_passport

PROTOCOL = "claims-layer/0.1.0"
SEAL_MEANING = (
    "Sealed: every claim's checks were run and passed, no claim is "
    "REFUTED, and every MEASUREMENT claim is VERIFIED. A seal proves "
    "consistency and provenance of this record -- not the ground "
    "truth of the underlying data."
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
    sealed = not reasons

    payload = {
        "protocol": PROTOCOL,
        "title": title,
        "subject": subject,
        "claims": entries,
        "sealed": sealed,
        "unsealed_reasons": reasons,
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    seal = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {**payload, "seal_sha256": seal, "seal_meaning": SEAL_MEANING}


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
            f"<td>{c['kind']}<br><small>{c['tag']}</small></td>"
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
<p><small>Protocol {p['protocol']} — Claims Layer (AGPL-3.0). Statuses are
assigned by machine-run checks, never by the claim's author.</small></p>
</body></html>"""
