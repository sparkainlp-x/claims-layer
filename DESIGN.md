# Design: why a claims layer, and what it can and cannot do

## The problem, precisely

Public argument runs on claims whose *kind* is invisible. A press
release (ANNOUNCEMENT) is quoted as a result (MEASUREMENT). A model
output (MODEL) is reported as an observation. A hypothesis is
headlined as a finding. The words travel; the epistemic status does
not. Every downstream reader — journalist, investor, regulator,
platform algorithm — then prices the claim as if it were the
strongest kind.

Existing fixes attack content (fact-checking) or speakers
(reputation). Both are slow, centralized, and adversarial. The
claims layer attacks the *packaging*: make the kind, the evidence
tag, and the verification state part of the claim itself,
machine-readable, and checkable by anyone who has the cited records.

## The model

A claim carries:

- **Kind** — ANNOUNCEMENT / MODEL / MEASUREMENT / HYPOTHESIS /
  INFERENCE (taxonomy from quantum-claims-passport). The author
  chooses the kind; the passport then keeps it verbatim. A claim that
  states a number cannot seal unless it is VERIFIED, whatever its kind
  (HYPOTHESIS excepted).
- **Evidence tag** — SYNTHETIC / REPORTED / TARGET / UNRUN. What
  stands behind the claim, in the org's existing convention.
- **Checks** — machine-runnable verifications against cited records:
  file digests (provenance), JSON values in run records (the
  recompute-the-claim pattern from sparkholo), textual citations
  (weak support).
- **Status** — VERIFIED / SUPPORTED / UNVERIFIED / REFUTED, assigned
  by running the checks, not typed in by the author. The author does
  still write the checks and their expected values, so the status is
  only as independent as those checks (see limits).

A passport seals when nothing is refuted and every measurement is
verified. The seal is a hash of the canonical record and of every
evidence file the checks read, with no timestamps, so anyone holding
the same evidence can re-check it with `verify_passport()`.

## Why these semantics

1. **Fail-closed everywhere.** An unrunnable check is a failed check.
   A measurement without a passing strong check cannot seal. Absence
   of evidence is rendered as UNVERIFIED, never silently upgraded.
2. **Weak evidence is labeled weak.** A text citation can only make a
   claim SUPPORTED. Most real-world "sourcing" is exactly this, and
   the status makes the difference visible instead of laundering a
   mention into a verification.
3. **The firewall screens combinations, not opinions.** SYNTHETIC +
   "measured on real patients" is refused not because it is false
   but because it is *internally dishonest* — the tag and the text
   disagree. Absolute adverbs ("proves", "guaranteed") are refused
   for the same reason: in this system, strength comes from checks.
4. **No wall-clock in the seal.** sparkholo's lesson: identical
   inputs, identical hash, so a passport can be re-checked later
   against the same evidence.

## Possible uses (not implemented or tested here)

- **Journals / preprint servers:** a passport attached to a paper's
  headline claims; MEASUREMENT claims check against deposited run
  records. Reviewers start from statuses, not from prose.
- **Platforms:** passported claims rank above bare ones; UNVERIFIED
  renders with its status visible, the way browsers made plain HTTP
  visible. No censorship — labeling.
- **AI systems:** a model emitting a consequential claim emits its
  passport too; downstream systems (and the sparkholo pattern) can
  refuse to display claims whose checks fail.
- **Procurement / funding:** claims about a product's performance
  arrive as passports; a REFUTED claim in a vendor passport is a
  permanent, citable fact.

## The honest limits (printed on every passport)

1. **A seal shows consistency and provenance, not ground truth.**
   Garbage data, honestly hashed, seals fine. The layer stops
   *laundering* (kind-swapping, number-inflation after the fact,
   citation theater) — it does not stop fabrication at the source.
   That is what replication and the oes512q-latch style of public
   benchmark are for; the layers compose, none suffices alone.
2. **Checks are only as good as their records.** If the run record
   itself is fabricated, json_value checks pass. Mitigation is
   procedural (records deposited before claims are made, hash
   chains, third-party archives) — the passport format supports it;
   this v0.1 does not enforce it.
3. **Textual support is weak by design** and stays weak: SUPPORTED
   is a ceiling, not a floor to argue from.
4. **Adoption is the hard part**, as with HTTPS: the technology is
   trivial next to the coordination. The bet is the same one the
   portfolio makes everywhere — ship a working reference
   implementation under AGPL, with the demos and the negative cases
   included, and let one institution go first.

5. **The default seal is an unkeyed hash, not a signature** (v0.2.0 adds an optional HMAC-SHA256 seal, which is a shared secret: anyone with the key can forge it). Anyone who edits a
   passport can recompute it. `verify_passport()` catches edits that do
   not also rewrite the evidence, but a forger who changes claims and
   evidence together is not caught. Sign the seal separately when the
   author may not be trusted.
6. **The author writes the checks.** Tolerances are capped (at most 1%
   of the expected value) and numbers in the claim text must match the
   checked value, but a digest the author takes from their own file
   only shows the file has not changed since.
7. **The firewall is a word list with normalisation.** v0.2.0 catches
   inflections, misspellings and intensified paraphrases, but certainty
   stated in other words still passes. Measured rates are in the README.

All examples and demos use SYNTHETIC data.
