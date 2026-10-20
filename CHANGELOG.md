# Changelog

## 0.1.0 (unreleased)

- The package as received is the first commit, kept unchanged in `spec/`.
- `demo.py` now uses only the standard library (it imported numpy).
- Checks: paths must stay inside the evidence folder, tolerances must be finite and at most 1% of the expected value, booleans no longer equal 1, and numbers in the claim text must match the checked value. Before this, "score is 9.99" checked against 0.75 was VERIFIED.
- Sealing: the seal also covers the SHA-256 of every evidence file. Non-hypothesis claims that state a number must be VERIFIED to seal (an unchecked INFERENCE "mean is 9.99" used to seal). Added `verify_passport()` and `compute_seal()`. HTML now escapes every field.
- Firewall: the real-measurement rule now applies to every tag except REPORTED (it covered SYNTHETIC only), and the org's banned terms were added. Remaining limits are documented and tested.
- `demo_cseq.py` was updated to the current digital-to-wave-cseq v0.2.0 run record. As received, it failed with two checks REFUTED.
- Wording: "proves" changed to "shows", and claims about deployment and permanence were removed.
- Added a pytest suite (32 tests, warnings are errors), CI on Python 3.10 to 3.13 running both demos, README, CITATION.cff and .zenodo.json.
