"""Adversarial firewall corpora.

The dev corpus was used to tune the rules, so it must be handled
exactly. The held-out corpus was written before tuning; its measured
rates are pinned here so a regression shows up, not so they look good.
"""

import json
import pathlib

import pytest

from claims_layer import Claim, screen_claim
from claims_layer.normalize import clauses, edit_distance

CORPUS = pathlib.Path(__file__).parent / "corpus"


def load(name):
    return json.loads((CORPUS / f"firewall_{name}.json").read_text(encoding="utf-8"))


def refused(text):
    return bool(screen_claim(Claim("x", text, "MODEL", "SYNTHETIC")))


DEV = load("dev")
HELD = load("heldout")


@pytest.mark.parametrize("text", DEV["must_refuse"])
def test_dev_must_refuse(text):
    assert refused(text)


@pytest.mark.parametrize("text", DEV["must_pass"])
def test_dev_must_pass(text):
    assert not refused(text)


def test_heldout_rates():
    caught = sum(refused(t) for t in HELD["must_refuse"])
    false_refusals = sum(refused(t) for t in HELD["must_pass"])
    assert caught >= 25 and len(HELD["must_refuse"]) == 25
    assert false_refusals <= 2 and len(HELD["must_pass"]) == 25


def test_normalisation():
    assert clauses("Pr0v3n -- ok; ＶＡＬＩＤ-ated, 100 % sure") == [["proven"], ["ok"], ["validated"], ["100%", "sure"]]
    assert clauses("doesn't") == [["doesnt"]]
    assert edit_distance("prooven", "proven") == 1
    assert edit_distance("abc", "xyzxyz", limit=2) == 3


# Bypass probes tried after the held-out run. The first group was fixed;
# the second is a documented limit (no word list catches everything).
FIXED_AFTER_PROBE = ["p r o v e n", "pr*ven", "pro\u200bven", "Not unproven.", "It is never not guaranteed."]
KNOWN_MISSES = [
    "The effect is beyond question.",
    "It works, period.",
    "The effect is real.",
    "Verified to work in all cases.",
    "Demonstrated with total certainty.",
]


@pytest.mark.parametrize("text", FIXED_AFTER_PROBE)
def test_probe_bypasses_now_refused(text):
    assert refused(text)


@pytest.mark.parametrize("text", KNOWN_MISSES)
def test_known_misses_documented(text):
    assert not refused(text)


@pytest.mark.parametrize("text", ["These results are unvalidated.", "The probe moved.", "It is not invalid."])
def test_probe_honest_sentences_pass(text):
    assert not refused(text)
