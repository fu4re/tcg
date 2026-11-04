# Specification Games prototype — implementation plan

Status: plan v1, 2026-11-02. Branch `feat/specgames` (from `main` @ 9388dae).
Source task: `TASK_specgame_prototype.md` (2026-11-02 draft, kept outside the repo).
Companion theory: the "Specification Games" note (Stoliarov, 2026-10-29),
`docs/papers/Specification_Games_Stoliarov_2026-10-29.pdf`; a text extraction
is in `specgame/reference/` for grepping definitions on the VM.

Roles: this session orchestrates and reviews; Opus sessions on the `tcg` VM
implement. Every verdict reported in the final note is re-run by the orchestrator
from the committed sources before it is accepted (project rule: judge = solver;
reviewer reproduces, never trusts a self-report).

---

## 0. Success criteria (restated as gates)

| Gate | Pass condition (binary) | Who checks |
|---|---|---|
| E1 | `verify.py` on a *second* machine, from the bundle only, recomputes `ms_cert` equal to the claimed one; a bundle with a swapped witness and one with swapped bytecode are both refused | orchestrator, on a machine that never saw the build session |
| E2 | kill-sets for the hand-written ladder are nested as sets; `kill(φ_owner ∧ φ_cap) == kill(φ_owner) ∪ kill(φ_cap)`; Prop. 6.2 counterexample reproduced on `M'` | script (`tools/events.py --ladder`), output table committed |
| E3 | 3 feedback conditions × ≥2 seeds × R=3 rounds ran; weakening/strengthening/shift events computed from `W*` as sets | `runs/` trajectories + `events.json` |
| E4 | ≥2 note definitions recorded as "had to be sharpened", each with a proposed text change | REPORT.md section |
| E5 (bonus) | one f∅ trajectory shows a non-Accept followed by a spec weakening visible as a shrunken kill-set on `W*` | REPORT.md, one diff |

Not claimed anywhere: H1–H4 as results, V-completeness, transfer to bytecode/KEVM/Lean.

---

## 1. Stack decisions (proposed; replaceable while the two invariants hold:
formal judge, deterministic replay on another machine)

| Role | Choice | Why |
|---|---|---|
| Compiler | pinned `solc` binary (0.8.35+commit.47b9dedd, same pin as `sheaf/cycle`), `evmVersion` pinned (`cancun`), optimizer off, `--metadata-hash none` | one compiler for both Check and run; runtime bytecode hash = mutant identity; metadata hash must be stripped or bytecode hashes drift with file paths |
| Check(b, φ) | solc SMTChecker, engine `chc`, solver `z3`, targets `assert`, fixed timeout; reuse the runner/parser design of `sheaf/cycle/trusted/solver.py` (copied, not imported — `specgame/` must stay self-contained) | known-good on this toolchain (sheaf Findings 0002/0005/0006) |
| run(b, σ) executor | **pyrevm** (pinned wheel) as the single execution core, via `tools/run.py`; fallback `py-evm` if pyrevm fails to install on the VM | one deterministic core shared by adversary, scorer and verifier; witness replay is literally the same function call; no anvil process, no JSON-RPC nondeterminism |
| Adversary A | own seeded random sequence fuzzer in Python over the same executor (`tools/adversary.py`), budget `B_A` = number of sequences per (mutant, φ) | forge fuzz/invariant witnesses are hard to export as replayable σ; our own fuzzer produces σ directly in the bundle format |
| Foundry | optional, only for `forge` cross-check of compilation in `make check`; not on the verifier path | keeps verifier deps minimal |
| Generator G | Claude API (`claude-sonnet-5-5` or `claude-opus-5-5`, temperature fixed, prompts frozen in `generator/prompts/`) via the official SDK; alternative: `claude -p` headless as in `sheaf/cycle/naive_loop` | see Q3 |
| Driver / verifier | Python 3.12, stdlib + pyrevm only; `verify.py` imports nothing from `tools/` except a tiny shared `specgame_core.py` that is itself hashed into the bundle | E1 trust story: a reader re-implements hashes + replay in an evening |

---

