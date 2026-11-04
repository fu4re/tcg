# Specification Games: prototype report (WP8)

Status 2026-11-04, branch `feat/specgames`. Every number below is read from a committed
artifact named next to it; numbers that come from outside the repository are marked as such
and listed in section 11. Verdicts are the solver's (SMTChecker CHC + z3) or deterministic
execution (pyrevm); nothing in this report is an LLM judgement.

## 1. Summary

We built a mutation-testing harness for specifications. A generator (Claude Sonnet 5.5)
writes a Solidity spec. SMTChecker certifies it against the real contract b (Check). A fixed
adversary then searches for witnesses σ that a mutant violates (ms_cert). Everything is
packaged as a bundle that a verifier re-checks with no network and no build workspace. We
measured two subjects, each with a hand ladder and six generator trajectories
(3 feedback conditions × 2 seeds × R = 3 rounds × k = 2 candidates): a capped ERC-20 token
and MakerDAO's Vat.

- **E1, verifier:** met for all six Vat trajectory bundles, re-verified in a container
  from the bundle only. Each gives the recorded verdict and recomputes the claimed ms_cert
  and kill set (section 5). Tampered bundles are refused (`verifier/README.md`).
- **E2, ladder relations:** nesting and Prop. 6.3 hold on both ladders. Prop. 6.2's
  counterexample does **not** reproduce on the capped token.
- **E3, trajectories:** met on both subjects: 6 + 6 trajectories, with events computed on W\*.
- **E4, sharpened definitions:** met, 16 items (section 6).
- **E5, weakening after a non-Accept:** met on Vat. In f0 seed 0, the round-2 Unknown is
  followed by a weakening on W\* (m08 lost, section 4.5). One hand σ shows the round-3 spec
  still kills m08, so the loss is a loss of K_cert on W\*, not of K_sem.

## 2. Setup

| Item | Value | Source |
|---|---|---|
| solc | 0.8.35+commit.47b9dedd, static Linux binary, sha256 `fa8ac9a3…a617f4` | `TOOLCHAIN.md` |
| z3 | 4.16.0, binary sha256 `e583c418…` | `TOOLCHAIN.md` |
| Python / pyrevm | 3.12.3 / 0.3.7 (hash-pinned wheel) | `TOOLCHAIN.md`, `requirements.lock` |
| Compiler settings | evmVersion cancun, optimizer off, metadata hash none | `protocol.json` `compiler` |
| Executor (core v2) | spec_id CANCUN; tx gas 10 000 000; deploy gas 30 000 000; code size limit 1 048 576, initcode 2 097 152 (Spec only); subject runtime ≤ 24 576 (EIP-170) | `protocol.json` `executor` |
| Check (v2) | CHC per check, isolated harnesses, 4 workers, 60 000 ms per query, 600 s wall per check; strict classifier (Accept only with a "safe" line for every assert) | `protocol.json` `check`, protocol.md "Protocol v2" |
| Subjects | `capped_token` (`subjects/capped_token/CappedToken.sol`); `vat` (`subjects/vat/Vat.sol`) | `protocol.json` `subjects` |
| Vat provenance | dss `fa4f663` `src/vat.sol` → sheaf's equivalence-verified 0.8 port → only `external`→`public`; portdiff: identical runtime bytecode, 5000 seeded σ give equal observations | `subjects/vat/PROVENANCE.md`, `subjects/vat/portdiff_log.json` |
| M | 8 included mutants per subject, each with a replayed properness σ | `subjects/<s>/mutants/mutants.json` |
| Adversary | B_A 2000, seed_A 0, max_txs 6, 1 witness per mutant; capped id `229abfec…` (v2 runs: `c16d1dd5…`), Vat id `da221ec5…`, typed-v2 σ generator | `protocol.json` `subjects.<s>.adversary` |
| Generator | `claude-sonnet-5-5`, effort high, no temperature (API default), R = 3, k = 2, seeds {0, 1}, conditions f0 / fM / fMplus; max_tokens 16 000 (capped), 64 000 (Vat, streamed) | `protocol.json` `subjects.<s>.generator` |
| W\* (pool) | per trajectory: that subject's ladder witnesses ∪ the trajectory's own W_t | protocol.md 16.6, `runs/v3/vat/*/seed_*/W_star.json` |
| Judge | SMTChecker CHC (Check, κ, vacuity) and pyrevm execution (σ, witnesses, properness) only; BMC unused; no LLM in any verdict | protocol.md §1, §9 |
| Exit codes (verify) | 0 HOLDS; 2 NOT_CERTIFIED (recorded Unknown reproduces) or COULD_NOT_VERIFY; 3 REFUSED | `verifier/README.md` |

Feedback conditions:
- **f0** shows lint and compile errors and the asserts the checker could not prove.
- **fM** adds the own score.
- **fMplus** adds the survivors' ids and fault classes.

Selection is best-of-k with Accept ranked above Unknown (protocol.md 16.3).

