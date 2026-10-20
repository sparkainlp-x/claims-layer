# Claims Layer

**Machine-checkable evidence passports for public claims.**

Any consequential claim — a study result, a product spec, an AI
summary, a benchmark number — should ship with its epistemic status
attached: what *kind* of claim it is, what evidence stands behind it,
and which machine-runnable checks were run against it, with results.
In the claims layer, the status (VERIFIED / SUPPORTED / UNVERIFIED /
REFUTED) is assigned **by the checks, never by the author** — and a
passport seals only when nothing is refuted and every measurement is
verified.

```
claim --kind----> ANNOUNCEMENT | MODEL | MEASUREMENT | HYPOTHESIS | INFERENCE
      --tag-----> SYNTHETIC | REPORTED | TARGET | UNRUN
      --checks--> file_sha256 | json_value | text_contains
      --status--> VERIFIED | SUPPORTED | UNVERIFIED | REFUTED   (by the checks)
passport --seal-> SHA-256 of the canonical record, re-checkable forever
```

## Combined from the portfolio

| Piece | From |
|---|---|
| Claim-kind taxonomy (announcement ≠ measurement) | `quantum-claims-passport` |
| Manifest → passport document | `evidence-passport` |
| Recompute-the-claim verification | `sparkholo-coherence-agent` |
| Claims firewall (refuse dishonest claim/tag pairs) | `spark-iis-api` |
| Hash-sealed records, no wall-clock | `measurement-trail`, `sparkholo` |

## Quick start

```bash
python tests.py        # 7 tests, stdlib only
python demo.py         # honest passport SEALED; tampered passport REFUTED + UNSEALED
python demo_cseq.py    # a passport over the Coherent Sequence Wave Computer's real run record
```

`demo.py` is self-contained. `demo_cseq.py` runs the sibling
`digital-to-wave-cseq` verified demo (seed 7) and passports its
claims — the claims layer verifying the verifier: main verdict
VERIFIED_RECALL ✓, control CONFABULATION_SUSPECTED ✓, fidelity
C_seq 1.0 ✓, file integrity ✓, one hypothesis honestly UNVERIFIED.
Passport: **SEALED**.

## Sealing rules (fail-closed)

- Any claim REFUTED → unsealed.
- Any MEASUREMENT claim not VERIFIED → unsealed.
- An unrunnable check counts as a failed check.
- Weak checks (textual citation) can make a claim SUPPORTED, never
  VERIFIED.
- The firewall refuses the passport outright if a claim's text
  contradicts its tag (e.g. SYNTHETIC + "measured on real patients")
  or uses absolute overclaim phrases ("proves", "guaranteed").

## What a seal means — and does not

Printed on every passport: *a seal proves consistency and provenance
of the record — that the claims match their cited records and the
record is unchanged. It does not prove the underlying data is true.*
Garbage data, honestly hashed, seals fine. The layer stops
laundering — kind-swapping, post-hoc number inflation, citation
theater — not fabrication at the source. See `DESIGN.md` for the
full reasoning, deployment picture, and limits.

## Layout

```
claims_layer/
  model.py     claim kinds, evidence tags, statuses
  checks.py    file_sha256 / json_value / text_contains, status logic
  firewall.py  tag-consistency + overclaim screening
  passport.py  build, seal, JSON + HTML render
demo.py        self-contained demo (honest vs tampered)
demo_cseq.py   passport over cseq_wave v0.2.0's run record
tests.py       7 tests
DESIGN.md      the deep think: model, semantics, deployment, limits
```

## License

AGPL-3.0 — same as the rest of the sparkainlp-x research line.
