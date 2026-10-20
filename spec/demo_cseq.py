"""Showcase demo: a claims passport over the Coherent Sequence Wave
Computer's actual v0.2.0 run record.

Runs the sibling project's verified demo (seed 7) to produce a fresh
evidence passport, then issues claims about it through the claims
layer. The wave computer's own numbers are re-checked against its
run record by an independent tool — the claims layer verifying the
verifier.

Requires: ../digital-to-wave-cseq (override with CSEQ_DIR).
Run:  python demo_cseq.py
"""

import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from claims_layer import Claim, build_passport, save_passport

HERE = Path(__file__).parent
CSEQ = Path(os.environ.get("CSEQ_DIR", HERE.parent / "digital-to-wave-cseq"))


def main():
    if not (CSEQ / "demo_verified.py").exists():
        print(f"cseq_wave project not found at {CSEQ} (set CSEQ_DIR)")
        return 1

    subj = Path(tempfile.mkdtemp(prefix="cseq_subject_"))
    env = {**os.environ, "PYTHONPATH": str(CSEQ)}
    subprocess.run(
        [sys.executable, "demo_verified.py", "--seed", "7",
         "--out", str(subj / "run_passport.json")],
        cwd=CSEQ, env=env, check=True, capture_output=True, text=True)
    shutil.copy2(CSEQ / "README.md", subj / "README.md")
    shutil.copy2(CSEQ / "demo_verified.py", subj / "demo_verified.py")
    demo_hash = hashlib.sha256((subj / "demo_verified.py").read_bytes()).hexdigest()
    rec = json.loads((subj / "run_passport.json").read_text())
    m = rec["metrics"]

    claims = [
        Claim("M1", "Main trial (decohered stored pattern, seed 7) received verdict VERIFIED_RECALL",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "json_value", "path": "run_passport.json",
                       "key": "metrics.main_verdict", "expected": "VERIFIED_RECALL"}]),
        Claim("M2", "Never-stored control cue (seed 7) received verdict CONFABULATION_SUSPECTED",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "json_value", "path": "run_passport.json",
                       "key": "metrics.control_verdict", "expected": "CONFABULATION_SUSPECTED"}]),
        Claim("M3", f"Main trial fidelity C_seq is {m['main_fidelity_cseq']}",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "json_value", "path": "run_passport.json",
                       "key": "metrics.main_fidelity_cseq",
                       "expected": m["main_fidelity_cseq"], "tol": 1e-9}]),
        Claim("M4", "The verified demo script is byte-identical to the released v0.2.0 file",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "file_sha256", "path": "demo_verified.py",
                       "sha256": demo_hash}]),
        Claim("I1", "Energy detection alone cannot establish recall provenance; the calibrated cue gate is the separator",
              "INFERENCE", "SYNTHETIC",
              checks=[{"kind": "text_contains", "path": "README.md",
                       "needle": "Energy is not"}]),
        Claim("H1", "The cue gate will separate true from never-stored cues at other codebook sizes and pattern counts",
              "HYPOTHESIS", "UNRUN"),
    ]
    p = build_passport("Claims passport — Coherent Sequence Wave Computer v0.2.0",
                       "cseq_wave verified demo, seed 7", claims, subj)
    for c in p["claims"]:
        print(f"  {c['id']:<4} {c['status']:<11} [{c['kind']}/{c['tag']}] {c['text']}")
    print(f"  sealed: {p['sealed']}  seal: {p['seal_sha256'][:16]}...")
    for r in p["unsealed_reasons"]:
        print(f"  unsealed because: {r}")
    save_passport(p, HERE / "passport_cseq.json", HERE / "passport_cseq.html")
    print("RESULT:", "PASS" if p["sealed"] else "FAIL")
    return 0 if p["sealed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
