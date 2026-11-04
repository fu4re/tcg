# Feedback on round 1

Checker verdict: not accepted

Not every assert was proved:
- line 178 in check_file_ilk_unknown: `assert(false);` could not be decided within the checker's budget
- line 244 in check_slip_overflow: `assert(false);` could not be decided within the checker's budget
- line 260 in check_flux_effect: `assert(gem["GOLD"][a] + x == ga);` could not be decided within the checker's budget
- line 285 in check_flux_ilk: `assert(gem[i][u] + uint256(dx) == gu);` could not be decided within the checker's budget
- line 294 in check_flux_underflow: `assert(false);` could not be decided within the checker's budget
- line 304 in check_move_effect: `assert(dai[a] + x == da);` could not be decided within the checker's budget
- line 327 in check_move_underflow: `assert(false);` could not be decided within the checker's budget
- line 335 in check_move_overflow: `assert(false);` could not be decided within the checker's budget
- line 349 in check_frob_collateral: `assert(urns[i][u].ink + uint256(-dx) == ink0);` could not be decided within the checker's budget
- line 363 in check_frob_debt_units: `assert(urns[i][u].art + uint256(-dy) == art0);` could not be decided within the checker's budget
- line 364 in check_frob_debt_units: `assert(ilks[i].Art + uint256(-dy) == A0);` could not be decided within the checker's budget
- line 378 in check_frob_dai: `assert(dai[u] + r0 * uint256(-dy) == d0);` could not be decided within the checker's budget
- line 379 in check_frob_dai: `assert(debt + r0 * uint256(-dy) == debt0);` could not be decided within the checker's budget
- line 375 in check_frob_dai: `assert(dai[u] == d0 + r0 * uint256(dy));` could not be decided within the checker's budget
- line 376 in check_frob_dai: `assert(debt == debt0 + r0 * uint256(dy));` could not be decided within the checker's budget
- line 417 in check_frob_roles_up: `assert(dai[msg.sender] == d0 + r0 * y);` could not be decided within the checker's budget
- line 432 in check_frob_roles_down: `assert(urns["GOLD"][a].ink + x == ink0);` could not be decided within the checker's budget
- line 433 in check_frob_roles_down: `assert(urns["GOLD"][a].art + y == art0);` could not be decided within the checker's budget
- line 435 in check_frob_roles_down: `assert(dai[msg.sender] + r0 * y == d0);` could not be decided within the checker's budget
- line 462 in check_frob_global_ceiling: `assert(false);` could not be decided within the checker's budget
- line 516 in check_fork_effect: `assert(urns[i][u].ink + uint256(dx) == inku);` could not be decided within the checker's budget
- line 517 in check_fork_effect: `assert(urns[i][u].art + uint256(dy) == artu);` could not be decided within the checker's budget
- line 518 in check_fork_effect: `assert(urns[i][msg.sender].ink == inkv + uint256(dx));` could not be decided within the checker's budget
- line 519 in check_fork_effect: `assert(urns[i][msg.sender].art == artv + uint256(dy));` could not be decided within the checker's budget
- line 535 in check_fork_effect_neg: `assert(urns[i][u].ink == inku + uint256(-dx));` could not be decided within the checker's budget
- line 536 in check_fork_effect_neg: `assert(urns[i][u].art == artu + uint256(-dy));` could not be decided within the checker's budget
- line 537 in check_fork_effect_neg: `assert(urns[i][msg.sender].ink + uint256(-dx) == inkv);` could not be decided within the checker's budget
- line 538 in check_fork_effect_neg: `assert(urns[i][msg.sender].art + uint256(-dy) == artv);` could not be decided within the checker's budget
- line 544 in check_fork_safe_after: `assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 545 in check_fork_safe_after: `assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 551 in check_fork_dust_after: `assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 552 in check_fork_dust_after: `assert(urns[i][msg.sender].art == 0 || urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 581 in check_grab_units: `assert(urns[i][u].ink + uint256(-dx) == ink0);` could not be decided within the checker's budget
- line 582 in check_grab_units: `assert(urns[i][u].art + uint256(-dy) == art0);` could not be decided within the checker's budget
- line 583 in check_grab_units: `assert(ilks[i].Art + uint256(-dy) == A0);` could not be decided within the checker's budget
- line 596 in check_grab_sin: `assert(sin[u] == s0 + r0 * uint256(-dy));` could not be decided within the checker's budget
- line 597 in check_grab_sin: `assert(vice == vice0 + r0 * uint256(-dy));` could not be decided within the checker's budget
- line 608 in check_grab_sin_positive: `assert(sin[u] + r0 * uint256(dy) == s0);` could not be decided within the checker's budget
- line 609 in check_grab_sin_positive: `assert(vice + r0 * uint256(dy) == vice0);` could not be decided within the checker's budget
- line 625 in check_grab_roles: `assert(sin[a] == sa + r0 * y);` could not be decided within the checker's budget
- line 627 in check_grab_roles: `assert(urns["GOLD"][a].ink + x == inka);` could not be decided within the checker's budget
- line 662 in check_heal_needs_dai: `assert(false);` could not be decided within the checker's budget
- line 668 in check_heal_needs_sin: `assert(false);` could not be decided within the checker's budget
- line 701 in check_suck_overflow: `assert(false);` could not be decided within the checker's budget
- line 711 in check_fold_rate: `assert(ilks[i].Art == A0);` could not be decided within the checker's budget
- line 715 in check_fold_rate: `assert(ilks[i].rate + uint256(-dy) == r0);` could not be decided within the checker's budget
- line 713 in check_fold_rate: `assert(ilks[i].rate == r0 + uint256(dy));` could not be decided within the checker's budget
- line 729 in check_fold_dai: `assert(dai[u] + A0 * uint256(-dy) == d0);` could not be decided within the checker's budget
- line 730 in check_fold_dai: `assert(debt + A0 * uint256(-dy) == debt0);` could not be decided within the checker's budget
- line 726 in check_fold_dai: `assert(dai[u] == d0 + A0 * uint256(dy));` could not be decided within the checker's budget
- line 727 in check_fold_dai: `assert(debt == debt0 + A0 * uint256(dy));` could not be decided within the checker's budget
- line 741 in check_fold_frame: `assert(ilks[i].spot == s0);` could not be decided within the checker's budget

Mutation score: 7 of 8 faulty variants of the token were shown to
violate your specification (ms_cert = 7/8).

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 2.
