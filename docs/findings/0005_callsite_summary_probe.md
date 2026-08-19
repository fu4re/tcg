# Finding 0005 — Gap #1 probe: raw `kprove` applies a callee summary as a circularity at an unresolved external CALL

- **Date:** 2026-08-19 · **Type:** bounded decisive experiment (the P1 gating unknown), N=1 two-contract toy · **Substrate:** the kompiled KEVM Haskell backend of Finding 0001 (`kevm-1.0.678`, **stock/unpatched** — no `ghost.diff`, no P0 lemma set) · **Prior art:** the P1 design spike (`scratchpad/p1-design.md` §5/§6), Finding 0001 (D3 reference this toy extends), the parent conservation≠delta result (sheaf `findings/0004`).
- **TL;DR:** the single unknown gating the value-conservation coverage work — *can the prover apply a separately-proved callee summary at an external `CALL`, or must we migrate to the Kontrol/pyk `APRProof` (CSE) driver?* — is answered **in favour of raw `kprove`.** On a two-contract toy (a mini-join `CALL`ing a mini-slip), with the callee account's `<code>` made **symbolic** so the frame cannot be inlined, `kprove` closes the caller root to `#Top` **only** by applying the injected `[trusted]` callee summary as a circularity at the stalled call frame. The result is non-vacuous under three discriminators (a +6 broken summary → Refute, summary dropped → Refute stuck at the symbolic frame, `ensures false` → not Accept) and reproduces **through tcg's own `prove.py`** (`caller_2a` → Accept; the +6 twin → Refute, exit 3). **P1 is therefore tcg-native work (~1–2 days), not a driver migration.** What surfaces — exactly as the design predicted on 9 bytes — is a new soundness obligation, the **bridge `S ⟸ D`** (the abstract summary is discharged by the concrete callee proof plus a code-identity binding); it is dischargeable, and closing it in the graph/verify closure is the ~1–2 day work.

---

## Setup (reproducible)

| | |
|---|---|
| Prover | `kprove` (Haskell backend), one invocation per goal claim; trusted children prepended into one module (the exact `prove.py` / `verify` replay path) |
| Definition | `~/toolchains/kevm-1.0.678/haskell`, main module `EDSL`, **stock** — `grep -c callCounter compiled.txt == 0` (no ghost cells); the toy needs none |
| Includes | `-I …/evm-semantics-source -I …/plugin` |
| Judge | **the solver, via `tcg.verdict.classify()`** — the same judge `prove`/`verify` use. Accept = exit 0 **and** `#Top`; Refute = `doesn't unify with the destination … cannot be rewritten further`; Unknown otherwise |
| Toy | callee mini-slip `60005460050160005500` (`slot0 += 5`) at `200`; caller mini-join `6000600060006000600060C86000F100` (push 7 CALL args, `CALL` 200, `STOP`) at `100`, the subject. `<useGas> false`, `NORMAL`/`DEFAULT` (as D3) |
| Artifacts | `tests/reference/callext/` — `raw/*.k` (standalone specs) + `raw/logs/*.log`; `tcg/{src,iface,subject}` + `tcg/logs/`; `run.sh` (verdict-checked raw reproduction), `run-tcg.sh` (tcg pipeline) |

Reproduce: `tests/reference/callext/run.sh` (all 10 specs, verdicts asserted) and `tests/reference/callext/run-tcg.sh`.

---

## Results

### The three variants (design §6)

| Variant | Install | Injected child | Verdict | Wall | Reading |
|---|---|---|---|---|---|
| **INLINE** (baseline) | A2 code **concrete** | `D` (concrete) | **Accept `#Top`** | ~19s | multi-contract `CALL` executes end-to-end; the callee was **inlined** — *no summary fired*. Necessary plumbing, **not** a Gap-#1 probe. |
| **2a** (decisive) | A2 `<code>` **symbolic** | `S` (abstract program `_PGM`) | **Accept `#Top`** | ~22s | R closes **only** by applying `S` as a circularity at the stalled symbolic-code CALL frame. **The Gap-#1 answer.** |
| **2b** (production path) | A2 code concrete, Kontrol `--cse` | — | **not run** | — | not decision-relevant once 2a closes; see caveat 4. |

`kprove` exit 0 in every Accept row; `#Top` is the sole stdout line.

### Non-vacuity guards for 2a (mandatory — a vacuous summary pass is worthless)