## 2. Definitions that must be fixed in code before anything runs (`protocol.md`)

These are the places where the note's definitions are not yet mechanical. Each is
both a design decision and an E4 candidate.

1. **Configuration σ (Σ gap, task §7.1).** σ = (constructor args, sender list,
   sequence of contract calls with senders and args, final probe). Every state is
   constructor-reachable by construction, matching what CHC actually proves.
   Pre is checked at execution time (a `require` revert = Pre unmet, not a witness).
2. **Shared probe signature (needed for a shared pool W\*).** A witness found under
   φ_t ends with a call to one of φ_t's `check_*` functions. To score the *same* σ
   against a different φ', every `check_*` in every spec takes the same fixed
   argument tuple `(address a, address b, uint256 x, uint256 y)` and is called
   with the same sender. Scoring σ against φ' = replay the prefix, then call each
   `check_*` of φ' with σ's tail; the pair (mutant, σ) is a witness for φ' iff some
   `check_*` ends in `Panic(0x01)`. Without this convention "W\* = ⋃ W_t" is not
   well defined across specs. (E4 item.)
3. **Outcome rule (Condition D).** `Panic(0x01)` from a `check_*` → violation
   (witness). Revert with `Error(string)` or empty revert → Pre unmet, not a
   witness. `Panic(0x11)` and other panics → logged as `other`, not a witness.
   Applied identically in adversary, scorer and verifier.
4. **κ (non-tautological conjunct count).** Proposed mechanical test: a conjunct
   `assert(e)` is tautological iff it proves over a *havoc* base — the same
   `check_*` compiled against a stub contract whose state is unconstrained
   (all storage free, functions return free values). Proving over `b` is **not**
   a tautology test (every true property of `b` proves over `b`). The
   M-relative alternative (empty kill-set on M) is recorded as an alternative,
   not used. (E4 item.)
5. **Unknown = non-Accept**, solver timeout fixed (proposal: 120 s per harness;
   measure on the ladder first and freeze in `protocol.md`).
6. **Properness pair** for a mutant m: a σ with `run(b, σ) ≠ run(m, σ)` where the
   observation is (success/revert outcome, return data, full storage of the token
   contract after the sequence). Found by differential fuzzing, re-checked by
   replay, stored in `mutants.json`. A mutant with no pair within budget is
   excluded and logged (open question 10 of the note: behavioural duplicates on
   the found σ are marked, not merged).
7. **Mutant identity** = keccak/sha256 of runtime bytecode compiled from the
   mutant source under the pinned compiler. Two mutants with equal runtime
   bytecode are the same mutant (rejected at library build time).
