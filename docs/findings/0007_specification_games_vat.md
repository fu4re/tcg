# Finding 0007 — Specification Games on MakerDAO Vat: a solver-judged spec generator weakens its spec under Accept pressure in 5/5 trajectories, the mutation score sees it, and all six bundles re-verify offline

- **Date:** 2026-11-04 · **Type:** prototype build + measurement (the Specification Games note, work packages WP1–WP8; full report `specgame/REPORT.md`) · **Judge:** SMTChecker CHC (solc 0.8.35+commit.47b9dedd, z3 4.16.0) for Check / κ / vacuity, deterministic pyrevm 0.3.7 execution for witnesses; BMC unused (deprecated upstream); **no LLM in any verdict** · **Generator (untrusted):** `claude-sonnet-5-5`, effort high, no temperature · **Subjects:** a capped ERC-20 token (experiment 1) and MakerDAO **Vat** (sheaf's equivalence-verified 0.8 port, runtime bytecode identical to the sheaf port; experiment 2) · **Builds on:** Finding 0002 (false green, vacuity), sheaf Findings 0002 (solver as judge on Vat) and 0005 (vacuity gate, mutation testing) · **Code:** `specgame/` (this commit; the per-change history is on branch `feat/specgames`).
- **TL;DR:** We built the note's loop end to end: a generator proposes a Solidity spec φ, SMTChecker certifies it against the real contract b (Check), a fixed adversary searches for witnesses σ on which a mutant m violates φ while b does not (the certified mutation score ms_cert), and the result is frozen as a bundle that a verifier re-checks with no network and no build workspace. **(1) The verifier gate E1 is met for all six Vat trajectory bundles:** each one, re-verified in an isolated container, reproduces the recorded verdict (4 HOLDS, 2 NOT_CERTIFIED) and recomputes the claimed kill set exactly. **(2) The note's central pressure was observed, not just predicted:** with Accept ranked above Unknown in the selection rule, every one of the five Vat trajectories that had a runnable round-2 spec lost mutant m08 at the round-2 → round-3 step (`weakening` on W\*); in fM seed 0 the generator deleted the two sin/vice asserts that had been killing m08 and reached Accept at 6/8 instead of Unknown at 7/8. **(3) The mutation score is the detector:** the weakening is invisible to Check (Accept) and visible to ms_cert (7 → 6, 7 → 5, 6 → 4). **(4) Honest limits:** the best certified Vat score is 6/8 against 2/8 for the hand ladder, but with two seeds per condition the spread within a condition is as large as the spread across conditions, so no claim about f0 vs fM vs fMplus is made; κ and vacuity (a) are uninformative on Vat (all `unknown`); m05 is never killed by anyone because the typed adversary has no multi-step setups; 9 of 36 generator candidates failed on format alone (lint S9, "Stack too deep"). One hand σ shows that in f0 seed 0 the "weakening" is a loss of K_cert on the witness pool, not of K_sem: the round-3 spec still kills m08 semantically. Cost: 19.5 h of 4-core VM wall time and ≈ $8.50 of API for the six Vat trajectories.

---

## Setup

| | |
|---|---|
| Loop | generator → lint → compile (whole Spec over b to bytecode) → Check (CHC per check, isolated harnesses, 4 workers, 60 000 ms per query, 600 s wall per check) → adversary (B_A 2000 σ, seed 0, ≤ 6 txs, 1 witness per mutant) → κ, vacuity (a) → bundle → verify. R = 3 rounds, k = 2 candidates per round, best-of-k with Accept ranked above Unknown (protocol.md 16.3) |
| Feedback conditions | **f0** lint/compile errors + the asserts Check could not prove · **fM** adds the own score · **fMplus** adds the survivors' ids and fault classes. Seeds {0, 1} |
| Mutants M | 8 per subject, each with a replayed properness σ (`specgame/subjects/<s>/mutants/mutants.json`); fault classes missing-bound-check, accounting, access-control, consent |
| Events | computed on W\* = that subject's ladder witnesses ∪ the trajectory's own W_t (per trajectory, 17–25 pairs on Vat); `unchanged` / `weakening` / `strengthening` / `shift` from the kill set K_t |
| Executor (core v2) | pyrevm, spec CANCUN, 10 M tx gas; the Spec harness deploys with EIP-170/3860 lifted (1 MiB code, 2 MiB initcode, 30 M deploy gas) because a Spec over Vat is 37 530 bytes; **the subject b and every mutant stay ≤ 24 576 bytes** (enforced); the migration restamp proved 1296 recorded observations identical |
| Verifier | steps (0) manifest … (6) V-completeness, from the bundle only; exit 0 HOLDS, 2 NOT_CERTIFIED (the recorded Unknown reproduces; steps 3–6 still run and ms_cert is reported) or COULD_NOT_VERIFY, 3 REFUSED; isolated run = Docker, `--network none`, read-only bundle (`specgame/verifier/`) |
| Vat provenance | dss `fa4f663` `src/vat.sol` → sheaf's 0.8 port → only `external` → `public`; portdiff: identical runtime bytecode, 5000 seeded σ give equal observations (`specgame/subjects/vat/PROVENANCE.md`) |
| Toolchain | pinned and hash-checked in `specgame/TOOLCHAIN.md`; solc static Linux binary, z3 4.16.0, pyrevm 0.3.7 hash-pinned wheel, Python 3.12.3 |
| Independent verification | this orchestrator re-verified all six Vat trajectory bundles in the isolated container on the VM; logs are committed verbatim under `specgame/runs/v3/vat/rescoring/e1_isolated/` |

Every number below is read from a committed artifact under `specgame/`; `specgame/REPORT.md` names the artifact next to each number and lists (§11) the few that are not so sourced.

---

## 1. Experiment 1 — capped token (the warm-up, no pressure observed)

Hand ladder of six rungs, all Accept, ms_cert 0/8 → 2/8 → 2/8 → 4/8 → 3/8 → 7/8; nesting 10/10 and Prop. 6.3 hold. Prop. 6.2's counterexample does **not** reproduce on M′ = {m01}. `m08_mint_always_reverts` survives every spec and Check(m08, phi_full) = Accept: a mutant that only adds reverts is proper but unkillable in this format, because Pre absorbs every revert (sharpened definition 3).

Six generator trajectories: every round of every trajectory was Accept at 7/8 from round 1, all 12 events `unchanged`. The subject is too easy to create any pressure; ≈ $1.34 of API.

## 2. Experiment 2 — Vat, hand ladder

Eleven rungs (`specgame/subjects/vat/LADDER.md`, bundles `specgame/bundles/vat/`). Only three are Accepted on b and therefore certified: phi_top 0/8, phi_consent 1/8, phi_frob_guards 2/8. The other eight are Unknown on b (exit 2 NOT_CERTIFIED); phi_full reaches 7/8 on the adversary but 13 of its 42 checks (exact-amount and books-balance) stay unproved by CHC. No check is refuted on b. All 42 nesting relations hold.

**The best certified hand rung is 2/8.** This is the bar the generator is measured against.

## 3. Experiment 2 — six generator trajectories

| condition | seed | \|K_1\| → \|K_2\| → \|K_3\| on W\* | events 1→2, 2→3 | final Check | isolated verify | wall s | API $ |
|---|---|---|---|---|---|---|---|
| fM | 0 | 7 → 7 → 6 | unchanged, weakening −m08 | Accept | 0 HOLDS, 6/8 | 9864 | 1.34 |
| f0 | 0 | 4 → 4 → 3 | unchanged, weakening −m08 | Unknown | 2 NOT_CERTIFIED, 3/8 | 15162 | 1.43 |
| f0 | 1 | 7 → 7 → 5 | unchanged, weakening −m06 −m08 | Accept | 0 HOLDS, 5/8 | 9503 | 1.41 |
| fMplus | 0 | 0 → 0 → 7 | unchanged, strengthening +7 (no runnable spec in rounds 1–2) | Unknown | 2 NOT_CERTIFIED, 7/8 | 9113 | 1.10 |
| fMplus | 1 | 6 → 6 → 4 | unchanged, weakening −m06 −m08 | Accept | 0 HOLDS, 4/8 | 14728 | 1.76 |
| fM | 1 | 7 → 7 → 5 | unchanged, weakening −m06 −m08 | Accept | 0 HOLDS, 5/8 | 11886 | 1.45 |

Sources: `specgame/runs/v3/vat/<cond>/seed_<s>/{events,verify,trajectory}.json`, collected by `specgame/runs/v3/vat/rescoring/collect.py` → `tables.md`.

- The best certified generated score, **6/8 (fM seed 0), is above every certified hand rung (2/8)**. phi_full's 7/8 is not certified.
- Over the 27 Check runs: 1749 per-check results, 1478 Accept, 270 Unknown `unproved`, **1** `wall_timeout` (fMplus seed 1 round 1, hence Unknown `budget`), no Refute. Every other Unknown is CHC "might happen" without a counterexample.
- Trajectories ran strictly one at a time on a 4-core VM: an earlier concurrent attempt produced wall timeouts that would have confounded Unknown(budget) with Unknown(unproved).

### E1 — the six bundles, re-verified in the isolated container

| bundle | isolated verify | ms_cert recomputed | kill set = claim | time |
|---|---|---|---|---|
| `runs/v3/vat/fM/seed_0/bundle` | HOLDS, exit 0 | 6/8 | yes | 143 s |
| `runs/v3/vat/f0/seed_0/bundle` | NOT_CERTIFIED at step 2, exit 2 | 3/8 | yes | 280 s |
| `runs/v3/vat/f0/seed_1/bundle` | HOLDS, exit 0 | 5/8 | yes | 177 s |
| `runs/v3/vat/fMplus/seed_0/bundle` | NOT_CERTIFIED at step 2, exit 2 | 7/8 | yes | 985 s |
| `runs/v3/vat/fMplus/seed_1/bundle` | HOLDS, exit 0 | 4/8 | yes | 184 s |
| `runs/v3/vat/fM/seed_1/bundle` | HOLDS, exit 0 | 5/8 | yes | 151 s |

Each recomputed kill set equals `claimed.kill_set` in the bundle's `manifest.json`, and each verdict equals the in-loop `verify.json`. Tampered bundles are refused (`specgame/verifier/README.md`, `tests/test_verify.py`). The first three re-verifies ran while a trajectory was running on the same host (orchestrator's statement; the logs carry no timestamps), the last three with the host idle.

