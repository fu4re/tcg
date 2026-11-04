# fM seed 0 — protocol v1 attempt (aborted)

Protocol v1 attempt, aborted after the first candidate's Check exceeded the
1500 s wall. Kept as a record; not a trajectory and not part of any result.

- Round 1, candidate 1: lint-clean spec, 11 checks, 22 asserts. Whole-harness
  Check (v1: one solc run over the whole spec, 120 000 ms per query, 1500 s
  wall) ended at the wall: `Unknown (wall_timeout)`, 1500.1 s. Its own W
  (adversary c16d1dd5a4a4…, B_A 2000) killed 7 of 8 mutants (not
  `m08_mint_always_reverts`). Request/response, Spec.sol, check.json,
  witnesses.json and score.json are in `round_1/cand_1/`.
- Round 1, candidate 2: the API call returned (response.json, Spec.sol); the
  run was stopped (2026-11-02) before its lint/Check finished, so there is no
  score for it.
- The author's decision after this attempt: protocol v2 (per-check isolated
  Check in parallel; protocol.md, "Protocol v2"), because a wall-timeout
  non-Accept fed back to the generator fakes the signal under study.
- A second v1 attempt is in `../seed_0_attempt2/`.
