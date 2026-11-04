# Aborted: Vat fM seed 0, attempt 3 (protocol v3, core v2, max_tokens 64 000)

The loop itself stopped with an uncaught CompileError (`trajectory.json`
`error`) during round 1, cand 1, after 2011 s wall. No feedback was sent; cand 2
was never requested.

Round 1 cand 1 (`end_turn`, 31 345 output tokens of which 18 848 thinking;
input 8 745): an 82-check spec that passed lint. Check(b, φ) ran: Unknown
(`budget`), 53 Accept, 25 unproved, 4 wall_timeout, 1806 s wall. The adversary
then compiled the whole Spec over each mutant to bytecode and solc stopped with
"Stack too deep" at `grab(i, u, u, msg.sender, dx, dy)` in
`check_grab_effects` (Spec.sol line 662). SMTChecker's own compile skips code
generation, so the error passed lint and Check (that check came out
`wall_timeout` in isolation) and surfaced only in the adversary, where the loop
did not catch it.

Fix (loop.py, protocol.md 16.2): the whole Spec over b is compiled to bytecode
before Check; failure = `acc Unknown`, `compile_error`, the compiler message as
the error and in the feedback, no Check, no adversary, as 16.2 already
prescribed. Test: `tests/test_generator.py` CodegenError.

Nothing here is a result about the specs; it is a loop defect.
