"""WP3: check.py exit codes, κ acceptance table, vacuity (a), ladder structure."""
import contextlib
import io
import json
import re
import tempfile
import unittest
from pathlib import Path

from tests._util import FIXTURES, ROOT, TOKEN, core, speclint

import check as check_cli  # noqa: E402  (tools/ is on sys.path via tests._util)
import kappa as kappa_mod  # noqa: E402
import vacuity as vacuity_mod  # noqa: E402

SPECS = ROOT / "subjects" / "capped_token" / "specs"
CONTROLS = SPECS / "controls"


def run_cli(main, *argv) -> tuple[int, str]:
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), contextlib.redirect_stderr(io.StringIO()):
        code = main([str(a) for a in argv])
    return code, buf.getvalue()


def checks_of(path: Path) -> dict[str, str]:
    """check name -> its full function text (whitespace-normalized)."""
    raw = path.read_text()
    s = speclint.strip_source(raw)
    out = {}
    for m in re.finditer(r"function\s+(check_[A-Za-z0-9_]+)\s*\(", s):
        open_ = s.index("{", m.end())
        close = speclint._match_brace(s, open_)
        out[m.group(1)] = " ".join(raw[m.start():close + 1].split())
    return out


class CheckCli(unittest.TestCase):
    def test_false_control_refutes_with_counterexample(self):
        with tempfile.TemporaryDirectory() as t:
            out = Path(t) / "r.json"
            code, text = run_cli(check_cli.main, CONTROLS / "phi_false.sol", "--json", out)
            self.assertEqual(code, 3, text)
            doc = json.loads(out.read_text())
        self.assertEqual(doc["check"]["verdict"], "Refute")
        self.assertEqual(doc["check"]["reason"], "counterexample")
        self.assertEqual(doc["check"]["mode"], "isolated")
        res = doc["check"]["checks"][0]["result"]
        self.assertTrue(res["targets"][0]["counterexample"]["trace"])
        self.assertRegex(res["solc_input_sha256"], r"^[0-9a-f]{64}$")
        self.assertIn("CHC: Assertion violation happens here.", res["raw_output"])

    def test_dead_control_accepts(self):
        code, text = run_cli(check_cli.main, CONTROLS / "phi_dead.sol")
        self.assertEqual(code, 0, text)
        self.assertIn("verdict   Accept", text)

    def test_top_accepts(self):
        self.assertEqual(run_cli(check_cli.main, SPECS / "phi_top.sol")[0], 0)

    def test_unknown_exit_2(self):
        code, text = run_cli(check_cli.main, FIXTURES / "smt" / "Nonlinear.sol", "--timeout-ms", "1")
        self.assertEqual(code, 2, text)
        self.assertIn("Unknown", text)

    def test_lint_failure_exit_1(self):
        with tempfile.TemporaryDirectory() as t:
            bad = Path(t) / "bad.sol"
            bad.write_text((SPECS / "phi_top.sol").read_text().replace(
                "assert(totalSupply == totalSupply);", "totalSupply = 0;\n        assert(totalSupply == 0);"))
            code, text = run_cli(check_cli.main, bad)
        self.assertEqual(code, 1, text)
        self.assertIn("S7", text)

    def test_usage_exit_1(self):
        self.assertEqual(run_cli(check_cli.main, "/nonexistent.sol")[0], 1)
        self.assertEqual(run_cli(check_cli.main)[0], 1)


