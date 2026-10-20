import hashlib
import json

import pytest

from claims_layer import (
    Claim,
    build_passport,
    compute_hmac,
    compute_seal,
    key_from_env,
    key_id,
    render_html,
    verify_passport,
)

KEY = b"k" * 32
OTHER = b"o" * 32


@pytest.fixture
def subj(tmp_path):
    (tmp_path / "record.json").write_text(json.dumps({"run": {"score": 0.75}}), encoding="utf-8")
    return tmp_path


def claims():
    return [Claim("m", "score is 0.75", "MEASUREMENT", "SYNTHETIC",
                  [{"kind": "json_value", "path": "record.json", "key": "run.score", "expected": 0.75}])]


def test_keyed_passport_fields_and_no_key_leak(subj):
    p = build_passport("t", "s", claims(), subj, key=KEY)
    assert p["seal_type"] == "hmac-sha256" and p["key_id"] == key_id(KEY)
    assert len(p["key_id"]) == 16 and p["key_id"] not in KEY.hex()
    blob = json.dumps(p)
    assert KEY.decode() not in blob and KEY.hex() not in blob
    assert p["key_id"] in render_html(p)
    assert verify_passport(p, subj, key=KEY) == (True, [])


def test_unkeyed_mode_unchanged(subj):
    p = build_passport("t", "s", claims(), subj)
    assert p["seal_type"] == "sha256" and p["key_id"] is None and "seal_hmac_sha256" not in p
    assert verify_passport(p, subj) == (True, [])


def test_v010_passports_still_verify(subj):
    p = build_passport("t", "s", claims(), subj, protocol="claims-layer/0.1.0")
    assert "seal_type" not in p
    assert verify_passport(p, subj) == (True, [])


def test_full_rewrite_without_key_is_caught(subj):
    p = build_passport("t", "s", claims(), subj, key=KEY)
    # attacker rewrites the evidence AND the claim consistently, then
    # recomputes the unkeyed seal; without the key they cannot redo the HMAC
    (subj / "record.json").write_text(json.dumps({"run": {"score": 0.99}}), encoding="utf-8")
    forged = build_passport("t", "s", [Claim("m", "score is 0.99", "MEASUREMENT", "SYNTHETIC",
                            [{"kind": "json_value", "path": "record.json", "key": "run.score", "expected": 0.99}])],
                            subj, key=OTHER)
    forged["key_id"] = p["key_id"]
    forged["seal_sha256"] = compute_seal(forged)
    ok, problems = verify_passport(forged, subj, key=KEY)
    assert not ok and any("keyed seal" in x for x in problems)
    # unkeyed checks alone would have accepted a consistent rewrite
    plain = build_passport("t", "s", [Claim("m", "score is 0.99", "MEASUREMENT", "SYNTHETIC",
                           [{"kind": "json_value", "path": "record.json", "key": "run.score", "expected": 0.99}])], subj)
    assert verify_passport(plain, subj)[0]


def test_downgrade_and_wrong_key_refused(subj):
    p = build_passport("t", "s", claims(), subj, key=KEY)
    assert not verify_passport(p, subj)[0]  # keyed passport, no key
    assert any("key_id" in x for x in verify_passport(p, subj, key=OTHER)[1])
    stripped = {k: v for k, v in p.items() if k != "seal_hmac_sha256"}
    stripped["seal_type"], stripped["key_id"] = "sha256", None
    stripped["seal_sha256"] = compute_seal(stripped)
    assert verify_passport(stripped, subj)[0]          # fine as an unkeyed passport...
    assert not verify_passport(stripped, subj, key=KEY)[0]  # ...but not when the key is expected


def test_key_rules(subj, monkeypatch):
    with pytest.raises(ValueError):
        build_passport("t", "s", claims(), subj, key=b"short")
    monkeypatch.setenv("CLAIMS_LAYER_SEAL_KEY", "e" * 20)
    assert key_from_env() == b"e" * 20
    monkeypatch.delenv("CLAIMS_LAYER_SEAL_KEY")
    assert key_from_env() is None
    with pytest.raises(ValueError):
        build_passport("t", "s", claims(), subj, protocol="claims-layer/9")


def test_hmac_matches_stdlib(subj):
    import hmac as _hmac

    p = build_passport("t", "s", claims(), subj, key=KEY)
    assert _hmac.compare_digest(p["seal_hmac_sha256"], compute_hmac(p, KEY))
    assert len(p["seal_hmac_sha256"]) == len(hashlib.sha256().hexdigest())