| Guard | Mutation | Verdict | Meaning |
|---|---|---|---|
| broken-summary | `S` says `+6` (106); R still needs 105 | **Refute** | R closed *because of* the correct +5 summary, not regardless of it |
| summary dropped | R alone, no `S` | **Refute** — stuck at `#next [ #lookupOpCode ( CODE0 , 0 , DEFAULT ) ] ~> #execute ~> #return 0 0 ~> #pc [ CALL ] …` | `S` is **necessary**; the symbolic frame is genuinely unresolved (**inline-leak check**: `CODE0` symbolic ⇒ nothing to inline) |
| vacuity | R with `ensures false`, `S` present | **not Accept** (`WarnClaimRHSIsBottom` → Unknown) | the 2a pass is **non-vacuous** (antecedent feasible; a vacuous claim's `ensures false` mutant would itself Accept — Finding 0002) |

### Controls and the bridge

| Spec | Verdict | Purpose |
|---|---|---|
| `callee-d` (concrete `D`) | Accept `#Top` | the +5 delta discharged over the **real** callee bytecode (the "discharged" half) |
| `bridge-s-at-p` (`S` with `_PGM := P`) | Accept `#Top` | the bridge `S ⟸ D`: the abstract summary, at the concrete program, proves by execution over the real bytecode |
| `caller-drain` (leading `STOP`) | Refute | callee never runs → `A2.storage[0]` stays 100 → structural refute (the D3-drain analogue) |
| `compat-ok` (Guar⟹Rely) | Accept `#Top` | callee frames A1; Rely (A1 untouched) is delivered by the Guar's frame |
| `compat-broken` (broken Rely) | Refute | caller relies on `A1[1]=999` the Guar never provides → structural refute + counterexample |

### Through tcg's real pipeline (`run-tcg.sh`)

`tcg prove callee` → Accept (17.5s) · `tcg prove caller_inline` → Accept (19.4s, 1 trusted child) · **`tcg prove caller_2a` → Accept (22.3s, 1 trusted child)** · `tcg prove caller_2a_broken` → **Refute, exit 3**. So the summary primitive is available in tcg **today at the prove step** — `prove.py` resolves the trusted child `{summary,s}` from `interfaces.json`, marks it `trusted`, prepends it, and `kprove` fires it at the CALL, exactly as in the raw runs.

---

## Diagnosis — the P1 path

**2a closes ⇒ the call-site-summary primitive exists in raw `kprove`; P1 is tcg-native work (~1–2 days), not the Kontrol/pyk `APRProof` migration.** The reachability engine, given the callee summary as a `[trusted]` circularity, applies it at the sub-frame `<k> #execute` the moment execution reaches the (symbolic-code) callee — before it would take the semantic `[step]` that otherwise stalls on the undecodable opcode. No `--cse`, no APRProof, no fork rebuild.

**The residual, located precisely.** `tcg graph check` on the 2a workspace refuses with:

```
graph check: trusted child s (summary) is Compiled, not Accepted — run `tcg prove summary`
```

This is the design's §0.1 spine — *"inject == discharge == one hash"* — **not spanning the program-abstraction boundary.** The abstract summary `S` (program cell `_PGM`, needed to unify with the symbolic callee frame) is a **different content hash** than the concrete proof `D`, and `S` **cannot itself be Accepted** (executing a symbolic program stalls). tcg's closure requires every trusted-lemma-reachable node to be Accepted; `S` never can be. The ~1–2 day native work is therefore exactly:

1. Let a root inject an **abstract summary node** `S` whose `<program>` is a variable and whose hash ≠ the concrete `D`'s (today `prove.py` already injects it; `graph`/`freeze`/`verify` closure must stop demanding `S` be Accepted).
2. Discharge `S` by the **bridge `S ⟸ D`**: `D` Accepted over the concrete code `P` (a real proof), plus the **code-identity binding** `external_code[addr] = P` with `keccak(P)` matched to the on-chain hash (pure text + keccak, no prover — design §3 items 1–3). `bridge-s-at-p` shows the execution half discharges; `S`'s entry cells are pinned to `D`'s precondition so the only gap the bridge must close is the program identity.
3. Keep the existing anti-proxy discipline (the +6 discriminator is the non-vacuity control; `compat-broken` the interference discriminator).

Everything else the composition needs — the trusted-lemma tree, per-node replay, root program-binding, vacuity re-derivation, the CALL drive — already works.

---

## Honest caveats

1. **This proves the PRIMITIVE, on 9 bytes, with a constant.** The toy deliberately avoids arithmetic (`+5` concrete), so it has **no P0 dependency** and the callee proof `D` is trivial. GemJoin's real callee deltas (`Vat.slip`'s signed `add`, `WETH.transferFrom`) are where P0's lemma set is needed — but that is the *callee-proof* problem (`D`), orthogonal to Gap #1 (*applying* `D`'s summary at the CALL), which is what this settles.
2. **The injected summary `S` is unsound in isolation** — its `<program> _PGM` is free, so as a bare axiom it would apply to any code at `200`. That is intended: soundness rides on the bridge `S ⟸ D` (caveat/point 2 above), which is a **new obligation tcg does not yet carry**. The 2a `#Top` is honestly *"R holds **given** S"*; the certificate is only sound once the bridge is discharged. `S`'s entry state is pinned to `D`'s precondition (only the program is abstracted), so the bridge is as small as it can be.
3. **All discriminators refute STRUCTURALLY** (a reached-vs-claimed storage mismatch), so they land cleanly on Refute, not the substrate's Unknown-for-false-arithmetic trap (Finding 0001 caveat 6). The vacuity guard returns Unknown (`RHS is bottom`), which is the correct *non*-vacuous direction under tcg's vacuity semantics (Accept-on-`ensures false` ⇒ vacuous).
4. **2b (Kontrol `--cse`) was not run.** Once 2a closes, 2b is not decision-relevant. It remains the recommended *production* path because it keeps concrete code and so preserves `S = D` (one hash, **no bridge obligation**) — the reliance shifting to Kontrol's CSE engine (proved sound in the parent's `report.md` Q3). If the bridge `S ⟸ D` proves fiddly to make airtight in the native path, 2b is the fallback that sidesteps it. Standing it up needs a foundry project + `kontrol build` + `kontrol prove --cse` (kontrol 1.0.255 is installed).
5. **Identity of `external_code` is declared, not checked here** — `tcg subject set` stores `environment.json` opaquely; binding `keccak(external_code[200])` to an on-chain hash is the §3 verifier action, unimplemented (as for the primary subject in Finding 0001 caveat 1).
6. **No `graph check`/`freeze`/`verify` bundle for 2a** — by construction it is refused at closure (the residual above). The INLINE composition *would* freeze/verify (it is the D3 trusted-lemma shape, already validated in Finding 0001), but that is composition-by-inlining and does not scale; it is not re-frozen here.

## Reproduction

```
tests/reference/callext/run.sh       # 10 raw specs on the real backend, each verdict asserted -> exit 0
tests/reference/callext/run-tcg.sh   # callee/inline/2a Accept, 2a_broken Refute(3), graph-check gap
```
