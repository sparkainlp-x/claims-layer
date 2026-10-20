import hashlib
import json
import os
import pathlib

import pytest

from claims_layer import (
    Claim,
    FirewallViolation,
    build_passport,
    claim_status,
    compute_seal,
    render_html,
    run_check,
    screen_claim,
    verify_passport,
)

ROOT = pathlib.Path(__file__).resolve().parents[1]


@pytest.fixture
def subj(tmp_path):
    (tmp_path / "data.txt").write_text("alpha beta gamma", encoding="utf-8")
    (tmp_path / "record.json").write_text(
        json.dumps({"run": {"score": 0.75, "label": "ok", "flag": 1, "on": True}}), encoding="utf-8")
    return tmp_path


def jv(key, expected, tol=None, path="record.json"):
    c = {"kind": "json_value", "path": path, "key": key, "expected": expected}
    if tol is not None:
        c["tol"] = tol
    return c


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


# --- model ---------------------------------------------------------------

def test_model_rejects_unknown_kind_and_tag():
    with pytest.raises(ValueError):
        Claim("x", "t", "OPINION", "SYNTHETIC")
    with pytest.raises(ValueError):
        Claim("x", "t", "MODEL", "MEASURED")


# --- statuses ------------------------------------------------------------

def test_statuses(subj):
    assert claim_status(Claim("a", "score is 0.75", "MEASUREMENT", "SYNTHETIC", [jv("run.score", 0.75)]), subj)[0] == "VERIFIED"
    assert claim_status(Claim("b", "score is 0.80", "MEASUREMENT", "SYNTHETIC", [jv("run.score", 0.80)]), subj)[0] == "REFUTED"
    weak = {"kind": "text_contains", "path": "data.txt", "needle": "beta"}
    assert claim_status(Claim("c", "mentions beta", "INFERENCE", "SYNTHETIC", [weak]), subj)[0] == "SUPPORTED"
    assert claim_status(Claim("d", "no checks", "HYPOTHESIS", "UNRUN"), subj)[0] == "UNVERIFIED"


def test_unknown_check_kind_and_missing_file_fail_closed(subj):
    assert not run_check({"kind": "vibes"}, subj)["ok"]
    assert not run_check({"kind": "file_sha256", "path": "nope.txt", "sha256": "0"}, subj)["ok"]
    assert not run_check(jv("run.missing", 1), subj)["ok"]
    assert not run_check({"kind": "text_contains", "path": "data.txt", "needle": ""}, subj)["ok"]


# --- bypasses found in review ---------------------------------------------

def test_claim_text_must_match_checked_number(subj):
    c = Claim("m", "score is 9.99", "MEASUREMENT", "SYNTHETIC", [jv("run.score", 0.75)])
    status, results = claim_status(c, subj)
    assert status == "REFUTED"
    assert any(r["kind"] == "text_binding" and not r["ok"] for r in results)


def test_rounded_number_in_text_still_binds(subj):
    c = Claim("m", "score is 0.8 (rounded)", "MEASUREMENT", "SYNTHETIC", [jv("run.score", 0.75, tol=0.0)])
    # 0.8 has one decimal, so it covers 0.75..0.85
    assert claim_status(c, subj)[0] == "VERIFIED"


@pytest.mark.parametrize("tol", [1e9, 0.5, -1, float("inf"), float("nan")])
def test_loose_or_invalid_tolerance_fails(subj, tol):
    assert not run_check(jv("run.score", 0.75, tol=tol), subj)["ok"]


def test_boolean_is_not_one(subj):
    assert not run_check(jv("run.flag", True), subj)["ok"]
    assert not run_check(jv("run.on", 1), subj)["ok"]
    assert run_check(jv("run.on", True), subj)["ok"]


@pytest.mark.parametrize("rel", ["../outside.txt", "/etc/hostname", "sub/../../outside.txt"])
def test_paths_cannot_escape_base_dir(subj, rel):
    (subj.parent / "outside.txt").write_text("x", encoding="utf-8")
    assert not run_check({"kind": "file_sha256", "path": rel, "sha256": "0"}, subj)["ok"]
    assert not run_check({"kind": "text_contains", "path": rel, "needle": "x"}, subj)["ok"]


def test_numeric_claim_cannot_dodge_seal_by_kind(subj):
    p = build_passport("t", "s", [Claim("i", "mean is 9.99", "INFERENCE", "SYNTHETIC")], subj)
    assert not p["sealed"]
    p = build_passport("t", "s", [Claim("h", "drift stays below 1%", "HYPOTHESIS", "UNRUN")], subj)
    assert p["sealed"]


# --- sealing ---------------------------------------------------------------

def test_unverified_measurement_blocks_seal(subj):
    p = build_passport("t", "s", [Claim("m", "unchecked", "MEASUREMENT", "SYNTHETIC")], subj)
    assert not p["sealed"] and p["unsealed_reasons"]


