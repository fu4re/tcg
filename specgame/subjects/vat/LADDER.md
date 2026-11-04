# Vat ladder (protocol v3, step 2): spec texts, Check(b, φ), kill sets

Status 2026-11-03. Spec texts, Check on b, kill sets from the adversary
(typed-v2 generator, frozen B_A), bundles `bundles/vat/<phi>/` verified with
`tools/verify.py` (after the verify/bundle subject fix, 959e47b / 4a5e9e6).
Reproduce: `make vat-ladder` (full), or `python tools/ladder.py --subject vat
--reuse-witnesses --survivor-specs phi_full` (bundle + verify on stored
witnesses), then `python tools/events.py --ladder --subject vat`.

## Setup

| Item | Value |
|---|---|
| b | `subjects/vat/Vat.sol` (profile `subjects/vat/profile.json`) |
| Check | v2 isolated, SMTChecker CHC + z3, timeout_ms 60000, wall 600.0 s per check, 4 workers, no cache |
| Command | `python tools/check.py subjects/vat/specs/<phi>.sol --subject vat --json <out>` |
| Raw results | `build/vat_ladder/check/<phi>.json` (1–16 MB each, not committed); summary in `specs/check_summary.json` |

## Rungs

| Spec | Intent item | Checks | Kind |
|---|---|---|---|
| phi_top | — | 1 | `debt == debt` |
| phi_auth | 1 | 10 | must-revert without wards: rely, deny, init, file (2), slip, grab, suck, fold, cage |
| phi_consent | 2 | 9 | must-revert without consent: frob u / v / w, fork src / dst, flux, move; hope / nope act on the caller only |
| phi_frob | 6 (amounts) | 4 | per-transition accounting of frob: urn ink/art, ilk Art and rate, gem[v], dai[w] and debt (= rate·dart) |
| phi_frob_guards | 6 (no-effect cases) | 4 | after a successful frob: ceilings, safety (if riskier), not dusty; no frob when not live |
| phi_fold | 10 | 3 | rate += dx, Art unchanged, dai[u] and debt += Art·dx; no fold when not live |
| phi_move_flux | 5 | 4 | move exact between two, self-move unchanged, third balance and debt unchanged; flux exact |
| phi_grab_heal_suck | 8, 9 | 5 | grab: urn, Art, gem[v], sin[w] and vice (= rate·dart), debt unchanged; heal and suck exact |
| phi_books | 12 | 3 | global, two keys: dai[a]+dai[b] ≤ debt, sin[a]+sin[b] ≤ vice, vice ≤ debt |
| phi_frob_both | 6 | 8 | phi_frob ∪ phi_frob_guards, textually (the Vat analogue of phi_both; Prop. 6.3) |
| phi_full | all | 42 | the textual union of the eight rungs other than phi_frob_both (test: `tests/test_vat_ladder.py`) |

`phi_frob_guards` and `phi_books` are additions to the requested rungs. Without
`phi_frob_guards` no rung can kill m03–m05: those faults only *remove* reverts
from frob, and every successful frob still moves exactly the requested amounts,
so phi_frob is satisfied by them. `phi_books` encodes intent 12 in the only
form the format allows (no loops, so no sums over all keys).

Arithmetic in the specs is written so that a fault surfaces as a violation, not
as a spec overflow (`Panic(0x11)` = `other`): debits are asserted additively
(`dai[a] + x == a0`), signed deltas through `int256` (a wrapped conversion or
an overflowing signed sum panics, never fakes a violation).

## Check(b, φ) per spec

