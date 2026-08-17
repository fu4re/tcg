"""Validate `tcg.commands.prove.classify()` against real Haskell-backend
kprove output.

Every log here is real, captured output (see tests/control/, docs/substrate.md
"classify() validation") -- none of it is synthesized text. Run:

    PYTHONPATH=. python3 -m unittest tests.test_classify -v

Track B (prover substrate hardening): these logs were produced by running
`kprove --definition ~/toolchains/kevm-1.0.678/haskell ...` directly on the
control specs in tests/control/, and (for the timeout case) by replicating
tcg.commands.prove.run()'s exact subprocess.run(..., timeout=...) pattern.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tcg.commands.prove import classify

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS = REPO_ROOT / "tests" / "control" / "logs"


def read(name: str) -> str:
    return (LOGS / name).read_text(encoding="utf-8")


class TestClassifyAgainstRealLogs(unittest.TestCase):
    """The three control cases required by Track B, against real logs."""

    def test_provable_is_accept(self):
        # kprove tests/control/provable.k ... -> exit 0, stdout "#Top".
        verdict, ucls = classify(0, read("provable.log"), False)
        self.assertEqual(verdict, "Accept")
        self.assertIsNone(ucls)

    def test_refutable_is_refute(self):
        # kprove tests/control/refutable.k ... -> exit 1. The claim asserts a
        # final <pc> of 999, which is false for any execution of a 1-byte
        # program starting at pc=0 -- a genuine counterexample, not merely an
        # under-specified claim (contrast with
        # test_underspecified_true_claim_is_unknown_not_refute below).
        verdict, ucls = classify(1, read("refutable.log"), False)
        self.assertEqual(verdict, "Refute")
        self.assertIsNone(ucls)

    def test_wallclock_timeout_is_unknown_b(self):
        # tcg prove's actual mechanism: subprocess.run(argv, timeout=N) ->
        # TimeoutExpired. classify() must route on the timed_out flag alone;
        # log content is irrelevant here (and was empty: kprove had not
        # flushed any output in the 2s budget used to capture this).
        verdict, ucls = classify(-1, read("undecided-timeout.log"), True)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "b")


class TestClassifyRegressionOnUnderSpecifiedTrueClaim(unittest.TestCase):
    """The bug this Track B pass found and fixed.

    Before iterating provable.k to its final, fully-concretized form (every
    non-transitioning cell given a concrete value), an earlier draft of the
    *same, semantically true* STOP claim left several cells symbolic
    (<static>, <id>, <caller>, <codeAddr>, ...). kprove could not discharge
    the residual implication and exited 1 -- but the claim itself is true
    (STOP really does reach <k> #halt ... </k> with EVMC_SUCCESS).

    Before the fix, classify() reported this as Refute: a false defect
    report on a valid claim. The real log contains a distinguishing
    preamble kprove does NOT print for a genuine (non-unifying) refutation:

        kore-exec: [...] Warning (WarnStuckClaimState):
            The configuration's term unifies with the destination's term,
            but the implication check between the conditions has failed.

    vs. refutable.log (genuinely false claim), which jumps straight to the
    generic terminal message with no such preamble. classify() now checks
    for this preamble first and reports Unknown("c") instead of Refute.
    """

    UNDERSPECIFIED_TRUE_LOG = """\
kore-exec: [3760685] Warning (WarnStuckClaimState):
    The configuration's term unifies with the destination's term, but the implication check between the conditions has failed. Location: stop-spec.k:7:9-13:44
Context:
    (InfoReachability) while checking the implication
[Error] Prover: backend terminated because the configuration cannot be
rewritten further. See output for more details.
"""

    def test_underspecified_true_claim_is_unknown_not_refute(self):
        verdict, ucls = classify(1, self.UNDERSPECIFIED_TRUE_LOG, False)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "c")

    def test_genuine_refutation_is_unaffected_by_the_fix(self):
        # Same generic trailer, no WarnStuckClaimState preamble -> still
        # Refute. This is the real refutable.log content (genuinely false
        # <pc> == 999 claim), confirming the fix does not blunt real defect
        # detection.
        verdict, ucls = classify(1, read("refutable.log"), False)
        self.assertEqual(verdict, "Refute")
        self.assertIsNone(ucls)


class TestKnownLimitationDepthBoundIsUnresolved(unittest.TestCase):
    """Documented, NOT fixed: --depth is currently unreachable in prove.py.

    tcg.commands.prove.run() never passes --depth or --branching-allowed to
    kprove, so this scenario cannot occur via the real CLI today. It is
    pinned here only so that anyone who *does* add such a flag to prove.py
    sees this test fail and reads the warning rather than assuming
    classify() already handles it.

    kprove --depth 1 on the (true) provable.k claim exits 1 with a log that
    ends in the exact same generic trailer as a genuine refutation, and
    critically shows NO WarnStuckClaimState preamble (the search ran out of
    steps before ever reaching an implication check) -- so the fix above
    does not and cannot distinguish this case from real refutation using
    log text alone. See tests/control/logs/undecided-depth-bound.log and
    tests/control/undecided.md.
    """

    def test_depth_bounded_true_claim_is_still_misclassified_as_refute(self):
        log = read("undecided-depth-bound.log")
        verdict, _ = classify(1, log, False)
        # This assertion documents current (undesired but currently
        # unreachable) behavior -- it is intentionally NOT the "correct"
        # verdict (which would be Unknown, since provable.k is true and was
        # merely cut short). Do not "fix" this test without also either (a)
        # confirming prove.py still never passes --depth, or (b) shipping an
        # actual classify()/prove.py fix for this case with its own log
        # evidence.
        self.assertEqual(verdict, "Refute")


if __name__ == "__main__":
    unittest.main()
