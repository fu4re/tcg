# Finding 0002 — Closing two false greens: root program-binding and an antecedent-reachability (vacuity) gate (Track E, gate G3→G4)

- **Date:** 2026-08-18 · **Type:** negative result turned fix (a blind dry-run produced `Accept` on a worthless claim) + e2e measurement on the real prover · **Substrate:** the kompiled KEVM Haskell backend of `docs/substrate.md` (Track B) · **Builds on / supersedes in part:** Finding 0001 (reference bundle e2e; this adds two verifier controls and supersedes its 5-control conformance table with a 6-control one) · **Ports the spirit of:** sheaf Finding 0005 (the automatic vacuity gate; `assert(false)`-proves ⇒ unreachable ⇒ vacuous) · **Decisions:** D1, D3, D4, D5
- **TL;DR:** a blind agent (gate G3) got `tcg` to hand out `Accept` — and pass every automated gate — on a claim that **(1a)** never references the subject bytecode and **(1b)** asserts nothing. This is the project's cardinal failure ("a false green is worse than no tool"). Two guards now close it, each demonstrated on the real prover, no simulated output. **P0-A program binding** (mechanical, no prover): a *root* claim's `<program>` cell must equal `subject/runtime.bin`; enforced at `freeze` and re-derived bundle-only at `verify` step 4. It catches the exact G3 claim (no `<program>` cell). **P0-B vacuity probe** (one extra prover run/root): falsify the postcondition (`ensures false`) and re-prove; if the falsified claim *still* proves, the antecedent is infeasible and the proof is **vacuous** — a refusal. It catches the deeper antecedent-failure case a program-bound claim can still hide. The reference root passes **both** (falsified form → Unknown, not Accept). A third, separate fix (**P1**) makes `compile-claims` atomic w.r.t. its verdict — exit code and on-disk effect now always agree — and makes re-compiling a proved loop a coherent, supported operation. **P2** (a cheap in-compiler K parse) is **deferred, with the measurement that justifies it**: the only local K parse (`kprove --dry-run`) costs ~12.5 s (essentially the full frontend), so it is not "cheap," and `prove` already surfaces the identical parser message.

---

## Setup (reproducible)

| | |
|---|---|
| Prover | `kprove` (Haskell backend), one invocation per goal claim / per probe |
| Definition | `~/toolchains/kevm-1.0.678/haskell`; includes `…/evm-semantics-source`, `…/plugin` |
| Toolchain (pinned) | k `v7.1.337` · kore-exec `0.1.155` · kevm `1.0.678` · z3 `4.16.0` · replay `{retries: 2, timeout_seconds: 3600}` |
| Runner | `PYTHONPATH=<repo> python3 -m tcg …` (pyenv 3.12.2) |
| Judge | **the solver, never prose.** Every verdict below is the exact `kprove` exit + log, classified by the single shared `tcg.verdict.classify()` (D5) that `prove`, `vacuity`, and `verify` all use |
| New guards | `tcg.claims.{extract_program_bytes, program_binding_error}` (P0-A); `tcg.claims.falsify_body` + `tcg vacuity` + `verify` step 5v (P0-B); `tcg/commands/compile_claims.py` + `tcg/workspace.py` transitions (P1) |
| Reproduction | `scripts/false-green.sh` (both false greens reproduced *and* refused); `scripts/build-reference.sh` (reference now passes both guards); `scripts/conformance.sh` (6/6, control 6 = program binding) |

---

## The G3 reproduction (the motivating negative result)

Every line below is a real run against the definition above.

**Hole 1a — no program binding, no assertion.** The blind-agent claim, verbatim:

```
claim <k> #execute ~> _ </k>
 [label(debit), all-path]
```

`kprove` → **exit 0**, log = `#Top` (preceded by `Warning (WarnTrivialClaim): Claim proven without rewriting`). `classify()` → **Accept**. `tcg prove` returns `Accept` (exit 0). The claim references no `<program>` cell — it is not about the subject bytecode at all — and its "postcondition" (`~> _`) asserts nothing. Yet `prove`, `graph check`, and `freeze` all passed it in the G3 dry-run; only the optional human-facing `tcg roots` carried any warning.

**Hole 1b — a program-bound but *vacuous* claim.** The reference root, with one contradictory antecedent added (`requires 100 =/=Int 100`):

