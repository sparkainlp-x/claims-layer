"""Self-contained demo: a claims passport over a synthetic experiment.

Builds a tiny seeded dataset + run record, issues claims about it,
and lets the checks assign the statuses. Then issues a second
passport containing one TAMPERED claim (a mean that does not match
the run record) to show the fail-closed seal: the claim is REFUTED
and the passport is issued UNSEALED, with the reason printed on it.

Run:  python demo.py
"""

import hashlib
import json
import shutil
from pathlib import Path

import random
import statistics

from claims_layer import Claim, build_passport, save_passport, verify_passport

HERE = Path(__file__).parent
SUBJ = HERE / "demo_subject"


def build_subject():
    if SUBJ.exists():
        shutil.rmtree(SUBJ)
    SUBJ.mkdir()
    rng = random.Random(11)
    data = [rng.gauss(2.50, 0.40) for _ in range(200)]
    csv = SUBJ / "sensor_data.csv"
    csv.write_text("\n".join(f"{v:.6f}" for v in data), encoding="utf-8")
    record = {
        "experiment": "synthetic sensor characterisation",
        "n": len(data),
        "mean": statistics.fmean(data),
        "std": statistics.pstdev(data),
        "data_sha256": hashlib.sha256(csv.read_bytes()).hexdigest(),
    }
    (SUBJ / "run_record.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    (SUBJ / "notes.txt").write_text(
        "Lab note: the full dataset and run record are archived with this passport.\n",
        encoding="utf-8")
    return record


def show(title, passport):
    print(f"--- {title} ---")
    for c in passport["claims"]:
        print(f"  {c['id']:<4} {c['status']:<11} [{c['kind']}/{c['tag']}] {c['text']}")
    print(f"  sealed: {passport['sealed']}  seal: {passport['seal_sha256'][:16]}...")
    for r in passport["unsealed_reasons"]:
        print(f"  unsealed because: {r}")
    print()


def main():
    rec = build_subject()
    mean = rec["mean"]

    good = [
        Claim("M1", f"Dataset mean is {mean:.4f} (seeded synthetic sensor data)",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "json_value", "path": "run_record.json",
                       "key": "mean", "expected": round(mean, 4), "tol": 1e-3}]),
        Claim("M2", "Dataset file matches the digest recorded at run time",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "file_sha256", "path": "sensor_data.csv",
                       "sha256": rec["data_sha256"]}]),
        Claim("A1", "The full dataset and run record are archived with this passport",
              "ANNOUNCEMENT", "SYNTHETIC",
              checks=[{"kind": "text_contains", "path": "notes.txt",
                       "needle": "archived with this passport"}]),
        Claim("H1", "The sensor drift will stay below 1% over 30 days",
              "HYPOTHESIS", "UNRUN"),
    ]
    p1 = build_passport("Synthetic sensor experiment", "demo_subject", good, SUBJ)
    show("Passport 1 — honest claims", p1)
    save_passport(p1, HERE / "passport_demo.json", HERE / "passport_demo.html")

    tampered = [
        Claim("M1", f"Dataset mean is {mean + 0.5:.4f} (seeded synthetic sensor data)",
              "MEASUREMENT", "SYNTHETIC",
              checks=[{"kind": "json_value", "path": "run_record.json",
                       "key": "mean", "expected": round(mean + 0.5, 4), "tol": 1e-3}]),
    ]
    p2 = build_passport("Synthetic sensor experiment (tampered claim)",
                        "demo_subject", tampered, SUBJ)
    show("Passport 2 — one inflated number", p2)

    ok1, _ = verify_passport(p1, SUBJ)
    print(f"--- Re-verify passport 1 against the evidence: {ok1}")
    edited = json.loads(json.dumps(p1))
    edited["claims"][0]["text"] = edited["claims"][0]["text"].replace("Dataset mean", "Mean")
    ok_edit, why_edit = verify_passport(edited, SUBJ)
    print(f"--- Passport 1 with an edited claim, seal not recomputed: {ok_edit} {why_edit}")
    csv = SUBJ / "sensor_data.csv"
    original = csv.read_bytes()
    csv.write_bytes(original + b"\n9.999999")
    ok_file, why_file = verify_passport(p1, SUBJ)
    csv.write_bytes(original)
    print(f"--- Passport 1 after one value is appended to the data file: {ok_file} {why_file}")
    print()

    ok = (p1["sealed"] and not p2["sealed"]
          and p2["claims"][0]["status"] == "REFUTED"
          and ok1 and not ok_edit and not ok_file)
    print("RESULT:", "PASS -- honest passport SEALED, tampered passport REFUTED and UNSEALED"
          if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
