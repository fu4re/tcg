# Finding 0003a — GemJoin's getters, split: the side-effect-free half proves NOW, without lemmas (Track P0.5)

- **Date:** 2026-08-19 · **Type:** partial-coverage measurement + a targeted probe of the P0 lemma wall's exact boundary · **Substrate:** the kompiled KEVM Haskell backend of `docs/substrate.md` (unpatched, current pinned definition — the same one Finding 0003 ran against; no lemmas added) · **Builds on:** Finding 0003 (blind battle audit of GemJoin ETH-A, gate G4), which scored k-dss behaviours #1/#2/#3 (`vat()`/`ilk()`/`gem()`) as **not covered** · **Subject:** the same MakerDAO `GemJoin` ETH-A runtime bytecode, `0x2F0b23f53734252Bda2277357e97e1517d6B042A`, 3462 bytes, on-chain `EXTCODEHASH` `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa`.
- **TL;DR:** Finding 0003 bundled each getter's *entire* behaviour — "returns the stored slot and changes no state" — into one claim, and that claim wedges on the missing byte/memory simplification lemmas. Splitting it into two independent halves — **(a) side-effect-freeness** (succeeds, touches no storage, makes no external call; output left unconstrained) and **(b) correct return value** (output equals the stored slot) — shows the wedge is entirely inside (b). All three getters' **(a) claims reach a real prover Accept** (exit 0, `#Top`) on the exact deployed bytecode, symbolic storage, and a symbolic caller/id over the full 160-bit range, with **zero lemmas added to the pinned definition**. This is a genuine, if partial, upgrade of k-dss coverage items #1/#2/#3 from "not covered" to "half covered, the other half is exactly what Track P0 is closing." The claims are bundled and independently re-verified (`tcg verify`, replay 6/6 Accept, vacuity 3/3 non-vacuous).

---

## Setup (reproducible)

