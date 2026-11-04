# Feedback on round 2

Checker verdict: not accepted

Not every assert was proved:
- line 217 in check_move_effect: `assert(dai[a] + x == da);` could not be decided within the checker's budget
- line 234 in check_flux_effect: `assert(gem["GOLD"][a] + x == ga);` could not be decided within the checker's budget
- line 290 in check_frob_dai_down: `assert(dai[u] + r0 == d0);` could not be decided within the checker's budget
- line 291 in check_frob_dai_down: `assert(debt + r0 == t0);` could not be decided within the checker's budget
- line 374 in check_fork_ink: `assert(urns[i][u].ink + uint256(dx) == inku);` could not be decided within the checker's budget
- line 375 in check_fork_ink: `assert(urns[i][msg.sender].ink == inkm + uint256(dx));` could not be decided within the checker's budget
- line 385 in check_fork_art: `assert(urns[i][u].art + uint256(dy) == artu);` could not be decided within the checker's budget
- line 386 in check_fork_art: `assert(urns[i][msg.sender].art == artm + uint256(dy));` could not be decided within the checker's budget
- line 402 in check_fork_safe_src: `assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 407 in check_fork_dust_src: `assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 416 in check_grab_ink_gem: `assert(urns[i][u].ink == ink0 + uint256(dx));` could not be decided within the checker's budget
- line 425 in check_grab_art: `assert(urns[i][u].art == art0 + uint256(dy));` could not be decided within the checker's budget
- line 426 in check_grab_art: `assert(ilks[i].Art == Art0 + uint256(dy));` could not be decided within the checker's budget
- line 436 in check_grab_sin_up: `assert(sin[u] == s0 + r0);` could not be decided within the checker's budget
- line 437 in check_grab_sin_up: `assert(vice == v0 + r0);` could not be decided within the checker's budget
- line 447 in check_grab_sin_down: `assert(sin[u] + r0 == s0);` could not be decided within the checker's budget
- line 448 in check_grab_sin_down: `assert(vice + r0 == v0);` could not be decided within the checker's budget
- line 494 in check_fold_up: `assert(ilks[i].Art == Art0);` could not be decided within the checker's budget
- line 495 in check_fold_up: `assert(ilks[i].rate == r0 + 1);` could not be decided within the checker's budget
- line 507 in check_fold_down: `assert(ilks[i].rate + 1 == r0);` could not be decided within the checker's budget
- line 508 in check_fold_down: `assert(dai[u] + Art0 == d0);` could not be decided within the checker's budget
- line 509 in check_fold_down: `assert(debt + Art0 == t0);` could not be decided within the checker's budget

Mutation score: 7 of 8 faulty variants of the token were shown to
violate your specification (ms_cert = 7/8).

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 1.
