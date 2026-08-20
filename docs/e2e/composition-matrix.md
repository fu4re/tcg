# composition E2E — discriminator matrix (acceptance checklist)

Every end-to-end case the composition E2E must exercise, for BOTH mechanisms of
`COMPOSITION_CONTRACT.md`: the cross-bundle **linker** (REUSE, Mechanism A) and the
typed **stub** (STUB, Mechanism B). This is the checklist the orchestrator
reproduces before merge (ground-rule 1: every prover verdict is a real `kprove`
run, command shown, log kept).

## The E2E toy shape

A minimal caller with **two external calls** (contract §E2E):
- **leg 1 — linker:** discharged by vendoring the callext callee as
  `deps/<callee_root>/` (reuse the `sbridge`-shaped root; see
  `docs/e2e/callext-inventory.md` §4c).
- **leg 2 — stub:** discharged by a typed assumption over the opaque callee
  `tests/reference/composition/opaque/` (`hook()`, keccak256
  `547a6447572440e47d4457dddf4a1b9c232ee8291b515aab464bb168b801fa57`).

Let `$CALLER` = the frozen caller bundle, `$DEP` = the vendored callee bundle root
dir `deps/<callee_root>/`. The join step ships a
`run-composition-discriminators.sh` analogous to
`tests/reference/callext/run-tcg-bridge-discriminators.sh`, which builds one GOOD
`$CALLER` and tampers copies of it.

## Exit-code legend (`tcg/outcome.py`, authoritative)

| code | name | meaning |
|---|---|---|
| **0** | `OK` | command succeeded; for `verify`: certificate holds |
| **1** | `USAGE` | usage / internal error (bad args, missing MANIFEST, no definition) |
| **2** | `UNKNOWN` | prover could not decide — conservative refusal (NOT a defect) |
| **3** | `REFUSED` | refuted with a witness, OR a bundle-only verifier check failed |

"Unknown ≠ Refute ≠ OK." A tamper that a structural/keccak check catches is exit
**3**; a prover that times out on the honest replay is exit **2**.

## Status of the two mechanisms (honesty)

Both mechanisms are **UNBUILT** in the current tree (verified on `5ab8b94`):
`tcg verify` reads no `deps/`, `tcg/bridge.py:resolve_ref` resolves only
`{loop,label}` in-graph, and there is no `assume` node, no `--strict`, no
`A_callee_*` ledger surfacing. So every **verify verdict below marked ⏳ is "to be
produced in the join step"** — a real run once the linker/stub verify code lands.
The **Catch** column names the target verifier step (and the existing pure
function) the join step must wire. Where an existing **in-graph** discriminator
already proves the same anti-proxy logic with committed evidence, it is cited as
the template (✅ = reproducible today via `run-tcg-bridge-discriminators.sh`).

---

## A. Linker (Mechanism A — cross-bundle REUSE)

| # | case | tamper / setup | exact command | expect | catch (verifier step / function) | status |
|---|---|---|---|---|---|---|
| A0 | **honest composition** | build GOOD `$CALLER` with vendored `$DEP`, honest cross-bundle bridge block | `tcg verify $CALLER` | **0** | all steps pass: dep recursed post-order (step 5), `dep_root ∈ dep roots`, code-identity recomputed (step 4), `binding_errors(S,D)` clean (step 4) | ⏳ join |
| A1 | **flipped dep byte** | flip one byte of `deps/<root>/subject/runtime.bin` | `tcg verify $CALLER` | **3** | step 1 integrity — the dep file is hash-linked in the caller MANIFEST → hash mismatch. (If MANIFEST is also rehashed: step 4 code-identity `keccak256(dep subject) ≠ code_hash`, and `<callee_root> ≠ sha256(dep MANIFEST)`.) | ⏳ join; logic ✅ analog = in-graph #2 |
| A2 | **non-root ref** | `concrete_proof.root` points at a NON-root (e.g. `guar`) claim of the dep | `tcg verify $CALLER` | **3** | linker obligation 2 (step 4): `concrete_proof.root ∉ dep MANIFEST roots` | ⏳ join |
| A3 | **code_hash mismatch** | caller node `code_hash` altered ≠ `keccak256(dep subject)` | `tcg verify $CALLER` | **3** | step 4 code-identity, PERFORMED (`bridge.py:structural_errors`, keccak recompute) | ⏳ join; logic ✅ analog = in-graph #2 |
| A4 | **external_code mismatch** | caller `environment.external_code[callee]` ≠ `deps/<root>/subject/runtime.bin` byte-for-byte | `tcg verify $CALLER` | **3** | step 4 code-identity byte-compare (`structural_errors`: `external_code[callee] == dep subject`) | ⏳ join |
| A5 | **proxy-delta** | summary `S` asserts a storage delta the dep root does not carry (plausible-but-false) | `tcg verify $CALLER` | **3** | step 4 binding `binding_errors(S_text, D_text)` — delta / entry mismatch | ⏳ join; logic ✅ analog = in-graph #3 (proxy +0) & #1 (+6) |
| A6 | **missing dep** | `concrete_proof.dep` set but `deps/<callee_root>/` absent | `tcg verify $CALLER` | **3** | step 1 integrity (MANIFEST lists dep files → missing file) + dep-resolution refusal | ⏳ join |
| A7 | **wrong MANIFEST hash** | `deps/<root>/` present but `sha256(deps/<root>/MANIFEST.json) ≠ <callee_root>` (dir name) | `tcg verify $CALLER` | **3** | dep content-address check: `<callee_root> = sha256(dep MANIFEST)` fails | ⏳ join |
| A8 | **dep does not itself verify** | a byte of the dep's own proved claim/evidence broken (dep alone would REFUSE) | `tcg verify $CALLER` | **3** | step 5 dep recursion: run the full protocol on `deps/<root>/` first; dep refusal ⇒ caller refused (contract obligation 1) | ⏳ join |