| Spec | Verdict | Accept / checks | Unknown checks |
|---|---|---|---|
| phi_top | **Accept** (all_checks_safe) | 1 / 1 | — |
| phi_auth | **Unknown** (unproved) | 9 / 10 | file_ilk_needs_auth |
| phi_consent | **Accept** (all_checks_safe) | 9 / 9 | — |
| phi_frob | **Unknown** (unproved) | 1 / 4 | frob_urn_exact, frob_ilk_exact, frob_dai_debt_exact |
| phi_frob_guards | **Accept** (all_checks_safe) | 4 / 4 | — |
| phi_fold | **Unknown** (unproved) | 1 / 3 | fold_rate_exact, fold_dai_debt_exact |
| phi_move_flux | **Unknown** (unproved) | 2 / 4 | move_exact, flux_exact |
| phi_grab_heal_suck | **Unknown** (unproved) | 3 / 5 | grab_urn_ilk_exact, grab_sin_vice_exact |
| phi_books | **Unknown** (unproved) | 0 / 3 | two_dai_within_debt, two_sin_within_vice, vice_within_debt |
| phi_full | **Unknown** (unproved) | 29 / 42 | file_ilk_needs_auth, frob_urn_exact, frob_ilk_exact, frob_dai_debt_exact, fold_rate_exact, fold_dai_debt_exact, move_exact, flux_exact, grab_urn_ilk_exact, grab_sin_vice_exact, two_dai_within_debt, two_sin_within_vice, vice_within_debt |

phi_full: 410.946 s wall, 1485.686 s solc total. **No check is Refuted on b.**

## Check(b, φ) per check (phi_full run; every rung's checks are among these)

| Check | Verdict | Per assert | s |
|---|---|---|---|
| check_cage_needs_auth | Accept (all_targets_safe) | safe | 5.78 |
| check_deny_needs_auth | Accept (all_targets_safe) | safe | 5.536 |
| check_file_global_needs_auth | Accept (all_targets_safe) | safe | 5.944 |
| check_file_ilk_needs_auth | Unknown (unproved) | unproved | 63.063 |
| check_flux_exact | Unknown (unproved) | unproved safe | 66.934 |
| check_flux_needs_consent | Accept (all_targets_safe) | safe | 6.449 |
| check_fold_dai_debt_exact | Unknown (unproved) | unproved unproved | 125.241 |
| check_fold_needs_auth | Accept (all_targets_safe) | safe | 5.625 |
| check_fold_needs_live | Accept (all_targets_safe) | safe | 5.197 |
| check_fold_rate_exact | Unknown (unproved) | unproved unproved | 125.156 |
| check_fork_needs_dst_consent | Accept (all_targets_safe) | safe | 7.255 |
| check_fork_needs_src_consent | Accept (all_targets_safe) | safe | 6.466 |
| check_frob_dai_debt_exact | Unknown (unproved) | unproved unproved | 124.637 |
| check_frob_gem_exact | Accept (all_targets_safe) | safe | 4.471 |
| check_frob_ilk_exact | Unknown (unproved) | unproved safe | 67.237 |
| check_frob_needs_live | Accept (all_targets_safe) | safe | 6.375 |
| check_frob_needs_u_consent | Accept (all_targets_safe) | safe | 5.704 |
| check_frob_needs_v_consent | Accept (all_targets_safe) | safe | 6.565 |
| check_frob_needs_w_consent | Accept (all_targets_safe) | safe | 6.99 |
| check_frob_not_dusty | Accept (all_targets_safe) | safe | 5.986 |
| check_frob_riskier_is_safe | Accept (all_targets_safe) | safe | 5.844 |
| check_frob_urn_exact | Unknown (unproved) | unproved unproved | 126.021 |
| check_frob_within_ceilings | Accept (all_targets_safe) | safe safe | 9.014 |
| check_grab_gem_exact | Accept (all_targets_safe) | safe | 5.824 |
| check_grab_needs_auth | Accept (all_targets_safe) | safe | 6.169 |
| check_grab_sin_vice_exact | Unknown (unproved) | unproved unproved safe | 127.856 |
| check_grab_urn_ilk_exact | Unknown (unproved) | unproved unproved unproved | 186.451 |
| check_heal_exact | Accept (all_targets_safe) | safe safe safe safe | 18.418 |
| check_hope_own_only | Accept (all_targets_safe) | safe safe | 11.399 |
| check_init_needs_auth | Accept (all_targets_safe) | safe | 5.72 |
| check_move_exact | Unknown (unproved) | unproved safe | 67.218 |
| check_move_needs_consent | Accept (all_targets_safe) | safe | 6.749 |
| check_move_others_and_debt_unchanged | Accept (all_targets_safe) | safe safe | 9.69 |
| check_move_self_unchanged | Accept (all_targets_safe) | safe | 5.487 |
| check_nope_own_only | Accept (all_targets_safe) | safe safe | 11.325 |
| check_rely_needs_auth | Accept (all_targets_safe) | safe | 6.031 |
| check_slip_needs_auth | Accept (all_targets_safe) | safe | 6.092 |
| check_suck_exact | Accept (all_targets_safe) | safe safe safe safe | 19.499 |
| check_suck_needs_auth | Accept (all_targets_safe) | safe | 5.462 |
| check_two_dai_within_debt | Unknown (unproved) | unproved | 63.07 |
| check_two_sin_within_vice | Unknown (unproved) | unproved | 62.898 |
| check_vice_within_debt | Unknown (unproved) | unproved | 62.838 |

