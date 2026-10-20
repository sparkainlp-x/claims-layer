"""Machine-runnable claim checks.

Three check kinds, in descending strength:

STRONG
  file_sha256  {path, sha256}
      The cited file's SHA-256 must equal the recorded digest.
      Proves the evidence is exactly what the claim cites --
      provenance and integrity.
  json_value   {path, key, expected, tol?}
      A value inside a JSON document (dotted key path) must equal
      `expected` -- numerically within `tol` when both are numbers,
      exactly otherwise. This is the recompute-the-claim pattern:
      the passport's number must match the run record's number.

WEAK
  text_contains {path, needle}
      The cited text must contain the needle. Proves only that a
      source mentions it -- citation support, not truth. A claim
      backed only by weak checks can reach SUPPORTED, never VERIFIED.

Every check returns {kind, strength, ok, detail}. A check that
cannot run (missing file, missing key) returns ok=False with the
reason: fail-closed, an unrunnable check is a failed check.
"""

import hashlib
import json
from pathlib import Path

STRENGTH = {"file_sha256": "strong", "json_value": "strong",
            "text_contains": "weak"}


def _result(check, ok, detail):
    return {
        "kind": check["kind"],
        "strength": STRENGTH.get(check["kind"], "weak"),
        "ok": bool(ok),
        "detail": detail,
    }


def run_check(check, base_dir):
    base = Path(base_dir)
    kind = check.get("kind")
    try:
        if kind == "file_sha256":
            path = base / check["path"]
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            ok = digest == check["sha256"]
            return _result(check, ok,
                           f"sha256 {digest[:12]}... "
                           f"{'==' if ok else '!='} recorded {check['sha256'][:12]}...")
        if kind == "json_value":
            data = json.loads((base / check["path"]).read_text(encoding="utf-8"))
            node = data
            for part in check["key"].split("."):
                node = node[part]
            expected = check["expected"]
            if isinstance(node, (int, float)) and isinstance(expected, (int, float)):
                tol = float(check.get("tol", 0.0))
                ok = abs(float(node) - float(expected)) <= tol
                return _result(check, ok,
                               f"{check['key']} = {node} vs expected {expected} (tol {tol})")
            ok = node == expected
            return _result(check, ok,
                           f"{check['key']} = {node!r} vs expected {expected!r}")
        if kind == "text_contains":
            text = (base / check["path"]).read_text(encoding="utf-8")
            ok = check["needle"] in text
            return _result(check, ok,
                           f"needle {'found' if ok else 'NOT found'} in {check['path']}")
        return _result(check, False, f"unknown check kind: {kind}")
    except Exception as exc:  # fail-closed: unrunnable == failed
        return _result(check, False, f"check could not run: {type(exc).__name__}: {exc}")


def claim_status(claim, base_dir):
    """Run a claim's checks; return (status, check_results)."""
    if not claim.checks:
        return "UNVERIFIED", []
    results = [run_check(c, base_dir) for c in claim.checks]
    if any(not r["ok"] for r in results):
        return "REFUTED", results
    if any(r["strength"] == "strong" for r in results):
        return "VERIFIED", results
    return "SUPPORTED", results