Notes:
- A1/A3/A4/A7 are all "the code the summary is bound to is not the code actually
  vendored/installed" — they differ only in *which* integrity edge is cut, so the
  join step must confirm EACH lands at exit 3 (not merely that one does).
- A5 is the soundness heart: it must fail at **binding**, identical strictness to
  the in-graph bridge (`docs/e2e/callext-inventory.md` §5, controls #1 and #3).

---

## B. Stub (Mechanism B — typed assumption)

| # | case | tamper / setup | exact command | expect | catch (verifier step / behavior) | status |
|---|---|---|---|---|---|---|
| B0 | **honest assume-node (default)** | GOOD `$CALLER` whose leg-2 call is an `assume` node with `A_callee_<addr>` in `trust-manifest.json` | `tcg verify $CALLER` | **0** | all steps pass; `S` injected (load-bearing); trailing **`⚠ N author-chosen assumption(s) load-bearing:`** section names address + frame + roots | ⏳ join |
| B1 | **`--strict` on the honest bundle** | same GOOD `$CALLER` | `tcg verify --strict $CALLER` | **3** | new `--strict` pre-gate: any `assume` node present ⇒ REFUSE ("auditor asked for a fully-discharged certificate") | ⏳ join |
| B2 | **deleted ledger entry** | remove the `A_callee_<addr>` entry from `trust-manifest.json` (assume-node still present); rehash MANIFEST | `tcg verify $CALLER` | **3** | consistency check: `ledger_id` referenced by an assume-node is absent from `trust-manifest.json` ⇒ REFUSE (no silent stub) | ⏳ join |
| B3 | **orphan ledger entry** | `A_callee_<addr>` present in `trust-manifest.json` but no assume-node references it | `tcg verify $CALLER` | **3** | same consistency check, other direction (no orphan ledger entry) | ⏳ join |
| B4 | **`tcg roots` surfaces it** | GOOD `$CALLER` (B0) | `tcg roots $CALLER` | **0** | `roots` output enumerates the load-bearing author assumption next to the roots (address + frame) | ⏳ join |
| B5 | **no assume-node ⇒ no behavior change** | any existing bundle with zero assume-nodes (e.g. the callext bridge bundle) | `tcg verify $BUNDLE` | **0** | prints NOTHING extra (no `⚠` section) — regression guard on existing bundles | ⏳ join (assert on a built callext bundle) |

Notes:
- B0's exit-0-plus-warning vs. a distinct advisory exit code is the contract's
  open **DECISION POINT** — flagged to the orchestrator, NOT decided here. Implement
  exit-0 + `⚠` + `--strict`; leave a TODO if a cleaner status model appears.
- B2/B3 enforce the contract's non-negotiable #5 ("a stub is never a clean pass"):
  the assumption must be enumerated on BOTH sides or the bundle is refused.
- The `⚠` section and `--strict` gate must fire AFTER steps 1–5v pass — a stub
  bundle that also fails integrity/replay is refused for THAT reason first.

---

## C. Cross-cutting acceptance invariants

1. **Three-way agreement (contract ground-rule 2).** The structural discharge of a
   composition node must be the SAME pure function in `graph check`, `freeze`, and
   `verify`. Acceptance: for a GOOD `$CALLER`, `tcg graph check` (build side) and
   `tcg verify` (bundle-only side) must AGREE on every A/B row's verdict; a tamper
   that `verify` refuses must also be refused (or unbuildable) on the build side.
2. **Import guard (ground-rule 3).** `scripts/repo-checks.sh` stays green: the new
   pure module(s) and `tcg/commands/verify.py` import neither `tcg.workspace` nor
   `tcg.commands.*`. Command: `scripts/repo-checks.sh` → exit 0.
3. **Self-contained dep (ground-rule 4).** `tcg verify $CALLER` needs ONLY
   `$CALLER` (dep is COPIED into `deps/`, not referenced remotely). Acceptance: move
   `$CALLER` to a fresh path with no network/other bundles; `verify` still exits 0
   on A0.
4. **Every fresh prover verdict is a real run.** A0, A5, A8, B0, B5 each involve a
   `kprove` replay; their verdicts are produced by an actual run with the command
   and log retained — never asserted from this table.

## D. What already reproduces today (evidence anchors)

The linker's anti-proxy logic (A3, A5, and A1's identity half) is already proved by
the **in-graph** bridge discriminators — reproducible now, no new code:

```
tests/reference/callext/run-tcg-bridge-discriminators.sh   # 5 controls, each REFUSED
tests/reference/callext/run-tcg-bridge.sh                  # honest in-graph bundle -> verify exit 0
```

Committed evidence: `tests/reference/callext/tcg/logs/*.log` (`#Top` = Accept for
`callee/d`, `caller_2a/r2a`), and the verdict table in
`tests/reference/callext/README.md`. These require the kompiled KEVM definition
(`~/toolchains/kevm-1.0.678`) and were NOT re-run for this matrix; the join step
runs them plus the new A/B rows and keeps the logs.