Unknown is always `unproved` (no check hit its 600 s wall); its durations are
multiples of the 60 s per-query timeout, i.e. queries exhausted their budget.
solc prints the same text for a query timeout and for incompleteness
(TOOLCHAIN.md finding 2), so the two are not separated.

Observations:

- Must-revert properties (auth, consent, live) are Accepted in 5–7 s, with one
  exception: `check_file_ilk_needs_auth` is Unknown although its sibling
  `check_file_global_needs_auth` is Accepted in 6 s. Re-run alone at
  300 000 ms / 1500 s (informational, outside the frozen budget): still
  Unknown (unproved), 301.9 s, i.e. one query exhausts any budget tried. The
  difference between the two is the `file(bytes32,bytes32,uint256)` body
  (three bytes32 comparisons and a struct write). The check is kept as
  written; phi_auth is therefore Unknown on b.
- The frob guards are Accepted (6–9 s) although they contain products: each
  assert restates a `require` frob has just passed.
- Exact-amount laws are Unknown whenever the amount is a product (rate·dart,
  Art·dx) and also for some purely linear ones (`frob_urn_exact`,
  `frob_ilk_exact` Art, `move_exact` debit, `flux_exact` debit, `grab_urn_ilk_exact`):
  presumably because the path condition carries frob's/grab's products, or the `_sub` helper's
  unchecked wrap-then-check, which CHC does not discharge within budget.
  Linear laws over `_add` only (`frob_gem_exact`, `grab_gem_exact`, `heal_exact`,
  `suck_exact`, `move_others_and_debt_unchanged`) are Accepted.
- Global invariants (phi_books) are Unknown, as measured in protocol.md
  (Protocol v3) for `two_dai_balances_within_debt`.

Consequence: on Vat, Accept is reached by phi_top, phi_consent and
phi_frob_guards only; spec strength must be read off kill sets (Unknown =
non-Accept everywhere, protocol.md section 9).

## Sanity: hand-written witnesses (old setup, before typed-v2; not kill sets)

One σ per mutant (`tests/test_vat_ladder.py`, `tests/test_vat_mutants.py`),
replayed with the core against every spec over b and every mutant.
`x` = some check ends in `Panic(0x01)`. b is never violated.

| Spec | b | m01 | m02 | m03 | m04 | m05 | m06 | m07 | m08 |
|---|---|---|---|---|---|---|---|---|---|
| phi_top | . | . | . | . | . | . | . | . | . |
| phi_auth | . | x | . | . | . | . | . | . | . |
| phi_consent | . | . | x | . | . | . | . | . | . |
| phi_frob | . | . | . | . | . | . | . | . | . |
| phi_frob_guards | . | . | . | x | x | x | . | . | . |
| phi_fold | . | . | . | . | . | . | x | . | . |
| phi_move_flux | . | . | . | . | . | . | . | x | . |
| phi_grab_heal_suck | . | . | . | . | . | . | . | . | x |
| phi_books | . | . | . | . | . | . | x | x | . |
| phi_full | . | x | x | x | x | x | x | x | x |

phi_frob kills no mutant of this library on these σ: none of the eight faults
changes the amounts a successful frob moves (m02–m05 only let more frobs
through, and those still move exact amounts). Unless the adversary finds
otherwise, phi_frob is M-vacuous for this M (vacuity check (c)) although it
is the most detailed rung; a mutant such as "frob credits dai[w] by dart
instead of rate·dart" would be needed to give it weight. Recorded, not fixed:
the library is the requested one.

