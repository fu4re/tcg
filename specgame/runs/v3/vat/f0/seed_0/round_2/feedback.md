# Feedback on round 2

Checker verdict: not accepted

Not every assert was proved:
- line 194 in check_file_ilk_unrecognized: `assert(false);` could not be decided within the checker's budget
- line 234 in check_flux_effect: `assert(int256(gem["GOLD"][a]) == int256(ga) - int256(x));` could not be decided within the checker's budget
- line 255 in check_move_effect: `assert(int256(dai[a]) == int256(da) - int256(x));` could not be decided within the checker's budget
- line 306 in check_frob_vault_down: `assert(int256(urns[i][u].ink) == int256(ink0) + dx);` could not be decided within the checker's budget
- line 307 in check_frob_vault_down: `assert(int256(urns[i][u].art) == int256(art0) + dy);` could not be decided within the checker's budget
- line 308 in check_frob_vault_down: `assert(int256(ilks[i].Art) == int256(tot0) + dy);` could not be decided within the checker's budget
- line 341 in check_frob_dai_down: `assert(int256(dai[u]) == int256(d0) + dy * 10**27);` could not be decided within the checker's budget
- line 342 in check_frob_dai_down: `assert(int256(debt) == int256(t0) + dy * 10**27);` could not be decided within the checker's budget
- line 380 in check_frob_unsafe: `assert(false);` could not be decided within the checker's budget
- line 399 in check_frob_dust: `assert(false);` could not be decided within the checker's budget
- line 418 in check_fork_effect: `assert(int256(urns["GOLD"][a].ink) == int256(ia) - int256(x));` could not be decided within the checker's budget
- line 419 in check_fork_effect: `assert(int256(urns["GOLD"][b].ink) == int256(ib) + int256(x));` could not be decided within the checker's budget
- line 420 in check_fork_effect: `assert(int256(urns["GOLD"][a].art) == int256(ra) - int256(y));` could not be decided within the checker's budget
- line 421 in check_fork_effect: `assert(int256(urns["GOLD"][b].art) == int256(rb) + int256(y));` could not be decided within the checker's budget
- line 447 in check_fork_src_unsafe: `assert(false);` could not be decided within the checker's budget
- line 459 in check_fork_dst_unsafe: `assert(false);` could not be decided within the checker's budget
- line 471 in check_fork_src_dust: `assert(false);` could not be decided within the checker's budget
- line 483 in check_fork_dst_dust: `assert(false);` could not be decided within the checker's budget
- line 501 in check_grab_vault: `assert(int256(urns[i][u].ink) == int256(ink0) + dx);` could not be decided within the checker's budget
- line 502 in check_grab_vault: `assert(int256(urns[i][u].art) == int256(art0) + dy);` could not be decided within the checker's budget
- line 503 in check_grab_vault: `assert(int256(ilks[i].Art) == int256(tot0) + dy);` could not be decided within the checker's budget
- line 518 in check_grab_sin: `assert(int256(sin[u]) == int256(s0) - dy * 10**27);` could not be decided within the checker's budget
- line 519 in check_grab_sin: `assert(int256(vice) == int256(v0) - dy * 10**27);` could not be decided within the checker's budget
- line 579 in check_fold_rate: `assert(int256(ilks[i].rate) == int256(r0) + dx);` could not be decided within the checker's budget
- line 580 in check_fold_rate: `assert(ilks[i].Art == art0);` could not be decided within the checker's budget
- line 591 in check_fold_credit: `assert(int256(dai[u]) == int256(d0) + dx);` could not be decided within the checker's budget
- line 592 in check_fold_credit: `assert(int256(debt) == int256(t0) + dx);` could not be decided within the checker's budget

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 1.
