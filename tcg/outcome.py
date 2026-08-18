"""Exit-code table shared by every command.

One table, one file: "could not verify" (2) must never share a code with
"found a defect" (3), and success (0) has exactly one definition. Unknown is a
refusal, not a pass.
"""
from __future__ import annotations

from enum import IntEnum


class Exit(IntEnum):
    OK = 0        # command succeeded; for verify: certificate holds
    USAGE = 1     # usage or internal error
    UNKNOWN = 2   # prover could not decide — conservative refusal
    REFUSED = 3   # refuted with a witness, or a verifier check failed


EXIT_MEANING: dict[int, str] = {
    Exit.OK: "ok",
    Exit.USAGE: "usage / internal error",
    Exit.UNKNOWN: "unknown — could not verify (refusal)",
    Exit.REFUSED: "refused — refutation witness or failed check",
}


# Unknown subclasses recorded by prove/verify. All three refuse; the class is
# kept because (a) carries localization useful for rebuilding a loop.
#
# (a) is spec vocabulary only against the real Haskell-backend kprove: it is
# currently unreachable (tcg never passes --depth/--branching-allowed), and
# if it ever becomes reachable there is no known text distinguishing it from
# a genuine refutation (see tcg/commands/prove.py, docs/substrate.md §4b).
#
# (c) covers any solver/proof-state "could not decide" outcome, INCLUDING a
# residual boolean implication left undischarged after the rewrite target
# was otherwise reached (kore-exec's "WarnStuckClaimState ... unifies ...
# implication check has failed"). This also covers the honest substrate
# limit in docs/substrate.md §9: a claim whose target is reached but whose
# postcondition is actually FALSE (e.g. a wrong arithmetic bound) is, in
# kore-exec's own output, textually indistinguishable from a true claim that
# is merely under-specified -- both land in (c), not Refute.
UNKNOWN_CLASSES: dict[str, str] = {
    "a": "iteration bound exhausted (spec vocabulary; unreachable against "
         "the real Haskell backend today)",
    "b": "timeout",
    "c": "solver/proof-state unknown, including a residual implication left "
         "undischarged (nonlinear arithmetic / hashing theory / an "
         "under-specified-but-possibly-true claim)",
}