8. **Events on W\*** (note §9, "Weakening event"). For rounds t, t+1 with
   certified kill-sets K_t, K_{t+1} computed on the *final* pool
   W\* = ⋃_t W_t: round t is a weakening iff K_{t+1} ⊊ K_t; a strengthening iff
   K_{t+1} ⊋ K_t; a shift iff incomparable; unchanged iff equal. Re-scoring a
   pair (b', σ) against another φ is sound because the pair does not depend on
   φ (needs item 2 above). The kill-set of a non-Accepted φ_t is still
   computed on W\* (it is a kill-set, not a certificate; certified adequacy
   additionally needs Accept on b, Def. 5.4), and `acc_t` is recorded next to
   it so "weakening after a non-Accept" (H1 mechanism, E5) is visible.
9. **Three vacuity checks kept apart** (note §5, remark after Def. 5.4):
   (a) Pre satisfiable — per `check_*`, an `assert(false)` placed right after
   the `require`s must get a counterexample under CHC (the sheaf Probe R
   convention: `assert(false)` proved ⇒ unreachable ⇒ flag); (b) conclusion
   non-trivial — the κ tautology test of item 4; (c) M-vacuity — empty
   certified kill-set. The bundle carries all three; none replaces another.
10. **Prop. 6.2 counterexample, as the note states it, may not reproduce.**
    The note's `m1` removes only the access control on `mint`; if the cap
    check survives in `m1`, no configuration lets a non-owner mint *past the
    cap*, so φ_cap does not kill `m1` and φ_owner ≢ φ_cap on M'. Whether the
    counterexample reproduces is an empirical outcome of WP6, not a target:
    if it fails, this is an E4 item with a proposed fix (e.g. the note's
    example needs `m1` to drop the whole guard, or a `CappedToken` whose
    owner and cap checks are one `require`). The ladder must not be bent to
    make the note's example pass.
11. **Trust classes in the manifest** (note §10, Table 2): b, φ, c → hard
    layer; M (hash identity), properness pairs, W, `B_A`, adversary id →
    evidence layer; fault labels / operators → metadata, `T*`, affect no
    verdict; V-completeness claim → absent, written to `not_claimed`;
    feedback condition, rounds, prompts → provenance layer. Step (1) of the
    verifier contract hashes the semantics version (pyrevm + solc build) and
    the verifier's own source.

---

## 3. Repository layout (as in the task, with the additions above)

```
specgame/
  PLAN.md  protocol.md  setup.sh  Makefile  README.md
  contracts/CappedToken.sol  intent.md
  mutants/m01_*.sol … m08_*.sol  mutants.json
  specs/phi_top.sol phi_owner.sol phi_cap.sol phi_both.sol phi_transfer.sol phi_full.sol
        SPEC_FORMAT.md            # the harness contract + probe signature + outcome rule
  tools/specgame_core.py          # hashing, compile, executor, outcome parsing (shared, hashed into bundle)
        compile.py check.py run.py adversary.py bundle.py verify.py events.py kappa.py
  generator/prompts/{system.md,intent_I.md,feedback_f0.md,feedback_fM.md,feedback_fMplus.md}
            loop.py
  bundles/<phi>/manifest.json + files
  runs/<condition>/<seed>/round_<t>/
  tests/                          # unit tests for outcome parsing, hashing, set algebra
  REPORT.md
```

---

## 4. Work packages, dependencies, parallelism

```
WP0 env ─┐
         ├─► WP-I interfaces (protocol.md draft, SPEC_FORMAT.md, JSON schemas, core stubs)
         │        │
         │        ├─► WP1+2 contract + mutants + properness   ─┐
         │        ├─► WP3  spec format + check.py + φ_top/neg  ├─► WP4 adversary + W ─► WP6 ladder (E2)
         │        └─► WP5  bundle.py + verify.py (+ tamper tests) ┘          │
         │                                                                     ├─► WP7 LLM loop (E3/E5)
         └──────────────────────────────────────────────────────────────────► WP8 REPORT (E4)
```

Each WP = one Opus session on the VM. Sessions that write code never share
files; the interface package (WP-I) is reviewed and frozen before the parallel
wave starts.

### Wave 0 — environment and interfaces (sequential, 2 sessions)

- **WP0 (env)**: `setup.sh` installing pinned solc, z3, Python 3.12 venv, pyrevm,
  (optional) foundry; `make check` = compile `CappedToken`, SMTChecker on a
  tautology (proved) and on `assert(false)` (counterexample), one pyrevm
  execution. Done when it runs from scratch on the VM and the log is committed.
- **WP-I (interfaces)**: writes `protocol.md` (section 2 above, with the
  parameters R, k, seeds, model, temperature, B_A, seed_A, timeout left as
  `TBD-before-WP7` placeholders), `SPEC_FORMAT.md`, JSON schemas for
  `mutants.json`, witness σ, `manifest.json`, and `specgame_core.py` with the
  hashing / compile / executor / outcome functions plus unit tests.
  Orchestrator review gate: every definition in section 2 is present and
  mechanical; no LLM anywhere on the judge path.

### Wave 1 — three parallel sessions

- **WP1+WP2 (subject + mutants)**: `CappedToken.sol`, `intent.md` (plain-language
  intent I, states that the goal is discriminating power, not checker
  acceptance), 6–8 mutants with `operator` / `fault_class`, ABI-identical to `b`,
  properness pairs found by differential fuzzing and re-checked by replay,
  duplicates by bytecode rejected, duplicates by behaviour flagged.
- **WP3 (spec format + Check)**: `check.py` wrapping SMTChecker with the fixed
  flags; `phi_top.sol`; negative control `phi_false` (an assert `b` violates)
  must yield Refute with a counterexample; a `require(false)`-guarded check must
  be reported Accept (vacuous by design, noted) so the φ⊤ assumption TA holds.
  `kappa.py` implementing the havoc-base tautology test.
- **WP5 (bundle + verifier)**: `bundle.py` assembling manifest + files;
  `verify.py` implementing the §10 contract steps (1)–(6) with exit codes
  0 HOLDS / 2 could-not-verify / 3 refused (same discipline as `tcg`); tamper
  fixtures: swapped witness, swapped mutant bytecode, edited `ms_cert`, dropped
  properness pair — all must be refused with the reason named.

### Wave 2 — adversary and ladder (sequential, 1–2 sessions)

- **WP4 (adversary + witnesses)**: seeded sequence fuzzer, budget `B_A` per
  (mutant, φ), every candidate witness replayed before it is kept, discarded
  pairs logged with reason. Output: `W_φ` in bundle format.
- **WP6 (ladder, E2)**: the six hand-written specs, Check + W + kill-set per
  spec; `events.py --ladder` asserts nesting and `kill(φ_both) == kill(φ_owner)
  ∪ kill(φ_cap)` and prints the spec × mutant table; the Prop. 6.2 `M'`
  experiment. Orchestrator re-runs `check.py` and `verify.py` on every bundle.

### Wave 3 — generator loop (1 session, after `protocol.md` is frozen)

- **WP7**: `generator/loop.py` with the three feedback conditions, R=3,
  best-of-k=2, ≥2 seeds; prompts frozen and hashed into the run manifests; cost
  estimated before the run (36 calls at ~15k input tokens ≈ well under $10 on
  Sonnet 5.5; Opus 5.5 roughly 5×). All rounds scored on the final `W*`;
  `events.py` emits the per-round event table and one spec diff per condition.

### Wave 4 — report

- **WP8**: `REPORT.md` in the `04_evidence` house style (Setup table, numbers
  with N, what is shown / not shown, caveats next to numbers), mandatory
  section "Note definitions that had to be sharpened" (≥2 items, with proposed
  wording), and the E1 second-machine log. The author decides whether it
  becomes Finding 0009.

---

## 5. Review protocol (orchestrator)

For every session result, before it is merged into `feat/specgames`:
1. Diff read in full; English-only check; no secrets / no Cyrillic in files.
2. Commands re-run by the orchestrator on the VM: `make check`, the unit tests,
   `check.py` on the ladder, `verify.py` on every bundle and on every tamper
   fixture (non-zero exit expected).
3. Soundness traps checked explicitly: vacuous Accepts (probe `assert(false)`
   reachability on each `check_*` of the ladder, reported, not hidden); witness
   that passes only because Pre is unmet; mutant whose runtime bytecode equals
   `b`; harness that mutates its own copy of the state instead of calling the
   token; Unknown counted as Accept anywhere.
4. One-line commits in dependency order, no attribution trailers (repo rule).
   Nothing is pushed to `origin` without an explicit per-push approval; code
   moves between the laptop and the VM through the `vm` remote.

---

## 6. Decisions taken by the author (2026-11-02)

- **Q0 — the note text.** `docs/papers/` on `main`, extraction in
  `specgame/reference/`.
- **Q1 — repository.** Stays in `tcg` under `specgame/`.
- **Q2 — second machine for E1.** Any isolation boundary on the VM is
  acceptable (clean container, separate unix user, or similar), as long as
  the verifier run never sees the build session's workspace. Plan: a
  separate unix user on the VM with a fresh clone of the verifier sources
  and only the bundle copied in; a container is the fallback.
- **Q3 — generator access.** Anthropic API key on the VM; model id,
  temperature and prompts pinned in `protocol.md`. The key lives only in the
  VM environment, never in the repo or the bundle.
- **Q4 — VM.** sudo is available; the KEVM toolchain under `~/toolchains`
  stays untouched.
- **Q5 — executor.** pyrevm as the single execution core, no objection.
