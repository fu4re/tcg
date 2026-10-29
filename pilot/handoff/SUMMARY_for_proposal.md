# Bundle pilot: summary for the proposal (TCG v3, GemJoin ETH-A)

- **As of:** 2026-10-29. Final variant-A run 17:39–19:15 UTC. Source of every number: `pilot/handoff/ladder_A.json` (sha256 `b5158b924d88b05b76e8fe6770597bc0a49aea1198a2da74703c6fddb6a839d1`) and `pilot/handoff/ladder_A.md`.
- **Status:** producer-side result. The bundle was assembled, signed and re-verified by the producing side. The hand-off to an independent consumer (task 07) has **not** been run yet.

## Paste-ready paragraph

> For the deployed MakerDAO GemJoin ETH-A adapter (Ethereum mainnet, block 26298481, ~$500M in WETH), we assembled a signed proof-carrying bundle in the TCG v3 format: artifact, specification, annotations, certificates, trusted base, evidence and provenance, as a content-addressed Merkle DAG of 381 files. A stdlib-only verifier (< 2,000 lines of Python) recomputes the verdict ladder from the bundle alone, given a pinned KEVM checker image and an archive RPC.
>
> - **L0 passes:** the on-chain code hash equals the bundled artifact, the fork (Osaka) matches, and the external code hashes match.
> - **L1 passes:** all 5 KEVM claims are re-discharged from scratch.
> - **L3 passes:** the oracle-signed specification is byte-identical to the proven one.
> - **L2 reports, rather than hides, partial coverage:** 3 of 9 informal requirements are fully covered, 2 partially and 4 not at all. Every claim has a replayable mutant witness that violates it.
> - **L4 (provenance replay) fails:** 11 of 136 deterministic events replay. This is an honest record of an assembly process that was not yet hermetic.
>
> The bundle is not self-contained, because the KEVM checker is an external image. As a first step towards self-containment, one claim (`ilk()`) was also proved in the Lean 4 kernel over EVMYulLean. It uses only the standard axioms, was cross-checked against the KEVM proof, and ships in the next bundle version.

## Ladder (variant A)

| Level | Result | Decided by | Key evidence |
|---|---|---|---|
| L0 identity + environment | **pass** | hash comparison against the chain (drpc) | keccak `0x8661c673…74fa` = artifact = on-chain at block 26298481; chain_id 1; fork osaka (blob params bpo2); WETH9 + MCD Vat code hashes match |
| L1 certificate check | **pass** | KEVM `kprove`, pinned image `sha256:7d4a35bc…c465` | 5/5 claims accept, 110–257 s each; verifier hash = trusted-base entry (`f7bde819…`) |
| L2 evidence (for the human oracle) | reported | tools run by the consumer | coverage R1–R3 covered, R4–R5 partial, R6–R9 blind; 12/12 mutant witnesses reproduced (every claim has a concrete-trace violation, and claim-04 also has a symbolic refute); pre-witness replays; back-translation 5/5, agreement left to H |
| L3 oracle approval | **pass** | ed25519 signature + hash equality | signed φ `adf5371e…` = proven φ; signer = oracle key, not the producer key |
| L4 provenance replay | **fail** | replay of recorded tool calls | ledger chain intact (151 events); 11 matched, 9 mismatched (undeclared imports), 88 depend on files outside the bundle |

Wall time: 1 h 35 min in total (L1 14 min, L2 82 min, sequential on one 2-vCPU container slot).

## What was proved (the 5 claims, all on the exact deployed bytecode)

| Claim | Statement | Quantification |
|---|---|---|
| 01–03 | `vat()`, `ilk()`, `gem()` succeed, return exactly the stored slot (masked to 160 bits for addresses), and leave storage unchanged | any caller, any storage |
| 04 | `cage()` reverts for every caller who is not a ward | any storage in which `wards[caller] == 0`; keccak treated as opaque (named assumption) |
| 05 | `join(usr, wad)` reverts once the adapter is caged (`live == 0`) | any caller, any storage with live == 0, any 256-bit usr/wad |

## What the bundle does NOT establish (state it in the proposal)

- **Value movement is not proved.** `join` and `exit` moving exactly `wad` (R6, R7), the storage frame of the success paths (R8) and non-payability (R9) are declared blind spots. They need cross-contract composition with Vat and WETH, which is open work.
- **Not self-contained:** variant A needs the external KEVM docker image. That image is pinned by digest but cannot be rebuilt bit-for-bit, because kompile is nondeterministic.
- **No independent consumer yet:** every level above was recomputed on the producer's VM. The task-07 hand-off (a fresh agent with the bundle only, then a human with a stopwatch, producing the list of what was missing) is the next step.
- **Semantics adequacy is assumed:** the KEVM OSAKA schedule models PRAGUE + CLZ only. GemJoin uses no post-Shanghai opcode (checked by disassembly). Gas is not modelled.

## Variant B (Lean), separate from the ladder above

- **Theorem:** `GemJoin.Ilk.ilk_correct`, over EVMYulLean @ `56253eb4` + 5 patches. Three of the patches are proved equal to upstream. The other two are named trusted-base assumptions: the jump-destination fuel, and the zero-byte FFI.
- **Axioms:** `[propext, Classical.choice, Quot.sound]`. No `sorry` and no `native_decide`. The Lean bytecode equals the bundled artifact. The kernel rejects 3 mutants (wrong slot, wrong selector, non-zero call value).
- **Narrowing:** fixed entry gas (30M), empty entry substate.
- **Cost:** about 10 min to build from scratch, peak about 6 GB. Most of it is kernel evaluation of the 1,596-step jump-table scan.
- **Status:** staged as the next bundle version. It needs a new φ version and the oracle's re-signature.

## Findings the pilot produced (feed into milestones and risks)

1. **The checker is the largest outside dependency.** It is a ~5 GB docker image and cannot be rebuilt bit-for-bit. A certificate-producing checker (Lean, variant B) is the path to self-containment.
2. **Proof claims must match reachable states.** Two of the August claims were non-vacuous but unreachable (empty storage). The pilot restated them over reachable configurations, and both still prove.
3. **The fork pin matters.** The August proofs used SHANGHAI semantics, while mainnet runs Osaka. Declaring "osaka" for them would have been a false green. All claims were re-proved under OSAKA.
4. **Provenance must be recorded hermetically.** Undeclared imports and script edits during assembly made most ledger events unreplayable. Tool hashes and imports must be captured automatically.
5. **Verification cost:** about 1.5 h, sequential. Parallel claim checking is expected to cut this about 3×.

## Pointers (on the VM `tcg`, `~/sheaf/tcg/pilot/`, not yet committed or pushed)

- `bundle/` holds the bundle (root `ef3cab53…`, 381 children). `verifier/` holds the verifier (frozen `f7bde819…`).
- `handoff/ladder_A.json` and `ladder_A.md` hold the ladder. `HARD_STATUS.md` and `variant_b/STATUS.md` hold the working records.
- `tasks/bundle_pilot/` holds the task set, the plan and a snapshot of TCG v3.
