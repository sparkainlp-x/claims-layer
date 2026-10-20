"""Tests for claims_layer. Run: python tests.py (stdlib + numpy-free)."""

import hashlib
import json
import tempfile
from pathlib import Path

from claims_layer import (
    Claim,
    FirewallViolation,
    build_passport,
    claim_status,
)


def make_subject(tmp):
    d = Path(tmp)
    (d / "data.txt").write_text("alpha beta gamma", encoding="utf-8")
    digest = hashlib.sha256((d / "data.txt").read_bytes()).hexdigest()
    (d / "record.json").write_text(json.dumps({"run": {"score": 0.75, "label": "ok"}}),
                                   encoding="utf-8")
    return d, digest


def test_strong_checks_verify():
    with tempfile.TemporaryDirectory() as tmp:
        d, digest = make_subject(tmp)
        c = Claim("M1", "score is 0.75", "MEASUREMENT", "SYNTHETIC",
                  checks=[{"kind": "json_value", "path": "record.json",
                           "key": "run.score", "expected": 0.75, "tol": 1e-9},
                          {"kind": "file_sha256", "path": "data.txt", "sha256": digest}])
        status, results = claim_status(c, d)
        assert status == "VERIFIED" and all(r["ok"] for r in results)


def test_tampered_value_refuted_and_unsealed():
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = make_subject(tmp)
        c = Claim("M1", "score is 0.99", "MEASUREMENT", "SYNTHETIC",
                  checks=[{"kind": "json_value", "path": "record.json",
                           "key": "run.score", "expected": 0.99, "tol": 1e-9}])
        p = build_passport("t", "s", [c], d)
        assert p["claims"][0]["status"] == "REFUTED"
        assert p["sealed"] is False and p["unsealed_reasons"]


def test_weak_only_is_supported_not_verified():
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = make_subject(tmp)
        c = Claim("A1", "the data mentions beta", "ANNOUNCEMENT", "SYNTHETIC",
                  checks=[{"kind": "text_contains", "path": "data.txt", "needle": "beta"}])
        status, _ = claim_status(c, d)
        assert status == "SUPPORTED"


def test_no_checks_unverified_and_measurement_blocks_seal():
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = make_subject(tmp)
        h = Claim("H1", "it will scale", "HYPOTHESIS", "UNRUN")
        status, _ = claim_status(h, d)
        assert status == "UNVERIFIED"
        m = Claim("M1", "score is high", "MEASUREMENT", "SYNTHETIC")
        p = build_passport("t", "s", [m], d)
        assert p["sealed"] is False  # unverified MEASUREMENT cannot seal


def test_missing_file_check_fails_closed():
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = make_subject(tmp)
        c = Claim("M1", "ghost file", "MEASUREMENT", "SYNTHETIC",
                  checks=[{"kind": "file_sha256", "path": "nope.bin", "sha256": "0" * 64}])
        status, results = claim_status(c, d)
        assert status == "REFUTED" and results[0]["ok"] is False


def test_firewall_refusals():
    with tempfile.TemporaryDirectory() as tmp:
        d, _ = make_subject(tmp)
        bad1 = Claim("M1", "we measured on real patients", "MEASUREMENT", "SYNTHETIC")
        bad2 = Claim("A1", "this proves the method works", "ANNOUNCEMENT", "REPORTED")
        bad3 = Claim("M1", "a measurement", "MEASUREMENT", "UNRUN")
        for bad in (bad1, bad2, bad3):
            try:
                build_passport("t", "s", [bad], d)
                raise AssertionError(f"firewall missed {bad.id}")
            except FirewallViolation:
                pass


def test_seal_deterministic_and_sensitive():
    with tempfile.TemporaryDirectory() as tmp:
        d, digest = make_subject(tmp)

        def mk(expected):
            return Claim("M1", f"score is {expected}", "MEASUREMENT", "SYNTHETIC",
                         checks=[{"kind": "json_value", "path": "record.json",
                                  "key": "run.score", "expected": expected, "tol": 1e-9}])

        p1 = build_passport("t", "s", [mk(0.75)], d)
        p2 = build_passport("t", "s", [mk(0.75)], d)
        assert p1["seal_sha256"] == p2["seal_sha256"] and p1["sealed"]
        p3 = build_passport("t", "s", [mk(0.76)], d)
        assert p3["seal_sha256"] != p1["seal_sha256"] and not p3["sealed"]


if __name__ == "__main__":
    for name, fn in sorted(
        [(k, v) for k, v in globals().items() if k.startswith("test_")]
    ):
        fn()
        print(f"PASS {name}")
    print("all tests passed")
