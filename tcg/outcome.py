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
UNKNOWN_CLASSES: dict[str, str] = {
    "a": "iteration bound exhausted",
    "b": "timeout",
    "c": "solver unknown (nonlinear arithmetic / hashing theory)",
}
