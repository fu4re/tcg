# Decision stub (provenance, class U)

- **Written by:** WS-H (hard layer + T-hat), 2026-10-29. Nothing committed.
- **Decisions D1-D11 and P1-P5:** by reference to `DECISIONS.md` (its sha256 + UTC time is ledger event 1). No per-decision evidence links (task 05).
- **Why this file has a second part:** task 02's rule is "nothing in this layer is new content; if a step needs new content, stop and record why here". The steps below each needed new content. Each one is listed with what was added, why, and the prover verdict that admitted it (judge = kprove in the pinned image `sha256:7d4a35bc…c465`, classified by `tcg/verdict.py`; ledger seq numbers are in `provenance/ledger.jsonl` and `provenance/iterations.json`; the producer working log `pilot/HARD_STATUS.md` sits outside the bundle).

## Decisions by reference (task 05: no per-decision evidence links)

All in `DECISIONS.md` (sha256 + UTC time = ledger event 1). D1 content hash · D2 addressing (Merkle DAG, canonical-JSON root) · D3 producer signature (ed25519) · D4 oracle signature over sha256(phi.json) ‖ sha256(requirements.md) · D5 H = the author · D6 Check′ for KEVM = pinned image by Id (variant A) · D7 Check′ for Lean · D8 identity id(b) = keccak256(runtime) at the pinned block · D9 environment for L0 via archive RPC, no snapshot inside the bundle · D10 trust-class labels U / T / T* · D11 not_claimed = the five v3 §10 sentences. Pilot-specific: P1 claim set (3 getters + 2 rebuilt revert roots) · P2 zero real certificates under A · P3 hard layer derived from tcg v1 · P4 no commits during the pilot · P5 consumer isolation.

## Part 2: new content recorded under task 02's rule

## N1. Two revert claims rebuilt (P1)

The Finding-0003 claim sources for `cage()` and `join()` were never committed (the August scratchpad is gone). They were rebuilt from Finding 0003's prose as `provenance/rebuild/src/{cage,join,joinempty}/*.k` with tcg's own claim idiom. This is new content: the original files cannot be compared byte for byte.

## N2. claim-04 generalised to a reachable Pre (orchestrator decision, 2026-10-29)

- **Was:** cage() with EMPTY storage (`<storage> .Map`). No constructed GemJoin is ever in that state, so the claim, although K-feasible, covered no reachable configuration. Vacuity PASS plus unreachable Pre is a reachable-state trap, not a green.
- **Now (`cagews`):** symbolic `STORAGE:Map` plus `#lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0`, i.e. wards[caller] == 0 with every other slot arbitrary. keccak stays opaque in the proof; its meaning is the named assumption `A_keccak` (KEVM keccak = Keccak-256, solc 0.5.12 mapping layout).
- **Command:** `python3 ../tools/assemble_hard.py variant --src provenance/rebuild/controls/cage-cage-prove.k --label cagews --storage-symbolic --requires "#lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0" [--schedule OSAKA] --out-dir …` (ledger seq 8, 10).
- **Bounded attempt:** up to two prove runs were budgeted. It Accepted on the first run under SHANGHAI (235.4 s, ledger seq 17) and under OSAKA (202.1 s, seq 35), vacuity probe NotAccept and discriminator Refute under both. So the fallback to EMPTY storage was not needed. The EMPTY-storage form is kept as a recorded control only (OSAKA: Accept seq 49, vacuity NotAccept seq 51).

## N3. claim-05 generalised to symbolic ABI arguments