## Kill sets (adversary, typed-v2, seed_A 0, B_A 2000, max_txs 6, 1 witness per mutant)

Adversary id `da221ec5557e073f…` (hashes adversary.py, seqgen.py and the parameters). Mutants: `subjects/vat/mutants/mutants.json`, 8 included, properness pairs replayed. Witnesses: `build/witnesses/vat/<phi>.json`; no candidate failed the replay gate.

### Own W of each spec

| mutant | phi_top | phi_auth | phi_consent | phi_frob | phi_frob_guards | phi_frob_both | phi_fold | phi_move_flux | phi_grab_heal_suck | phi_books | phi_full |
|---|---|---|---|---|---|---|---|---|---|---|---|
| m01_slip_no_auth | none | witness | none | none | none | none | none | none | none | none | witness |
| m02_frob_no_consent_v | none | none | witness | none | none | none | none | none | none | none | witness |
| m03_frob_no_ceiling | none | none | none | none | witness | witness | none | none | none | none | witness |
| m04_frob_no_safety | none | none | none | none | witness | witness | none | none | none | none | witness |
| m05_frob_no_dust | none | none | none | none | none | none | none | none | none | none | none |
| m06_fold_no_debt | none | none | none | none | none | none | witness | none | none | witness | witness |
| m07_move_no_debit | none | none | none | none | none | none | none | witness | none | witness | witness |
| m08_grab_no_vice | none | none | none | none | none | none | none | none | witness | witness | witness |
| **killed / total** | 0/8 | 1/8 | 1/8 | 0/8 | 2/8 | 2/8 | 1/8 | 1/8 | 1/8 | 3/8 | 7/8 |

### Pooled W* (|W*| = 10 distinct pairs)

| mutant | phi_top | phi_auth | phi_consent | phi_frob | phi_frob_guards | phi_frob_both | phi_fold | phi_move_flux | phi_grab_heal_suck | phi_books | phi_full |
|---|---|---|---|---|---|---|---|---|---|---|---|
| m01_slip_no_auth | none | witness | none | none | none | none | none | none | none | none | witness |
| m02_frob_no_consent_v | none | none | witness | none | none | none | none | none | none | none | witness |
| m03_frob_no_ceiling | none | none | none | none | witness | witness | none | none | none | none | witness |
| m04_frob_no_safety | none | none | none | none | witness | witness | none | none | none | none | witness |
| m05_frob_no_dust | none | none | none | none | none | none | none | none | none | none | none |
| m06_fold_no_debt | none | none | none | none | none | none | witness | none | none | witness | witness |
| m07_move_no_debit | none | none | none | none | none | none | none | witness | none | witness | witness |
| m08_grab_no_vice | none | none | none | none | none | none | none | none | witness | witness | witness |
| **killed / total** | 0/8 | 1/8 | 1/8 | 0/8 | 2/8 | 2/8 | 1/8 | 1/8 | 1/8 | 3/8 | 7/8 |

Own W and W* give the same table.

### Relations (asserted)

- Nesting: K(phi_top) ⊆ K(every rung and phi_full), K(every rung) ⊆ K(phi_full), K(phi_frob) ⊆ K(phi_frob_both), K(phi_frob_guards) ⊆ K(phi_frob_both): **42 / 42 hold** (own W and W*).
- Prop. 6.3 on P = W(phi_frob) ∪ W(phi_frob_guards) ∪ W(phi_frob_both) (2 pairs): K_P(phi_frob_both) = ['m03_frob_no_ceiling', 'm04_frob_no_safety'] = K_P(phi_frob) ∪ K_P(phi_frob_guards) = ['m03_frob_no_ceiling', 'm04_frob_no_safety']: **holds** (trivially here: K_P(phi_frob) = ∅).
- No Prop. 6.2 measurement for Vat (it is a capped-token item).

### Readings

- **phi_full kills 7/8.** The survivor is m05_frob_no_dust (below).
- **phi_frob kills nothing** (0/8, every mutant at the full budget): confirmed on the adversary's
  pool, as predicted from the hand witnesses. It is M-vacuous for this M (vacuity check (c)),
  though Accept-wise it is no different from the other per-transition rungs (Unknown on b).
  K(phi_frob_both) = K(phi_frob_guards): adding the accounting rung to the guards adds nothing.