## 3. Experiment 1: capped token

The ladder report is `bundles/ladder_report.md`.

| Spec | Check(b) | κ / asserts | ms_cert (verifier) |
|---|---|---|---|
| phi_top | Accept | 0 / 1 | 0/8 |
| phi_owner | Accept | 3 / 3 | 2/8 |
| phi_cap | Accept | 2 / 2 | 2/8 |
| phi_both | Accept | 5 / 5 | 4/8 |
| phi_transfer | Accept | 7 / 7 | 3/8 |
| phi_full | Accept | 11 / 11 | 7/8 |

Nesting (10/10) and Prop. 6.3 hold. Prop. 6.2 on M′ = {m01}: K(phi_owner) = {m01} and
K(phi_cap) = ∅, and Check(m01, phi_cap) = Accept, so the note's equivalence does not
reproduce.

`m08_mint_always_reverts` survives every spec, and Check(m08, phi_full) = Accept. It only
adds reverts, and a revert is `pre_unmet` (sharpened definition 3), so no spec in this
format can kill it.

Six trajectories (`runs/v2/<cond>/seed_<s>/trajectory.md`): every round of every
trajectory was Accept at 7/8 from round 1. All 12 events are `unchanged`. Tokens total
221 840 in and 89 553 out (sum of `trajectory.json` `tokens`), about $1.34.

## 4. Experiment 2: Vat

### 4.1 Hand ladder

Source: `subjects/vat/LADDER.md`, bundles `bundles/vat/<phi>/`, verify reports
`bundles/vat/verify/<phi>.json`. The Accept count for phi_frob_both comes from its
manifest's `hard.c.checks`.

| Spec | checks | Check(b) | Accept / checks | ms_cert | verify exit |
|---|---|---|---|---|---|
| phi_top | 1 | Accept | 1/1 | 0/8 | 0 HOLDS |
| phi_auth | 10 | Unknown | 9/10 | 1/8 | 2 NOT_CERTIFIED |
| phi_consent | 9 | Accept | 9/9 | 1/8 | 0 HOLDS |
| phi_frob | 4 | Unknown | 1/4 | 0/8 | 2 NOT_CERTIFIED |
| phi_frob_guards | 4 | Accept | 4/4 | 2/8 | 0 HOLDS |
| phi_frob_both | 8 | Unknown | 5/8 | 2/8 | 2 NOT_CERTIFIED |
| phi_fold | 3 | Unknown | 1/3 | 1/8 | 2 NOT_CERTIFIED |
| phi_move_flux | 4 | Unknown | 2/4 | 1/8 | 2 NOT_CERTIFIED |
| phi_grab_heal_suck | 5 | Unknown | 3/5 | 1/8 | 2 NOT_CERTIFIED |
| phi_books | 3 | Unknown | 0/3 | 3/8 | 2 NOT_CERTIFIED |
| phi_full | 42 | Unknown | 29/42 | 7/8 | 2 NOT_CERTIFIED |

- All 42 nesting relations hold, and so does Prop. 6.3 (trivially, since K(phi_frob) = ∅).
- No check is refuted on b. The 13 non-Accept checks of phi_full are all exact-amount or
  books-balance checks that CHC leaves unproved.
- Only the three Accepted rungs are certified scores. The best of them is 2/8.

### 4.2 Six trajectories

Generated by `runs/v3/vat/rescoring/collect.py` → `tables.md` / `collect.json`, from
`runs/v3/vat/<cond>/seed_<s>/`. ★ marks the selected candidate. "Check" counts per-check
verdicts from `check_summary.json`; the wall is the Check pool's.

#### fM seed 0

| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |
|---|---|---|---|---|---|---|
| 1 | 1 | lint_rejected: S9 (11 errors) | — | 0/8 | — | 33033 / 21643 |
| 1 | 2 ★ | Unknown (unproved) | 35 / 25 unproved (1344 s) | 7/8 | 641 | 18901 / 10146 |
| 2 | 1 | Unknown (unproved) | 49 / 3 unproved (249 s) | 4/8 | 1514 | 15208 / 9150 |
| 2 | 2 ★ | Unknown (unproved) | 53 / 13 unproved (469 s) | 7/8 | 666 | 15172 / 7404 |
| 3 | 1 | Unknown (unproved) | 59 / 6 unproved (195 s) | 7/8 | 647 | 9260 / 2382 |
| 3 | 2 ★ | Accept | 59 / 0 (11 s) | 6/8 | 958 | 7207 / 856 |

#### f0 seed 0

| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |
|---|---|---|---|---|---|---|
| 1 | 1 | compile_error: Stack too deep | — | 0/8 | — | 25985 / 14089 |
| 1 | 2 ★ | Unknown (unproved) | 39 / 15 unproved (592 s) | 4/8 | 1805 | 20383 / 11750 |
| 2 | 1 ★ | Unknown (unproved) | 41 / 16 unproved (511 s) | 4/8 | 2000 | 19005 / 9797 |
| 2 | 2 | Unknown (unproved) | 42 / 16 unproved (565 s) | 3/8 | 2331 | 17711 / 8679 |
| 3 | 1 ★ | Unknown (unproved) | 49 / 4 unproved (203 s) | 3/8 | 2016 | 12885 / 5345 |
| 3 | 2 | Unknown (unproved) | 47 / 3 unproved (9 s) | 3/8 | 1894 | 10744 / 3550 |

#### f0 seed 1

| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |
|---|---|---|---|---|---|---|
| 1 | 1 ★ | Unknown (unproved) | 50 / 21 unproved (804 s) | 7/8 | 728 | 26040 / 17078 |
| 1 | 2 | compile_error: Stack too deep | — | 0/8 | — | 26438 / 16368 |
| 2 | 1 ★ | Unknown (unproved) | 52 / 10 unproved (514 s) | 7/8 | 673 | 16808 / 6756 |
| 2 | 2 | Unknown (unproved) | 56 / 1 unproved (78 s) | 5/8 | 1333 | 10081 / 3350 |
| 3 | 1 | Unknown (unproved) | 52 / 10 unproved (504 s) | 7/8 | 662 | 13051 / 3284 |
| 3 | 2 ★ | Accept | 54 / 0 (10 s) | 5/8 | 1279 | 8552 / 1644 |

#### fMplus seed 0

| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |
|---|---|---|---|---|---|---|
| 1 | 1 ★ | lint_rejected: S9 (3 errors) | — | 0/8 | — | 16061 / 6898 |
| 1 | 2 | lint_rejected: S9 (11 errors) | — | 0/8 | — | 21736 / 11363 |
| 2 | 1 ★ | compile_error: Stack too deep | — | 0/8 | — | 10678 / 614 |
| 2 | 2 | compile_error: Stack too deep | — | 0/8 | — | 9387 / 351 |
| 3 | 1 ★ | Unknown (unproved) | 55 / 25 unproved (920 s) | 7/8 | 901 | 11828 / 977 |
| 3 | 2 | Unknown (unproved) | 57 / 26 unproved (515 s) | 7/8 | 937 | 12352 / 1290 |

#### fMplus seed 1

| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |
|---|---|---|---|---|---|---|
| 1 | 1 ★ | Unknown (budget) | 53 / 14 unproved + 1 wall_timeout (772 s) | 6/8 | 1245 | 23182 / 13318 |
| 1 | 2 | compile_error: Stack too deep | — | 0/8 | — | 23102 / 13325 |
| 2 | 1 ★ | Unknown (unproved) | 56 / 12 unproved (686 s) | 6/8 | 1329 | 25302 / 14013 |
| 2 | 2 | Unknown (unproved) | 63 / 13 unproved (454 s) | 6/8 | 1400 | 29021 / 17566 |
| 3 | 1 ★ | Accept | 66 / 0 (39 s) | 4/8 | 2105 | 18196 / 8366 |
| 3 | 2 | Accept | 68 / 0 (25 s) | 4/8 | 2147 | 16416 / 6658 |

#### fM seed 1

| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |
|---|---|---|---|---|---|---|
| 1 | 1 ★ | Unknown (unproved) | 53 / 28 unproved (957 s) | 7/8 | 935 | 24548 / 13431 |
| 1 | 2 | lint_rejected: S9 (1 error) | — | 0/8 | — | 21335 / 11174 |
| 2 | 1 | Unknown (unproved) | 64 / 6 unproved (215 s) | 6/8 | 1711 | 19718 / 10578 |
| 2 | 2 ★ | Unknown (unproved) | 68 / 3 unproved (188 s) | 7/8 | 1204 | 20551 / 11225 |
| 3 | 1 ★ | Accept | 69 / 0 (10 s) | 5/8 | 1724 | 9003 / 198 |
| 3 | 2 | Accept | 69 / 0 (6 s) | 5/8 | 1719 | 8992 / 207 |

#### Summary

Kill sets K_t on the trajectory's own W\* come from `events.json`, the verify result from
`verify.json`, the wall time from `runs/v3/vat/rescoring/loop_logs/<traj>.log`, and tokens
from `trajectory.json`.

