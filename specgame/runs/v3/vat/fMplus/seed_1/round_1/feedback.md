# Feedback on round 1

Checker verdict: not accepted

Not every assert was proved:
- line 246 in check_file_ilk_unknown: `assert(false);` could not be decided within the checker's budget
- line 310 in check_flux_effect: `assert(gem[k][a] + x == ga);` could not be decided within the checker's budget
- line 343 in check_flux_insufficient: `assert(false);` could not be decided within the checker's budget
- line 353 in check_move_effect: `assert(dai[a] + x == da);` could not be decided within the checker's budget
- line 376 in check_move_insufficient: `assert(false);` could not be decided within the checker's budget
- line 383 in check_move_overflow: `assert(false);` could not be decided within the checker's budget
- line 399 in check_frob_collateral: `assert(urns[i][u].ink + uint256(-dx) == ink0);` could not be decided within the checker's budget
- line 423 in check_frob_debt: `assert(urns[i][u].art + uint256(-dy) == art0);` could not be decided within the checker's budget
- line 424 in check_frob_debt: `assert(ilks[i].Art + uint256(-dy) == tot0);` could not be decided within the checker's budget
- line 425 in check_frob_debt: `assert(dai[msg.sender] + r0 * uint256(-dy) == d0);` could not be decided within the checker's budget
- line 426 in check_frob_debt: `assert(debt + r0 * uint256(-dy) == debt0);` could not be decided within the checker's budget
- line 510 in check_fork_effect: `assert(urns[i][u].ink + uint256(dx) == inku);` could not be decided within the checker's budget
- line 511 in check_fork_effect: `assert(urns[i][u].art + uint256(dy) == artu);` could not be decided within the checker's budget
- line 512 in check_fork_effect: `assert(urns[i][msg.sender].ink == inkv + uint256(dx));` could not be decided within the checker's budget
- line 513 in check_fork_effect: `assert(urns[i][msg.sender].art == artv + uint256(dy));` could not be decided within the checker's budget
- line 516 in check_fork_effect: `assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 517 in check_fork_effect: `assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 518 in check_fork_effect: `assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 519 in check_fork_effect: `assert(urns[i][msg.sender].art == 0 || urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- check_grab_effect (line 538): the checker ran out of time on this check
- line 599 in check_heal_no_dai: `assert(false);` could not be decided within the checker's budget
- line 605 in check_heal_no_sin: `assert(false);` could not be decided within the checker's budget
- line 632 in check_suck_debt_overflow: `assert(false);` could not be decided within the checker's budget
- line 638 in check_suck_vice_overflow: `assert(false);` could not be decided within the checker's budget
- line 652 in check_fold_effect: `assert(ilks[i].Art == tot0);` could not be decided within the checker's budget
- line 659 in check_fold_effect: `assert(ilks[i].rate + uint256(-dx) == r0);` could not be decided within the checker's budget
- line 660 in check_fold_effect: `assert(dai[u] + tot0 * uint256(-dx) == d0);` could not be decided within the checker's budget
- line 661 in check_fold_effect: `assert(debt + tot0 * uint256(-dx) == t0);` could not be decided within the checker's budget
- line 655 in check_fold_effect: `assert(ilks[i].rate == r0 + uint256(dx));` could not be decided within the checker's budget

Mutation score: 6 of 8 faulty variants of the token were shown to
violate your specification (ms_cert = 6/8).

Faulty variants not yet shown to violate it (id, fault class):
- 652a40501289 (consent)
- 0b16a3ae4f99 (missing-bound-check)

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 2.
