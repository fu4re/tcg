# Task 08 — Checker variants A and B

- **Type:** two instantiations of Check′ for the same bundle · **Effort:** A is free (exists); B is the one real research step in the pilot · **Output:** two `trusted_base.json` variants, two ladders, one comparison
- **Why both:** the bundle format is supposed to be indifferent to the checker. Running the same hard layer under two checkers is the cheapest test of that claim, and the difference between the two ladders is exactly the cost of not having a self-contained certificate.
- **Precondition for B (checked 2026-10-28):** EVMYulLean's `step` covers every opcode in GemJoin ETH-A's runtime bytecode. No semantics extension needed.

## Variant A — pinned KEVM re-discharge

What exists today.

- Check′ = the pinned `kevm-prove` image, hash in T̂.
- c for each KEVM claim = the re-discharge invocation, not a proof object.
- `self_contained: false`, reason recorded.
- L1 wall time ≈ 28 s × 5 claims; the consumer re-proves.
- `outside_bundle` includes the image.

Nothing to build. Run the verifier, record the ladder. This is the baseline the proposal reports honestly.

## Variant B — Lean kernel over EVMYulLean

What M3 of the proposal promises; the pilot attempts the smallest version.

### Scope for the pilot

Not all five claims. **One claim**, the simplest (likely a getter or the `exit` path without the external call), re-stated over EVMYulLean and proved in Lean. If it goes through, a second. Five is M3, not the pilot.

### Steps

1. Vendor EVMYulLean at a pinned commit into `bundle/semantics/evmyullean/` (or reference by hash with a fetch script; vendoring is what v3 §4 asks for, so vendor if size allows, else record why not).
2. Re-state the claim: translate the K pre/post into a Lean statement over `EVM.State` using EVMYulLean's `step`/`run`. Record the translation as a new `phi.json` version; H must re-sign (this is the L3 mechanism working as designed).
3. Prove it. Expect to use `unfold; rfl`-style evaluation for straight-line code (evm-smith's pattern) and the Frame library for storage reasoning if the claim touches `gem[ilk][usr]`. If it does not close in two days, record where it stuck and stop; that is a result.
4. Certificate = the `.olean` plus source. Checker = `lean` kernel, `#print axioms`, no `sorry`. The claim leaves `claims_without_certificate`.
5. Rerun the verifier with `--variant B`. L1 for that claim should read `checker: lean`, `self_contained: true`.

### Cross-check

The same claim now has two discharges: KEVM (A) and Lean/EVMYulLean (B). Agreement is recorded in T̂ as `cross_checked: ["claim-0N"]`. Disagreement is a finding against one of the two semantics or against the translation in step 2, and it is written up before anything else.

## Comparison — `handoff/variants.md`

| | A | B |
|---|---|---|
| Claims certified | 0 of 5 | 1–2 of 5 |
| `self_contained` | false | true for certified claims |
| Checker size | KEVM image (GB) | Lean toolchain, named by version |
| L1 time per claim | ~28 s re-prove | kernel check, seconds |
| `outside_bundle` | image + RPC | RPC |
| Trusted base change | A3 = K prover | A3 = Lean kernel; A1 gains a second semantics |

Plus one paragraph: what it would take to move the remaining claims (the honest scope of M3).

## Done when

- Variant A ladder exists.
- At least one claim is either certified under B, or the exact obstacle is written down with the Lean goal state where it stopped.
- `variants.md` is filled with measured values, not the expectations above.
