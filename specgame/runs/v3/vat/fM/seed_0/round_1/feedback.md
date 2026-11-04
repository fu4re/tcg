# Feedback on round 1

Checker verdict: not accepted

Not every assert was proved:
- line 105 in check_hope_effect: `assert(can[msg.sender][a] == 1);` could not be decided within the checker's budget
- line 107 in check_hope_effect: `assert(can[b][a] == c0);` could not be decided within the checker's budget
- line 110 in check_hope_effect: `assert(can[msg.sender][b] == c1);` could not be decided within the checker's budget
- line 118 in check_nope_effect: `assert(can[msg.sender][a] == 0);` could not be decided within the checker's budget
- line 120 in check_nope_effect: `assert(can[b][a] == c0);` could not be decided within the checker's budget
- line 123 in check_nope_effect: `assert(can[msg.sender][b] == c1);` could not be decided within the checker's budget
- line 203 in check_file_ilk_unknown: `assert(false);` could not be decided within the checker's budget
- line 225 in check_live_flag: `assert(live == 0 || live == 1);` could not be decided within the checker's budget
- line 243 in check_move_effect: `assert(dai[a] + x == da);` could not be decided within the checker's budget
- line 258 in check_move_underflow: `assert(false);` could not be decided within the checker's budget
- line 265 in check_move_overflow: `assert(false);` could not be decided within the checker's budget
- line 274 in check_flux_effect: `assert(gem["GOLD"][a] + x == ga);` could not be decided within the checker's budget
- line 288 in check_flux_underflow: `assert(false);` could not be decided within the checker's budget
- line 295 in check_flux_overflow: `assert(false);` could not be decided within the checker's budget
- line 319 in check_frob_ink_gem: `assert(urns[i][u].ink + uint256(-dx) == ink0);` could not be decided within the checker's budget
- line 333 in check_frob_art: `assert(urns[i][u].art + uint256(-dy) == art0);` could not be decided within the checker's budget
- line 334 in check_frob_art: `assert(ilks[i].Art + uint256(-dy) == Art0);` could not be decided within the checker's budget
- line 349 in check_frob_dai_debt: `assert(dai[u] + r0 * uint256(-dy) == d0);` could not be decided within the checker's budget
- line 350 in check_frob_dai_debt: `assert(debt + r0 * uint256(-dy) == t0);` could not be decided within the checker's budget
- line 346 in check_frob_dai_debt: `assert(dai[u] == d0 + r0 * uint256(dy));` could not be decided within the checker's budget
- line 347 in check_frob_dai_debt: `assert(debt == t0 + r0 * uint256(dy));` could not be decided within the checker's budget
- line 356 in check_frob_guards: `assert(live == 1);` could not be decided within the checker's budget
- line 357 in check_frob_guards: `assert(ilks[i].rate != 0);` could not be decided within the checker's budget
- line 359 in check_frob_guards: `assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);` could not be decided within the checker's budget
- line 360 in check_frob_guards: `assert(debt <= Line);` could not be decided within the checker's budget
- line 363 in check_frob_guards: `assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 364 in check_frob_guards: `assert(u == msg.sender || can[u][msg.sender] == 1);` could not be decided within the checker's budget
- line 366 in check_frob_guards: `assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 386 in check_frob_distinct_pos: `assert(urns["GOLD"][a].ink == ink0 + x);` could not be decided within the checker's budget
- line 387 in check_frob_distinct_pos: `assert(urns["GOLD"][a].art == art0 + y);` could not be decided within the checker's budget
- line 388 in check_frob_distinct_pos: `assert(ilks["GOLD"].Art == Art0 + y);` could not be decided within the checker's budget
- line 389 in check_frob_distinct_pos: `assert(gem["GOLD"][b] + x == g0);` could not be decided within the checker's budget
- line 390 in check_frob_distinct_pos: `assert(dai[msg.sender] == d0 + r0 * y);` could not be decided within the checker's budget
- line 391 in check_frob_distinct_pos: `assert(debt == t0 + r0 * y);` could not be decided within the checker's budget
- line 393 in check_frob_distinct_pos: `assert(a == msg.sender || can[a][msg.sender] == 1);` could not be decided within the checker's budget
- line 396 in check_frob_distinct_pos: `assert(b == msg.sender || can[b][msg.sender] == 1);` could not be decided within the checker's budget
- line 411 in check_frob_distinct_neg: `assert(urns["GOLD"][a].ink + x == ink0);` could not be decided within the checker's budget
- line 412 in check_frob_distinct_neg: `assert(urns["GOLD"][a].art + y == art0);` could not be decided within the checker's budget
- line 413 in check_frob_distinct_neg: `assert(ilks["GOLD"].Art + y == Art0);` could not be decided within the checker's budget
- line 415 in check_frob_distinct_neg: `assert(dai[msg.sender] + r0 * y == d0);` could not be decided within the checker's budget
- line 416 in check_frob_distinct_neg: `assert(debt + r0 * y == t0);` could not be decided within the checker's budget
- line 433 in check_fork_effect: `assert(urns["GOLD"][a].ink + x == inka);` could not be decided within the checker's budget
- line 434 in check_fork_effect: `assert(urns["GOLD"][b].ink == inkb + x);` could not be decided within the checker's budget
- line 435 in check_fork_effect: `assert(urns["GOLD"][a].art + y == arta);` could not be decided within the checker's budget
- line 436 in check_fork_effect: `assert(urns["GOLD"][b].art == artb + y);` could not be decided within the checker's budget
- line 446 in check_fork_safe: `assert(urns["GOLD"][a].art * ilks["GOLD"].rate <= urns["GOLD"][a].ink * ilks["GOLD"].spot);` could not be decided within the checker's budget
- line 447 in check_fork_safe: `assert(urns["GOLD"][b].art * ilks["GOLD"].rate <= urns["GOLD"][b].ink * ilks["GOLD"].spot);` could not be decided within the checker's budget
- line 448 in check_fork_safe: `assert(urns["GOLD"][a].art == 0 || urns["GOLD"][a].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);` could not be decided within the checker's budget
- line 449 in check_fork_safe: `assert(urns["GOLD"][b].art == 0 || urns["GOLD"][b].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);` could not be decided within the checker's budget
- line 456 in check_fork_self: `assert(urns[i][u].ink == ink0);` could not be decided within the checker's budget
- line 457 in check_fork_self: `assert(urns[i][u].art == art0);` could not be decided within the checker's budget
- line 473 in check_grab_neg: `assert(urns["GOLD"][a].ink + x == ink0);` could not be decided within the checker's budget
- line 474 in check_grab_neg: `assert(urns["GOLD"][a].art + y == art0);` could not be decided within the checker's budget
- line 475 in check_grab_neg: `assert(ilks["GOLD"].Art + y == Art0);` could not be decided within the checker's budget
- line 477 in check_grab_neg: `assert(sin[msg.sender] == s0 + r0 * y);` could not be decided within the checker's budget
- line 478 in check_grab_neg: `assert(vice == v0 + r0 * y);` could not be decided within the checker's budget
- line 494 in check_grab_pos: `assert(urns["GOLD"][a].ink == ink0 + x);` could not be decided within the checker's budget
- line 495 in check_grab_pos: `assert(urns["GOLD"][a].art == art0 + y);` could not be decided within the checker's budget
- line 496 in check_grab_pos: `assert(ilks["GOLD"].Art == Art0 + y);` could not be decided within the checker's budget
- line 498 in check_grab_pos: `assert(sin[msg.sender] + r0 * y == s0);` could not be decided within the checker's budget
- line 499 in check_grab_pos: `assert(vice + r0 * y == v0);` could not be decided within the checker's budget
- line 519 in check_heal_underflow: `assert(false);` could not be decided within the checker's budget
- line 525 in check_heal_underflow_sin: `assert(false);` could not be decided within the checker's budget
- line 543 in check_suck_overflow: `assert(false);` could not be decided within the checker's budget
- line 554 in check_fold_effect: `assert(ilks[i].Art == Art0);` could not be decided within the checker's budget
- line 560 in check_fold_effect: `assert(ilks[i].rate + uint256(-dx) == r0);` could not be decided within the checker's budget
- line 561 in check_fold_effect: `assert(dai[u] + Art0 * uint256(-dx) == d0);` could not be decided within the checker's budget
- line 562 in check_fold_effect: `assert(debt + Art0 * uint256(-dx) == t0);` could not be decided within the checker's budget
- line 556 in check_fold_effect: `assert(ilks[i].rate == r0 + uint256(dx));` could not be decided within the checker's budget
- line 557 in check_fold_effect: `assert(dai[u] == d0 + Art0 * uint256(dx));` could not be decided within the checker's budget
- line 558 in check_fold_effect: `assert(debt == t0 + Art0 * uint256(dx));` could not be decided within the checker's budget

Mutation score: 7 of 8 faulty variants of the token were shown to
violate your specification (ms_cert = 7/8).

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 2.
