# Finding 0003b — GemJoin's getters, made whole: the FULL k-dss behaviour proves on the lemma-equipped substrate (Track P0.5b)

- **Date:** 2026-08-19 · **Type:** coverage upgrade (side-effect-free half → full k-dss behaviour) + a discriminator control on the return-value equality itself · **Substrate:** the **lemma-equipped** kompiled KEVM Haskell backend, `~/toolchains/kevm-1.0.678-lemmas` (Finding 0004; `theory/patches/{ghost,lemmas}.diff` vendored and pinned in `toolchain.lock`) · **Builds on:** Finding 0003a (the side-effect-free half, proved without lemmas) and Finding 0004 (the simplification lemmas that were expected to remove the wall) · **Subject:** the same MakerDAO `GemJoin` ETH-A runtime bytecode, `0x2F0b23f53734252Bda2277357e97e1517d6B042A`, 3462 bytes, on-chain `EXTCODEHASH` `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa` (independently re-derived below, not taken on faith from either prior finding).
- **TL;DR:** Finding 0003a proved "side-effect-free" for `vat()`/`ilk()`/`gem()` — succeeds, touches no storage, returns to the same frame — but left the return value unconstrained, because the pre-lemma definition could not reduce the byte/memory algebra that connects `<output>` back to the stored slot. This finding re-adds that conjunct. All three getters' **FULL** claims — side-effect-free **AND** `<output>` equals the exact stored (and, for the two address getters, 160-bit-masked) slot value — reach a real prover **Accept (`#Top`)** on the lemma-equipped definition. The exact RHS that reduces needed one addition beyond the "obvious" `#buf(32, #lookup(STORAGE, slot))` form: an explicit `#rangeUInt(256, #lookup(STORAGE, slot))` fact in `requires` (true of any real EVM storage word, since only 256-bit words are ever `SSTORE`d) — without it, the single simplification lemma that folds `#padToWidth(32, #asByteStack(V))` into `#buf(32, V)` does not fire, because its own side condition is exactly that fact and the symbolic `Map` lookup carries no bound on its own. A **discriminator control** (a getter claiming the *wrong* slot's value) confirms the equality is genuinely load-bearing: none of the three wrong-slot variants prove. k-dss behaviours #1–#3 (`vat()`/`ilk()`/`gem()`) move from "half covered" to **FULLY covered**.

---

## Setup (reproducible)