| condition | seed | \|K_1\| → \|K_2\| → \|K_3\| on W\* | \|W\*\| | events 1→2, 2→3 | final acc | verify | wall s | tokens in / out (thinking) | $ |
|---|---|---|---|---|---|---|---|---|---|
| fM | 0 | 7 → 7 → 6 | 25 | unchanged, weakening −m08 | Accept | 0 HOLDS, 6/8 | 9864.5 | 175 992 / 98 781 (51 581) | 1.34 |
| f0 | 0 | 4 → 4 → 3 | 17 | unchanged, weakening −m08 | Unknown | 2 NOT_CERTIFIED, 3/8 | 15161.9 | 180 734 / 106 713 (53 210) | 1.43 |
| f0 | 1 | 7 → 7 → 5 | 19 | unchanged, weakening −m06 −m08 | Accept | 0 HOLDS, 5/8 | 9503.4 | 201 520 / 100 970 (48 480) | 1.41 |
| fMplus | 0 | 0 → 0 → 7 | 18 | unchanged, strengthening +7 (no runnable spec in rounds 1–2) | Unknown | 2 NOT_CERTIFIED, 7/8 | 9112.7 | 140 396 / 82 042 (21 493) | 1.10 |
| fMplus | 1 | 6 → 6 → 4 | 21 | unchanged, weakening −m06 −m08 | Accept | 0 HOLDS, 4/8 | 14727.8 | 206 150 / 135 219 (73 246) | 1.76 |
| fM | 1 | 7 → 7 → 5 | 21 | unchanged, weakening −m06 −m08 | Accept | 0 HOLDS, 5/8 | 11885.6 | 203 658 / 104 147 (46 813) | 1.45 |

The best certified Vat score is 6/8 (fM seed 0). It is above every certified rung of the
hand ladder (best 2/8). phi_full reaches 7/8 but is not certified.

### 4.3 Format failures

Source: `collect.json` `format_failures`, 36 candidates in the six trajectories.

| kind | count | rate | where |
|---|---|---|---|
| runnable (lint-clean and compiles) | 27 | 27/36 = 75 % | — |
| lint S9 (`require` outside the leading Pre block) | 4 | 4/36 = 11 % | fM s0 r1c1 (11 errors), fMplus s0 r1c1 (3), fMplus s0 r1c2 (11), fM s1 r1c2 (1) |
| compile_error: "Stack too deep" (codegen; passes SMTChecker's compile) | 5 | 5/36 = 14 % | f0 s0 r1c1, f0 s1 r1c2, fMplus s0 r2c1, fMplus s0 r2c2, fMplus s1 r1c2 |
| max_tokens with no text | 0 | 0/36 | — |

All S9 failures are in round 1. Every round-2 and round-3 candidate is lint-clean, which
suggests that the feedback fixed the format. The compile errors appear in rounds 1 and 2.

The three aborted fM seed 0 attempts are kept as records with READMEs and are not part of
any result. Their summary is in `collect.json` `aborted`.

| attempt | candidates | outcome | cause |
|---|---|---|---|
| `runs/v3/vat/fM/seed_0_aborted_max_tokens` | r1c1, r1c2 | both lint_rejected, `stop_reason max_tokens`, 16 000 output tokens all thinking, no text | max_tokens 16 000 at effort high on an 8 745-token prompt → Vat max_tokens 64 000 |
| `runs/v3/vat/fM/seed_0_aborted_code_size` | r1c1 | Check Unknown (49 Accept / 24 unproved, 805 s); adversary 0/8 with every check `not_run` | Spec over Vat runtime 37 530 bytes > EIP-170, every deploy `CreateContractSizeLimit` → core v2 |
| `runs/v3/vat/fM/seed_0_aborted_stack_too_deep` | r1c1 | Check ran (82 checks, 1806 s); the loop crashed on the adversary's compile ("Stack too deep") | codegen error not gated → compile before Check |

### 4.4 Unknown reasons

Source: `collect.json` `unknown_reasons`.

- **Per check.** Over the 27 Check runs of the six trajectories there are 1749 per-check
  results: 1478 Accept, 270 Unknown `unproved`, **1** Unknown `wall_timeout`, and no Refute.
  The one wall timeout is in fMplus seed 1 round 1 candidate 1, which is therefore Unknown
  (`budget`). Every other Unknown is `unproved`: CHC returned "might happen" without a
  counterexample within 60 000 ms per query. f0 seed 0, f0 seed 1 and fM seed 0 have no wall
  timeout in any Check.
- **Per spec.** Of the 26 Unknown candidates, 20 are `unproved`, 5 `compile_error` and
  1 `budget`.
- **κ.** Separately, the κ run of fMplus seed 1 (Check over the havoc base) has one check,
  `check_frob_debt_pos`, at the 600 s wall. So κ is undetermined there (`kappa.json`:
  `determined false`, 139 asserts, 2375.8 s).

### 4.5 The weakening

Diffs: `runs/v3/vat/rescoring/weakening_diffs.md`, produced by `diffs.py`. Probe:
`runs/v3/vat/f0/seed_0/probes/m08_sin_setup/`.

**fM seed 0, round 2 → 3** (`round_2/cand_2` → `round_3/cand_2`). Two checks are deleted:
`check_grab_sin_up` (dy = −1: sin[u] and vice rise by rate) and `check_grab_sin_down`
(dy = 1: both fall by rate). They are replaced by `check_grab_debt_unchanged`, which keeps
only `assert(debt == t0)`. The sin and vice asserts were what killed m08_grab_no_vice. The
round-3 spec is Accept, at 6/8.

**f0 seed 0, round 2 → 3** (`round_2/cand_1` → `round_3/cand_1`). `check_grab_sin` (dx, dy ≤ 0, the
liquidation regime) became `check_grab_sin_up` (dx, dy ≥ 0) with the same asserts.

- From the profile's setup, dy > 0 underflows `sin[u]` (setup sin is 0). The only reachable
  case in W\* is therefore dy = 0, where m08 equals b, so m08 left K on W\*.
- The hand σ adds a sin-creating setup first: `suck(bob, bob, 1 ray)` by the ward, then the
  probe `check_grab_sin_up(GOLD, bob, 0, 1)`.
- Over b this σ ends `success` with no check violated (38 pre_unmet, 15 success). Over m08
  `check_grab_sin_up` ends in `violation` (Panic 0x01).
- So the round-3 spec still kills m08 semantically. The weakening is of K_cert on W\*; K_sem
  did not shrink on this mutant. The typed-v2 adversary never generates the two-step setup
  (first sin > 0, then grab with dy > 0).
- The same hand σ does **not** kill m08 for fM seed 0's round-3 spec (`rescoring.json`
  column `K_union_probe`). That spec deleted the asserts, so its loss is in the spec itself.

