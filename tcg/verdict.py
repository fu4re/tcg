"""Shared prover-verdict judge: classify raw kprove output into Accept /
Refute / Unknown.

No workspace or filesystem state, no tcg.commands import — shared by
`prove` (workspace path) and `verify` (bundle-only path). Neither this
module nor verify.py/roots.py may name tcg.workspace or tcg.commands.* in an
import statement (see scripts/repo-checks.sh's mechanical guard). Same
judge, same discipline, on both sides: a claim is not "more Accepted"
because it was judged by the workspace tool instead of the verifier.

Validated against real Haskell-backend kprove output -- see
tests/control/logs/ and docs/substrate.md §4.
"""
from __future__ import annotations

import re

# kore-exec's own success marker for a fully-discharged all-path claim (the
# pretty-printed \top formula). Pinned empirically: tests/control/logs/
# provable.log is exactly "#Top\n" with nothing else on stdout.
_ACCEPT_PATTERN = "#Top"

_WS = re.compile(r"\s+")

# "WarnStuckClaimState" covers two OPPOSITE outcomes -- "unifies... but the
# implication check has failed" (Unknown: solver-decidability gap) vs.
# "doesn't unify..." (Refute: genuine structural counterexample) -- so only
# the first phrase is a valid Unknown signal; matching the bare tag name
# swallows a found defect into a false "could not verify". Full argument,
# real log evidence, and why "stuck" must win regardless of textual position
# (not just whichever comes first) are in docs/substrate.md §4a and
# tests/test_classify.py. One precompiled case-insensitive alternation,
# matched against one whitespace-collapsed copy of the log -- not several
# lowercased copies -- since real proof logs can reach tens of MB.
_STUCK_OR_REFUTE = re.compile(
    r"(?P<stuck>unifies with the destination)|(?P<refute>cannot be rewritten further)",
    re.IGNORECASE,
)


def classify(returncode: int, log: str, timed_out: bool) -> tuple[str, str | None, str | None]:
    """(verdict, unknown_class, hint). Only exit 0 *and* a corroborated
    success marker is Accept. Validated against real Haskell-backend kprove
    output -- see tests/control/logs/ and docs/substrate.md §4.
    """
    if timed_out:
        return "Unknown", "b", None
    if returncode == 0:
        if _ACCEPT_PATTERN in log:
            return "Accept", None, None
        return "Unknown", "c", "prover exited 0 but no proof pattern found"
    norm = _WS.sub(" ", log)
    saw_refute = False
    for m in _STUCK_OR_REFUTE.finditer(norm):
        if m.group("stuck"):
            return ("Unknown", "c",
                    "residual implication undischarged — claim may need more "
                    "concretized cells; see log")
        saw_refute = True
    if saw_refute:
        return "Refute", None, None
    # Anything unrecognized stays Unknown -- never Refute. The class "a"
    # (iteration bound exhausted) this function used to detect via a
    # "depth bound"/"iteration bound"/"max iterations" text match was
    # removed: real kprove never emits that text (see docs/substrate.md §4b
    # and tcg.outcome.UNKNOWN_CLASSES, where the name is kept as spec
    # vocabulary only).
    return "Unknown", "c", None


def to_text(x: str | bytes | None) -> str:
    """subprocess.TimeoutExpired's e.stdout/e.stderr may be str (text-mode
    Popen) or bytes, depending on how far communicate() got -- don't assume."""
    if x is None:
        return ""
    return x.decode(errors="replace") if isinstance(x, bytes) else x