`kprove` → **exit 0**, log = `#Top` (preceded by `Warning (WarnTrivialClaim): Claim proven during initialization … The left-hand side of the claim may be undefined`). `classify()` → **Accept**. The claim *does* carry the subject's `<program>`, so program-binding alone would pass it — but no initial state satisfies `100 =/=Int 100`, so the proof holds for an empty reason.

**Hole 2 — the state machine reported failure while mutating.** `tcg compile-claims` from a non-`Compiled`/`Stale` loop state (`Unknown`/`Refuted`/`Accepted`) wrote the new claim files, graph nodes, and `interfaces.json`, and *then* raised `illegal state transition` → exit 1. Exit code said "failed"; the workspace said "done."

---

## P0-A — program binding (the cheap mechanical guard)

**What it checks.** A *root* claim (role `loop`, `root: true`) must carry an extractable `<program>` cell whose bytes equal `subject/runtime.bin`. Extraction is pure text: `#parseByteStack("<hex>")` (0x-prefixed or bare) or a bare hex literal; if the cell rewrites (`X => Y`) the *installed* (left) program binds. A root with **no** extractable `<program>` cell is refused with a message naming the fix. Enforced at `freeze` (workspace) **and** re-derived bundle-only at `verify` step 4 (text + byte compare — a self-consistent hash tree does not launder a mismatch).

**Non-roots are deliberately not bound**, and this is a soundness decision, not laziness: the bundle's guarantee *is* the set of roots (a verifier reads the roots — bundle-spec §4). A `frame`/`guar` lemma legitimately proves a *sub*-program (the reference `frame` proves the bare `STOP`, program `00`); `junction`/`compat`/`env`/`subsumption` nodes carry no `<program>` cell at all. Binding the roots ties the transferable guarantee to the deployed bytecode; binding the lemmas would reject honest ones and buys nothing (a lemma is re-proved on its own in replay).

**What it provably catches:** the exact G3 claim (no `<program>` ⇒ refused), and any root whose program ≠ subject. **What it does not:** it is a *text* extraction, not a K parse — see caveats. It says nothing about constructor args / immutables / environment (those remain a verifier action, per Finding 0001).

---

## P0-B — the vacuity probe (the deeper guard)