**Regularity, observed on W\* only.**
- m08 is lost at round 2 → 3 in all five trajectories that had a runnable round-2 spec.
- m06_fold_no_debt is lost at the same step in three of them (f0 s1, fMplus s1, fM s1).
- In the four trajectories whose final is Accept, the loss coincides with the selection of
  an Accept round-3 spec over Unknown alternatives:
  - In fM s0, f0 s1 and fM s1, the round-3 alternative candidate (or the round-2 pick) was
    Unknown at 7/8.
  - In fMplus s1, both round-3 candidates were Accept at 4/8.
- The Unknown-final trajectory f0 seed 0 lost m08 as well (4 → 4 → 3), so the loss is not
  tied to the Accept step alone.
- fMplus seed 0 has no comparable step, since its first runnable spec is in round 3.

This is a measured instance of the pressure the selection rule creates: Accept is ranked
above Unknown. It is not a claim about K_sem beyond the one probed mutant and spec.

### 4.6 Union-pool rescoring (protocol.md 16.11)

Source: `runs/v3/vat/rescoring/rescore.py` → `rescoring.json`. pyrevm only, 267.5 s,
4 processes.

- **Pool.** U is the union of the six trajectories' W\* and the Vat ladder's evidence: 56
  distinct (mutant, σ) pairs, sha256 `c3b1e50a…`. Per mutant: m01 4, m02 7, m03 7, m04 6,
  m05 0, m06 10, m07 6, m08 16.
- **Specs scored.** Every round's selected spec (a round without a runnable spec is scored
  as K = ∅), plus the 11 ladder rungs.
- **Result.** Every spec's K on U equals its K on its own pool, so no spec gains or loses a
  mutant. The ordering of the six finals and phi_full is identical on both pools:
  fMplus s0 (7) = phi_full (7) > fM s0 (6) > f0 s1 (5) = fM s1 (5) > fMplus s1 (4) >
  f0 s0 (3). Ties are broken by name.
- **Caveat.** The per-trajectory pools are therefore not what separates the trajectories
  here. U contains 16 m08 pairs, and still no final Accept spec kills m08 on U, nor does
  any final spec kill m05.
- **With the probe.** U plus the hand σ of 4.5 adds m08 only for f0 seed 0's round-3 spec
  (3/8 → 4/8).

### 4.7 κ and vacuity (a) on Vat

Sources: `kappa.json`, `vacuity_a.json` of each trajectory, `collect.json`.

| trajectory | κ / asserts | κ wall s | vacuity (a): checks, flagged, unknown | vacuity wall s |
|---|---|---|---|---|
| fM s0 | 84 / 84 | 1394.7 | 59, 0, 59 | 1010.1 |
| f0 s0 | 96 / 96 | 1343.5 | 53, 0, 53 | 920.4 |
| f0 s1 | 92 / 92 | 1281.3 | 54, 0, 54 | 878.2 |
| fMplus s0 | 160 / 160 | 2373.0 | 80, 0, 80 | 2074.8 |
| fMplus s1 | undetermined (139 asserts; one wall_timeout over H) | 2375.8 | 66, 0, 66 | 1081.5 |
| fM s1 | 134 / 134 | 1590.1 | 69, 0, 69 | 800.3 |

**Both are uninformative on Vat.**
- κ equals the assert count wherever it is determined. Over the havoc base every assert is
  unproved or violated, so none is counted as a tautology, and κ therefore does not
  separate the specs.
- Vacuity (a) is `unknown` for all 381 checks: the probe placed after Pre comes back
  "might happen" without a counterexample. Pre satisfiability is not established for any
  check, although nothing is flagged.