- **phi_books kills 3/8** (m06, m07, m08) with three two-key global inequalities, more than any
  single per-function rung, and none of its checks is provable on b (Unknown). The
  books-balance consequences catch accounting faults in fold, move and grab that are otherwise
  caught only by the exact-amount checks of the matching function.
- Every per-function rung kills exactly the mutant of its own function, nothing else.

### Why phi_full does not kill m05_frob_no_dust

A **search miss, not unkillability**, established by execution:

- The hand σ of `tests/test_vat_ladder.py` (ward `file(GOLD, dust, 1e48)`, then
  `check_frob_not_dusty` probed by alice on her setup urn with (1, 1)) replays as a
  `Panic(0x01)` witness against phi_full over m05 and is not a violation over b, so
  m05 ∈ K_sem(phi_full). The fault needs a dust above the setup urns' debt
  (50 wad × 1 ray = 5e46) followed by a frob on such an urn; the typed-v2
  distribution did not produce that pair within 2000 σ (it did produce the
  ceiling and safety analogues, m03 at σ 531, m04 at σ 130).
- Survivor Check(m05, phi_full): **Unknown** (unproved, 404.587 s wall). Over m05 `check_frob_not_dusty` is unproved (over b it is Accept in 6 s), i.e. CHC finds
  neither a proof nor the counterexample within budget. The other 13 unproved checks are
  the same ones that are Unknown over b.
- So the certified score 7/8 is a lower bound of the semantic score 8/8 for phi_full on
  this M (note, Def. 5.3: K_cert ⊆ K_sem), with the gap caused by the adversary's
  distribution, not by the spec format.

### σ tried per (spec, mutant) until the first kept witness (2000 = budget exhausted) and adversary wall time

| Spec | m01 | m02 | m03 | m04 | m05 | m06 | m07 | m08 | wall s |
|---|---|---|---|---|---|---|---|---|---|
| phi_top | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 50.364 |
| phi_auth | 1 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 396.616 |
| phi_consent | 2000 | 64 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 388.472 |
| phi_frob | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 197.482 |
| phi_frob_guards | 2000 | 2000 | 531 | 130 | 2000 | 2000 | 2000 | 2000 | 146.315 |
| phi_frob_both | 2000 | 2000 | 531 | 130 | 2000 | 2000 | 2000 | 2000 | 292.081 |
| phi_fold | 2000 | 2000 | 2000 | 2000 | 2000 | 8 | 2000 | 2000 | 122.27 |
| phi_move_flux | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 1 | 2000 | 161.533 |
| phi_grab_heal_suck | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 2000 | 64 | 204.441 |
| phi_books | 2000 | 2000 | 2000 | 2000 | 2000 | 89 | 567 | 27 | 92.247 |
| phi_full | 1 | 64 | 531 | 130 | 2000 | 8 | 1 | 27 | 379.105 |

Total adversary time 2431 s (41 min) for 11 specs, single process, ~3.6 ms per check replay
(setup of 21 transactions, up to 6 more, the probe, ~60 getter reads). Cost per surviving (spec, mutant)
≈ 2000 × #checks × 3.6 ms; phi_full's one survivor costs 300 s of its 379 s.

### phi_full witnesses (one per killed mutant)

| Mutant | check | σ index |
|---|---|---|
| m01_slip_no_auth | check_slip_needs_auth | 0 |
| m02_frob_no_consent_v | check_frob_needs_v_consent | 63 |
| m03_frob_no_ceiling | check_frob_within_ceilings | 530 |
| m04_frob_no_safety | check_frob_riskier_is_safe | 129 |
| m06_fold_no_debt | check_fold_dai_debt_exact | 7 |
| m07_move_no_debit | check_move_exact | 0 |
| m08_grab_no_vice | check_two_sin_within_vice | 26 |

## Bundles and verify (`bundles/vat/<phi>/`, `tools/verify.py <bundle>`)