- **Was:** join with symbolic storage and live == 0, but ONE concrete (usr, wad) = (0xdead, 1e18).
- **Now (`joinsym`):** calldata `0x3b4da69f ++ #buf(32, USR) ++ #buf(32, WAD)` for every 256-bit USR, WAD (`#rangeUInt(256, ·)`, annotation `Aasm-rangeUInt-args`). The symbolic-storage + live == 0 Pre is the orchestrator's decision for claim-05. The Finding-0003 EMPTY-storage form (`joinempty`) stays as a recorded control.
- **Command:** `python3 ../tools/assemble_hard.py variant --src provenance/rebuild/controls/join-join-prove.k --label joinsym --calldata 'b"\x3b\x4d\xa6\x9f" +Bytes #buf(32, USR:Int) +Bytes #buf(32, WAD:Int)' --requires "#rangeUInt(256, USR)" --requires "#rangeUInt(256, WAD)" [--schedule OSAKA] --out-dir …` (ledger seq 9, 11).

## N4. Re-proof of all five claims under `<schedule> OSAKA </schedule>`

- **Why:** mainnet at the pinned block 26298481 runs osaka execution rules (`eth_config`, 3 RPCs). The original claims say SHANGHAI. Declaring `fork: osaka` over SHANGHAI proofs would be a false green on L0-environment.
- **Rule (orchestrator):** ship OSAKA only if all 5 Accept under OSAKA with clean vacuity probes and discriminators; otherwise ship SHANGHAI with `fork: shanghai` and let L0-environment fail honestly.
- **What KEVM OSAKA is:** PRAGUE + EIP-7939 (CLZ) only (`provenance/kevm_osaka_adequacy.json`). Its gaps against mainnet osaka are named in T-hat (`semantics[0].adequacy_evidence`, `A_osaka_model`, `A_blob_params`). GemJoin uses no post-Shanghai opcode (`provenance/opscan.json`).
- **Outcome:** all 5 shipped claims Accept under OSAKA (seq 35, 37, 41, 42, 48). Every vacuity probe is NotAccept (exit 1), every discriminator is Refute, and the three getter wrong-slot controls are NotAccept. The SHANGHAI matrix gives the same verdicts. The pre_witness replay under OSAKA exits 0 (seq 63). **The bundle ships OSAKA** (`environment.fork: osaka`, `hard/spec/claim-0N.k` carry `<schedule> OSAKA </schedule>`). The SHANGHAI re-proof is kept as provenance (`provenance/rebuild/results/matrix-shanghai/`). This is evidence that KEVM's OSAKA and SHANGHAI agree on these paths. It is NOT evidence that KEVM OSAKA equals mainnet osaka (A_osaka_model).

## N5. requirements.md (n)

Written by the producing agent as a DRAFT for the author. It is new content by nature. It is NOT signed; the oracle signs it (D4) after the author's review.

## N6. Evidence-layer choices (WS-H, task 04 minus mutants)

- **pre_witness copied, not moved,** to `evidence/pre_witness/` (ledger seq 69, byte-identical). The original under `provenance/rebuild/pre_witness/` stays, so ledger events 27-29 and 63 remain replayable at their recorded paths. tbase + rehash re-run on the new location (seq 70-71).
- **Back-translation input stripped.** The translator got a copy of phi.json without the fields that describe requirements or carry producer judgement (declared_blind_spots, reading_guide, status, requirements_file/sha256, per-claim coverage_of_requirements, caveats, controls, observed, source; 30 removals, `provenance/sessions/bt-input.strip_record.json`). Requirement ids were kept. A 6-word-shingle check against requirements.md found 0 hits.
- **Coverage total = false, kept, not hidden.** `evidence/coverage.json` (WS-A's coverage.py) reports R4 and R5 as `blind_spots_actually_covered`: phi.json lists them both as claimed (claims 04/05) and as declared blind spots with `partial: true`, because each claim covers only part of the requirement. The verifier's rule has no notion of partial coverage. Making total = true would need either dropping the partial blind-spot entries (which hides the uncovered remainder of R4/R5) or a schema change. Left for the orchestrator / WS-A to decide; phi.json was not changed.
- **Agreement left "unclear"** for every back-translated claim. Judging agree/disagree is H's job.