| | |
|---|---|
| Prover | `kprove` (Haskell backend), one invocation per goal claim |
| Definition | `~/toolchains/kevm-1.0.678-lemmas/haskell` (the **lemma-equipped** definition Finding 0004 built and pinned — **not** the plain `kevm-1.0.678` Finding 0003a used); `-I …/evm-semantics-source -I …/plugin` |
| Toolchain (pinned) | k `v7.1.337` · kore-exec `0.1.155` · kevm `1.0.678` · z3 `4.16.0` · replay `{retries: 2, timeout_seconds: 3600}` |
| Runner | `PYTHONPATH=<repo> python3 -m tcg …` (pyenv 3.12.2), `tcg init --definition ~/toolchains/kevm-1.0.678-lemmas/haskell -I …/evm-semantics-source -I …/plugin` (pins the lemma definition into `toolchain.lock`, the point of Track P0) |
| Judge | the solver, never prose — every verdict below is `kprove`'s exit + log, through the shared `tcg.verdict.classify()` |
| Subject bytecode | `tests/reference/getters/subject/runtime.hex` — **reused unchanged** from Finding 0003a (same 3462-byte fetch); not duplicated into a second copy since the bytecode did not change |
| Strengthened claims | `tests/reference/getters-full/src/{vat,ilk,gem}/{name}.k` (root) + `{name}_g.k` (guar, identical restatement — same convention Finding 0003a used); kept as a **separate `getters-full/` subdirectory**, not an in-place edit of `tests/reference/getters/` — the side-effect-free bundle stays reproducible exactly as Finding 0003a recorded it, and the two coverage levels (half vs. full) stay independently buildable and diffable |
| New interfaces | `tests/reference/getters-full/iface/{vat,ilk,gem}.json` |
| Discriminator control | `tests/control/getters-full/wrong-slot.k` (3 standalone modules, run directly via `kprove`, not part of any bundle — same pattern as Finding 0004's `false-identities.k`) |
| Build script | `scripts/build-getters-full.sh` (mirrors `scripts/build-reference.sh`'s shape: init → per-getter loop/iface/compile/prove/vacuity → subject/approve/graph/freeze → self-verify) |
| Workspace | `/private/tmp/.../scratchpad/getters-full-ws` (throwaway, outside the repo) |

---

## The claim shape (full behaviour)

Same as Finding 0003a's side-effect-free claim (concrete selector, `<callValue>` 0, symbolic `<id>`/`<caller>` over the full 160-bit range, storage fully symbolic `STORAGE:Map`, `<callStack>` pinned `.List` before/after, program bound to the full 3462-byte runtime) with two changes: (1) the postcondition's `?OUT` is no longer abstracted — it is equated to the exact return-value expression; (2) `requires` carries one added fact per getter, `#rangeUInt(256, #lookup(STORAGE, <slot>))`.

```
requires 0 <=Int ACCTID andBool ACCTID <Int (2 ^Int 160)
 andBool 0 <=Int MSGSENDER andBool MSGSENDER <Int (2 ^Int 160)
 andBool #rangeUInt(256, #lookup(STORAGE, <slot>))
ensures ?SC ==K EVMC_SUCCESS
 andBool ?OUT ==K <return-value expression>
[label(<name>), all-path]
```

**Why the `#rangeUInt` fact is necessary, not decorative** (established empirically, not guessed — see "the wall inside the wall" below): `bytes-simplification.k` line 282 carries
`rule #padToWidth(32, #asByteStack(V)) => #buf(32, V) requires #rangeUInt(256, V) [simplification]`. This is the ONE rule that folds the raw memory content KEVM's own `MSTORE`/`RETURN` semantics produce (`#padToWidth(32, #asByteStack(V))`) back into the idiomatic `#buf(32, V)` form the `ensures` clause is written in. Its side condition needs `V` (here, a `#lookup(STORAGE, slot)` term, possibly `&Int`-masked) provably in `[0, 2^256)`. A raw symbolic `Map` lookup carries no such bound on its own — real EVM storage cells only ever hold 256-bit words (every `SSTORE` truncates to a word), so the fact is unconditionally true of any *real* storage cell, but it is not *derivable* from the claim's other hypotheses without being stated. Once stated, the fold fires, both sides of the return-value equality reduce to the same `#buf(32, …)` normal form, and the remaining `#buf`/`&Int` arithmetic closes via the vendored `BYTES-SIMPLIFICATION`/`EVM-INT-SIMPLIFICATION`/`BITWISE-SIMPLIFICATION` submodules (Finding 0004).

**Return-value expression per getter** (confirmed against `cast disassemble` of the real runtime, not assumed from the getter's Solidity type alone — see the disassembly table below):

| getter | slot | return-value expression (the exact RHS that reduced) | shape |
|---|---|---|---|
| `vat()` | 1 | `#buf(32, #lookup(STORAGE, 1) &Int maxUInt160)` | address — 160-bit masked |
| `ilk()` | 2 | `#buf(32, #lookup(STORAGE, 2))` | bytes32 — raw, unmasked |
| `gem()` | 3 | `#buf(32, #lookup(STORAGE, 3) &Int maxUInt160)` | address — 160-bit masked |

---

## Confirming the mask/no-mask shape against the real bytecode (not assumed)

`cast disassemble` on the exact installed `subject/runtime.bin` (code region only — the tail CBOR metadata, bytes 3410–3462, is stripped before disassembly since it is not valid opcode stream and a strict disassembler chokes on it; this does not touch the region of interest, which ends at byte 0x0a60 = 2656):

| getter | trampoline (pc) | body (pc) | body opcodes | double-AND in the ABI return-formatter? |
|---|---|---|---|---|
| `vat()` | `0x00af`–`0x00b6` | `0x0323`–`0x0348` | `PUSH1 0x01 PUSH1 0x00 SWAP1 SLOAD SWAP1 PUSH2 0x0100 EXP SWAP1 DIV PUSH20 0xffff…ff AND DUP2 JUMP` | yes — `0x00bc`–`0x00ea`: `DUP3 PUSH20 …AND PUSH20 …AND DUP2 MSTORE` (idempotent double mask, harmless) |
| `ilk()` | `0x02b7`–`0x02be` | `0x0a5b`–`0x0a60` | `PUSH1 0x02 SLOAD DUP2 JUMP` | no — `0x02c0`–`0x02c6`: `DUP1 DUP3 DUP2 MSTORE` (raw value, no AND) |
| `gem()` | `0x0195`–`0x019c` | `0x08e3`–`0x0908` | `PUSH1 0x03 PUSH1 0x00 SWAP1 SLOAD SWAP1 PUSH2 0x0100 EXP SWAP1 DIV PUSH20 0xffff…ff AND DUP2 JUMP` | yes, identical shape to `vat()` |

The prologue (`PUSH1 0x80 PUSH1 0x40 MSTORE`, pc 1–5) confirms the standard free-memory-pointer convention (0x80), so each getter's `RETURN` reads back exactly the word its own body computed — no other memory traffic is on the path. `EXP` with a concrete `0x0100`/offset-`0` exponent argument is the identity (`W ^Word 1 = W`, since `256^0 = 1` in the offset-0 case; disassembly confirms `PUSH1 0x00` for the byte-offset before `EXP`, i.e. this getter's stored variable starts at byte 0 of its slot, so no shift is actually applied) — divide-by-1 is a no-op, and the getter's own mask (`PUSH20` `AND`) is the only real transformation `vat()`/`gem()` apply, confirming the `&Int maxUInt160` in the claimed return value is not a guess but a read of the actual opcode stream. `ilk()`'s body has no `EXP`/`DIV`/`AND` at all — a bare `SLOAD`, matching its unmasked RHS.

---

## Results (real prover, this session)

| getter | claim (root) | verdict | wall time | guar claim | verdict | wall time |
|---|---|---|---|---|---|---|
| `vat()` | `vat` (`dc862e90a150…`) | **Accept** (`#Top`) | 53.756s | `vat_g` (`0bcf2db57c9c…`) | **Accept** | 53.680s |
| `ilk()` | `ilk` (`1a0ba9545c80…`) | **Accept** (`#Top`) | 43.510s | `ilk_g` (`23e86d9f9226…`) | **Accept** | 44.554s |
| `gem()` | `gem` (`828438f9bb57…`) | **Accept** (`#Top`) | 62.572s / 63.893s* | `gem_g` (`3557d95eaa26…`) | **Accept** | 64.557s / 66.231s* |

*gem's `tcg prove` was run twice this session: once inside the full `scripts/build-getters-full.sh` pipeline (62.572s/64.557s, the numbers used for the delivered bundle), and once standalone during recovery from an interrupted background invocation of that same script (63.893s/66.231s) — both real, independent `kprove` invocations, both Accept, consistent within normal wall-time variance. No verdict was assumed or carried over between the two; each is a fresh solver run.

**Vacuity (roots only):** all three falsified mutants (`ensures false`, antecedent kept) came back **Unknown(c)** (residual implication, not `#Top`) — i.e. **non-vacuous**: `vat` 19.941s, `ilk` 20.035s, `gem` 19.209s (from the clean pipeline run; independently re-confirmed at 21.801s/23.178s/22.374s in a second pass — same verdict both times).

**Program binding + graph:** `tcg graph check` → `OK (6 node(s), 0 edge(s), 3 root(s))` — all three roots' `<program>` cells text-match `subject/runtime.bin` byte-for-byte.

---

## The discriminator: a wrong-slot claim must NOT prove

This is the mandatory non-vacuity check on the return-value equality **itself** — a probe of a different kind than the vacuity gate above (which checks the *antecedent* is feasible; this checks the *consequent*'s specific binding is actually being discharged, not passing for some unrelated reason). `tests/control/getters-full/wrong-slot.k` is a byte-for-byte copy of each real, Accepted claim — same program, same calldata (same selector), same symbolic caller/id range, same storage frame — with exactly one change: the `ensures` return-value equality names a **different** stored slot than the one the getter body actually reads.

| module | claims getter | claims (wrong) slot | verdict | residual (the actual undischarged obligation) |
|---|---|---|---|---|
| `WRONG-SLOT-VAT-SPEC` | `vat()` (reads slot 1) | slot 2 (ilk's) | **NOT Accept** (exit 1, `WarnStuckClaimState`) | `#Not({ maxUInt160 &Int #lookup(STORAGE,1) #Equals maxUInt160 &Int #lookup(STORAGE,2) })` |
| `WRONG-SLOT-ILK-SPEC` | `ilk()` (reads slot 2) | slot 3 (gem's) | **NOT Accept** (exit 1, `WarnStuckClaimState`) | `#Not({ #lookup(STORAGE,2) #Equals #lookup(STORAGE,3) })` |
| `WRONG-SLOT-GEM-SPEC` | `gem()` (reads slot 3) | slot 1 (vat's) | **NOT Accept** (exit 1, `WarnStuckClaimState`) | `#Not({ maxUInt160 &Int #lookup(STORAGE,1) #Equals maxUInt160 &Int #lookup(STORAGE,3) })` |

All three residuals are exactly what is expected: `STORAGE` is a single, fully symbolic `Map` with no relation asserted between two different keys' values, so `#lookup(STORAGE, i)` and `#lookup(STORAGE, j)` (`i =/= j`) are independent symbolic `Int`s that no vendored simplification lemma relates (the lemma set operates on byte/word algebra, not on distinctness/independence of unrelated map keys). None of the three wrong-slot claims Accept. This confirms the real claims' `#Top` is not a vacuous pass or an artifact of an over-permissive lemma — the equality between the getter's actual return value and the *correct* stored slot is genuinely what the solver discharges.

Run: `kprove tests/control/getters-full/wrong-slot.k --spec-module WRONG-SLOT-{VAT,ILK,GEM}-SPEC --definition ~/toolchains/kevm-1.0.678-lemmas/haskell -I …/evm-semantics-source -I …/plugin`. Logs (this session): `/private/tmp/.../scratchpad/wrong-slot-run/WRONG-SLOT-{VAT,ILK,GEM}-SPEC.log`.

---

## Bundle

`tcg freeze` → 25 files, 3 roots, **certificate `sha256(MANIFEST.json)` = `56f83565097a2a52ed5014cfa32393e4dc16046012fec6b5096057fa592434bf`**. `tcg verify <bundle>` — bundle-only replay from a clean invocation — **certificate holds**:

```
step 1 integrity: OK (25 file(s))
step 2 identity: verifier action — compare keccak(subject/runtime.bin) with the on-chain code hash (see assumptions/trust-manifest.json)
step 3 theory: OK (patch hashes match toolchain.lock)
step 4 graph: OK (6 node(s), 3 root(s); root <program> cells bind to subject/runtime.bin)
step 5 replay [1/6]: vat/vat_g Accept
step 5 replay [2/6]: ilk/ilk Accept
step 5 replay [3/6]: ilk/ilk_g Accept
step 5 replay [4/6]: gem/gem_g Accept
step 5 replay [5/6]: gem/gem Accept
step 5 replay [6/6]: vat/vat Accept
step 5 replay: OK (6 node(s) re-proved)
step 5v vacuity [ilk/ilk]: OK (falsified form does not prove: Unknown)
step 5v vacuity [gem/gem]: OK (falsified form does not prove: Unknown)
step 5v vacuity [vat/vat]: OK (falsified form does not prove: Unknown)
certificate holds; step 6 is yours: `tcg roots <bundle>`
```

Step 2 (bytecode identity vs. the on-chain `EXTCODEHASH`) is a verifier action by design (`verify` reads only the bundle, never the chain); performed independently here: `keccak(subject/runtime.bin)` (via `cast keccak 0x<hex>` on the exact installed bytes, stripped of the trailing newline in `runtime.hex`) = `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa` — matches the on-chain `EXTCODEHASH` Finding 0003/0003a recorded from independent RPCs, byte-for-byte.

*Reproducibility note:* an earlier, uninterrupted run of `scripts/build-getters-full.sh` in this same session produced a second, independently self-verifying bundle with a different certificate hash (`2976f498c46b421be046f523ccd47008220096178644670c97723c48af35d308`) — the difference is entirely the `assumptions/oracle-record.json` timestamp (each `tcg approve` stamps the current UTC time, which is part of the hash tree), not a difference in claims, evidence, or verdicts; both bundles' six claims are byte-identical and both replay 6/6 Accept + 3/3 non-vacuous. The certificate hash above (`56f83565…`) is from the bundle actually delivered on this branch.

---

## Updated k-dss coverage table

| k-dss behaviour | Finding 0003 | Finding 0003a | this finding |
|---|---|---|---|
| 1. `vat()` accessor | not covered | half covered (side-effect-free only) | **FULLY covered**: side-effect-free AND `<output> == #buf(32, #lookup(STORAGE,1) &Int maxUInt160)` |
| 2. `ilk()` accessor | not covered | half covered (side-effect-free only) | **FULLY covered**: side-effect-free AND `<output> == #buf(32, #lookup(STORAGE,2))` |
| 3. `gem()` accessor | not covered | half covered (side-effect-free only) | **FULLY covered**: side-effect-free AND `<output> == #buf(32, #lookup(STORAGE,3) &Int maxUInt160)` |

---

## Honest caveats

1. **The `#rangeUInt` requires-fact is an axiom about real storage, not a proved fact inside this claim.** It is true of every EVM storage cell in every reachable chain state (a 256-bit word is all `SSTORE` can ever write), but it is asserted, not derived from KEVM's own storage-cell typing within this claim's scope. This is the same category of move Finding 0004's own control (`reduce-abi-decode.k`) made for its free symbolic `USR`/`WAD` variables (`requires #rangeUInt(256, USR) andBool #rangeUInt(256, WAD)`) — not a new kind of assumption, but worth stating plainly rather than leaving implicit in a claim that otherwise reads as "no assumptions beyond caller/id range."
2. **"No external call" is still a bytecode-inspection fact, not an independent K postcondition** (unchanged from Finding 0003a — `<callStack>` pinned `.List` is the same mild strengthening, not a standalone "no CALL" proof; see that finding's caveat #2 for the full argument, which applies verbatim here since the reachable region did not change).
3. **N=3, one substrate, one session, same trivial SLOAD-then-format shape.** All three getters share the same pattern (either bare `SLOAD` or `SLOAD` + identity-`EXP`/`DIV` + `AND`-mask); this does not predict whether a getter with a non-zero byte offset (a packed storage slot with a real shift, not the offset-0 no-op case here) or a different width (e.g. `uint128`) would need a different RHS shape or a different lemma to close. GemJoin has no such getter — this is a genuine limit of the sample, not a discovered gap.
4. **The double-AND in the return-formatter is exactly idempotent here** (`(X &Int mask) &Int mask` with the same concrete mask both times) and the lemma set closed it without needing an explicit idempotence rewrite in the claim — worth flagging as a positive data point for Finding 0004's "reusable core" characterization, not a new capability being claimed for the lemma set in general.
5. **This does not touch the harder wall.** `join`/`exit`'s positive 1:1 accounting (k-dss #4/#5) still needs an assume-guarantee story for the two external callees (Finding 0003's conclusion, and Finding 0004's own caveat #5, both stand unchanged) — full return-value coverage of the three trivial getters is a real but narrow slice of GemJoin's full behaviour.

---

## Reproduction

```
scripts/build-getters-full.sh                          # full pipeline: 6 Accepts, 3 non-vacuous, bundle + self-verify
# the discriminator (run directly, not part of any bundle):
kprove tests/control/getters-full/wrong-slot.k --spec-module WRONG-SLOT-VAT-SPEC \
  --definition ~/toolchains/kevm-1.0.678-lemmas/haskell \
  -I ~/toolchains/kevm-1.0.678-lemmas/evm-semantics-source -I ~/toolchains/kevm-1.0.678-lemmas/plugin
# (repeat with --spec-module WRONG-SLOT-ILK-SPEC / WRONG-SLOT-GEM-SPEC)
```