**Proposal, not a result: a constructive route to non-vacuity.** A check is non-vacuous on b
if some σ, executed, reaches its Post with Pre met. Concretely, the probe returns `success`
over b rather than `pre_unmet`. The adversary's replay logs already record these outcomes:
for example, the hand σ above gives 15 checks `success` on b. Counting, per check, whether
any σ in W\* or in the 2000 adversary σ reached `success` on b would give an
execution-certified lower bound on non-vacuity without the solver. Not implemented.

### 4.8 m05_frob_no_dust

- **Never killed.** No spec kills m05, hand-written or generated, on any pool: U has 0 m05
  pairs, and m05 is absent from every K in `rescoring.json`.
- **Not unkillable.** The hand σ in `tests/test_vat_ladder.py` (ward `file(GOLD, dust,
  1e48)`, then `check_frob_not_dusty`) kills m05 for phi_full. So m05 ∈ K_sem(phi_full).
- **Why the adversary misses it.** The kill needs a dust above the setup urns' debt
  (50 wad × 1 ray) and then a probe on the same ilk. Typed-v2 draws the probe's arguments
  independently of the prefix: of phi_full's 2000 σ, 20 set such a dust from the ward and
  2 probe the same ilk (`subjects/vat/LADDER.md`, "Distribution gap"). This is a
  distribution gap of the adversary, not a limit of the spec format.

## 5. Gates

| Gate | Status | Evidence | Caveat |
|---|---|---|---|
| E1 | met for all six bundles | isolated re-verify (`verifier/run_isolated.sh`, Docker, `--network none`, read-only bundle), run by the orchestrator on the VM, logs `runs/v3/vat/rescoring/e1_isolated/<cond>_seed_<s>.log`; refusals: `verifier/README.md` "Recorded runs", `tests/test_verify.py` Tamper | see the rows below |
| E2 | nesting and Prop. 6.3 met; Prop. 6.2 not reproduced | `bundles/ladder_report.md` (ii)–(iv); `subjects/vat/LADDER.md` Relations | the Prop. 6.2 result is a measurement against the note, reported as such |
| E3 | met | `runs/v2/*/seed_*/events.json`, `runs/v3/vat/*/seed_[01]/events.json` | two seeds per condition; W\* per trajectory (4.6) |
| E4 | met (16 items) | section 6 | — |
| E5 | met (Vat f0 seed 0) | 4.5 diff; `runs/v3/vat/f0/seed_0/events.json` | the shrunken kill set is on W\*; one probe shows K_sem did not shrink for m08 |

E1 rows. Source: `runs/v3/vat/rescoring/e1_isolated/<cond>_seed_<s>.log`, the verifier's
summary plus the shell's `time`; time = `real`. These are verbatim copies of the
orchestrator's logs. The last three come from one log, split at its `== <cond>/<seed>`
headers, and are in that log's shorter form.

| bundle | isolated verify | ms_cert recomputed | kill set = claim | time |
|---|---|---|---|---|
| `runs/v3/vat/fM/seed_0/bundle` | HOLDS, exit 0 | 6/8 | yes | 143 s (2m23.435s) |
| `runs/v3/vat/f0/seed_0/bundle` | NOT_CERTIFIED at step 2, exit 2 | 3/8 | yes | 280 s (4m40.492s) |
| `runs/v3/vat/f0/seed_1/bundle` | HOLDS, exit 0 | 5/8 | yes | 177 s (2m57.479s) |
| `runs/v3/vat/fMplus/seed_0/bundle` | NOT_CERTIFIED at step 2, exit 2 | 7/8 | yes | 985 s (16m24.980s) |
| `runs/v3/vat/fMplus/seed_1/bundle` | HOLDS, exit 0 | 4/8 | yes | 184 s (3m4.115s) |
| `runs/v3/vat/fM/seed_1/bundle` | HOLDS, exit 0 | 5/8 | yes | 151 s (2m31.054s) |

- **Verdicts.** Every recomputed kill set is the bundle's claimed one: the full mutant ids
  on each log's `ms_cert = … kill set […]` line equal `claimed.kill_set` of
  `runs/v3/vat/<cond>/seed_<s>/bundle/manifest.json`. Every verdict equals the in-loop
  verify of the same bundle (`runs/v3/vat/<cond>/seed_<s>/verify.json`).
- **Concurrency.** The orchestrator states that the first three ran concurrently with a
  running trajectory on the same host. The logs carry no timestamps, so this is not
  established from them. No Check of those three trajectories hit a wall timeout (4.4).
- **Last three.** They ran sequentially with no trajectory running (load 0 at start),
  also per the orchestrator.
- **Isolation.** The container shares the host kernel and CPU (`verifier/README.md`).

## 6. Sharpened definitions (E4)

Consolidated from protocol.md "Sharpened definitions", items 1–16, and the gate E4 list in
`PLAN.md`.

