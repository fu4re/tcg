# Task 06 — Verifier

- **Type:** the only new code in the pilot · **Effort:** two to three days · **Output:** `verifier/` (source), its hash recorded in `trusted_base.json` → `checker`
- **Source:** TCG v3 §5 (re-verifiability, assumptions that become checks), §6 (verdict ladder, monotonicity, reporting), §10 (threats, in particular artefact substitution and custom axioms)
- **Invariant:** the verifier emits a level per layer as structured output and **never** a single summary mark. A function that collapses the ladder to one value does not exist in the codebase.

## Interface

```
verify <bundle-dir> --oracle-pubkey <file> --producer-pubkey <file> \
       --rpc <url> | --state-snapshot <dir> \
       --variant A|B --out ladder.json
```

Exit code 0 if the verifier ran to completion, regardless of levels. Levels are in the output, not the exit code.

## Output — `ladder.json`

```
{
  "bundle_root": "...",
  "verifier_hash": "...",
  "self_contained": false,
  "L0": { "status": "pass|fail", "checks": { "root_hash": ..., "producer_sig": ..., "identity": {...}, "environment": {...} } },
  "L1": { "status": "pass|fail|refused", "claims": [ { "claim": "claim-01", "checker": "kevm-prove|lean", "result": "accept|refute|unknown", "axioms": [...], "admits": 0 } ],
          "refused_reason": null },
  "L2": { "coverage_total": true, "backtranslation": [ {...} ], "mutants": [ { "claim": ..., "replayed": true, "refuted": true } ], "pre_witness_replays": true },
  "L3": { "status": "pass|fail", "approved_hash": "...", "proven_hash": "...", "signer": "..." },
  "L4": { "status": "pass|fail|partial", "events_replayed": 12, "events_total": 15, "mismatches": [...] },
  "outside_bundle": [ "kevm 1.0.678 image pulled from <registry>", "archive RPC at block N" ]
}
```

`outside_bundle` is the field the hand-off (task 07) is about. Everything the verifier had to fetch that was not a child of the manifest goes here.

## Checks per level

### L0 — hashes and identity (no trust)

1. Recompute `root_hash` over the manifest children; compare.
2. Verify `producer_sig` over `root_hash`.
3. **Identity:** read runtime bytecode at `identity.address` from the RPC or snapshot at `identity.block`; compute keccak256; compare with `identity.value` **and** with `sha256`→keccak of `hard/artifact.bin`. The verifier must compute the chain-side hash itself; a verifier that compares `identity.value` with `identity.value` passes everything (v3 §10, artefact substitution). A test asserts the chain read happens.
4. **Environment:** for each entry in `environment.external_code`, read code at the address at the pinned block, hash, compare. Compare `chain_id`, `fork` with the snapshot metadata. Mismatch → L0 fail with the field named; the proof is not invalidated, the transfer to this deployment is.

### L1 — certificate check (trust class T)

Precondition: `trusted_base.json` → `assumptions` non-empty and closed over `hard/annotations.json`. If not, `L1.status = "refused"`, `refused_reason = "empty or incomplete assumption ledger"`, and no claim results are reported. This is the honest-reporting rule.

Per claim:
- **Lean lemma:** build with the toolchain named in `lean-toolchain`; check the kernel accepts; run `#print axioms <thm>`; accept only if the axiom set ⊆ {propext, Classical.choice, Quot.sound} (or the set named in T̂); reject on any `sorry`/admit. Record axioms in output.
- **KEVM claim, variant A:** pull the image whose hash is in `trusted_base.json` → `checker[kevm-prove].hash`; verify the hash matches before running; run the invocation from `certs/claim-0N.rediscuss.json`; record result and wall time. Record `"self_contained": false` and add the image to `outside_bundle`.
- **KEVM claim, variant B:** check the Lean proof term over EVMYulLean exactly as a Lean lemma above; the semantics hash in T̂ must match the vendored EVMYulLean tree in the bundle.

Checker hash: before running any checker, hash the binary and compare with T̂. Mismatch → that claim's result is `"checker_hash_mismatch"`, not `refute`.

### L2 — evidence tools (reported, judged by H)

- Coverage: recompute totality from `phi.json` and `requirements.md`; report gaps.
- Back-translation: **do not re-run a model.** Report the stored translations and agreement flags as data.
- Mutants: for each `evidence/mutants/claim-0N/`, run `replay.sh`; report whether the refutation reproduces.
- Pre witness: run its replay; report.

### L3 — oracle approval

Verify `approval.sig` against the oracle pubkey over `sha256(hard/spec/phi.json) ∥ sha256(hard/spec/requirements.md)`. Compare the signed `phi` hash with the hash of the `phi.json` actually in `hard/`. Equal → pass. Signature valid but hash differs → fail with both hashes shown (the "approved then weakened" case). Signature by the producer key instead of the oracle key → fail, reason `"approval signed by producer"`.

### L4 — provenance replay

Walk `ledger.jsonl`, verify the chain. For each event with `deterministic: true` whose tool is available by hash, re-run with the recorded argv and input hashes; compare output hashes. Report replayed/total and every mismatch. Non-deterministic events are counted, not replayed.

## Monotonicity test

A test suite that takes a passing bundle and, one at a time: replaces a child with garbage; forges the approval with the producer key; adds a fabricated ledger event; edits `phi.json` after signing; swaps `artifact.bin` for WETH9's bytecode. Each mutation must lower at least one level and raise none. This is the one property the verifier is required to prove about itself.

## Size

Target: under 2,000 lines, Python, no framework. The Lean toolchain and the KEVM image are not part of this count; they are named by hash in T̂. If the verifier grows past that, something that belongs in a checker has leaked into it.

## Done when

- Runs end-to-end on the GemJoin bundle under variant A and emits `ladder.json`.
- Monotonicity suite passes (every mutation lowers, none raises).
- The chain-read assertion in L0 passes (identity computed, not copied).
- `outside_bundle` is non-empty and accurate for variant A.
