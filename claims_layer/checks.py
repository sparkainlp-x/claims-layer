"""Machine-runnable claim checks.

Three check kinds, in descending strength:

STRONG
  file_sha256  {path, sha256}
      The cited file's SHA-256 must equal the recorded digest.
      Shows the evidence is byte-identical to what the claim cites
      (integrity since the digest was taken).
  json_value   {path, key, expected, tol?}
      A value inside a JSON document (dotted key path) must equal
      `expected` -- numerically within `tol` when both are numbers,
      exactly otherwise. This is the recompute-the-claim pattern:
      the passport's number must match the run record's number.

WEAK
  text_contains {path, needle}
      The cited text must contain the needle. Shows only that a
      source mentions it -- citation support, not truth. A claim
      backed only by weak checks can reach SUPPORTED, never VERIFIED.

Every check returns {kind, strength, ok, detail}. A check that
cannot run (missing file, missing key) returns ok=False with the
reason: fail-closed, an unrunnable check is a failed check.

Hardening (v0.1.0 review):
- Paths must be relative and stay inside base_dir; absolute paths and
  "../" escapes fail.
- json_value tolerance must be finite, >= 0 and at most
  max(1% of |expected|, 1e-9). A looser tolerance fails the check, so a
  wide tol cannot turn any number into a pass.
- Booleans are compared as booleans: True no longer equals 1.
- For a numeric json_value check, the claim TEXT must contain a number
  that matches the checked value (within tol plus its own rounding).
  Otherwise the claim is REFUTED: the check would verify a different
  number from the one the reader sees.

What checks cannot do: the author still writes the checks and the
expected values. A file_sha256 digest taken by the author from the same
file only shows the file has not changed since, not who made it.
"""

import hashlib
import json
import math
import re
from pathlib import Path

MAX_REL_TOL = 0.01
MIN_ABS_TOL = 1e-9
_NUMBER = re.compile(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?")


def resolve_inside(base_dir, rel):
    """Resolve rel under base_dir; raise ValueError if it escapes."""
    rel_path = Path(rel)
    if rel_path.is_absolute():
        raise ValueError(f"absolute path not allowed: {rel}")
    base = Path(base_dir).resolve()
    target = (base / rel_path).resolve()
    if target != base and base not in target.parents:
        raise ValueError(f"path escapes base_dir: {rel}")
    return target


def _is_number(x):
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def lookup(data, key):
    node = data
    for part in key.split("."):
        node = node[part]
    return node

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
    kind = check.get("kind")
    try:
        if kind == "file_sha256":
            path = resolve_inside(base_dir, check["path"])
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            ok = digest == check["sha256"]
            return _result(check, ok,
                           f"sha256 {digest[:12]}... "
                           f"{'==' if ok else '!='} recorded {str(check['sha256'])[:12]}...")
        if kind == "json_value":
            path = resolve_inside(base_dir, check["path"])
            node = lookup(json.loads(path.read_text(encoding="utf-8")), check["key"])
            expected = check["expected"]
            if _is_number(node) and _is_number(expected):
                tol = float(check.get("tol", 0.0))
                limit = max(MAX_REL_TOL * abs(float(expected)), MIN_ABS_TOL)
                if not math.isfinite(tol) or tol < 0 or tol > limit:
                    return _result(check, False, f"tolerance {tol} not allowed (must be 0..{limit:g})")
                ok = math.isfinite(float(node)) and abs(float(node) - float(expected)) <= tol
                return _result(check, ok,
                               f"{check['key']} = {node} vs expected {expected} (tol {tol})")
            ok = type(node) is type(expected) and node == expected
            return _result(check, ok,
                           f"{check['key']} = {node!r} vs expected {expected!r}")
        if kind == "text_contains":
            path = resolve_inside(base_dir, check["path"])
            text = path.read_text(encoding="utf-8")
            ok = isinstance(check["needle"], str) and bool(check["needle"]) and check["needle"] in text
            return _result(check, ok,
                           f"needle {'found' if ok else 'NOT found'} in {check['path']}")
        return _result(check, False, f"unknown check kind: {kind}")
    except Exception as exc:  # fail-closed: unrunnable == failed
        return _result(check, False, f"check could not run: {type(exc).__name__}: {exc}")


def _text_binds(text, value, tol):
    """True if text contains a number matching value within tol + rounding."""
    for m in _NUMBER.finditer(text):
        tok = m.group(0)
        decimals = len(tok.split(".")[1].split("e")[0].split("E")[0]) if "." in tok else 0
        if abs(float(tok) - float(value)) <= tol + 0.5 * 10 ** (-decimals) + 1e-12:
            return True
    return False


def text_binding(claim, base_dir):
    """Results tying numbers in claim text to numeric json_value checks."""
    out = []
    for c in claim.checks:
        if c.get("kind") != "json_value" or not _is_number(c.get("expected")):
            continue
        try:
            path = resolve_inside(base_dir, c["path"])
            node = lookup(json.loads(path.read_text(encoding="utf-8")), c["key"])
        except Exception:
            continue  # the check itself already fails closed
        if not _is_number(node):
            continue
        ok = _text_binds(claim.text, node, float(c.get("tol", 0.0)))
        out.append({"kind": "text_binding", "strength": "strong", "ok": ok,
                    "detail": f"claim text {'contains' if ok else 'does NOT contain'} "
                              f"the checked value {c['key']} = {node}"})
    return out


def claim_status(claim, base_dir):
    """Run a claim's checks; return (status, check_results)."""
    if not claim.checks:
        return "UNVERIFIED", []
    results = [run_check(c, base_dir) for c in claim.checks]
    results += text_binding(claim, base_dir)
    if any(not r["ok"] for r in results):
        return "REFUTED", results
    if any(r["strength"] == "strong" for r in results):
        return "VERIFIED", results
    return "SUPPORTED", results
