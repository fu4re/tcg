# Aborted: Vat fM seed 0, attempt 2 (protocol v3, max_tokens 64 000)

In one line: the generator produced a 73-check Spec of 37 530 runtime bytes,
and Check had already run on it: Unknown, 49 Accept / 24 unproved, in 805 s.

Stopped by hand during round 1 (`round_1/cand_2` holds only the request in
flight; no response was received). Wall time up to the stop: 2558 s.

Round 1 cand 1 (`end_turn`, 30 892 output tokens of which 21 014 thinking):
a 73-check spec. Check(b, φ) = Unknown (unproved), 49 checks Accept and 24
unproved, 805 s wall / 3074 s solc. Adversary: ms_cert 0/8 in 1465 s, with
`check_outcome_counts = {"not_run": 146000}` (2000 σ × 73 checks) for every
mutant, i.e. no check ever ran.

Cause: Spec-over-b runtime is 37 530 bytes, above the EIP-170 limit of
24 576 that the executor (pyrevm, default CfgEnv) enforces; every deployment
of the Spec ends in `CreateContractSizeLimit` (`deploy.outcome = other`), so
`evaluate_witness` marks every check `not_run`. Vat's own runtime is 12 239
bytes; the hand-written ladder's `phi_full` (42 checks) is 23 899 bytes, just
under the limit. The 0/8 is an executor artifact, not a property of the spec,
and the fM feedback would have reported "0 of 8" with no reason, so the run
was stopped rather than spend rounds 2-3.

Nothing here is a result about the specs; it is a measurement-harness limit.