**What it does.** For each proved goal claim, `falsify_body` replaces the postcondition with `false` (keeping the antecedent: `requires` + LHS cells), and the claim is re-proved standalone. The rule (ported from sheaf Finding 0005's Probe R): **falsified form proves Accept ⇒ antecedent infeasible ⇒ original proof vacuous ⇒ refuse**; anything else (Refute / Unknown) ⇒ the antecedent is feasible enough that an impossible postcondition is not vacuously provable ⇒ non-vacuous. `freeze` requires a non-vacuous record for every root; `verify` **re-derives** it bundle-only at step 5v (it does not trust the bundled `evidence/vacuity/<h>.json`).

**The discriminator is empirical, measured on the real backend** — the whole reason this is a solver judgement and not prose:

| claim (real run) | plain `kprove` | falsified (`ensures false`) form | probe verdict |
|---|---|---|---|
| reference root `withdraw/main` (feasible antecedent) | Accept (`#Top`) | **Unknown** — `WarnClaimRHSIsBottom` then "unifies with the destination … implication check has failed" | **non-vacuous** (PASS) |
| G3-style vacuous claim (`requires 100 =/=Int 100`) | Accept (`#Top`) | **Accept** (`#Top`, "proven during initialization … LHS may be undefined") | **VACUOUS** (REFUSE) |

Why the mutation and not the warning text: kore-exec *does* emit `WarnTrivialClaim`/"left-hand side may be undefined" on the vacuous cases, but warning-text matching is fragile (substrate §4a burned us once already by over-matching a `WarnStuckClaimState` tag). The mutation reduces the question to a single clean `classify()` verdict on a re-proof — Accept or not — judged by the same shared judge as everything else.

**Runs standalone (no trusted children):** an infeasible antecedent proves regardless of lemmas, and true lemmas cannot make a feasible antecedent infeasible, so children are irrelevant to reachability and only cost prover time.

**Cost:** one extra `kprove` run per root (~one prove's wall time, ~16 s here). Single attempt in `verify` (only Accept flags vacuity; no retry).

**What it provably catches:** antecedent-failure vacuity (a contradictory `requires`, or LHS cells no reachable state satisfies). **What it does NOT catch:** a *feasible-but-weak* postcondition — a live spec that asserts too little (the "how useless is the spec" question). That is Finding 0005's Probe M (component load-bearing against an adversary family) and needs a curated family; it is out of scope here. Also, if the falsified mutant returns Unknown for an *unrelated* reason (timeout / solver incompleteness), the probe reads it as non-vacuous — it only ever FLAGS on a clean Accept, which is the safe direction against false-flagging a good claim but is a blind spot for a vacuous claim the prover cannot decide.

---

## Both holes closed — real prover output

`scripts/false-green.sh` (exit 0):

```
== Demo A: program binding catches the G3 no-<program> root ==
  PASS  G3 claim proves (false green)      exit=0     # prove -> Accept
  PASS  freeze REFUSES (program binding)   exit=3
== Demo B: the vacuity probe catches a program-bound vacuous root ==
  PASS  vacuous claim proves (false green) exit=0     # prove -> Accept
  PASS  vacuity REFUSES (antecedent empty) exit=3
  PASS  freeze REFUSES (vacuous root)      exit=3
```

Exact refusal messages (verbatim):

```
freeze: root debit/debit: root claim has no extractable <program> cell binding it to
  the subject; author it as `<program> #parseByteStack("<hex>") </program>` with <hex>
  = subject/runtime.bin
freeze: REFUSED (3 violation(s)); `tcg status` shows what's next per loop

VACUOUS: vac/vac — the falsified claim (ensures false) STILL proves Accept, so its
  antecedent is infeasible and the proof is empty; log: …/vac-vac-vacuity.log; fix the
  claim's `requires`/initial cells so the initial state is reachable, then re-prove
vacuity: REFUSED — at least one claim of vac is vacuous; a vacuous proof is a refusal,
  never a pass
```

**Which guard catches which hole:** program-binding catches Hole 1a (the G3 no-`<program>` claim); the vacuity probe catches Hole 1b (the program-bound infeasible-antecedent claim). The G3 claim is *not* vacuous by the antecedent test (it is reflexive, feasible — just worthless for lack of binding), so the two guards are complementary, not redundant.

**The reference root passes both** (`scripts/build-reference.sh`, exit 0):

```
-- vacuity probe withdraw (root main + guar) --
non-vacuous: withdraw/guar — falsified mutant did not prove (Unknown(c)), antecedent feasible
non-vacuous: withdraw/main — falsified mutant did not prove (Unknown(c)), antecedent feasible
…
step 4 graph: OK (3 node(s), 1 root(s); root <program> cells bind to subject/runtime.bin)
step 5v vacuity [withdraw/main]: OK (falsified form does not prove: Unknown)
certificate holds; step 6 is yours: `tcg roots <bundle>`
```

**Conformance (bundle-spec §9), now 6 controls** (`scripts/conformance.sh`, 6/6, exit 0 — supersedes Finding 0001's 5-control table):

| # | Control (tamper on a copy) | Expected | Actual | Step |
|---|---|---|---|---|
| 1 | flip one byte in `subject/runtime.bin` | 3 | 3 | 1-integrity |
| 2 | delete a proved child claim (closure) | 3 | 3 | 4-graph |
| 3 | inject a false trusted lemma | 3 | 3 | 5-replay |
| 4 | cut `replay.timeout_seconds` to 1 | 2 | 2 | 5-replay (Unknown) |
| 5 | delete `nav/` entirely | 0 | 0 | passes |
| **6** | **change subject bytes so root `<program>` no longer binds (rehashed in MANIFEST)** | **3** | **3** | **4-graph (program binding)** |

Control 6 is the point: a bundle whose hash tree is *fully self-consistent* is still refused because its root proves a property of a different program than the installed subject. The vacuity control (§9 #7) is exercised by `false-green.sh` rather than `conformance.sh`, because a tamper of the reference bundle cannot manufacture an infeasible antecedent without re-proving.

---

## P1 — `compile-claims` atomicity + coherent re-compile (Hole 2)

The transition legality is now checked, and every claim body validated + emitted **in memory**, *before* any file is written. An illegal compile (only `Proving → Compiled` remains illegal) writes nothing and exits USAGE — pinned by `tests/test_recompile.py::TestAtomicity` (a full workspace snapshot is byte-identical before/after). Re-compiling is now a legal, intended operation: it **invalidates** prior proof state — the loop returns to `Compiled`, its stale Accept/vacuity evidence and graph edges are dropped, its nodes are replaced, and any *other* loop that trusted one of its claims as a lemma is cascaded to `Stale` (pinned by `TestRecompileInvalidates`, `TestCascade`). Exit code and on-disk effect now always agree. (Content-addressing could skip re-proving an unchanged-hash claim; that optimization is deferred — re-compile conservatively returns to `Compiled`.)

---

## P2 — cheap in-compiler K parse: **deferred, with the measurement**

G3 noted `compile-claims` does zero K parsing, so a real syntax error only surfaces minutes later in `prove`'s log. Measured on this substrate: the only local K parse is `kprove --dry-run`, and it costs **~12.5 s on a valid spec** (it runs the full frontend — load definition, parse, kompile the spec to Kore — and stops before the proof search; a *broken* spec fails at ~5 s). That is not "cheap": running it on every claim would make a multi-claim `compile-claims` a multi-minute step (the exact thing the task said not to add), and `prove` already emits the *identical* parser message at the same frontend cost. No cheaper definition-free check is reliable — K uses `<`/`>` for both cell delimiters and integer comparison (`<Int`, `>=Int`), so a naive "balanced cell-tag" lint false-positives on legitimate claims. **Decision: skip, honestly, rather than ship a slow or fragile check.** Recorded here so a future move to a real parse budget trips over this measurement instead of silently doubling compile time.

---

## Honest caveats — what these guards still do NOT catch

Program binding and the vacuity probe close the two *demonstrated* G3 holes. They are not a completeness claim. Residual false-green surfaces, stated plainly:

1. **Program binding is text, not K semantics.** `extract_program_bytes` recognizes `#parseByteStack("…")` and bare hex. A root that expresses its program as a raw `b"…"` byte literal extracts as "no program" (refused — conservative), but a claim could in principle carry a decoy `<program>` cell whose bytes match the subject while the *proof obligation* references a different program elsewhere in the configuration. For a normal KEVM reachability claim the `<program>` cell *is* what `#execute` runs, so this is not reachable through the shipped claim form — but it is not adversarially K-proof. Lifting it needs a Kore-level check that the executed program is the subject.
2. **Vacuity catches antecedent failure, not weak postconditions.** A claim with a feasible antecedent and a true-but-trivial postcondition (asserts too little) passes the probe. That is a genuine "live but useless spec" and needs Finding 0005's Probe M (component mutation against an adversary family), not built here.
3. **The vacuity probe trusts the prover's Accept.** `ensures false`-proves ⇒ vacuous rests on kore-exec returning `#Top` only for a genuinely infeasible antecedent. That is the project's standing "judge = solver" axiom; a prover soundness bug is outside this guard.
4. **A vacuous claim the prover cannot decide is not flagged.** The probe FLAGS only on a clean mutant Accept; an Unknown mutant reads as non-vacuous.
5. **The arithmetic-postcondition-false substrate limit is unchanged** (Finding 0001 caveat 6 / substrate §4d): a reached-but-false *arithmetic* postcondition still surfaces as Unknown, not Refute. Program binding and vacuity do nothing about it; it needs structured counterexample extraction (`kore-rpc` `implies`/`get-model`).
6. **A root can bind + be non-vacuous + still not mean what the reader wants.** That the roots express the intended property is the irreducible human step (bundle-spec §8 step 6). No guard here touches it.
7. **Bytecode-identity, environment, and un-vendored semantics** remain verifier actions / assumptions exactly as in Finding 0001 (caveats 1, 2, 4). Program binding ties the root to `subject/runtime.bin`; whether that file *is* the on-chain code is still step 2's manual comparison.
8. **Re-compile edge cases.** A claim hash shared across two loops has its evidence dropped when either loop re-compiles (conservative: forces a re-prove of the other, never a false green). The cross-loop cascade follows `trusted-lemma` edges only.

## Reproduction

```
scripts/false-green.sh   [WORKDIR]   # reproduce BOTH G3 false greens, then refuse each
scripts/build-reference.sh [WORKDIR] # reference now passes program-binding + vacuity
scripts/conformance.sh   [BUNDLE]    # 6/6 controls (control 6 = program binding)
PYTHONPATH=<repo> python3 -m unittest discover -s tests   # 27 tests
```
