# Feedback on round 2

Checker verdict: not accepted

The file does not compile:
- Compiler error (/solidity/libsolidity/codegen/LValue.cpp:50): Stack too deep. Try compiling with `--via-ir` (cli) or the equivalent `viaIR: true` (standard JSON) while enabling the optimizer. Otherwise, try removing local variables.

Mutation score: 0 of 8 faulty variants of the token were shown to
violate your specification (ms_cert = 0/8).

Faulty variants not yet shown to violate it (id, fault class):
- 4f38b3220282 (access-control)
- 652a40501289 (consent)
- 0d256aef3845 (missing-bound-check)
- 7a3cae9442cf (missing-bound-check)
- 0b16a3ae4f99 (missing-bound-check)
- 3d19cd9060a9 (accounting)
- 1a63e0033ca6 (accounting)
- f23fd9948544 (accounting)

Revise the specification. Reply with the complete file in exactly one
`solidity` code block. Revisions left after this one: 1.
