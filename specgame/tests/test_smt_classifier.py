"""Strict SMTChecker classifier: captured solc outputs (no solc run) plus one
live round trip each for Accept and Refute."""
import copy
import json
import unittest

from tests._util import FALSE, FIXTURES, TAUTOLOGY, TOKEN, core

V = core.Verdict


def load(name: str) -> dict:
    return json.loads((FIXTURES / "smt" / f"{name}.json").read_text())


def classify(doc: dict):
    return core.classify_smt_output(doc["output"], doc["sources"])


class CapturedOutputs(unittest.TestCase):
    def test_proved(self):
        verdict, reason, targets, _ = classify(load("proved"))
        self.assertEqual((verdict, reason), (V.ACCEPT.value, "all_targets_safe"))
        self.assertEqual([(t["function"], t["status"]) for t in targets], [("check_tautology", "safe")])

    def test_counterexample(self):
        verdict, reason, targets, _ = classify(load("counterexample"))
        self.assertEqual(verdict, V.REFUTE.value)
        cex = targets[0]["counterexample"]
        self.assertIn("x = 6", cex["assignments"])
        self.assertTrue(any(l.startswith("Spec.check_reachable(") for l in cex["trace"]))

    def test_might_happen_is_unknown(self):
        verdict, reason, _, _ = classify(load("might_happen"))
        self.assertEqual((verdict, reason), (V.UNKNOWN.value, "unproved"))

    def test_no_solver_is_unknown(self):
        verdict, reason, _, _ = classify(load("no_solver"))
        self.assertEqual((verdict, reason), (V.UNKNOWN.value, "solver_unavailable"))

    def test_no_solver_without_marker_is_still_not_accept(self):
        # Even if solc stopped printing the "not available" warning, a run with
        # no per-target result line must not be an Accept.
        doc = load("no_solver")
        doc["output"]["errors"] = [e for e in doc["output"]["errors"]
                                   if not any(m in e["message"] for m in core.NO_SOLVER_MARKERS)]
        verdict, reason, _, _ = classify(doc)
        self.assertEqual((verdict, reason), (V.UNKNOWN.value, "missing_target"))

    def test_unrecognized_smt_message_is_unparsed(self):
        doc = load("proved")
        for e in doc["output"]["errors"]:
            if e["message"] == core.MSG_SAFE:
                e["message"] = "CHC: Assertion violation check is probably safe."
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "unparsed"))

    def test_result_at_unknown_location_is_unparsed(self):
        doc = load("proved")
        for e in doc["output"]["errors"]:
            if e["message"] == core.MSG_SAFE:
                e["sourceLocation"]["start"] += 1
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "unparsed"))

    def test_duplicate_result_is_unparsed(self):
        doc = load("proved")
        safe = [e for e in doc["output"]["errors"] if e["message"] == core.MSG_SAFE][0]
        doc["output"]["errors"].append(copy.deepcopy(safe))
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "unparsed"))

    def test_counterexample_without_trace_is_unparsed(self):
        doc = load("counterexample")
        for e in doc["output"]["errors"]:
            if e["message"].startswith(core.MSG_VIOLATED):
                e["message"] = core.MSG_VIOLATED + "\nCounterexample:\nx = 6\n"
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "unparsed"))

    def test_info_severity_mismatch_is_unparsed(self):
        doc = load("proved")
        for e in doc["output"]["errors"]:
            if e["message"] == core.MSG_SAFE:
                e["severity"] = "warning"
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "unparsed"))

    def test_compile_error(self):
        doc = load("proved")
        doc["output"]["errors"].append({"severity": "error", "type": "TypeError", "message": "boom"})
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "compile_error"))

    def test_wall_timeout(self):
        self.assertEqual(core.classify_smt_output(None, {})[:2], (V.UNKNOWN.value, "wall_timeout"))

    def test_no_targets(self):
        doc = load("proved")
        doc["output"]["errors"] = [e for e in doc["output"]["errors"] if "CHC" not in e["message"]]
        doc["output"]["sources"]["Spec.sol"]["ast"] = {}
        self.assertEqual(classify(doc)[:2], (V.UNKNOWN.value, "no_targets"))


class LiveRoundTrip(unittest.TestCase):
    def test_accept(self):
        r = core.smtcheck(TAUTOLOGY, TOKEN, 20000, 300)
        self.assertEqual((r.verdict, r.reason), (V.ACCEPT.value, "all_targets_safe"), r.targets)
        self.assertEqual(r.solc_input["settings"]["modelChecker"]["contracts"], {"Spec.sol": ["Spec"]})

    def test_refute(self):
        r = core.smtcheck(FALSE, TOKEN, 20000, 300)
        self.assertEqual(r.verdict, V.REFUTE.value, r.targets)
        self.assertIsNotNone(r.targets[0]["counterexample"])


if __name__ == "__main__":
    unittest.main()