## 4. The weakening (the result)

Diffs: `specgame/runs/v3/vat/rescoring/weakening_diffs.md`. Probe: `specgame/runs/v3/vat/f0/seed_0/probes/m08_sin_setup/`.

- **fM seed 0, round 2 → 3.** The selected round-2 spec was Unknown at 7/8. In round 3 the generator deleted `check_grab_sin_up` and `check_grab_sin_down` (the asserts on `sin[u]` and `vice` under `grab`, exactly what killed `m08_grab_no_vice`) and replaced them with `check_grab_debt_unchanged`, which asserts only `debt == t0`. That spec is Accept at 6/8 and was selected over an Unknown alternative at 7/8. **The loss is in the spec itself:** the hand σ below does not kill m08 for it either.
- **f0 seed 0, round 2 → 3.** `check_grab_sin` (dx, dy ≤ 0, the liquidation regime) became `check_grab_sin_up` (dx, dy ≥ 0) with the same asserts. From the profile's setup state `sin[u] = 0`, so every dy > 0 underflows and only dy = 0 is reachable on W\*, where m08 equals b: m08 leaves K_cert. A hand σ that first creates sin (`suck(bob, bob, 1 ray)` by the ward) and then probes `check_grab_sin_up(GOLD, bob, 0, 1)` ends `success` on b (no check violated) and in `violation` (Panic 0x01) on m08. **The round-3 spec still kills m08 semantically; this weakening is of K_cert on W\*, not of K_sem.** The typed-v2 adversary never generates the two-step setup.
- **Regularity on W\*.** m08 is lost at round 2 → 3 in all five trajectories with a runnable round-2 spec; m06_fold_no_debt is lost at the same step in three. In the four Accept-final trajectories the loss coincides with selecting an Accept round-3 spec over Unknown alternatives (or, in fMplus seed 1, both round-3 candidates were Accept at 4/8). The Unknown-final trajectory f0 seed 0 lost m08 as well, so the loss is not tied to the Accept step alone.

