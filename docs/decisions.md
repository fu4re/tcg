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

## D4 — Definition discovery: init-time only, never at prove/verify time

The kompiled K/KEVM definition path is resolved exactly once, in `tcg init`:
from `--definition PATH` if given, else from `$TCG_DEFINITION` at that moment
(flag wins over env), else left unset. Whatever is resolved — including
"unset" — is written into `.tcg/toolchain.lock` verbatim.

`tcg prove` and `tcg verify` read only their own `--definition` flag or the
lock; neither one re-reads the environment. The lock is the single pinned
record a replay trusts, so init-time-only discovery keeps every proof run
attributable to a fixed, on-disk value rather than to whatever a shell
happened to export that day. A prover run that "worked on my machine" because
of an ambient `$TCG_DEFINITION` and fails on replay would be exactly the kind
of untraceable drift the lock exists to rule out.

## D5 — One verdict judge, shared: `tcg.verdict.classify()`

Raw `kprove` output is classified into Accept/Refute/Unknown by exactly one
function, `tcg.verdict.classify()`, called by both `tcg prove` (workspace
path) and `tcg verify`'s replay step (bundle-only path). A claim is not
"more Accepted" because it was judged by the workspace tool instead of the
verifier that re-checks a stranger's bundle — before this, `verify` judged
replay by raw exit code alone (any non-zero, non-timeout result was
"failed", i.e. Refute), which silently conflated a genuine structural
counterexample with an undecided solver result and, on replay, refused the
certificate (exit REFUSED, 3) for cases that should have been a conservative
"could not re-verify" (exit UNKNOWN, 2) instead.

`tcg.verdict` carries no workspace or filesystem state and imports nothing
from `tcg.workspace` or `tcg.commands.*` — the bundle-only contract `verify`
and `roots` already had for their other dependencies (`tcg.claims`) extends
to the judge itself. `scripts/repo-checks.sh` greps `tcg/commands/verify.py`,
`tcg/commands/roots.py`, and `tcg/verdict.py` for exactly such an import and
fails loudly if one appears, so the contract can't erode one convenient
import at a time.

Retries (`toolchain.lock`'s `replay.retries`) apply only while the classifier
says Unknown — absorbing solver nondeterminism on an undecided result.
Accept and Refute are both final on the first attempt: re-running a
deterministic prover against the same fixed claim hoping a genuine
refutation goes away on the next attempt would not be a retry, it would be
forum shopping.
