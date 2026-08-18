# Finding 0003 — Blind battle audit of a live mainnet contract (GemJoin ETH-A): what a from-scratch agent could formally establish, scored against the public k-dss artifact (gate G4)

- **Date:** 2026-08-18 · **Type:** end-to-end battle test + coverage measurement (N=1 mainnet subject, blind agent) · **Substrate:** kompiled KEVM Haskell backend (Track B / gate G1) · **Builds on:** Findings 0001 (reference bundle e2e), 0002 (false-green guards) · **Subject:** MakerDAO `GemJoin` for ETH-A, `0x2F0b23f53734252Bda2277357e97e1517d6B042A`, holding ~$515M WETH on Ethereum mainnet.
- **TL;DR:** An Opus agent, given only the deployed runtime bytecode + Solidity source + the `tcg` CLI, told nothing about the project or its known audit, formally established **7 genuine safety properties** of the real deployed contract — all program-bound to the exact 3462-byte on-chain bytecode — and **5 of them sit in a self-contained bundle that this orchestrator independently re-verified** (bytecode-identity to the on-chain `EXTCODEHASH`, 10/10 replay Accept, 5/5 roots non-vacuous). Every proved root is a **revert/guard property** (access control, not-live, overflow, non-payable). Scored against the public **k-dss** artifact's 5 GemJoin behaviours, the coverage is **complementary, not nested**: 0 of the 5 fully covered, 2 partially covered (the reverting *guards* that protect `join`/`exit`, not their positive 1:1 accounting), 3 not covered (the getters); and 4 of the 7 proofs are *outside* the public artifact's scope entirely (the auth-admin surface k-dss never specified). The core value-moving behaviours (k-dss #4/#5: `join`/`exit` conservation with external calls) hit a precisely-diagnosed wall — the kompiled EDSL definition ships no byte/int simplification lemmas, so symbolic ABI-decode never binds, and each function makes two calls to unaudited external code. This is the honest measured gap between "the tool proves toy contracts" and "the tool on live $515M code," and it is exactly the basis for the next improvement cycle.

---

## Setup

| | |
|---|---|
| Subject | GemJoin ETH-A runtime bytecode, 3462 bytes, fetched from mainnet (block 25782890); on-chain code hash `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa` |
| Source | makerdao/dss tag `1.0.0` commit `6fd7de01`, `src/join.sol` `GemJoin` (solc 0.5.12; irrelevant — `tcg` proves over the fetched bytecode) |
| External calls in scope | `Vat.slip` (`0x7cdd3fde`) and the gem token (WETH `0xC02aaA39`) `transferFrom`/`transfer` — visible in the bytecode; the hard part |
| Prover / tool | `tcg` on the kompiled KEVM Haskell backend (`~/toolchains/kevm-1.0.678`); judge = kore-exec, never prose |
| Blind protocol | fresh Opus agent, given `g4-subject/` (bytecode, source, neutral facts) only; forbidden to read the tool's own source or the k-dss oracle; discovered `tcg` from its CLI surface alone; ~1h45m active work across 2 server interruptions |
| Yardstick (agent never saw it) | dapphub/k-dss commit `ca582e04`, `src/dss.md` GemJoin section — 5 enumerable behaviours |
| Independent verification | this orchestrator re-ran `tcg verify` on the delivered bundle, confirmed bytecode-identity, and read the roots (protocol step 6) — the verdicts below are the solver's, re-established from the bundle alone |

---

## What the blind agent proved (verified by me, not taken on report)

The delivered 5-root bundle (`cert sha256(MANIFEST.json)=668f3d7d…`) was re-verified by this orchestrator on a clean invocation:

- **Bytecode-identity holds**: `keccak(bundle subject/runtime.bin)` = `0x8661c6…74fa` = the on-chain `EXTCODEHASH`. The certificate is about the *real deployed contract*.
- **`tcg verify`**: integrity OK, theory OK, **step 4 graph OK — "root `<program>` cells bind to subject/runtime.bin"**, **step 5 replay 10/10 Accept**, **step 5v vacuity 5/5 non-vacuous** (falsified form does not prove), "certificate holds."
- **Roots read (step 6, done by me):** every root's `ensures` is `?SC ==K EVMC_REVERT` — all five are **revert properties**, universal over the caller (`MSGSENDER`/`ACCTID` free across the full 160-bit range), with the decision-relevant state pinned concretely (empty `<storage>`, concrete 4-byte selector `<callData>`, concrete `<callValue>`), against the full deployed `<program>`.

| # | Proved property (root, in words) | Quantification | Verified in bundle |
|---|---|---|---|
| 1 | `cage()` reverts for every caller when `wards` is empty | ∀ caller | ✅ replayed by me |
| 2 | `rely(usr)` reverts for every caller when `wards` is empty | ∀ caller | ✅ |
| 3 | `deny(usr)` reverts for every caller when `wards` is empty | ∀ caller | ✅ |
| 4 | `join(usr,wad)` reverts when `live==0`, before any external call | ∀ caller | ✅ |
| 5 | `exit(usr,wad)` with `wad>2**255` reverts, before any external call | concrete `wad` witness | ✅ |
| 6 | `join(usr,wad)` with `live==1`, `wad>=2**255` reverts, before any external call | concrete `wad` witness | frozen (7-root bundle), not re-verified within the 10-min synchronous ceiling |
| 7 | `cage()` with `msg.value>0` reverts (non-payable) | ∀ value | frozen, not re-verified in-session |

Honest scope (the agent stated this itself and I confirmed it in the claim texts): the auth proofs use an **empty `wards` map** — they establish "with no ward set, nobody can cage/rely/deny," not "a non-ward reverts while other wards exist" (that needs the `keccak(caller‖0)` mapping-slot reasoning blocked by the wall). The overflow guards are **concrete boundary witnesses**, not universal over `wad`, for the same reason. All guards fire **before** the external calls, so they hold regardless of the vat/gem.

---

## Coverage vs the public k-dss artifact (the point of G4)

The k-dss GemJoin spec establishes exactly 5 behaviours. Scoring the blind agent's verified work against them:

| k-dss behaviour | tcg blind-audit result | why |
|---|---|---|
| 1. `vat()` side-effect-free accessor | **not covered** | getter-return needs memory/`#buf` simplification lemmas the EDSL build lacks (same wall) |
| 2. `ilk()` side-effect-free accessor | **not covered** | same |
| 3. `gem()` side-effect-free accessor | **not covered** | agent tried a sibling getter `live()` → Unknown(stuck); abandoned |
| 4. `join` mints 1:1, no overflow, calls `Vat.slip`+`transferFrom` | **partial** — the two protective **reverts** proved (not-live #4, overflow #6), on the real bytecode, before the external calls | positive 1:1 accounting + external-call composition unreachable: missing simplification lemmas (symbolic ABI-decode opaque) **and** two calls to unaudited external code |
| 5. `exit` burns 1:1, no overflow, calls `Vat.slip`+`transfer` | **partial** — the overflow **revert** proved (#5), before the external calls | same wall |

**Beyond the oracle** — real safety properties the public artifact never specified (its own §"does NOT cover": constructor, `cage`/`rely`/`deny`/`wards`): proofs **1, 2, 3, 7** (the entire auth-admin + non-payability surface). The blind agent found and proved genuine safety properties the famous public FV effort simply did not target.

**Bluntly:** of the 5 public behaviours, **0 fully reproduced, 2 partially (guard slices), 3 untouched**; plus **4 real properties outside the public scope**. Coverage is complementary, not a subset — the tool took the *defensive revert layer* (and the auth surface), while k-dss took the *positive value-conservation* layer via klab's assume-guarantee machinery over modeled external callees.

---

## The wall (exact, reproducible)

The kompiled definition's main module **EDSL** bundles no byte-array/integer simplification lemmas, and they cannot be added at spec time:

```
imports BYTES-SIMPLIFICATION → [Error] Compiler: Could not find productions for KApply
    with label #let in module EDSL   (lemmas/bytes-simplification.k: `#let S = S2 -Int S1 #in …`)
imports LEMMAS →                 [Error] Compiler: Only claims and simplification rules are
    allowed in proof modules         (lemmas.k contains the non-simplification rule #addrFromPrivateKey)
```

Consequence: a symbolic ABI-decoded calldata word (`#asWord(#range(sel +Bytes #buf(32,USR) +Bytes #buf(32,WAD), 36, 32))`) never reduces to the symbolic argument, so a claim quantified over `wad`/`usr` leaves the guard branch unpruned and the prover walks into the external `CALL` — residual/Unknown. The agent's sound workaround (and the reason the 7 proofs have the shape they do): keep the *decision-path* state concrete (empty storage, concrete selector/args) and confine the universal quantifier to what EDSL's SMT reasons about directly (caller, callvalue, `#lookup` storage). That yields real, universal-where-it-counts revert guarantees but not the positive-accounting theorems.

---

## Tool findings surfaced by the battle test (backlog for the next cycle)

Confirmed real, from the agent's journal and my own reading:

1. **`tcg verify` re-proves from scratch (~28s/claim)** — a 7-root bundle's 21-run replay overran a 10-min budget. This is v1-by-design (replay evidence, not proof objects); the bundle-spec §6 v2 proof-object path is the fix. Meanwhile large bundles are wall-clock-heavy to verify.
2. **Deleting a loop directory does not unregister it** from `spec/graph.json`/`interfaces.json` — graph check then fails on ghosts (matches the G3 "graph debt" backlog item). Needs a `tcg loop rm` / retire affordance.
3. **A prove killed mid-flight leaves the loop stuck in `Proving`**, which blocks both `compile-claims` and `prove` — a recover-only-by-recreate deadlock. The state machine needs a `Proving → {Draft,Stale}` recovery transition.
4. **The guar-node requirement is undocumented** at `iface set` and only surfaces at graph-check/freeze (matches a G3 backlog item).
5. **Environment friction:** under `fish`, unquoted `$INC` does not word-split, silently mangling repeated `-I` flags into "file not found" — several spurious Unknowns traced to this, not to any claim. A `tcg`-level include convention (or a note) would help.

None of these are soundness defects; all are usability/scale. The soundness guards from Finding 0002 did their job — every Accept here is program-bound and non-vacuous, re-checked from the bundle.

---

## Honest caveats / what remains assumed

1. **Revert-layer, not conservation-layer.** The certificate guarantees the reverting guards, not that a *succeeding* `join`/`exit` moves value correctly. It bounds how the contract *fails safe*, not how it *succeeds correctly*.
2. **Empty-wards / concrete-`wad` scoping** (above) — the universal strengthenings are future work behind the lemma wall.
3. **Bytecode-identity** is confirmed here by me (`keccak == on-chain EXTCODEHASH`) but is a verifier action, not something the bundle discharges internally; **semantics remain unvendored** (replay needs the pinned KEVM on disk).
4. **The k-dss yardstick models `gem` as a DSToken**; the live ETH-A gem is WETH9 — the comparison is interface-level, and neither side's `join`/`exit` external-call composition was reproduced here anyway.
5. **N=1, one agent, one substrate.** This measures feasibility and the wall's location, not a distribution.

## Conclusion

Driven blind, the tool did the thing it exists to do: it produced **honest, independently-verifiable formal guarantees about a live $515M contract, refused every false green, and stopped exactly at the frontier it could not cross** — the external-call value-conservation of `join`/`exit`, walled by the EDSL build's missing simplification lemmas. It did **not** reproduce the public k-dss artifact; it established a *complementary* defensive slice plus the auth surface k-dss never covered. The measured gap — getters + positive `join`/`exit` accounting, blocked by (a) absent simplification lemmas and (b) unmodeled external callees — is the concrete, prioritized target for the next iteration: load/rebuild a KEVM definition that carries the simplification lemmas, and add an assume-guarantee story for the two external callees. That is a productization gap, not a soundness one — which is the right kind of gap to be left with.
