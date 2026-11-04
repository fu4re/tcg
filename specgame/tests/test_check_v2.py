"""Check v2 (protocol.md, Protocol v2): per-check isolated harnesses in a pool,
the combine rule, agreement with the whole-harness Check, the verdict cache."""
import json
import re
import sys
import tempfile
import unittest
from dataclasses import asdict
from pathlib import Path

from tests._util import ROOT, TOKEN, core, speclint

sys.path.insert(0, str(ROOT / "generator"))
import loop  # noqa: E402

SPECS = ROOT / "subjects" / "capped_token" / "specs"
LADDER = [SPECS / f"{p}.sol" for p in ("phi_top", "phi_owner", "phi_cap", "phi_both", "phi_transfer", "phi_full")]
CONTROLS = [SPECS / "controls" / "phi_false.sol", SPECS / "controls" / "phi_dead.sol"]


def r(verdict, reason):
    return {"verdict": verdict, "reason": reason}


class Isolation(unittest.TestCase):
    def test_each_harness_is_the_header_plus_one_check(self):
        for p in LADDER + CONTROLS:
            text = p.read_text()
            checks = core.check_functions(text)
            self.assertEqual(sorted(n for n, _ in checks),
                             core.compile_spec_over(p, TOKEN)["checks"], p.name)
            for name, body in checks:
                h = core.isolate_check(text, name)
                self.assertEqual(h, core.ISOLATED_HEADER + body + "\n}\n")
                self.assertIn(body, text)
                self.assertEqual(re.findall(r"function (check_\w+)", h), [name])
                self.assertEqual(speclint.lint_spec(h), [], f"{p.name}:{name}")

    def test_comments_outside_the_check_do_not_change_the_harness(self):
        text = (SPECS / "phi_owner.sol").read_text()
        edited = text.replace("/// phi_owner:", "/// a different comment\n/// phi_owner:")
        for name, _ in core.check_functions(text):
            self.assertEqual(core.isolate_check(text, name), core.isolate_check(edited, name))

    def test_not_a_spec(self):
        with self.assertRaises(core.CompileError):
            core.check_functions("contract Other { }")


class Combine(unittest.TestCase):
    def test_rules(self):
        A, R, U = "Accept", "Refute", "Unknown"
        c = core.combine_verdicts
        self.assertEqual(c([r(A, "all_targets_safe")] * 3), (A, "all_checks_safe"))
        self.assertEqual(c([r(A, "x"), r(R, "counterexample"), r(U, "wall_timeout")]), (R, "counterexample"))
        self.assertEqual(c([r(R, "violation_without_counterexample")]), (R, "violation_without_counterexample"))
        self.assertEqual(c([r(A, "x"), r(U, "wall_timeout"), r(U, "unproved")]), (U, "budget"))
        self.assertEqual(c([r(A, "x"), r(U, "unproved")]), (U, "unproved"))
        self.assertEqual(c([r(U, "wall_timeout"), r(U, "compile_error")]), (U, "compile_error"))
        self.assertEqual(c([r(U, "missing_target")]), (U, "missing_target"))
        self.assertEqual(c([]), (U, "no_targets"))


class AgreesWithWholeHarness(unittest.TestCase):
    """The isolated verdict equals the whole-harness verdict, per spec and per
    assert (phi_full's whole-harness Check takes ~10 min and is left out here;
    protocol.md Protocol v2 records it)."""

    def test_small_specs(self):
        for p in LADDER[:5] + CONTROLS:
            whole = core.smtcheck(p, TOKEN, core.CHECK_TIMEOUT_MS, core.CHECK_WALL_TIMEOUT_S)
            iso = core.smtcheck_isolated(p, TOKEN, core.CHECK_TIMEOUT_MS, core.CHECK_WALL_TIMEOUT_S)
            self.assertEqual(iso.verdict, whole.verdict, p.name)
            per_fn = {}
            for t in whole.targets:
                per_fn.setdefault(t["function"], []).append(t["status"])
            for c in iso.checks:
                self.assertEqual([t["status"] for t in c["result"]["targets"]], per_fn[c["check"]],
                                 f"{p.name}:{c['check']}")


class Cache(unittest.TestCase):
    def test_hit_returns_the_same_result_and_the_key_covers_the_input(self):
        spec = SPECS / "phi_cap.sol"
        with tempfile.TemporaryDirectory() as t:
            a = core.smtcheck_isolated(spec, TOKEN, 60000, 600, cache_dir=Path(t))
            b = core.smtcheck_isolated(spec, TOKEN, 60000, 600, cache_dir=Path(t))
            self.assertEqual((a.cache_hits, b.cache_hits), (0, len(b.checks)))
            self.assertEqual([c["result"] for c in a.checks], [c["result"] for c in b.checks])
            c = core.smtcheck_isolated(spec, TOKEN, 59999, 600, cache_dir=Path(t))
            self.assertEqual(c.cache_hits, 0)
            self.assertEqual(len(list(Path(t).glob("*.json"))), 2 * len(a.checks))

    def test_verifier_never_reads_the_cache(self):
        src = (ROOT / "tools" / "verify.py").read_text()
        self.assertNotIn("CACHE_DIR", src)
        self.assertIn("cache_dir=None", src)


class LoopMapsLinesToTheCandidateFile(unittest.TestCase):
    def test_not_proved_lines_point_into_the_spec(self):
        text = (SPECS / "controls" / "phi_false.sol").read_text()
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "Spec.sol"
            p.write_text(text)
            res = core.smtcheck_isolated(p, TOKEN, 60000, 600)
        rows = loop.not_proved(text, res)
        self.assertEqual(len(rows), 1)
        self.assertEqual(text.splitlines()[rows[0]["line"] - 1].strip(), "assert(totalSupply < cap);")
        self.assertEqual(rows[0]["text"], "assert(totalSupply < cap);")


if __name__ == "__main__":
    unittest.main()