class Kappa(unittest.TestCase):
    def test_acceptance_table(self):
        # protocol.md section 11: x == x, totalSupply <= cap under its Pre and
        # !r || r are tautological; the frame conditions after transfer and r are not.
        res = kappa_mod.kappa(FIXTURES / "specs" / "kappa_acceptance.sol", TOKEN, 20000, 300)
        self.assertTrue(res["determined"])
        self.assertEqual([r["tautological"] for r in res["rows"]], [True, True, False, False, False, True])
        self.assertEqual(res["kappa"], 3)

    def test_phi_top_is_all_tautology(self):
        res = kappa_mod.kappa(SPECS / "phi_top.sol", TOKEN, 20000, 300)
        self.assertEqual(res["kappa"], 0)

    def test_phi_owner_has_content(self):
        res = kappa_mod.kappa(SPECS / "phi_owner.sol", TOKEN, 20000, 300)
        self.assertEqual(res["kappa"], res["asserts"])
        self.assertGreater(res["kappa"], 0)

    def test_committed_havoc_base_is_current(self):
        committed = (SPECS / "havoc" / "CappedToken.sol").read_text()
        self.assertEqual(kappa_mod.generate_havoc(TOKEN), committed,
                         "specs/havoc/CappedToken.sol is stale: run `make havoc`")

    def test_havoc_rejects_unsupported_artifact(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "a.sol"
            p.write_text(TOKEN.read_text().replace("uint256 public cap;", "uint256[] public cap;"))
            with self.assertRaises(kappa_mod.HavocError):
                kappa_mod.generate_havoc(p)


class Vacuity(unittest.TestCase):
    def test_dead_is_flagged(self):
        res = vacuity_mod.vacuity(CONTROLS / "phi_dead.sol", TOKEN, 20000, 300)
        self.assertEqual(res["flagged"], ["check_dead"])

    def test_top_is_satisfiable(self):
        res = vacuity_mod.vacuity(SPECS / "phi_top.sol", TOKEN, 20000, 300)
        self.assertEqual([r["pre"] for r in res["rows"]], ["satisfiable"])

    def test_owner_must_revert_check_is_not_flagged(self):
        # check_mint_nonowner_no_supply_change has an unreachable assert on b by
        # design; check (a) tests Pre only, so it must not be flagged.
        res = vacuity_mod.vacuity(SPECS / "phi_owner.sol", TOKEN, 20000, 300)
        self.assertEqual({r["check"]: r["pre"] for r in res["rows"]},
                         {c: "satisfiable" for c in checks_of(SPECS / "phi_owner.sol")})

    def test_cli_exit_codes(self):
        self.assertEqual(run_cli(vacuity_mod.main, CONTROLS / "phi_dead.sol")[0], 3)
        self.assertEqual(run_cli(vacuity_mod.main, SPECS / "phi_top.sol")[0], 0)


class LadderStructure(unittest.TestCase):
    def test_every_spec_lints(self):
        for p in sorted(SPECS.glob("*.sol")) + sorted(CONTROLS.glob("*.sol")):
            self.assertEqual(speclint.lint_spec(p.read_text()), [], p.name)

    def test_unions_are_textual(self):
        owner, cap, transfer = (checks_of(SPECS / f"{n}.sol") for n in ("phi_owner", "phi_cap", "phi_transfer"))
        self.assertEqual(checks_of(SPECS / "phi_both.sol"), {**owner, **cap})
        shared = set(owner) & set(transfer)
        self.assertEqual(shared, {"check_transfer_keeps_supply"})
        self.assertEqual(owner["check_transfer_keeps_supply"], transfer["check_transfer_keeps_supply"])
        self.assertEqual(checks_of(SPECS / "phi_full.sol"), {**owner, **cap, **transfer})


class BareViolationMessage(unittest.TestCase):
    def test_happens_here_without_counterexample_is_refute(self):
        doc = json.loads((FIXTURES / "smt" / "counterexample.json").read_text())
        for e in doc["output"]["errors"]:
            if e["message"].startswith(core.MSG_VIOLATED):
                e["message"] = core.MSG_VIOLATED
        verdict, reason, targets, _ = core.classify_smt_output(doc["output"], doc["sources"])
        self.assertEqual((verdict, reason), ("Refute", "violation_without_counterexample"))
        self.assertIsNone(targets[0]["counterexample"])


if __name__ == "__main__":
    unittest.main()
