# Changelog

## Unreleased

- Documentation only: added a Provenance statement that says which files are derived from the package received under Mun Seok Lee's name and by how much, that he is not an author of this release and has not endorsed it.

## 0.2.0 (2026-10-21)

- Archived on Zenodo: version DOI [10.5281/zenodo.23530283](https://doi.org/10.5281/zenodo.23530283), concept DOI [10.5281/zenodo.23530282](https://doi.org/10.5281/zenodo.23530282).
- Optional HMAC-SHA256 keyed seal (`key=` or `CLAIMS_LAYER_SEAL_KEY`). The passport records `seal_type` and a `key_id` fingerprint, never the key. Verification is constant-time, refuses downgrades, and catches a full rewrite of claims and evidence by anyone without the key. HMAC is a shared secret, not a public-key signature. Unkeyed and v0.1.0 passports still verify.
- Firewall R3 rewritten: normalisation (`normalize.py`), inflected claim verbs, misspellings by edit distance with an allowlist, intensifier plus verb, certainty phrases, banned compounds, and conservative clause-scoped negation. On the held-out corpus it refuses 25/25 sentences that should be refused and 2/25 that should pass. Known misses are documented.
- `demo.py` shows the keyed seal and a keyless full rewrite being caught.
- Tests: 32 -> 127.

## 0.1.0 (unreleased)

- The package as received is the first commit, kept unchanged in `spec/`.
- `demo.py` now uses only the standard library (it imported numpy).
- Checks: paths must stay inside the evidence folder, tolerances must be finite and at most 1% of the expected value, booleans no longer equal 1, and numbers in the claim text must match the checked value. Before this, "score is 9.99" checked against 0.75 was VERIFIED.
- Sealing: the seal also covers the SHA-256 of every evidence file. Non-hypothesis claims that state a number must be VERIFIED to seal (an unchecked INFERENCE "mean is 9.99" used to seal). Added `verify_passport()` and `compute_seal()`. HTML now escapes every field.
- Firewall: the real-measurement rule now applies to every tag except REPORTED (it covered SYNTHETIC only), and the org's banned terms were added. Remaining limits are documented and tested.
- `demo_cseq.py` was updated to the current digital-to-wave-cseq v0.2.0 run record. As received, it failed with two checks REFUTED.
- Wording: "proves" changed to "shows", and claims about deployment and permanence were removed.
- Added a pytest suite (32 tests, warnings are errors), CI on Python 3.10 to 3.13 running both demos, README, CITATION.cff and .zenodo.json.
