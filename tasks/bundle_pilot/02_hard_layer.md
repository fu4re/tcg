# Task 02 — Hard layer: b, φ, a, c

- **Type:** serialisation of existing artefacts · **Effort:** one day · **Output:** `bundle/hard/`
- **Source:** GemJoin ETH-A pilot (tcg F0003, F0001), KEVM claims, Lean lemmas (tcg F0004), assumption ledger
- **Rule:** nothing in this layer is new content. If a step needs new content, stop and record why in `provenance/decision-stub.md`.

## b — the artefact

- Read runtime bytecode of GemJoin ETH-A from chain at the pinned block (D9). Store as `hard/artifact.bin`.
- Record `keccak256(artifact.bin)` and confirm it equals the constant already used in the KEVM/Lean development. If it does not, stop: the existing proofs are about a different object.
- Do **not** store source. Source is provenance, not artefact (v3 §4).

## φ — the specification

- One file per claim: `hard/spec/claim-01.k` … `claim-05.k`, exactly the K claims that were discharged.
- Alongside, `hard/spec/phi.json`: for each claim, its Pre / Post / Exit* in a form a non-K reader can parse, plus `requirements: [...]` referencing numbered entries of `n`.
- `hard/spec/requirements.md` = **n**, the informal specification: five to ten numbered sentences stating what GemJoin ETH-A must do (join moves exactly `wad` WETH from caller to adapter and credits `gem[ilk][usr]` by `wad`; exit is the inverse; no other storage changes; revert on insufficient balance; …). Written by the author or the producing agent; **signed by the author in task 04**. Each sentence has an id `R1…Rn`.
- Every claim references ≥1 requirement; every requirement is referenced by ≥1 claim, or is listed under `declared_blind_spots` in `phi.json` (v3 §7, coverage matrix). Totality is checked in task 04.

## a — checked annotations

- `hard/annotations.json`: every Aasm fact, every simplification lemma (F0004) and every loop/arith annotation the proofs depend on. Each entry: `id`, `statement`, `used_by: [claim ids]`, `justification` (one sentence), `class: "T"`.
- The list must be closed: a script greps the K and Lean sources for every lemma/axiom name and fails if one is missing from `annotations.json`.

## c — certificates

Two kinds, two statuses, both recorded honestly.

**Lean lemmas (real certificates).** For each theorem: the source `.lean` and the compiled `.olean`, the exact Lean toolchain (`lean-toolchain` file) and `lake-manifest.json`. These are checked by the Lean kernel in task 06.

**KEVM claims.** Variant A (task 08): no proof object exists. Store `hard/certs/claim-0N.rediscuss.json` = exact prover invocation (command line, KEVM version 1.0.678, semantics hash, options, expected result), and list each claim in `trusted_base.json` → `claims_without_certificate` with reason `"K prover emits no proof object; re-discharged by pinned prover"`. Variant B: the Lean proof terms over EVMYulLean, when and if they exist, go here as real certificates and the claim leaves `claims_without_certificate`.

## Output

```
hard/
  artifact.bin
  spec/claim-01.k … claim-05.k
  spec/phi.json
  spec/requirements.md
  annotations.json
  certs/lemma-*.lean, lemma-*.olean, lean-toolchain, lake-manifest.json
  certs/claim-0N.rediscuss.json         (variant A)
  certs/claim-0N.lean                   (variant B, if available)
```

## Done when

- `keccak(artifact.bin)` matches the development constant.
- `phi.json` references every claim file by hash and every claim references ≥1 requirement.
- The annotation-closure script passes.
- Every KEVM claim is either certified (B) or listed under `claims_without_certificate` (A). No claim is silently neither.
