# Claims Layer

A small, standard-library Python reference implementation of **machine-checkable evidence passports for claims**. Each claim states what *kind* of claim it is, what evidence tag stands behind it, and which machine-runnable checks were run against its cited records. The status comes from running those checks, not from the author typing it in.

**Evidence label: SYNTHETIC.** The demos use seeded synthetic data. Nothing here has been tried on real publications or by any institution.

```
claim --kind----> ANNOUNCEMENT | MODEL | MEASUREMENT | HYPOTHESIS | INFERENCE
      --tag-----> SYNTHETIC | REPORTED | TARGET | UNRUN
      --checks--> file_sha256 | json_value | text_contains
      --status--> VERIFIED | SUPPORTED | UNVERIFIED | REFUTED   (computed by the checks)
passport --seal-> SHA-256 of the record + every evidence file; verify_passport() re-checks it
```

## Quick start

```bash
python demo.py           # honest passport SEALED; inflated number REFUTED; edits and data changes detected
python tests.py          # original script-style checks
pip install -r requirements-dev.txt && python -m pytest    # 32 tests, warnings are errors
CSEQ_DIR=../digital-to-wave-cseq python demo_cseq.py         # passport over a cseq_wave v0.2.0 run record
```

`claims_layer` and `demo.py` need only the Python standard library (3.10+). `demo_cseq.py` runs [digital-to-wave-cseq](https://github.com/sparkainlp-x/digital-to-wave-cseq), which needs numpy.

## Demo results (SYNTHETIC)

- **`demo.py`:** the honest passport seals. The passport claiming the mean is 0.5 higher has that claim REFUTED and is issued UNSEALED. `verify_passport()` accepts the honest passport, and rejects it after a claim is edited, and after one value is appended to the data file.
- **`demo_cseq.py`** (digital-to-wave-cseq at `ad8ea3a`, seed 7): main verdict VERIFIED_RECALL, control CONFABULATION_SUSPECTED, fidelity 1.0 and cue overlap 0.2576 all VERIFIED against the run record. The README inference is SUPPORTED (text citation only), the hypothesis is UNVERIFIED, and the passport SEALS and re-verifies. As received, this demo **failed**: two of its checks pointed at a key and a README phrase that no longer exist in digital-to-wave-cseq, so the layer correctly REFUTED them, while the original README said the passport sealed.

## Sealing rules (fail-closed)

- Any REFUTED claim leaves the passport unsealed.
- Any MEASUREMENT claim that isn't VERIFIED leaves it unsealed. So does any other claim that states a number and isn't VERIFIED, except a HYPOTHESIS.
- An unrunnable check counts as a failed check. Paths must stay inside the evidence folder.
- A numeric check's tolerance must be at most 1% of the expected value, and the number in the claim's text must match the checked value.
- Text citations can make a claim SUPPORTED, never VERIFIED.
- The firewall refuses the whole passport when a non-REPORTED claim asserts a real-world measurement, or when a claim uses absolute or banned phrases ("proves", "guaranteed", "validated", "production-ready", and so on).

## Limitations

1. **A seal shows consistency and provenance, not truth.** Fabricated data, honestly hashed, seals fine.
2. **The seal is an unkeyed hash, not a signature.** `verify_passport()` catches edits and changed evidence, but not a forger who rewrites the claims and the evidence together.
3. **The author still writes the checks.** A digest the author takes from their own file only shows the file hasn't changed since.
4. **The firewall is a phrase list.** Paraphrases and misspellings pass it ("conclusively demonstrates"). It also refuses negated phrases ("not guaranteed"), which is the safe direction.
5. **The author chooses the claim kind.** The numeric-claim rule limits kind-swapping, but it can't catch a claim that states no number.

## How this differs from related repositories

- [quantum-claims-passport](https://github.com/sparkainlp-x/quantum-claims-passport) is a one-off audit of a specific announcement. This repo reuses its claim-kind taxonomy as a general library with machine-run checks.
- [evidence-passport](https://github.com/sparkainlp-x/evidence-passport) turns one experiment manifest into an HTML passport. Here each claim gets its own checks and status, and the passport only seals when they pass.
- [measurement-trail](https://github.com/sparkainlp-x/measurement-trail) hash-chains processing steps. This repo doesn't chain records; it seals one passport together with the evidence files it cites.
- The re-compute-before-display idea comes from [sparkholo-coherence-agent](https://github.com/sparkainlp-x/sparkholo-coherence-agent), and the refuse-don't-edit claims firewall from [spark-iis-api](https://github.com/sparkainlp-x/spark-iis-api).

## Acknowledgements

The `demo_cseq.py` example passports results from digital-to-wave-cseq, whose recall-fidelity readout uses the C_seq phase-coherence formula from Mun Seok Lee's *Coherent Sequence Unified Coupled-Field Theory* (2026 preprint). He has not reviewed or endorsed this software. The original package as received is kept unchanged in [spec/](spec/).

## How to cite

See [CITATION.cff](CITATION.cff).

## License

Copyright (c) 2026 Jean-François Brisson, Spark AI NLP.

This software is available under the GNU Affero General Public License v3.0 only (AGPL-3.0-only); see [LICENSE](LICENSE).