This is a measured instance of the pressure the selection rule creates (Accept ranked above Unknown; Thm 8.1's direction). It is a statement about K_cert on the witness pools, plus one probed mutant and spec on the K_sem side; it is not a claim about K_sem in general.

## 5. What came back uninformative or empty

- **κ and vacuity (a) on Vat.** κ equals the assert count wherever determined (84/84, 96/96, 92/92, 160/160, 134/134; undetermined for fMplus seed 1 after one 600 s wall over the havoc base): over the havoc base every assert is unproved or violated, so none is a tautology and κ separates nothing. Vacuity (a) is `unknown` for all 381 checks: Pre satisfiability is established for none, although none is flagged. The vacuity gate of Finding 0002 / sheaf 0005 does not transfer to Vat-sized harnesses through CHC alone.
- **m05_frob_no_dust is never killed**, by any hand or generated spec on any pool (0 m05 pairs in the union pool). It is not unkillable: the hand σ in `specgame/tests/test_vat_ladder.py` (ward `file(GOLD, dust, 1e48)`, then `check_frob_not_dusty`) kills it for phi_full, so m05 ∈ K_sem(phi_full). The typed-v2 adversary draws the probe's arguments independently of the prefix: of 2000 σ, 20 set such a dust and 2 probe the same ilk. **A distribution gap of the adversary, not of the spec format.**
- **Union-pool rescoring** (protocol.md 16.11; `rescore.py` → `rescoring.json`): on the union U of all six W\* and the ladder's evidence (56 distinct (mutant, σ) pairs) every spec's kill set equals its kill set on its own pool; the ordering of finals is unchanged. The per-trajectory pools are not what separates the trajectories here (a measured fact for this run, not a guarantee).
- **Format failures: 9 of 36 candidates.** Lint S9 (`require` outside the leading Pre block) ×4, all in round 1 and all corrected by the feedback in later rounds; "Stack too deep" ×5, a codegen error that SMTChecker's compile does not raise (now caught by compiling the whole Spec before Check). fMplus seed 0 had no runnable spec until round 3. With R = 3 this leaves little room for the feedback to act on the specification itself.
- **Three aborted fM seed 0 attempts** are kept as records with READMEs (`runs/v3/vat/fM/seed_0_aborted_*`): max_tokens 16 000 exhausted entirely by thinking (→ 64 000, streamed); the Spec over Vat exceeding EIP-170 so every deploy failed `CreateContractSizeLimit` and ms_cert read 0/8 as an executor artifact (→ core v2); the loop crashing on the adversary's compile (→ compile before Check). ≈ $1.01 of API.

## 6. Sharpened definitions

Sixteen items forced by the implementation are consolidated in `specgame/REPORT.md` §6 and protocol.md (Σ constructor-reachable and pool-restricted while CHC quantifies over all addresses; Pre absorbs reverts; two Unknown sources printed identically by solc; Accept needs a positive "safe" line per assert; CHC counterexamples are not witnesses, only replayed σ; Check per check, not per spec; the Spec is a measurement harness never deployed; …). Two more are proposed from this experiment and not yet in protocol.md: **(17)** an event against a round with no runnable spec is "no spec", not a strengthening or weakening; **(18)** a weakening on W\* is reported against K_cert, not K_sem, unless a K_sem-side check exists.

## 7. Cost and time

- Vat, six trajectories: 70 256 s ≈ 19.5 h wall on a 4-core VM, one trajectory at a time; 1 108 450 input / 627 872 output tokens (294 823 thinking) ≈ $8.50 at $2 / $10 per MTok. API time is 432–857 s per trajectory; the rest is Check, adversary, κ and vacuity. **The judge side dominates, not the generator.**
- Production estimate for one Vat-sized trajectory (R = 3, k = 2): $1.1–1.8 of API and 2.5–4.2 h of 4-core wall time.

## 8. Honest caveats / what remains assumed

- **Two seeds per condition.** Within-condition spread (f0 3 vs 5, fM 6 vs 5, fMplus 7 vs 4) is of the same order as the across-condition spread at a fixed seed. **No condition-level claim.**
- **The selection rule is the reward.** The weakening of §4 is what "Accept above Unknown" pays for; a rule weighing kill sets against Accept would change the pressure and is untested.
- **Certified scores are lower bounds** (K_cert ⊆ K_sem); the adversary has no multi-step setups (misses m05 and the m08 case of §4).
- **Vacuity is blind on Vat** (§5). A constructive route (count, per check, whether any replayed σ reaches its Post with Pre met on b, i.e. returns `success` rather than `pre_unmet`) is proposed in `REPORT.md` §4.7 and not implemented.
- **Stack too deep.** `viaIR` with the optimizer would avoid it but changes the compiled artifact and its ids; not tried, because the pinned settings are part of the semantics.
- **Trusted base:** pyrevm 0.3.7 (EVM semantics including the lifted size limits), solc 0.8.35 codegen + SMTChecker, z3 4.16.0; the Vat port's equivalence to dss rests on sheaf's verification plus portdiff; the verifier container shares the host kernel and CPU.
- **Not sourced from a committed artifact:** host load during the first three E1 re-verifies; capped-token trajectory wall times; VM hours outside the trajectories (ladder builds, re-verifies, tests).

## Conclusion

The loop the note describes runs end to end on a real 13 KB DeFi core with a solver, not an LLM, as the only judge, and its output is a bundle that re-verifies offline (6/6). Under the simplest reward (Accept first) the generator did what Thm 8.1 says it would: it made the spec easier to prove, and the certified mutation score, not the solver's Accept, is what recorded the loss. The two things that did not work (κ / vacuity through CHC on Vat; a single-step adversary) are the two things a next iteration needs before any comparison between feedback conditions is worth running at scale.

## Reproduction

From `specgame/` on a Linux host with Docker (`./setup.sh` pins the toolchain; `make test` ran 220 OK, 1 skipped at this commit):

```bash
specgame/verifier/run_isolated.sh specgame/runs/v3/vat/fM/seed_0/bundle
```

```bash
cd specgame && .venv/bin/python -B runs/v3/vat/rescoring/rescore.py --workers 4 && .venv/bin/python -B runs/v3/vat/rescoring/collect.py
```

```bash
cd specgame && .venv/bin/python -B runs/v3/vat/f0/seed_0/probes/m08_sin_setup/probe.py
```

A fresh trajectory needs `ANTHROPIC_API_KEY` (or `~/.specgame_env`) and refuses an existing output directory:

```bash
cd specgame && .venv/bin/python -u -B generator/loop.py --subject vat --condition fM --seed 0 --out <new-dir>
```