| # | Sharpening | Forced by |
|---|---|---|
| 1 | Σ is the constructor-reachable, pool-restricted configuration space; K_sem is relative to it, while CHC quantifies over all addresses | protocol.md §4–5, the pool in `subjects/<s>/profile.json` |
| 2 | φ is a conjunction of per-check implications, and a witness is "some check panics", so Prop. 6.3 holds for the union of checks without "share Pre" | `bundles/ladder_report.md` (iii) |
| 3 | Pre absorbs every revert, so liveness is inexpressible and an add-reverts mutant is proper but unkillable | capped m08: Check(m08, phi_full) = Accept, `bundles/ladder_report.md` survivor table |
| 4 | Observable = outcome class + success return data + getter state; gas, events and revert payloads are excluded | protocol.md §6 |
| 5 | κ's havoc base must havoc behaviour (an unknown external call), not only state | protocol.md §11 measurement |
| 6 | Unknown has two sources (query timeout, over-approximation) that solc prints identically | `TOOLCHAIN.md` finding 2 |
| 7 | Accept needs a positive "safe" line for every assert: without z3, solc skips CHC and exits 0 | `TOOLCHAIN.md` finding 1 |
| 8 | An unreachable assert is Accepted, hence vacuity (a) as a separate test | `subjects/capped_token/specs/controls/phi_dead.sol` |
| 9 | Two identities: mutant id = runtime sha256; pair id = Spec-over-artifact runtime sha256 | protocol.md §10 |
| 10 | ms_cert is an exact rational over included mutants only | `schemas/manifest.schema.json` `claimed` |
| 11 | Behavioural duplicates are decided on the union of the recorded properness σ, flagged and kept | `tools/properness.py` |
| 12 | CHC counterexamples are not witnesses; only replayed σ count | protocol.md §9 |
| 13 | The probe's `check` field is provenance; a witness is scored against every check | `tools/events.py` |
| 14 | Vacuity (a) tests Pre satisfiability, not assert reachability | protocol.md §12 |
| 15 | Check is per check (isolated harnesses), not per spec | phi_full 632 s → 0.8 s; `runs/fM/seed_0/README.md` (1500 s wall) |
| 16 | The Spec is a measurement harness, never deployed: EIP-170 / EIP-3860 lifted for it only | `runs/v3/vat/fM/seed_0_aborted_code_size/README.md` |

Two further items from this experiment, proposed and not yet in protocol.md:
- **(17)** An event against a round without a runnable spec (lint or compile failure, K = ∅)
  is "no spec", not a strengthening or weakening. Evidence: fMplus seed 0.
- **(18)** A weakening on W\* must be reported against K_cert, not K_sem, unless a
  K_sem-side check exists (4.5).

## 7. Protocol and core history

| Change | Trigger artifact | Commit |
|---|---|---|
| Protocol v1 → v2: per-check isolated Check, 4 workers, 60 000 ms, 600 s per check | the v1 whole-harness Check of the generator's first spec ended at the 1500 s wall (`runs/fM/seed_0/README.md`); phi_full 597–632 s whole vs 0.8 s isolated (protocol.md "Protocol v2") | `fae2ea9`, `2f3a5f9` |
| protocol.json / protocol.md split; restamp | every prose change forced a full ladder rebuild (23 min, protocol.md 16.9) | `92593e6`, `052e2d4` |
| Protocol v3: subjects with pinned profiles, typed σ, setup in σ, typed-v2 generator | Vat needs bytes32/int256 arguments, a setup state and multiple probe signatures (`subjects/vat/profile.json`) | `be5ce2c`, `48002f1`, `5ec8bbf` |
| Verifier exit semantics: NOT_CERTIFIED = exit 2 | 8 Vat ladder bundles with a reproduced Unknown came out exit 3 although steps 3–5 passed (`subjects/vat/LADDER.md`) | `23d4691` |
| Vat max_tokens 16 000 → 64 000, streamed | `runs/v3/vat/fM/seed_0_aborted_max_tokens` | `abbafe0` |
| Core v1 → v2: Spec deploys with 1 MiB / 2 MiB limits, 30 M deploy gas; subject ≤ 24 576 enforced; migration restamp proves 1296 observations identical | `runs/v3/vat/fM/seed_0_aborted_code_size` | `d381d5a` |
| Compile the whole Spec to bytecode before Check | `runs/v3/vat/fM/seed_0_aborted_stack_too_deep` | `0da54cb` |
| Storage: `check.json.gz` + `check_summary.json` in v3 runs | 20–25 MB raw Check record per Vat candidate (protocol.md 16.10) | `7411561` |

## 8. Cost and time

Prices: `claude-sonnet-5-5` at $2 per MTok input and $10 per MTok output (thinking is
billed as output and included in output tokens). Source: `collect.py`.

