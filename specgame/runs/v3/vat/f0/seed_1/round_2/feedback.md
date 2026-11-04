# Feedback on round 2

Checker verdict: not accepted

Not every assert was proved:
- line 369 in check_frob_wipe_urn: `assert(urns["GOLD"][msg.sender].ink + x == ink0);` could not be decided within the checker's budget
- line 370 in check_frob_wipe_urn: `assert(urns["GOLD"][msg.sender].art + y == art0);` could not be decided within the checker's budget
- line 371 in check_frob_wipe_urn: `assert(ilks["GOLD"].Art + y == tot0);` could not be decided within the checker's budget
- line 410 in check_fork_conserves: `assert(urns["GOLD"][a].ink + x == ia);` could not be decided within the checker's budget
- line 411 in check_fork_conserves: `assert(urns["GOLD"][b].ink == ib + x);` could not be decided within the checker's budget
- line 412 in check_fork_conserves: `assert(urns["GOLD"][a].art + y == aa);` could not be decided within the checker's budget
- line 413 in check_fork_conserves: `assert(urns["GOLD"][b].art == ab + y);` could not be decided within the checker's budget
- line 430 in check_fork_safe: `assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 431 in check_fork_safe: `assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);` could not be decided within the checker's budget
- line 440 in check_fork_dust: `assert(urns[i][msg.sender].art == 0 || urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 441 in check_fork_dust: `assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);` could not be decided within the checker's budget
- line 456 in check_grab_up_urn: `assert(urns["GOLD"][a].ink == ink0 + x);` could not be decided within the checker's budget
- line 457 in check_grab_up_urn: `assert(urns["GOLD"][a].art == art0 + y);` could not be decided within the checker's budget
- line 458 in check_grab_up_urn: `assert(ilks["GOLD"].Art == tot0 + y);` could not be decided within the checker's budget
- line 471 in check_grab_up_debt: `assert(sin[msg.sender] + ilks["GOLD"].rate * y == s0);` could not be decided within the checker's budget
- line 472 in check_grab_up_debt: `assert(vice + ilks["GOLD"].rate * y == v0);` could not be decided within the checker's budget
- line 485 in check_grab_down_urn: `assert(urns["GOLD"][a].ink + x == ink0);` could not be decided within the checker's budget
- line 486 in check_grab_down_urn: `assert(urns["GOLD"][a].art + y == art0);` could not be decided within the checker's budget
- line 487 in check_grab_down_urn: `assert(ilks["GOLD"].Art + y == tot0);` could not be decided within the checker's budget
- line 499 in check_grab_down_debt: `assert(sin[msg.sender] == s0 + ilks["GOLD"].rate * y);` could not be decided within the checker's budget
- line 500 in check_grab_down_debt: `assert(vice == v0 + ilks["GOLD"].rate * y);` could not be decided within the checker's budget
- line 540 in check_fold_up: `assert(ilks[i].rate == r0 + uint256(dx));` could not be decided within the checker's budget
- line 541 in check_fold_up: `assert(dai[u] == d0 + ilks[i].Art * uint256(dx));` could not be decided within the checker's budget
- line 542 in check_fold_up: `assert(debt == t0 + ilks[i].Art * uint256(dx));` could not be decided within the checker's budget
- line 555 in check_fold_down: `assert(ilks[i].rate + m == r0);` could not be decided within the checker's budget
- line 556 in check_fold_down: `assert(dai[u] + ilks[i].Art * m == d0);` could not be decided within the checker's budget
- line 557 in check_fold_down: `assert(debt + ilks[i].Art * m == t0);` could not be decided within the checker's budget

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 1.
