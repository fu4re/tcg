"""Validate `tcg.verdict.classify()` against real Haskell-backend kprove
output.

`classify()` lives in tcg/verdict.py, not tcg/commands/prove.py: it is the
shared judge both `prove` (workspace path) and `verify` (bundle-only replay)
use, so it must not import tcg.workspace or tcg.commands.* (see
scripts/repo-checks.sh's bundle-only-import guard).

Every log here is real, captured output (see tests/control/, docs/substrate.md
"classify() validation") -- none of it is synthesized text, EXCEPT the one
test that says so explicitly (the mixed-signal test below, which documents a
combinatorial case no single real capture demonstrates on its own). Run:

    PYTHONPATH=. python3 -m unittest tests.test_classify -v

Track B (prover substrate hardening): these logs were produced by running
`kprove --definition ~/toolchains/kevm-1.0.678/haskell ...` directly on the
control specs in tests/control/, against the EXACT committed spec files (not
predecessor drafts), and (for the timeout case) by replicating
tcg.commands.prove.run()'s exact subprocess.run(..., timeout=...) pattern.
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tcg.verdict import classify

REPO_ROOT = Path(__file__).resolve().parents[1]
LOGS = REPO_ROOT / "tests" / "control" / "logs"


def read(name: str) -> str:
    return (LOGS / name).read_text(encoding="utf-8")


class TestClassifyAgainstRealLogs(unittest.TestCase):
    """The three control cases required by Track B, against real logs."""

    def test_provable_is_accept(self):
        # kprove tests/control/provable.k ... -> exit 0, stdout "#Top".
        verdict, ucls, hint = classify(0, read("provable.log"), False)
        self.assertEqual(verdict, "Accept")
        self.assertIsNone(ucls)
        self.assertIsNone(hint)

    def test_refutable_is_refute(self):
        # kprove tests/control/refutable.k ... -> exit 1. The claim asserts a
        # final <pc> of 999, which is false for any execution of a 1-byte
        # program starting at pc=0 -- a genuine counterexample, not merely an
        # under-specified claim (contrast with
        # test_underspecified_true_claim_is_unknown_not_refute below).
        #
        # This log's road to that verdict is the noisy one: before reaching
        # the generic terminal trailer, kore-exec hits an internal Krypto
        # builtin assertion failure and crash-recovers (docs/substrate.md
        # §5). It has NEITHER WarnStuckClaimState variant's text at all --
        # just the crash, then the generic trailer. This pins that a crash
        # is never itself a classification signal, and that the generic
        # trailer alone is still enough for a correct Refute even with a
        # noisy log (contrast with refutable-structural.log below, the same
        # false-claim shape captured *without* the crash, showing the actual
        # "doesn't unify" warning text).
        verdict, ucls, hint = classify(1, read("refutable.log"), False)
        self.assertEqual(verdict, "Refute")
        self.assertIsNone(ucls)
        self.assertIsNone(hint)

    def test_refutable_structural_is_refute(self):
        # kprove tests/control/refutable-structural.k ... -> exit 1. Same
        # false-claim shape as refutable.k (a claim that cannot possibly
        # hold), but with the <k> cell's RHS closed (no trailing "...") to
        # avoid inviting the crash above -- so this log shows the *other*
        # WarnStuckClaimState variant cleanly:
        #
        #     Warning (WarnStuckClaimState):
        #         The configuration's term doesn't unify with the
        #         destination's term and the configuration cannot be
        #         rewritten further.
        #
        # ("doesn't unify", not "unifies... but the implication check ...
        # failed" -- the two are different verb forms, "unify" vs.
        # "unifies", and classify()'s guard is precise about which one it
        # matches). This must stay Refute: it is the regression case for the
        # over-broad "warnstuckclaimstate" tag match this Track B pass
        # removed (see docs/substrate.md §4a) -- that earlier guard would
        # have swallowed this genuine defect into Unknown.
        verdict, ucls, hint = classify(1, read("refutable-structural.log"), False)
        self.assertEqual(verdict, "Refute")
        self.assertIsNone(ucls)
        self.assertIsNone(hint)

    def test_wallclock_timeout_is_unknown_b(self):
        # tcg prove's actual mechanism: subprocess.run(argv, timeout=N) ->
        # TimeoutExpired. classify() must route on the timed_out flag alone;
        # log content is irrelevant here (and was empty: kprove had not
        # flushed any output in the 2s budget used to capture this).
        verdict, ucls, hint = classify(-1, read("undecided-timeout.log"), True)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "b")
        self.assertIsNone(hint)


class TestClassifyRegressionOnUnderSpecifiedTrueClaim(unittest.TestCase):
    """The bug this Track B pass found and fixed.

    Before iterating provable.k to its final, fully-concretized form (every
    non-transitioning cell given a concrete value), an earlier draft of the
    *same, semantically true* STOP claim -- committed verbatim as
    tests/control/underspecified-true.k -- left several cells symbolic
    (<static>, <id>, <caller>, <codeAddr>, ...). kprove could not discharge
    the residual implication and exited 1 -- but the claim itself is true
    (STOP really does reach <k> #halt ... </k> with EVMC_SUCCESS).

    Before the fix, classify() reported this as Refute: a false defect
    report on a valid claim. The real log contains a distinguishing
    preamble kprove does NOT print for a genuine (non-unifying) refutation
    (contrast with tests/control/logs/refutable-structural.log, which
    prints the sibling "doesn't unify" variant of the same warning name for
    an actually-false claim):

        kore-exec: [...] Warning (WarnStuckClaimState):
            The configuration's term unifies with the destination's term,
            but the implication check between the conditions has failed.

    classify() now matches only that specific phrase ("unifies with the
    destination"), not the bare "WarnStuckClaimState" tag, and reports
    Unknown("c") with an actionable hint instead of Refute.
    """

    def test_underspecified_true_claim_is_unknown_not_refute(self):
        verdict, ucls, hint = classify(1, read("underspecified-true.log"), False)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "c")
        self.assertIn("residual implication undischarged", hint)


class TestClassifyAcceptRequiresCorroboration(unittest.TestCase):
    """exit 0 alone is not Accept -- the success marker must be present too.

    Guards against a kprove invocation that exits 0 without actually having
    proven anything (e.g. a wrapper-script early-exit, or a future kprove
    flag/mode this substrate hasn't been validated against). The one real
    success shape observed on this substrate is exactly "#Top" on stdout,
    nothing else (tests/control/logs/provable.log, 5 bytes: "#Top\\n").
    """

    def test_exit_zero_without_top_is_unknown_with_hint(self):
        verdict, ucls, hint = classify(0, "some other output entirely\n", False)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "c")
        self.assertEqual(hint, "prover exited 0 but no proof pattern found")

    def test_exit_zero_with_top_is_accept(self):
        verdict, ucls, hint = classify(0, read("provable.log"), False)
        self.assertEqual(verdict, "Accept")
        self.assertIsNone(ucls)
        self.assertIsNone(hint)


class TestClassifyMixedSignalsPreferUnknown(unittest.TestCase):
    """Documented limit: classify() sees one whole log per kprove call, and
    a single call's search can visit several branches, each logging its own
    WarnStuckClaimState verdict independently. If a log contains BOTH the
    "unifies... implication failed" signal and a genuine-refutation signal
    (either the "doesn't unify" phrasing or just the bare generic trailer),
    classify() must not resolve that ambiguity in favor of Refute merely
    because the refutation-shaped text happens to appear first: an
    unresolved branch anywhere makes the whole call's verdict unreliable, so
    it stays Unknown regardless of which signal comes first in the log.

    This scenario is not something any single real captured log
    demonstrates (none of tests/control/logs/ contains both signals at
    once) -- it is deliberately synthesized to pin the priority rule
    directly, including the harder ordering (refutation-shaped text
    appearing textually BEFORE the stuck-unifies text).
    """

    def test_stuck_signal_wins_regardless_of_order(self):
        # Genuine "doesn't unify" text (and the generic trailer) appears
        # BEFORE the "unifies... but implication failed" text -- a naive
        # leftmost-match classifier would say Refute. It must not.
        mixed_refute_first = (
            "kore-exec: [1] Warning (WarnStuckClaimState):\n"
            "    The configuration's term doesn't unify with the "
            "destination's term and the configuration cannot be rewritten "
            "further.\n"
            "kore-exec: [2] Warning (WarnStuckClaimState):\n"
            "    The configuration's term unifies with the destination's "
            "term, but the implication check between the conditions has "
            "failed.\n"
        )
        verdict, ucls, hint = classify(1, mixed_refute_first, False)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "c")
        self.assertIn("residual implication undischarged", hint)

    def test_stuck_signal_wins_in_natural_order_too(self):
        # The order every real capture actually shows: stuck-unifies first,
        # generic trailer last.
        mixed_stuck_first = (
            "kore-exec: [1] Warning (WarnStuckClaimState):\n"
            "    The configuration's term unifies with the destination's "
            "term, but the implication check between the conditions has "
            "failed.\n"
            "[Error] Prover: backend terminated because the configuration "
            "cannot be\nrewritten further.\n"
        )
        verdict, ucls, hint = classify(1, mixed_stuck_first, False)
        self.assertEqual(verdict, "Unknown")
        self.assertEqual(ucls, "c")


class TestKnownLimitationDepthBoundIsUnresolved(unittest.TestCase):
    """Documented, NOT fixed: --depth is currently unreachable in prove.py.

    tcg.commands.prove.run() never passes --depth or --branching-allowed to
    kprove, so this scenario cannot occur via the real CLI today. It is
    pinned here only so that anyone who *does* add such a flag to prove.py
    sees this test fail and reads the warning rather than assuming
    classify() already handles it.

    kprove --depth 1 on the (true) provable.k claim exits 1 with a log that
    ends in the exact same generic trailer as a genuine refutation, and
    critically shows NO WarnStuckClaimState preamble at all (the search ran
    out of steps before ever reaching an implication check) -- so there is
    no log text, anywhere, that distinguishes this case from real
    refutation. classify() no longer has a depth/iteration-bound branch (it
    was dead code against the real backend -- see tcg/commands/prove.py and
    tcg/outcome.py). See tests/control/logs/undecided-depth-bound.log and
    tests/control/undecided.md.
    """

    def test_depth_bounded_true_claim_is_still_misclassified_as_refute(self):
        log = read("undecided-depth-bound.log")
        verdict, ucls, _hint = classify(1, log, False)
        # This assertion documents current (undesired but currently
        # unreachable) behavior -- it is intentionally NOT the "correct"
        # verdict (which would be Unknown, since provable.k is true and was
        # merely cut short). Do not "fix" this test without also either (a)
        # confirming prove.py still never passes --depth, or (b) shipping an
        # actual classify()/prove.py fix for this case with its own log
        # evidence.
        self.assertEqual(verdict, "Refute")
        self.assertIsNone(ucls)


if __name__ == "__main__":
    unittest.main()
