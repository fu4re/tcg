# Side probe: m08_grab_no_vice with a sin-creating setup (f0 seed 0, round 3)

Not part of any pool, bundle or score; `events.json` is unchanged. A hand σ,
judged by the executor only (`evaluate_witness`, core v2), no solver.

**Question.** The round 2 -> 3 event of this trajectory is a weakening that
loses m08 on W*: round 2's `check_grab_sin` (dy <= 0, the liquidation regime
in which sin and vice grow) became round 3's `check_grab_sin_up` (dy >= 0,
same asserts). From the profile's setup state, dy > 0 makes `grab` underflow
`sin[u]`, so in W* the only reachable case is dy = 0, where m08 (grab no
longer updates `vice`) is indistinguishable from b. Is m08 still killable by
the round-3 spec when sin[u] > 0 first?

**σ** (`probe.py`, sha256 in `result.json`): deployer alice (the ward), the
profile's setup, then `alice: suck(bob, bob, 1 ray)` (sin[bob] = vice +=
1 ray), then the probe `check_grab_sin_up(GOLD, bob, dx = 0, dy = 1)` from
alice, i.e. `grab(GOLD, bob, bob, bob, 0, 1)`.

**Result** (`result.json`), spec `round_3/cand_1/Spec.sol` (53 checks):

| artifact | suck | check_grab_sin_up | checks violated | outcomes |
|---|---|---|---|---|
| b (Vat.sol) | success | success | none | 38 pre_unmet, 15 success |
| m08_grab_no_vice | success | **violation** (Panic 0x01) | check_grab_sin_up | 38 pre_unmet, 14 success, 1 violation |

On b, grab lowers sin[bob] and vice by 1 ray and both asserts hold; on m08
vice stays put and `assert(int256(vice) == int256(v0) - dy * 10**27)` fails.
So this σ is a witness that kills m08 for the round-3 spec.

**Reading.** The round 2 -> 3 event is a weakening of K_cert on W* (the
kill set on the trajectory's witness pool lost m08), while K_sem did not
shrink on this mutant: the round-3 spec still distinguishes m08 from b. The
adversary's typed-v2 generator does not produce the two-step setup (first
make sin[u] > 0, by suck or by a grab with dy < 0, then grab with dy > 0), so
W* contains no such σ. (One hand σ, one mutant; it does not say K_sem of
rounds 2 and 3 are equal elsewhere.)