| | |
|---|---|
| Prover | `kprove` (Haskell backend), one invocation per goal claim |
| Definition | `~/toolchains/kevm-1.0.678/haskell` (current pinned definition — **not** the lemma-patched one Track P0 is building); includes `…/evm-semantics-source`, `…/plugin` |
| Toolchain (pinned) | k `v7.1.337` · kore-exec `0.1.155` · kevm `1.0.678` · replay `{retries: 2, timeout_seconds: 3600}` |
| Runner | `PYTHONPATH=<repo> python3 -m tcg …` (pyenv 3.12.2) |
| Judge | the solver, never prose — every verdict below is `kprove`'s exit + log, through the shared `tcg.verdict.classify()` |
| Subject bytecode | `tests/reference/getters/subject/runtime.hex` (copied from the same fetch as Finding 0003's `g4-subject/runtime.hex`; independently re-hashed below) |
| New claims | `tests/reference/getters/src/{vat,ilk,gem}/{name}.k` (root) + `{name}_g.k` (guar, identical restatement — same convention Finding 0003's own auth-revert claims used) |
| New interfaces | `tests/reference/getters/iface/{vat,ilk,gem}.json` |
| Workspace | `/private/tmp/.../scratchpad/p05-ws` (throwaway, outside the repo, same pattern as `scripts/build-reference.sh`) |

---

## The claim shape (part a — side-effect-freeness)

One root per getter (D2), each with: selector concrete in `<callData>` (no ABI-decoded arguments — these getters take none), `<callValue>` 0, `<id>`/`<caller>` symbolic over the full 160-bit range, storage fully SYMBOLIC (`STORAGE:Map`, no arrow — same variable on both sides, so the claim only holds if the map is provably unchanged), `<callStack>` pinned `.List` on both sides (returned to the same top-level frame depth), and the postcondition asserting only `?SC ==K EVMC_SUCCESS`. `<output>` is left **abstracted** (`?OUT:Bytes`, no equality) — that is the entire difference from Finding 0003's original, wedged claim shape. Program-bound to the full GemJoin runtime (`<program> #parseByteStack("0x<runtime hex>")`, checked mechanically by `tcg graph check` / `freeze`'s program-binding gate against `subject/runtime.bin`).

```
claim
  <kevm>
    <k> #execute => #halt </k>
    ...
    <output> _ => ?OUT:Bytes </output>          <- ABSTRACTED, not asserted
    <statusCode> _ => ?SC:StatusCode </statusCode>
    <callStack> .List </callStack>               <- same before/after: returned to top frame
    <callState>
      <program> #parseByteStack("0x<3462-byte GemJoin runtime>") </program>
      <id> ACCTID:Int </id>
      <caller> MSGSENDER:Int </caller>
      <callData> b"<4-byte selector>" </callData>
      <callValue> 0 </callValue>
      ...
    </callState>
    <account>
      <acctID> ACCTID:Int </acctID>
      <storage> STORAGE:Map </storage>            <- no arrow: unchanged, by construction
      ...
    </account>
  requires 0 <=Int ACCTID andBool ACCTID <Int 2^160
   andBool 0 <=Int MSGSENDER andBool MSGSENDER <Int 2^160
  ensures ?SC ==K EVMC_SUCCESS
  [label(<name>), all-path]
```

This proves: **the getter cannot revert, writes no storage, and returns to the same call frame it was entered at, for every caller and every storage state.** It does *not* prove what it returns.

---

## Why this was expected to work (the evidence, not a guess)

Finding 0003 records that the blind agent tried a sibling getter, `live()` (same GemJoin family, slot 5, same dispatch/return-formatter shape as `vat`/`ilk`/`gem`), with the *combined* claim (`ensures ?SC ==K EVMC_SUCCESS andBool ?OUT ==K #buf(32, #lookup(STORAGE, 5))`), and got **Unknown(c)** — abandoned as "stuck." I re-read that captured log (`g4-audit/.tcg/logs/live_get-live_getter-prove.log`, this team's own prior working files, not the oracle) rather than re-deriving it: `kore-exec`'s `WarnStuckClaimState` is the **`TermsUnifiableStuck`** variant — *"the configuration's term **unifies** with the destination's term, but the implication check ... has failed."* The log's own leftover-obligation printout is the value equality alone:

```
#Not({ #range(<mstore'd memory>, #asWord(...), 32) #Equals #buf(32, #lookup(STORAGE, 5)) })
#And <kevm> ... <statusCode> EVMC_SUCCESS </statusCode> ... </kevm>
```

`<statusCode>` is already `EVMC_SUCCESS` **inside** the unified term, not part of the failed obligation. That is a direct, empirical signal that reachability + success + (implicitly, since storage is never rewritten on this path) the storage frame were **not** the wedge — only the byte-buffer equality was. This finding turns that signal into a hypothesis (drop the equality, keep everything else) and confirms it on all three of the actually-scoped getters (`live()` itself was out of scope here — only `vat`/`ilk`/`gem`, per k-dss behaviours #1-#3).

**Storage slots**, confirmed by disassembly (`cast disassemble` + manual opcode trace), not assumed from declaration order alone:

| getter | selector | dispatcher trampoline (pc) | body (pc) | slot | opcodes on the reachable path |
|---|---|---|---|---|---|
| `vat()` | `0x36569e77` | `0x00ae`-`0x00b6` | `0x0322`-`0x0348` | 1 | `JUMPDEST PUSH1 PUSH1 SWAP1 SLOAD SWAP1 PUSH2 EXP SWAP1 DIV PUSH20 AND DUP2 JUMP` |
| `ilk()` | `0xc5ce281e` | `0x02b6`-`0x02be` | `0x0a5a`-`0x0a60` | 2 | `JUMPDEST PUSH1 SLOAD DUP2 JUMP` |
| `gem()` | `0x7bd2bea7` | `0x0194`-`0x019c` | `0x08e2`-`0x0908` | 3 | `JUMPDEST PUSH1 PUSH1 SWAP1 SLOAD SWAP1 PUSH2 EXP SWAP1 DIV PUSH20 AND DUP2 JUMP` |

(slot order matches Solidity declaration order in `GemJoin.sol`: `wards` mapping = slot 0, `vat` = 1, `ilk` = 2, `gem` = 3, `dec` = 4, `live` = 5 — consistent with Finding 0003's own `live()` claim using slot 5.) None of these ranges, nor the shared ABI-return-formatter code each trampoline calls into afterward, contains a `CALL`/`CALLCODE`/`DELEGATECALL`/`STATICCALL`/`CREATE`/`CREATE2` opcode, and no `JUMPI` in this region depends on anything but the concrete dispatch selector — so the executed path is unique and call-free by inspection, for every value of the symbolic `id`/`caller`/storage.

---

## Results (real prover, this session)

| getter | claim (root) | verdict | wall time | guar claim | verdict | wall time |
|---|---|---|---|---|---|---|
| `vat()` | `vat` (`7e65011ee7e5…`) | **Accept** (`#Top`) | 36.805s | `vat_g` (`5bf2e36e6576…`) | **Accept** | 34.554s |
| `ilk()` | `ilk` (`7af7bb727038…`) | **Accept** (`#Top`) | 39.045s | `ilk_g` (`8cbee7ee2b1e…`) | **Accept** | 38.417s |
| `gem()` | `gem` (`9e9d5168a0b4…`) | **Accept** (`#Top`) | 44.427s | `gem_g` (`60b90032f6c8…`) | **Accept** | 40.628s |

**Vacuity (P0-B, roots only):** all three falsified mutants (`ensures false`, antecedent kept) came back **Unknown(c)** (residual implication, not `#Top`) — i.e. **non-vacuous**: `vat` 19.913s, `ilk` 19.793s, `gem` 19.822s. A symbolic-storage, symbolic-caller getter has an obviously feasible antecedent; the probe confirms it rather than just asserting it.

**Program binding + graph:** `tcg graph check` → `OK (6 node(s), 0 edge(s), 3 root(s))` — all three roots' `<program>` cells text-match `subject/runtime.bin` byte-for-byte (P0-A gate, Finding 0002).

**Bytecode identity**, independently re-derived here (not taken from Finding 0003's record): `keccak(subject/runtime.bin)` (installed via `tcg subject set`) = `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa`, computed via `cast keccak 0x<hex>` on the exact installed bytes — matches the on-chain `EXTCODEHASH` Finding 0003 recorded from three independent RPCs.

**Bundle:** `tcg freeze` → 24 files, 3 roots, **certificate `sha256(MANIFEST.json)` = `ce7fd9725621a1ab9c4497cb8e338040383043759535ef8bdd35a38197086893`**. `tcg verify <bundle>` — bundle-only replay from a clean invocation (no workspace state consulted) — **certificate holds**:

```
step 1 integrity: OK (24 file(s))
step 2 identity: verifier action — compare keccak(subject/runtime.bin) with the on-chain code hash (see assumptions/trust-manifest.json)
step 3 theory: OK (patch hashes match toolchain.lock)
step 4 graph: OK (6 node(s), 3 root(s); root <program> cells bind to subject/runtime.bin)
step 5 replay [1/6]: vat/vat_g Accept
step 5 replay [2/6]: gem/gem_g Accept
step 5 replay [3/6]: ilk/ilk Accept
step 5 replay [4/6]: vat/vat Accept
step 5 replay [5/6]: ilk/ilk_g Accept
step 5 replay [6/6]: gem/gem Accept
step 5 replay: OK (6 node(s) re-proved)
step 5v vacuity [ilk/ilk]: OK (falsified form does not prove: Unknown)
step 5v vacuity [vat/vat]: OK (falsified form does not prove: Unknown)
step 5v vacuity [gem/gem]: OK (falsified form does not prove: Unknown)
certificate holds; step 6 is yours: `tcg roots <bundle>`
```

Step 2 (bytecode identity vs. the on-chain `EXTCODEHASH`) is a verifier action by design (bundle-spec: `verify` reads only the bundle, never the chain); I performed it myself, above, exactly as Finding 0003's orchestrator did for the 7-root bundle.

---

## What this does and does not establish

**Established (part a, all three getters, universally quantified over caller/id, symbolic storage):** `vat()`, `ilk()`, `gem()` each (1) cannot revert, (2) write no storage, (3) return control to the same call frame they were entered at — on the real 3462-byte deployed bytecode, with the current, lemma-less kompiled definition.

**Not established here (part b, deferred to Track P0):** that the returned bytes equal the stored slot. That needs `BYTES-SIMPLIFICATION`/`LEMMAS` (or an equivalent memory/byte-buffer reduction), which the current `EDSL` kompiled definition does not carry and cannot import at spec time (Finding 0003's "the wall," reproduced verbatim there — `imports LEMMAS` fails to compile in a proof module). Once Track P0 lands a definition that carries those lemmas, the natural next step is to re-add the `?OUT ==K #buf(32, #lookup(STORAGE, <slot>))` conjunct to these same three claims (the side-effect-free half does not need to be re-proved; the full behaviour is this claim strictly strengthened).

**"No external call" is a bytecode-inspection fact, not an independent K postcondition.** I pinned `<callStack>` unchanged as a mild, correctly-typed strengthening (it asserts the call returned to the same frame depth — matches KEVM's own default value, `evm.md:54`), but by itself that does not rule out an internal call-then-return round trip (the list would read `.List` again after a paired push/pop). The actual "no CALL happened at all" guarantee rests on the disassembly table above (the reachable region is straight-line and call-opcode-free) plus the corroborating empirical fact that the `live()` getter's Unknown(c) run unified successfully without ever needing a second `<account>` entry in `<accounts>` — if a CALL had been on the path, unification itself would have stalled differently (missing callee data), not landed cleanly on the single value-equality obligation. I deliberately did **not** attempt to force this into the ensures clause by closing the `<accounts>` bag (untested here, and risks introducing an unrelated new wall — KEVM's account-existence handling for a closed bag is not something this session characterized) or by building the ghost-cell reentrancy monitor (`theory/patches/ghost.diff`, Finding 0003 §7) — that requires a second, separately-kompiled Haskell backend and is out of scope for a same-day partial-coverage pass. This mirrors exactly how Finding 0003's own revert claims established "before any external call": from the bytecode's PC ordering, not from a K-encoded assertion.

**Coverage update to Finding 0003's table** (k-dss behaviours #1-#3):

| k-dss behaviour | Finding 0003 | this finding |
|---|---|---|
| 1. `vat()` side-effect-free accessor | not covered | **half covered**: side-effect-freeness Accept; return-value half awaits Track P0 |
| 2. `ilk()` side-effect-free accessor | not covered | **half covered**: same |
| 3. `gem()` side-effect-free accessor | not covered | **half covered**: same |

---

## Honest caveats

1. **Genuinely partial.** "Side-effect-free" is real and machine-checked, but it is not the k-dss behaviour as stated (which is conjunctive: side-effect-free *and* returns the slot). Anyone reading the bundled roots sees exactly `?SC ==K EVMC_SUCCESS` and an abstracted `?OUT` — the certificate does not overclaim, but a careless reading of "vat() proved" would.
2. **`<callStack>` pinning is weak**, as explained above — included for rigor, not oversold as a standalone "no call" proof.
3. **N=3, one substrate, one session.** All three getters share the same trivial SLOAD-then-format shape; this does not predict whether a getter with internal branching (none exist in GemJoin, but might in other contracts) would clear as easily.
4. **This does not touch the harder wall.** `join`/`exit`'s positive 1:1 accounting (k-dss #4/#5) still needs both the simplification lemmas *and* an assume-guarantee story for the two external callees (Finding 0003's conclusion stands unchanged).