| Spec | Check(b) | verify exit | verdict | failing step | ms_cert (recomputed by the verifier) | kill set = adversary's | verify s |
|---|---|---|---|---|---|---|---|
| phi_top | Accept | 0 | HOLDS | — | 0/8 | yes | 5 |
| phi_auth | Unknown | 2 | NOT_CERTIFIED | 2 | 1/8 | yes | 69 |
| phi_consent | Accept | 0 | HOLDS | — | 1/8 | yes | 17 |
| phi_frob | Unknown | 2 | NOT_CERTIFIED | 2 | 0/8 | yes | 125 |
| phi_frob_guards | Accept | 0 | HOLDS | — | 2/8 | yes | 9 |
| phi_frob_both | Unknown | 2 | NOT_CERTIFIED | 2 | 2/8 | yes | 126 |
| phi_fold | Unknown | 2 | NOT_CERTIFIED | 2 | 1/8 | yes | 125 |
| phi_move_flux | Unknown | 2 | NOT_CERTIFIED | 2 | 1/8 | yes | 66 |
| phi_grab_heal_suck | Unknown | 2 | NOT_CERTIFIED | 2 | 1/8 | yes | 187 |
| phi_books | Unknown | 2 | NOT_CERTIFIED | 2 | 3/8 | yes | 64 |
| phi_full | Unknown | 2 | NOT_CERTIFIED | 2 | 7/8 | yes | 401 |

- **HOLDS** (exit 0) for the three specs Accepted on b (phi_top 0/8, phi_consent 1/8, phi_frob_guards 2/8):
  these are the only *certified* scores of the Vat ladder.
- **NOT_CERTIFIED** (exit 2, step 2 only) for the eight specs that are Unknown on b: the bundle
  records Check = Unknown and the verifier's re-run reproduces every per-check verdict, so it is
  not a certificate (Def. 5.3), while steps 3–6 pass: the mutant ids and properness pairs, every
  witness and the score are recomputed, and the recomputed kill set equals the adversary's. These
  ms_cert values are therefore checked kill sets of specs that are **not** certified.
- Exit codes are the v3 semantics (verifier/README.md; 23d4691). Before that change the same eight
  bundles came out exit 3 REFUSED at step 2 with the same steps 3–5 and the same ms_cert. Reports:
  `bundles/vat/verify/<phi>.json` (re-run after core v2, d381d5a, and the restamp of 0da54cb;
  verify s above are that run's, 1194 s in total). `ladder.py: verify_consistent` now requires
  NOT_CERTIFIED / exit 2 / failing steps [2] for a spec Unknown on b.
- `events.py --ladder --subject vat` re-run on the witnesses read back from the bundles
  (`evidence.W` of each manifest): kill sets on own W and on W*, and the W* hash, equal the
  ones from the adversary's files; all 42 nesting relations and Prop. 6.3 hold (exit 0).

## Distribution gap behind the m05 miss (input for a possible typed-v3; generator unchanged)

The σ shape that kills m05_frob_no_dust under phi_full (or phi_frob_guards):

1. a prefix transaction by the ward (the deployer): `file(I, "dust", D)` with
   `D > rate(I) · art(I, U)`; for the setup urns that is `D > 50 wad · 1 ray = 5e46`;
2. the probe `check_frob_not_dusty(i = I, u = U, dx, dy)` sent by `s` with `s == U` or
   `can[U][s] == 1`, whose frob leaves `art(I, U) ≠ 0` and passes every other guard (the
   simplest is `dx = dy = 0`: a no-op frob that b reverts as dusty and m05 lets through).

Each part is producible by typed-v2 (`file` dust values `rad_le_1000000` reach 1e51), but
the probe's `i`, `u`, `dx`, `dy` are drawn independently of the prefix. Measured on the 2000
σ of phi_full: 362 `file(bytes32,bytes32,uint256)` txs, 98 set dust, 25 above 5e46, 20 of
them by the ward; only 2 of those σ probe the same ilk, and neither probes a frob that keeps
the urn dusty. A typed-v3 that draws the probe's `i` from the ilks the prefix touched (and
`u` from the sender or a hoped address, `dx`/`dy` from `0`/`repeat`) would make this shape
common; the same coupling would help any must-hold-after-a-parameter-change property.