def test_seal_deterministic_and_covers_evidence(subj):
    claims = [Claim("m", "score is 0.75", "MEASUREMENT", "SYNTHETIC", [jv("run.score", 0.75)])]
    a = build_passport("t", "s", claims, subj)
    b = build_passport("t", "s", claims, subj)
    assert a["seal_sha256"] == b["seal_sha256"] == compute_seal(a)
    assert a["evidence_sha256"]["record.json"] == sha(subj / "record.json")
    # change the evidence file in a way the claim's check does not notice
    rec = json.loads((subj / "record.json").read_text())
    rec["run"]["label"] = "changed"
    (subj / "record.json").write_text(json.dumps(rec), encoding="utf-8")
    c = build_passport("t", "s", claims, subj)
    assert c["sealed"] and c["seal_sha256"] != a["seal_sha256"]


def test_verify_passport_detects_edits_and_evidence_changes(subj):
    claims = [Claim("m", "score is 0.75", "MEASUREMENT", "SYNTHETIC", [jv("run.score", 0.75)])]
    p = build_passport("t", "s", claims, subj)
    assert verify_passport(p, subj) == (True, [])

    edited = json.loads(json.dumps(p))
    edited["claims"][0]["status"] = "VERIFIED"
    edited["title"] = "other"
    assert not verify_passport(edited, subj)[0]

    # editor recomputes the seal: still caught, because the re-run differs
    forged = json.loads(json.dumps(p))
    forged["claims"][0]["text"] = "score is 0.99"
    forged["claims"][0]["checks"][0]["expected"] = 0.99
    forged["seal_sha256"] = compute_seal(forged)
    ok, problems = verify_passport(forged, subj)
    assert not ok and any("claims" in x for x in problems)

    (subj / "record.json").write_text(json.dumps({"run": {"score": 0.75, "label": "x"}}), encoding="utf-8")
    ok, problems = verify_passport(p, subj)
    assert not ok and any("evidence_sha256" in x for x in problems)


def test_verify_passport_fails_closed_on_garbage(subj):
    assert not verify_passport({"claims": "nope"}, subj)[0]


def test_unkeyed_seal_limit_is_documented():
    """A forger who rewrites claims AND evidence consistently is not caught."""
    from claims_layer.passport import SEAL_MEANING

    assert "not a signature" in SEAL_MEANING


# --- firewall ----------------------------------------------------------------

@pytest.mark.parametrize("text,tag", [
    ("measured on real patients", "SYNTHETIC"),
    ("measured on real patients", "TARGET"),
    ("This proves it", "SYNTHETIC"),
    ("100% accurate", "REPORTED"),
    ("A validated, production-ready tool", "SYNTHETIC"),
    ("shows quantum advantage", "SYNTHETIC"),
])
def test_firewall_refuses(subj, text, tag):
    c = Claim("x", text, "MODEL", tag)
    assert screen_claim(c)
    with pytest.raises(FirewallViolation):
        build_passport("t", "s", [c], subj)


def test_firewall_allows_reported_real_measurement_and_unrun_rule():
    assert screen_claim(Claim("x", "measured on real patients", "MEASUREMENT", "REPORTED")) == []
    assert screen_claim(Claim("x", "run later", "MEASUREMENT", "UNRUN"))


def test_firewall_known_limits():
    """Documented: paraphrases pass, and negated phrases are refused."""
    assert screen_claim(Claim("x", "conclusively demonstrates the effect", "MODEL", "SYNTHETIC")) == []
    assert screen_claim(Claim("x", "results are not guaranteed", "MODEL", "SYNTHETIC"))


# --- html ---------------------------------------------------------------

def test_html_escapes_claim_text(subj):
    p = build_passport("<b>t</b>", "s", [Claim("<i>", "<script>x</script>", "HYPOTHESIS", "UNRUN")], subj)
    out = render_html(p)
    assert "<script>" not in out and "&lt;script&gt;" in out


# --- demos -----------------------------------------------------------------

def test_demo_passes(monkeypatch, tmp_path):
    import demo

    monkeypatch.setattr(demo, "SUBJ", tmp_path / "subject")
    monkeypatch.setattr(demo, "HERE", tmp_path)
    assert demo.main() == 0


@pytest.mark.skipif(not (pathlib.Path(os.environ.get("CSEQ_DIR", ROOT.parent / "digital-to-wave-cseq")) / "demo_verified.py").exists(),
                    reason="digital-to-wave-cseq checkout not available")
def test_demo_cseq_passes(monkeypatch, tmp_path):
    import demo_cseq

    monkeypatch.setattr(demo_cseq, "HERE", tmp_path)
    assert demo_cseq.main() == 0


def test_stdlib_only():
    import ast

    stdlib = {"hashlib", "json", "math", "re", "html", "pathlib", "random", "statistics",
              "shutil", "os", "subprocess", "sys", "tempfile"}
    for f in list((ROOT / "claims_layer").glob("*.py")) + [ROOT / "demo.py", ROOT / "demo_cseq.py"]:
        for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
            if isinstance(node, ast.Import):
                names = [a.name.split(".")[0] for a in node.names]
            elif isinstance(node, ast.ImportFrom) and node.level == 0:
                names = [node.module.split(".")[0]]
            else:
                continue
            for n in names:
                assert n in stdlib or n == "claims_layer", (f.name, n)
