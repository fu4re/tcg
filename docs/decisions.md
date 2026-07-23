# Design decisions (v0)

Short records of the choices that fix the v0 implementation. Each can be
revisited in a later major version; none can drift silently.

## D1 — Canonical claim form: K spec module, one claim per file

A canonical claim is a single K `claim` in its own spec module, content-addressed
by the SHA-256 of its canonical text. This is the form exercised against the
pinned prover; a Kore-level canonical form stays open as a future option. The
guard against frontend syntax drift is the mandatory **round-trip check**: the
compiler re-reads its own emitted artifact, re-canonicalizes, and requires the
identical hash before the claim enters `interfaces.json`.

In v0 claim bodies are authored by hand. `compile-claims` does not invent
proof content — it canonicalizes, enforces form discipline (explicit all-path
attribute, label integrity), content-addresses, and round-trips. Generation of
claim bodies is a later, untrusted, non-acceptance-path stage.

Attribute position is fixed empirically against the pinned prover: attributes
live in the claim's **trailing** attribute list, `[label(<l>), all-path]` —
the `claim [x]:` head position accepts only a bare label and rejects a comma.
Authored bodies must not carry `trusted`; `tcg prove` injects it when supplying
children, so an assumption can never be smuggled in as an authored claim.

## D2 — Root granularity: one root per external function, linear assembly only

Each external function of the subject contributes exactly one root claim.
Composite roots exist only as linear root-assembly chains
(see bundle-spec §5); graph-shaped assembly is out of scope for v1.

## D3 — Demo pair: correct form proved, drain form as refutation control

The reference workspace proves the checks-effects-interactions form of
`withdraw` (ledger debit before the external call). The vulnerable
demonstration variant zeroes the ledger entry after the external call
(`bal = 0`), because under Solidity 0.8 checked arithmetic the `-=` variant
reverts on reentrant drain and the refutation would be a discipline flag
without an executable exploit. The refutation control must refute with a
concrete counterexample, so the really drainable form is the honest choice.
