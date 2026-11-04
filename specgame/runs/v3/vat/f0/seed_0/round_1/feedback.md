# Feedback on round 1

Checker verdict: not accepted

Not every assert was proved:
- line 194 in check_file_ilk_unrecognized: `assert(false);` could not be decided within the checker's budget
- line 235 in check_flux_effect: `assert(gem["GOLD"][a] + x == ga);` could not be decided within the checker's budget
- line 257 in check_move_effect: `assert(dai[a] + x == da);` could not be decided within the checker's budget
- line 284 in check_frob_vault: `assert(int256(urns[i][u].ink) == int256(ink0) + dx);` could not be decided within the checker's budget
- line 285 in check_frob_vault: `assert(int256(urns[i][u].art) == int256(art0) + dy);` could not be decided within the checker's budget
- line 286 in check_frob_vault: `assert(int256(ilks[i].Art) == int256(tot0) + dy);` could not be decided within the checker's budget
- line 302 in check_frob_dai: `assert(int256(dai[u]) == int256(d0) + dy * int256(r0));` could not be decided within the checker's budget
- line 303 in check_frob_dai: `assert(int256(debt) == int256(t0) + dy * int256(r0));` could not be decided within the checker's budget
- line 343 in check_frob_unsafe: `assert(false);` could not be decided within the checker's budget
- line 362 in check_frob_dust: `assert(false);` could not be decided within the checker's budget
- line 381 in check_fork_effect: `assert(urns["GOLD"][a].ink + x == ia);` could not be decided within the checker's budget
- line 382 in check_fork_effect: `assert(urns["GOLD"][b].ink == ib + x);` could not be decided within the checker's budget
- line 383 in check_fork_effect: `assert(urns["GOLD"][a].art + y == ra);` could not be decided within the checker's budget
- line 384 in check_fork_effect: `assert(urns["GOLD"][b].art == rb + y);` could not be decided within the checker's budget
- line 412 in check_fork_src_unsafe: `assert(false);` could not be decided within the checker's budget
- line 424 in check_fork_dst_unsafe: `assert(false);` could not be decided within the checker's budget
- line 436 in check_fork_src_dust: `assert(false);` could not be decided within the checker's budget
- line 448 in check_fork_dst_dust: `assert(false);` could not be decided within the checker's budget
- line 466 in check_grab_vault: `assert(int256(urns[i][u].ink) == int256(ink0) + dx);` could not be decided within the checker's budget
- line 467 in check_grab_vault: `assert(int256(urns[i][u].art) == int256(art0) + dy);` could not be decided within the checker's budget
- line 468 in check_grab_vault: `assert(int256(ilks[i].Art) == int256(tot0) + dy);` could not be decided within the checker's budget
- line 485 in check_grab_sin: `assert(int256(sin[u]) == int256(s0) - dy * int256(r0));` could not be decided within the checker's budget
- line 486 in check_grab_sin: `assert(int256(vice) == int256(v0) - dy * int256(r0));` could not be decided within the checker's budget
- line 489 in check_grab_sin: `assert(ilks[i].rate == r0);` could not be decided within the checker's budget
- line 553 in check_fold_effect: `assert(int256(ilks[i].rate) == int256(r0) + dx);` could not be decided within the checker's budget
- line 554 in check_fold_effect: `assert(int256(dai[u]) == int256(d0) + int256(art0) * dx);` could not be decided within the checker's budget
- line 555 in check_fold_effect: `assert(int256(debt) == int256(t0) + int256(art0) * dx);` could not be decided within the checker's budget
- line 556 in check_fold_effect: `assert(ilks[i].Art == art0);` could not be decided within the checker's budget

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 2.
