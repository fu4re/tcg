# Finding 0006 — Call-site value-conservation, P1: the bridge lands and the token leg proves, but the signed-add Vat leg hits the substrate implication ceiling

- **Date:** 2026-08-19 · **Type:** implementation + measurement (the P1 build-out following the Finding-0005 probe) · **Substrate:** kompiled KEVM Haskell backend `kevm-1.0.678`; bridge on the stock def, callee summaries on the lemma-equipped def (`-lemmas` and the new `-lemmas2`) · **Builds on:** Findings 0003 (the GemJoin wall), 0004 (simplification lemmas), 0005 (the call-site-summary probe + the `S ⟸ D` bridge obligation) · **Subjects:** the `callext` toy (bridge), live mainnet **WETH9** `0xC02aaA39…756Cc2` (token leg), live mainnet **Vat** `0x35D1b3F3…492B` (value leg).
- **TL;DR:** The three pieces the value-conservation coverage needs were built and measured independently. **(1) The bridge `S ⟸ D` is implemented in `graph`/`freeze`/`verify` and merged** (`Track P1-A`): an abstract callee-summary node `S` (free `<program>`, which can never Accept) is discharged by a concrete proof `D` over code `P`, a verifier-computed code-identity `keccak256(P)=code_hash`, a bridge-at-`P` proof `B`, and an anti-proxy binding `S⟺B` — re-derived bundle-only; **all five anti-proxy discriminators refuse**, including two hash-tree-consistent tampers a self-consistent MANIFEST does not launder. **(2) Both WETH9 token-leg summaries prove over the real 3124-byte bytecode** (`transferFrom` for `join`, `transfer` for `exit`), non-vacuously, once the omitted bool2Word + map-reasoning `[simplification]` lemmas are supplied. **(3) The Vat `slip` summary does not.** After the bool2Word lemma wall (Finding 0004) is removed by a properly-vendored, consistency-gated def extension, `slip` reaches the exact `+wad` storage delta over the real Vat but the postcondition never Accepts — it hits the **§9 substrate implication ceiling** on the signed `_add` split: `slip_d`, `slip_wrong`, and `slip_vac` **all** surface as `Unknown(c)`, so the summary is neither positively discharged nor structurally refuted (the Finding-0001/D5 blind spot). This is the honest frontier: the lemma tail was necessary but not sufficient, and closing `slip` needs substrate work (kore-rpc `implies` / pyk `APRProof`) deliberately not undertaken here. **`join`/`exit` positive accounting (k-dss #4/#5) is therefore substrate-blocked on the Vat leg.**

---

## Setup

| | |
|---|---|
| Bridge subject | `tests/reference/callext` toy — a mini-`join` `CALL`ing a mini-`slip` (Finding 0005); bridge exercised on the **stock** def `~/toolchains/kevm-1.0.678` |
| Token-leg subject | WETH9 `0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2`, runtime 3124 bytes, on-chain `EXTCODEHASH` = `keccak256(runtime)` = `0xd0a06b12ac47863b5c7be4185c2deaad1c61557033f56c7d4ea74429cbb25e23` (3 RPCs + independent keccak agree) |
| Value-leg subject | Vat `0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B`, runtime 13493 bytes, on-chain `EXTCODEHASH` = `keccak256(runtime)` = `0x808b98f6475736d56c978e4fb476175ecd9d7abdab0797017fc10c7f46311a59` |
| Def (callee summaries) | lemma-equipped `~/toolchains/kevm-1.0.678-lemmas` (Finding 0004), extended here to `-lemmas2` (adds a bool2Word `[simplification]` submodule) |
| Judge | the solver via `tcg.verdict.classify()` — the same judge `prove`/`verify` use. Accept = exit 0 + `#Top`; Refute = structural non-unification; `Unknown(c)` = unifies-but-implication-undischarged |
| Independent verification | this orchestrator re-verified every verdict below on its own invocation: keccak anchors, bridge `verify` + 5 discriminators, WETH 6 summary/discriminator verdicts, slip 3 verdicts, consistency gate 5/5, the def differential |

The three pieces were built by three subagents (bridge; Vat.slip; WETH); this orchestrator reviewed each diff and reproduced each verdict. The bridge is merged to `main`; the callee-summary work is banked on branches (`p1-b-vat-slip`, `p1-c-weth`), referenced below.

---

## 1. The bridge `S ⟸ D` (implemented, merged, discriminated)

Finding 0005 located the exact residual: tcg's closure demanded every trusted-lemma-reachable node be Accepted, but a call-site summary `S` must abstract `<program>` (a free variable, to unify with the stalled symbolic-code CALL frame) and so **can never Accept**. The fix discharges `S` structurally instead of demanding it Accepted. Three obligations, all re-derived **bundle-only**:

1. **D** — a concrete callee proof of the delta over code `P`, Accepted in its own loop, `<program> == P`.
2. **code-identity** — `keccak256(external_code[callee]) == code_hash`, **computed by the verifier** (`tcg/keccak.py`, real Keccak-256, validated against known vectors — *not* `hashlib.sha3`), and `external_code[callee] == D`'s `== B`'s `<program>` byte-for-byte.
3. **B (bridge-at-P)** — `S` instantiated with `<program> := P` proves by execution over the real bytecode, Accepted.

Plus the **anti-proxy binding `S⟺B`** (`tcg/bridge.py:binding_errors`): `B` agrees with `S` cell-for-cell on every entry/effect `S` pins, carries `S`'s exact callee storage delta, and is at least as general as `S` at entry — bound by **content hash**, not name. Wiring: `graph.py` closure discharges the bridge node and pushes `D`/`B` as ordinary Accept-required nodes; `freeze.py` exempts `S` from replay evidence and records a `bridge_S_from_D` trust-manifest entry (present only when a bridge node exists, so other bundles are byte-identical); `verify.py` re-derives the structural + keccak check from the bundle and replays `D`+`B`+caller, skipping `S`.

**Verified (this orchestrator, on `run-tcg-bridge*.sh`):** `caller_2a` — `graph check` OK, `freeze` OK, **`verify` HOLDS** ("1 abstract-summary node bridge-discharged S⟸D"; `D`+`B`+caller replayed, `S` not replayed, vacuity OK). All **five discriminators refuse (7/7 assertions):**

| # | Discriminator | Refused because |
|---|---|---|
| 1 | broken-summary `+6` | `B` **Refutes over P** (the caller Accepts the false lemma; the bridge catches it) |
| 2 | wrong-code-identity | `keccak256(P') = f437cdf9… ≠ a7d0eaef…` — a **hash-tree-consistent tamper** (MANIFEST rehashed), caught only by semantic re-derivation |
| 3 | proxy-swap `+0` no-op | `B` Refutes over P (a plausible-but-false summary cannot ride through) |
| 4 | undischarged (bridge stripped) | verify demands replay evidence `S` can never have — hash-tree-consistent tamper, no regression to a false green |
| 5 | compat-broken | interference obligation Refutes |

No collateral regression: `conformance` 6/6 (the non-bridge path is byte-intact), `lemma-consistency` 4/4, `false-green` both G3 holes caught, 16 new structural unit tests.

**Trusted-base delta (named):** the declared `code_hash == on-chain EXTCODEHASH` is a chain read — a verifier action, exactly the residual `subject_identity` already leaves for the primary subject. Everything else the bridge performs (keccak, the binding, `D`/`B` Accept) is discharged.

---

## 2. The WETH9 token-leg summaries (proved over the real bytecode)

`join` calls `WETH.transferFrom(usr, adapter, wad)`; `exit` calls `WETH.transfer(usr, wad)`. Both proved over the exact 3124-byte on-chain WETH9 `<program>` (identity anchor above, re-checked by this orchestrator):

| spec | judge | verdict |
|---|---|---|
| `transferFrom_d` (join leg) | `-lemmas` + omitted-lemma subset | **Accept** — `balanceOf[usr] -= wad`, `balanceOf[adapter] += wad`, EVMC_SUCCESS, `return 1` |
| `transfer_d` (exit leg) | same | **Accept** — `balanceOf[adapter] -= wad`, `balanceOf[usr] += wad`, EVMC_SUCCESS, `return 1` |
| `transferFrom_wrong` / `transfer_wrong` (delta `+wad+1`) | same | Unknown — **NOT Accept** |
| `transferFrom_vac` / `transfer_vac` (`ensures false`) | same | Unknown — **NOT Accept** |

**Scope (honest):** `wad` universal over uint256 and over symbolic storage; `src`/`dst`/`msg.sender` **concrete-pinned** (usr, adapter) so keccak is a concrete constant — the ±wad delta is proved at the opaque slot constants, a schema instantiable at any concrete pair with `src ≠ dst` (klab's concrete-key discipline). `transferFrom` takes the **infinite-allowance** precondition (`allowance[usr][adapter] = 2^256−1`), skipping the allowance-decrement branch (finite-allowance is a documented extension). No external CALL in either → the reentrancy frame holds trivially. `src == dst` aliasing excluded by construction.

**Why it proves and slip does not:** WETH's arithmetic is **unsigned** (`require(bal ≥ wad); bal -= wad`), which after bool2Word + map-reasoning closes to Accept. The Vat's is **signed** `_add` (§4).

---

## 3. The lemma tail — extended, gated, conservative (bool2Word); the second family (map-reasoning)

The Finding-0004 driver imports four pure `[simplification]` submodules but omits upstream `lemmas/lemmas.k` (module `LEMMAS-WITHOUT-SLOT-UPDATES`). Two omitted families were needed here, each pinned to a concrete wall:

- **(A) bool2Word** — `require(bal ≥ wad)` / signed `_add`'s guard compiles to nested `bool2Word(bool2Word(… ==Int 0) …)` that never reduces. Fix: `[b2w-eq-zero]` (`lemmas.k:71`), `[b2w-eq-one]` (`l.72`). **This is the Finding-0004 Vat.slip wall, independently re-hit by WETH.**
- **(B) map-reasoning** (new to the two-slot token legs; the one-SSTORE `slip` never hit it) — the second balance read over the updated map `#lookup(STORAGE[K1<-_], K2)` never reduces. Fix: the `#lookup` lookup-over-update + range rules (`lemmas.k:125-130`).

**Delivered (bool2Word, merged discipline, on `p1-b-vat-slip`):** a 5th `[simplification]`-only submodule extracted **verbatim** from `lemmas.k:58-111`, imported by the driver, rebuilt to `~/toolchains/kevm-1.0.678-lemmas2` (old `-lemmas` untouched). It deliberately does **not** import `LEMMAS-WITHOUT-SLOT-UPDATES` wholesale — that module carries the non-simplification `#addrFromPrivateKey [priority(40), concrete]` rewrite (`lemmas.k:137`), the exact P0 trap. **Verified by this orchestrator:** the differential (`b2w-eq-zero` occurs 4× in the new `definition.kore`, 0× in the old); the consistency gate at **5/5** on the new def (the four Finding-0004 false identities plus a new wrong-direction bool2Word probe, all refused); full regression unchanged (getters-full 6/6, build-reference, `conformance` 6/6 — logs committed). The map-reasoning family (B) is currently supplied to the WETH proofs as a spec-time import (`callee-proofs/weth/specs/lemmas_min.k`, verbatim upstream); folding it into the def is a small, non-substrate residual that would make the WETH summaries prove def-only.

---

## 4. The frontier — Vat `slip` hits the §9 substrate implication ceiling

`slip(bytes32 ilk, address usr, int256 wad)` sets `gem[ilk][usr] = _add(gem[ilk][usr], wad)` (signed `_add`), auth-gated. Proved in its own loop over the real 13493-byte Vat `<program>`, keccak-bound, keccak treated as an uninterpreted opaque slot (concrete-pinned `ilk`/`usr`; `wad` universal over non-negative int256 = `join`'s sign).

On the bool2Word-extended `-lemmas2` def, the bool2Word REVERT wall is **gone** — `slip` reaches `EVMC_SUCCESS` and the exact `+wad` storage delta over the real Vat. But the postcondition never Accepts. **Verified (this orchestrator, `-lemmas2`):**

| spec | verdict | duration |
|---|---|---|
| `slip_d` (`0 ≤ wad`) | **Unknown(c)** — reaches `+wad`, implication undischarged | 286s |
| `slip_wrong` (`+wad+1`) | **Unknown(c)** — NOT Accept | 286s |
| `slip_vac` (`ensures false`) | **Unknown(c)** — NOT Accept | 42s |

The reached configuration **unifies** with the destination, but `kore-exec`'s one-shot implication check will not close the signed `_add` sign split — the documented **§9 substrate ceiling** (`prove.py` §9), not the lemma set (`bool2Word` = 0 in the new-def logs) and not the claim shape (three structures tried, incl. a getters-style existential, all `Unknown(c)`). The getters Accept because their path has no signed arithmetic/branch split.

**The honest consequence:** because `slip_d`, `slip_wrong`, and `slip_vac` all surface as `Unknown(c)`, the discriminators "refuse" (NOT Accept) but provide **no positive contrast** — a false delta and a vacuous claim are indistinguishable from the true one, all `Unknown`. This is exactly the **Finding-0001/D5 blind spot**: on this substrate a signed-arithmetic postcondition can be neither Accepted nor structurally Refuted. **`slip` is not positively discharged.**

---

## Coverage vs the public k-dss artifact (updated)

| k-dss behaviour | status after P1 | note |
|---|---|---|
| 1. `vat()` · 2. `ilk()` · 3. `gem()` getters | **FULL** ✅ (Findings 0003a/b) | proved to exact return value |
| 4. `join` 1:1 (+ `Vat.slip`, `WETH.transferFrom`) | **partial** — revert/auth guards (G4) + **bridge ✅ + WETH leg ✅**; positive accounting **blocked on `slip`** | slip = §9 substrate ceiling |
| 5. `exit` 1:1 (+ `Vat.slip`, `WETH.transfer`) | **partial** — same; **bridge ✅ + WETH leg ✅**; blocked on `slip` | same |
| (beyond oracle) auth-admin surface | proved (G4) | k-dss never specified it |

P1 moved #4/#5 from "walled at the lemma tail" (Finding 0003) to "three of four sub-parts done — composition infrastructure, the token leg, and the lemma tail — with the fourth (the signed-add Vat value leg) blocked one layer deeper, at the substrate implication check." Removing the lemma wall revealed the substrate wall beneath it.

---

## The reopening lever (documented, not undertaken)

Per decision, substrate-fitting was **not** pursued. The levers that could close `slip`, in ascending cost:

1. **kore-rpc `implies` / `get-model`** — replace `kore-exec`'s one-shot implication with the RPC/booster implication procedure; may close the sign split. A prover-invocation change in `prove.py`/`verify.py`; the cheapest thing to try.
2. **pyk `APRProof` (CSE)** — the driver migration Finding 0005 deliberately avoided; most robust for signed `_add`, but weeks-class and changes the pipeline's trusted base.
3. **Claim reshaping / concretization** — tried (three structures) and insufficient; deeper concretization (concrete storage) weakens the summary below the k-dss statement.

Folding map-reasoning (§3B) into the def — orthogonal to `slip`, and non-substrate — would make the WETH summaries prove **def-only** (no spec-time lemma import) and is the natural next consolidation whenever this reopens.

---

## Honest caveats / what remains assumed

1. **`slip` is the crux and it is not discharged.** The bridge and the WETH leg are real, but `join`/`exit` conservation cannot compose without a proved `slip`; the certificate for #4/#5 does not exist.
2. **The bridge's code-identity residual** (declared `code_hash == on-chain EXTCODEHASH`) is a verifier action, not internally discharged — named in the trust manifest.
3. **WETH scope** is concrete-pinned addresses + infinite-allowance; the summaries prove with a **spec-time** lemma import (a named trusted-base delta), not yet folded into the def.
4. **The lemma extension changes a shared def.** Its conservativeness is evidenced (regression unchanged, consistency 5/5), but it re-opens every lemma-def proof's validity; `-lemmas2` is a new versioned def, the old one untouched.
5. **N=1 per subject, one substrate.** This measures the frontier's location, not a distribution.

## Conclusion

The composition machinery works and the token leg proves over live code, but the value leg — signed `_add` in `Vat.slip` — sits in the substrate's implication-check blind spot, which no lemma removes. The tool did the honest thing: it removed the lemma wall it could remove, refused every false green (five bridge discriminators; a gated lemma extension; `slip` surfacing as `Unknown`, never a spurious Accept), and stopped exactly at the substrate frontier rather than manufacturing a verdict the engine cannot support. #4/#5 positive accounting is blocked on `slip`, and the precise, costed levers to reopen it are recorded above.
