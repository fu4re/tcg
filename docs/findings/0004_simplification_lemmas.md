# Finding 0004 — Equipping the KEVM substrate with byte/int/bitwise simplification lemmas: the Finding-0003 wall removed, and the trusted-base growth it costs (Track P0, gate G4→G5)

- **Date:** 2026-08-19 · **Type:** substrate capability upgrade + soundness bound (a trusted-base-growing change) · **Substrate:** kompiled KEVM Haskell backend (Track B) · **Builds on:** Findings 0002 (false-green guards), 0003 (the coverage wall this removes) · **Decisions:** D4 (definition pinned at init), and the user's explicit architectural decision: a **vendored, pinned diff**.
- **TL;DR:** Finding 0003 diagnosed the exact wall on the live GemJoin audit — the kompiled EDSL definition ships **no** byte/int simplification lemmas, so a symbolic ABI-decoded word (`#asWord(#range(sel +Bytes #buf(32,USR) +Bytes #buf(32,WAD), 36, 32))`) never binds and any claim quantified over `wad` walks into the external `CALL` → Unknown. This finding removes that wall by baking KEVM's own four **pure-simplification** submodules (bytes, int, evm-int, bitwise — **287** rules, every one `[simplification]`) into a new kompiled definition via a **37-line vendored driver module** (`theory/patches/lemmas.diff`, applied on top of `ghost.diff`). The control is decisive and reproduced by the same shared judge as everything else: the exact G4 decode term is **Unknown(c)** under the old definition and **Accept (`#Top`)** under the new one — same spec, two definitions. Because adding simplification rules **grows the trusted base** and neither vacuity nor program-binding catches a *false* lemma, the growth is bounded by a mandatory consistency control (`scripts/lemma-consistency.sh`): **four known-false identities, one per submodule, none of which prove** (all Unknown(c), never Accept). The old work still proves against the new definition (**3 Accepts + verify OK**, drain control still **Refute**), and every guard suite stays green. Honest limit: the lemma set is a large **reusable core, not provably closed** — keccak stays an injectivity axiom (`A_keccak`), nonlinear arithmetic stays a wall.

---

## Setup (reproducible)