- **Vat, six trajectories.**
  - Wall time 70 256 s ≈ 19.5 h, on a 4-core VM, strictly one trajectory at a time.
  - 1 108 450 input and 627 872 output tokens (294 823 thinking), ≈ $8.50.
  - API time is 432–857 s per trajectory (sum of `trajectory.json` `calls[].wall_s`). The
    rest is Check, the adversary, κ and vacuity.
- **Vat, aborted attempts.** 35 k input and 94 k output tokens received ≈ $1.01. Logged
  wall time 4570 s (attempts 2 and 3). Attempt 1 has no WALL line.
- **Capped token** (`runs/v2`). 221 840 input and 89 553 output tokens ≈ $1.34.
- **Production estimate.** One Vat-sized spec trajectory (R = 3, k = 2) costs $1.1–1.8 in
  API and 2.5–4.2 h of 4-core wall time. The judge side dominates, not the generator.

## 9. Limitations and open questions

- **Format failures eat the budget.** On Vat, 9 of 36 candidates were not runnable, and
  fMplus seed 0 had no runnable spec until round 3. R = 3 leaves little room for the
  feedback to act on the specification itself.
- **Per-trajectory pools.** W\* differs per trajectory (17–25 pairs). On Vat, rescoring on
  the union changed nothing (4.6), but that is a measured fact for this run, not a guarantee.
- **Vacuity is blind on Vat.** Vacuity (a) is unknown for every check, and κ equals the
  assert count. Neither separates the specs, and the constructive route (4.7) is only a
  proposal.
- **Two seeds per condition.** The spread between the two seeds within a condition is
  f0 3 vs 5, fM 6 vs 5 and fMplus 7 vs 4. That is of the same order as the spread across
  conditions at a fixed seed (seed 0: 3–7, seed 1: 4–5). No condition-level claim is made.
- **The selection rule is the reward.** Accept is ranked above Unknown. The weakening of
  4.5 is what this rule pays for. A rule that weighed kill sets against Accept would change
  the pressure, and that is untested.
- **The typed-v2 adversary has no multi-step setups.**
  - It misses m05 (dust, then a frob on the same ilk) and the m08 case of 4.5 (sin > 0, then
    grab with dy > 0).
  - The certified scores are lower bounds of the semantic ones (K_cert ⊆ K_sem).
- **Stack too deep.**
  - 5 of 36 candidates failed in code generation, which SMTChecker's compile skips.
  - `viaIR` with the optimizer would avoid it, but changes the compiled artifact and its
    ids. It is not tried here, because the pinned settings are part of the semantics.
- **BMC deliberately unused.** It is deprecated upstream and was cancelled in step 2a. The
  engine-probe numbers in `subjects/vat/specs/measurement/engine_probe.json` are a
  historical note only.
- **Trusted base.**
  - pyrevm 0.3.7 (EVM semantics, including the lifted size limits), solc 0.8.35 code
    generation and SMTChecker, and z3 4.16.0.
  - The Vat port's equivalence to dss rests on sheaf's verification plus portdiff:
    identical bytecode to the sheaf port, and 5000 σ.
  - The container shares the host kernel.

## 10. Reproduction

Run from `specgame/`. At this commit `make test` ran 220 tests: OK, 1 skipped (the Vat
refusal test, which applies only when the mutants or the ladder are missing).

Toolchain setup, then the unit tests:

```bash
./setup.sh
```

```bash
make test
```

Verify one ladder bundle, and one trajectory bundle in the container:

```bash
.venv/bin/python -I -B tools/verify.py bundles/vat/phi_frob_guards
```

```bash
verifier/run_isolated.sh runs/v3/vat/fM/seed_0/bundle
```

Re-run the union-pool rescoring and the collected tables:

```bash
.venv/bin/python -B runs/v3/vat/rescoring/rescore.py --workers 4
```

```bash
.venv/bin/python -B runs/v3/vat/rescoring/collect.py
```

The m08 probe:

```bash
.venv/bin/python -B runs/v3/vat/f0/seed_0/probes/m08_sin_setup/probe.py
```

One trajectory (live API, needs `ANTHROPIC_API_KEY` or `~/.specgame_env`; refuses an
existing output directory):

```bash
.venv/bin/python -u -B generator/loop.py --subject vat --condition fM --seed 0 --out <new-dir>
```

## 11. Numbers not sourced from a committed artifact

- **Load during E1:** that the first three isolated re-verifies ran concurrently with a
  trajectory, and the last three with none. The orchestrator states this; the committed
  logs have no timestamps. The results and times themselves are in
  `runs/v3/vat/rescoring/e1_isolated/`.
- **Capped-token trajectory wall times:** not recorded in `runs/v2` and not given here.
- **Vat bundle re-verify wall times** (1192–1194 s per pass, quoted in
  `subjects/vat/LADDER.md`): from verifier runs whose logs are not committed. Only the
  per-bundle times appear in LADDER.md.
- **VM hours outside the trajectories** (ladder builds, re-verifies, tests): not counted in
  section 8.
