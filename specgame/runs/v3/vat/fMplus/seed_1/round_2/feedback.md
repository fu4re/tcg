# Feedback on round 2

Checker verdict: not accepted

Not every assert was proved:
- line 245 in check_file_ilk_unknown: `assert(false);` could not be decided within the checker's budget
- line 313 in check_flux_effect: `assert(ga - gem[k][a] == x);` could not be decided within the checker's budget
- line 314 in check_flux_effect: `assert(gem[k][b] - gb == x);` could not be decided within the checker's budget
- line 352 in check_move_effect: `assert(da - dai[a] == x);` could not be decided within the checker's budget
- line 353 in check_move_effect: `assert(dai[b] - db == x);` could not be decided within the checker's budget
- line 396 in check_frob_collateral_neg: `assert(ink0 - urns[i][u].ink == uint256(-dx));` could not be decided within the checker's budget
- line 437 in check_frob_debt_neg: `assert(art0 - urns[i][u].art == uint256(-dy));` could not be decided within the checker's budget
- line 438 in check_frob_debt_neg: `assert(tot0 - ilks[i].Art == uint256(-dy));` could not be decided within the checker's budget
- line 439 in check_frob_debt_neg: `assert(d0 - dai[msg.sender] == r0 * uint256(-dy));` could not be decided within the checker's budget
- line 440 in check_frob_debt_neg: `assert(debt0 - debt == r0 * uint256(-dy));` could not be decided within the checker's budget
- line 528 in check_fork_effect: `assert(urns[i][u].ink <= inku);` could not be decided within the checker's budget
- line 529 in check_fork_effect: `assert(urns[i][u].art <= artu);` could not be decided within the checker's budget
- line 530 in check_fork_effect: `assert(urns[i][msg.sender].ink >= inkv);` could not be decided within the checker's budget
- line 531 in check_fork_effect: `assert(urns[i][msg.sender].art >= artv);` could not be decided within the checker's budget
- line 532 in check_fork_effect: `assert(inku - urns[i][u].ink == uint256(dx));` could not be decided within the checker's budget
- line 533 in check_fork_effect: `assert(artu - urns[i][u].art == uint256(dy));` could not be decided within the checker's budget
- line 534 in check_fork_effect: `assert(urns[i][msg.sender].ink - inkv == uint256(dx));` could not be decided within the checker's budget
- line 535 in check_fork_effect: `assert(urns[i][msg.sender].art - artv == uint256(dy));` could not be decided within the checker's budget
- line 562 in check_fork_unsafe_dst: `assert(false);` could not be decided within the checker's budget
- line 574 in check_fork_unsafe_src: `assert(false);` could not be decided within the checker's budget
- line 585 in check_grab_collateral: `assert(urns[i][u].ink >= ink0);` could not be decided within the checker's budget
- line 587 in check_grab_collateral: `assert(urns[i][u].ink - ink0 == uint256(dx));` could not be decided within the checker's budget
- line 602 in check_grab_debt: `assert(urns[i][u].art >= art0);` could not be decided within the checker's budget
- line 603 in check_grab_debt: `assert(ilks[i].Art >= tot0);` could not be decided within the checker's budget
- line 606 in check_grab_debt: `assert(urns[i][u].art - art0 == uint256(dy));` could not be decided within the checker's budget
- line 607 in check_grab_debt: `assert(ilks[i].Art - tot0 == uint256(dy));` could not be decided within the checker's budget
- line 608 in check_grab_debt: `assert(s0 - sin[msg.sender] == r0 * uint256(dy));` could not be decided within the checker's budget
- line 609 in check_grab_debt: `assert(v0 - vice == r0 * uint256(dy));` could not be decided within the checker's budget
- line 676 in check_fold_pos: `assert(ilks[i].rate >= r0);` could not be decided within the checker's budget
- line 679 in check_fold_pos: `assert(ilks[i].rate - r0 == uint256(dx));` could not be decided within the checker's budget
- line 680 in check_fold_pos: `assert(dai[u] - d0 == tot0 * uint256(dx));` could not be decided within the checker's budget
- line 681 in check_fold_pos: `assert(debt - t0 == tot0 * uint256(dx));` could not be decided within the checker's budget
- line 683 in check_fold_pos: `assert(ilks[i].Art == tot0);` could not be decided within the checker's budget
- line 693 in check_fold_neg: `assert(ilks[i].rate <= r0);` could not be decided within the checker's budget
- line 696 in check_fold_neg: `assert(r0 - ilks[i].rate == uint256(-dx));` could not be decided within the checker's budget

Mutation score: 6 of 8 faulty variants of the token were shown to
violate your specification (ms_cert = 6/8).

Faulty variants not yet shown to violate it (id, fault class):
- 652a40501289 (consent)
- 0b16a3ae4f99 (missing-bound-check)

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 1.