| | |
|---|---|
| Prover | `kprove` / `kore-exec` (Haskell backend), one invocation per claim / per probe |
| Toolchain (pinned) | k `v7.1.337` · kore-exec `0.1.155` · kevm `1.0.678` · z3 `4.16.0` |
| Old definition (lemma-less) | `~/toolchains/kevm-1.0.678/haskell` (main module EDSL) — carries **0** simplification lemmas (`grep -c BYTES-SIMPLIFICATION definition.kore` → 0) |
| New definition (lemma-equipped) | `~/toolchains/kevm-1.0.678-lemmas/haskell`, main module **LEMMAS-DRIVER**; carries the four submodules (130 `BYTES-SIMPLIFICATION` refs) and the ghost cells (11 refs). Reproducibility is at the **source+patch** level (both patches hashed); `definition.kore` itself is **not** byte-deterministic across `kompile` runs (embeds ordering/paths) — its sha256 is a per-build drift marker in `provenance.json`, re-validated behaviorally, not by hash |
| Patches (vendored, pinned) | `theory/patches/ghost.diff` (sha256 `e300f622…`) then `theory/patches/lemmas.diff` (sha256 `8e0e5b57…`, 40 lines) |
| Judge | **the solver, never prose.** Every verdict below is the exact `kprove` exit + log, classified by the single shared `tcg.verdict.classify()` |
| Build | `scripts/build-kevm.sh --lemmas` (kompile of LEMMAS-DRIVER); **wall time 38 s** on this machine (K reuses the base definition's cache) |
| Reproduction | `scripts/lemma-consistency.sh`; `KEVM=~/toolchains/kevm-1.0.678-lemmas scripts/build-reference.sh`; control logs under `tests/control/lemmas/logs/` |

---

## The wall removed (the control — I will independently reproduce this)

The Finding-0003 wall, distilled to a standalone functional claim
(`tests/control/lemmas/reduce-abi-decode.k`, module `REDUCE-ABI-DECODE-SPEC`).
Calldata = a concrete 4-byte selector `++ #buf(32, USR) ++ #buf(32, WAD)`; the
guard reads the second argument as `#asWord(#range(sel ++ #buf(32,USR) ++
#buf(32,WAD), 36, 32))`, which is exactly `WAD`. **Same spec, two definitions:**

```
kprove tests/control/lemmas/reduce-abi-decode.k --spec-module REDUCE-ABI-DECODE-SPEC \
  --definition <DEF>/haskell -I <DEF>/evm-semantics-source -I <DEF>/plugin
```

| definition | exit | kore-exec signal | `classify()` |
|---|---|---|---|
| **OLD** `kevm-1.0.678` (lemma-less) | 1 | `WarnStuckClaimState`: *"unifies with the destination's term, but the implication check between the conditions has failed"* — residual `#Not({WAD #Equals #asWord(#range(…))})`: the decode term never reduced | **Unknown(c)** |
| **NEW** `kevm-1.0.678-lemmas` | 0 | `#Top` (the LHS simplifies to `WAD`, so LHS ≡ RHS) | **Accept** |

Logs: `tests/control/lemmas/logs/reduce-abi-decode.{old,new}.log`. The reduction
uses only the four vendored submodules: `range-outside-cHead` and
`range-buf-value` (bytes) peel the 36-byte prefix and read the 32-byte tail;
`asWord-buf-inversion` (evm-int) inverts `#asWord(#buf(32,WAD))` to `WAD`. This
is the precise coverage unlock Finding 0003 named as the next-cycle target.

(The `#Top` carries a `WarnTrivialClaim: proven without rewriting` — expected for
a *functional* claim: there is no EVM step, the simplification of the term **is**
the proof. Its legitimacy is established by the two flanking facts: the OLD
definition does **not** prove it, and the false variants below do **not** prove.)

---

## The inclusion mechanism chosen, and why (task 1)

Two candidates were weighed **empirically**, not assumed:

**(A) Reuse Kontrol's already-kompiled definition.** Kontrol's `KONTROL-BASE`
target on this machine *does* carry the lemmas (`BYTES-SIMPLIFICATION` present,
14 `#asWord`/`#buf` inversion rules). **Rejected**, on evidence: its
configuration is foundry/cheatcode-shaped (`PGM: EthereumSimulation`, `<foundry>`
/`<cheatcodes>` cells — `configVars.sh`, `definition.kore`), which does **not**
match tcg's raw-KEVM claim idiom (`<k> #execute => #halt </k> <program>…
<account>…`, per `tests/control` and `tests/reference`); and it is
`kontrol-1.0.0` at a specific commit, not tcg's pinned `kevm-1.0.678`, so adopting
it would un-pin the substrate and tie tcg to the foundry harness. Not
idiom-compatible, not reproducible under tcg's own pin.

**(B) Vendor a minimal diff that bakes the four pure-simplification submodules
into the kompile closure.** Chosen — and it is also the user's explicit
architectural decision. `theory/patches/lemmas.diff` adds a single 37-line
driver, `lemmas-driver.k`:

```k
requires "edsl.md"
requires "lemmas/bitwise-simplification.k"   // + bytes / evm-int / int
module LEMMAS-DRIVER [symbolic]
    imports EDSL
    imports BITWISE-SIMPLIFICATION            // + BYTES / EVM-INT / INT -SIMPLIFICATION
endmodule
```

kompiled with `--main-module LEMMAS-DRIVER`. Why this is the clean form:

- **The two Finding-0003 obstacles dissolve at kompile time.** `imports LEMMAS`
  failed because the aggregate `lemmas.k` carries a *non-simplification* rule
  (`#addrFromPrivateKey`, concrete); importing the four submodules **directly**
  excludes it — verified: the rule's RHS constant `721457…935711` has **0**
  occurrences in the new `definition.kore` (the `#addrFromPrivateKey` *symbol*
  declaration remains, exactly as in the old def — it is a harmless krypto hook
  with no rule). `imports BYTES-SIMPLIFICATION` from a spec failed because K's
  `#let`/`#in` productions (defined in the builtin `K` module of `kast.md`) are
  absent from EDSL's *spec-import* closure; baking the submodules into the
  **definition** resolves `#let` at kompile time (rules are parsed with the `K`
  module in scope), so a spec never has to import them.
- **Nothing added is a semantic rewrite step.** All **287** rule blocks across
  the four submodules carry `[simplification]` (checked mechanically — 0
  exceptions); simplification rules rewrite only the constraint / normal-form
  representation the backend already reasons about, never which stock EVM rule
  applies. The lemmas apply globally to any spec on the definition (they are
  gathered into the definition's simplification set at kompile time), so the
  existing `imports EVM` claims pick them up unchanged.
- **EDSL base, not EVM.** The driver imports EDSL (the KEVM verification
  substrate the old prebuilt def already used), so the new def is a strict
  superset — old-work regression surface is minimal — and it transitively pulls
  in the ghost-instrumented `evm.md` when `ghost.diff` is applied first.

`build-kevm.sh --lemmas` builds it reproducibly from the pinned base source +
both patches (dry-run then apply; a reject is a hard stop), writing
`provenance.json` with both patch hashes. `tcg init` now vendors **both**
`ghost.diff` and `lemmas.diff` and records both hashes in the workspace
`toolchain.lock` (`patches`) — no trusted input enters silently.

---

## The soundness control (task 4 — mandatory, non-negotiable)

Adding simplification lemmas **grows the trusted base**, and neither the vacuity
probe (antecedent reachability) nor program-binding (subject identity) catches a
**false lemma**: a wrong simplification rule would let the prover Accept a false
postcondition. `scripts/lemma-consistency.sh` bounds that growth. It attempts to
prove four **known-false identities** — one per submodule
(`tests/control/lemmas/false-identities.k`) — and requires the prover to refuse
**every** one (verdict ≠ Accept: no `#Top`, non-zero exit). Each probe's LHS is
reduced by a *real* rule to its **correct** value, leaving a genuinely false
residual, so the probe would wrongly Accept only if that rule reduced to the
wrong thing.

| probe (submodule) | claim `<k> LHS => WRONG </k>` | reduces to (residual) | `classify()` |
|---|---|---|---|
| P1 evm-int | `#asWord(#buf(32,X)) => X +Int 1` | `X` (residual `X ==Int X+1`) | **Unknown(c)** — refused |
| P2 bytes | `#asWord(#range(sel++#buf(32,USR)++#buf(32,WAD),36,32)) => USR` | `WAD` (residual `USR ==Int WAD`) | **Unknown(c)** — refused |
| P3 int | `(A +Int B) -Int B => A +Int 1` | `A` (residual `A ==Int A+1`) | **Unknown(c)** — refused |
| P4 bitwise | `X &Int X => X +Int 1` | `X` (residual `X ==Int X+1`) | **Unknown(c)** — refused |

`scripts/lemma-consistency.sh` → exit 0, *"all 4 false identities refused."* The
residual logs confirm the probes are **meaningful**, not vacuous: P1's `<k>` cell
becomes `X:Int` with residual `#Not({X #Equals X +Int 1})` (the lemma reduced
`#asWord(#buf(32,X))` to `X`); P2's residual is `#Not({USR #Equals WAD})` (the
lemma correctly extracted the **second** argument `WAD`, not the first). The
lemmas fire and reduce **correctly**, then the false target is refused. **No
false identity proves.** If any had, the rule would be: STOP, do not ship.

---

## Regression: the new definition still proves the old work (task 6)

A lemma can change normal forms or loop, so this was **validated, not assumed**.
`KEVM=~/toolchains/kevm-1.0.678-lemmas scripts/build-reference.sh` (wall time
**192 s**):

| claim | role | verdict on NEW def |
|---|---|---|
| `ledger/base` | frame | **Accept** (22.2 s) |
| `withdraw/main` | root | **Accept** (21.2 s) |
| `withdraw/guar` | guar | **Accept** (24.6 s) |
| `withdraw/main` vacuity probe | — | **non-vacuous** (falsified mutant → Unknown; the lemmas did **not** make an `ensures false` mutant provable) |
| bundle freeze → `tcg verify` | — | **certificate holds** (exit 0; step 5v vacuity OK) |
| `drain/drain` refutation control | — | **Refute** (exit 3, structural — the lemmas did **not** make the false drain claim provable) |

Other suites, all green on the new substrate / with the re-pin:

- `scripts/false-green.sh` (KEVM=new) → **exit 0**: both G3 false greens still
  reproduce **and** are refused by the right guard (program-binding + vacuity
  still discriminate under the lemmas).
- `scripts/conformance.sh` on the new-def bundle → **6/6** controls PASS (each
  its exact `(exit, step)`: 1,2,3,6 → exit 3; 4 → exit 2; 5 → exit 0).
- `python -m unittest discover -s tests` → **32/32**.
- `scripts/repo-checks.sh` → **ALL PASS** (patch-parity now covers *both*
  `ghost.diff` and `lemmas.diff`).

Lemmas only helped here; nothing prior broke.

---

## Trusted base: what grew, and how it is bounded (task 5)

`tcg freeze`'s `trust-manifest.json` now enumerates the vendored lemmas as a
named assumption (bundle-spec §7):

- **`A_simp_lemmas`** — the four `[simplification]`-only submodules
  (`theory/patches/lemmas.diff`), status **proven-upstream** (KEVM's own lemmas;
  `#addrFromPrivateKey` excluded) **+ assumed-consistent**, bounded by
  `scripts/lemma-consistency.sh`. Explicitly **not_closed**: keccak stays
  `A_keccak`, nonlinear arithmetic stays a wall. **upstream_intent** recorded.
- **`A_instrumentation`** — the ghost-cell patch, transparency obligation listed
  as `residual, pending` (unchanged in substance from Track B).
- **`vendored_patches`** — the patch paths travelling in the bundle's hash tree.

No silent trusted inputs: both patches are vendored, hashed in the lock, and
shipped in `theory/patches/` inside every bundle.

---

## Honest caveats — what the lemmas still do NOT reduce (the residual wall)

1. **The set is NOT provably closed.** It is a large, reusable **core** plus a
   convergent tail: 287 rules cover the byte/word algebra that ABI-decode,
   memory returns, and masks generate, but there is no theorem that it
   normalizes every term. Novel symbolic shapes can still stick.
2. **keccak stays an injectivity axiom (`A_keccak`).** The lemmas bound
   `keccak(_)` to `[0, pow256)` but do **not** decide `keccak(k1) == keccak(k2)`;
   mapping-slot disjointness (e.g. `wards[a]` vs `wards[b]`) still rests on the
   assumed injectivity. The Finding-0003 "non-empty `wards`" strengthening is
   **not** unlocked by this change alone.
3. **Nonlinear arithmetic stays a wall.** Rules that discharge `X *Int Y` bounds
   need concrete factors or specific range side-conditions (`concrete(A,C)`,
   `Y <=Int maxUInt256 /Int X`); genuinely symbolic nonlinear multiplication is
   not reduced — it is handed to z3, which is incomplete on it.
4. **The consistency control is a bound, not a completeness proof.** Four false
   identities refusing shows the set is not *grossly* inconsistent on the tested
   shapes; it does **not** prove the 287 rules are jointly sound (that is KEVM's
   upstream obligation, which we inherit via `proven-upstream`). A subtly wrong
   rule outside the probes' reach would not be caught here.
5. **Functional-claim caveat.** The control/probe claims prove via
   `WarnTrivialClaim` ("proven without rewriting") because they are functional
   (no EVM step). This is sound for term reduction but is a *different* proof
   shape from a reachability claim; the GemJoin *end-to-end* symbolic `join`/
   `exit` (external-call composition) is still gated by the unmodeled external
   callees (Finding 0003 caveat), which lemmas do not address.
6. **Substrate limits unchanged.** The Unknown-vs-Refute arithmetic-postcondition
   limit (substrate §4d) is why the false-identity probes surface as **Unknown**,
   not Refute — the safe direction (they do not Accept), but the same reason a
   false *arithmetic* postcondition is not cleanly refuted.

## The upstream plan

The four submodules are KEVM's own; the vendored driver exists only because
`imports BYTES-SIMPLIFICATION` from a spec fails on the missing `#let`/`#in`
productions and `imports LEMMAS` drags in `#addrFromPrivateKey`. The clean
upstream fix is a KEVM-provided verification module that bundles exactly the four
pure-simplification submodules (no concrete rules), so downstream users
`imports <that module>` and pin by **KEVM version** instead of vendoring a
driver. Until then `lemmas.diff` is pinned by hash in the lock and shipped in
every bundle. When upstreamed, this finding is **superseded** by the version pin,
not rewritten.

## Reproduction

```
scripts/build-kevm.sh --lemmas                       # build the lemma-equipped def (~40s warm)
scripts/lemma-consistency.sh                          # 4 false identities, none prove (exit 0)
# before/after control (same spec, two defs):
kprove tests/control/lemmas/reduce-abi-decode.k --spec-module REDUCE-ABI-DECODE-SPEC \
  --definition ~/toolchains/kevm-1.0.678<-lemmas>/haskell -I …/evm-semantics-source -I …/plugin
KEVM=~/toolchains/kevm-1.0.678-lemmas scripts/build-reference.sh   # 3 Accepts + verify OK
KEVM=~/toolchains/kevm-1.0.678-lemmas scripts/false-green.sh       # both false greens refused
scripts/repo-checks.sh ; python3 -m unittest discover -s tests     # green + 32/32
```
