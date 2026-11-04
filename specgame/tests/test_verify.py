"""Verifier (tools/verify.py): HOLDS on the fixture bundle; every tamper kind of
tests/fixtures/bundle/tamper.py is refused (or could-not-verify) with the
named failing step; the CLI exit codes."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._util import FIXTURES, ROOT

sys.path.insert(0, str(FIXTURES / "bundle"))
import tamper  # noqa: E402
import verify  # noqa: E402

GOOD = FIXTURES / "bundle" / "good"


class Fixture(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        # Verify a copy outside the workspace tree, as on a second machine.
        cls.bundle = Path(cls.tmp.name) / "good"
        shutil.copytree(GOOD, cls.bundle)
        cls.rep = verify.verify(cls.bundle)
        cls.m = json.loads((GOOD / "manifest.json").read_text())

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_holds(self):
        self.assertEqual((self.rep["verdict"], self.rep["exit_code"]), ("HOLDS", 0), verify.summary(self.rep))
        self.assertEqual([(s["step"], s["status"]) for s in self.rep["steps"]],
                         [(i, "pass") for i in range(7)])

    def test_recomputed_score(self):
        self.assertEqual(self.rep["ms_cert"], {"killed": 2, "total": 3})
        self.assertEqual(self.rep["kill_set"], self.m["claimed"]["kill_set"])
        survivors = [e["id"] for e in self.m["evidence"]["M"] if e["id"] not in self.m["claimed"]["kill_set"]]
        self.assertEqual(self.rep["mutants_without_valid_witness"], survivors)
        self.assertEqual([d["by"] for d in self.rep["discarded"]], ["producer"])

    def test_labels_are_reported_not_used(self):
        self.assertEqual(self.rep["labels"], self.m["metadata"]["mutants"])

    def test_cli_exit_code(self):
        out = Path(self.tmp.name) / "report.json"
        p = subprocess.run([sys.executable, "-I", "-B", str(ROOT / "tools" / "verify.py"), str(self.bundle),
                            "--json", str(out)], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertIn("verdict: HOLDS, exit 0", p.stdout)
        self.assertEqual(json.loads(out.read_text())["ms_cert"], {"killed": 2, "total": 3})

    def test_missing_bundle_is_could_not_verify(self):
        self.assertEqual(verify.main([str(Path(self.tmp.name) / "nope"), "--quiet"]), 2)


class Tamper(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.reps = {}
        for kind in tamper.KINDS:
            d = tamper.make(GOOD, kind, Path(cls.tmp.name) / kind)
            cls.reps[kind] = verify.verify(d)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_every_kind(self):
        for kind, (_, code, first, failing) in tamper.KINDS.items():
            with self.subTest(kind=kind):
                rep = self.reps[kind]
                self.assertEqual(rep["exit_code"], code, verify.summary(rep))
                self.assertEqual(rep["first_failing_step"], first, verify.summary(rep))
                self.assertEqual(set(rep["failing_steps"]), failing, verify.summary(rep))

    def step(self, kind: str, n: int) -> dict:
        return next(s for s in self.reps[kind]["steps"] if s["step"] == n)

    def test_swapped_bytecode_is_caught_by_properness_not_by_a_hash(self):
        s1, s3 = self.step("swapped_bytecode", 1), self.step("swapped_bytecode", 3)
        self.assertEqual(s1["status"], "pass")  # every hash is consistent
        bad = [d for d in s3["mutants"] if d["properness"] is False]
        self.assertEqual(len(bad), 1)
        self.assertTrue(bad[0]["id_matches_source"])  # the id recomputes fine
        self.assertTrue(all(not p["differs"] for p in bad[0]["pairs"]))

    def test_swapped_witness_discards_both(self):
        rep = self.reps["swapped_witness"]
        self.assertEqual(rep["ms_cert"], {"killed": 0, "total": 3})
        self.assertEqual(sum(d["by"] == "verifier" for d in rep["discarded"]), 2)

    def test_error_string_probe_is_discarded_and_score_drops(self):
        rep = self.reps["error_string_probe"]
        ver = [d for d in rep["discarded"] if d["by"] == "verifier"]
        self.assertEqual(len(ver), 1)
        self.assertIn('Error("cap exceeded") -> pre_unmet', ver[0]["reason"])
        self.assertEqual(rep["ms_cert"], {"killed": 1, "total": 3})

    def test_edited_claim_names_both_numbers(self):
        self.assertIn("claimed ms_cert 3/3 != recomputed 2/3", self.step("edited_ms_cert", 5)["details"][0])

    def test_v_completeness_named_at_step_6(self):
        self.assertIn("V-completeness claim present", self.step("v_completeness_claim", 6)["details"][0])

    def test_flipped_byte_names_the_file(self):
        self.assertTrue(any("sha256 mismatch: phi/Spec.sol" in d for d in self.step("flipped_spec_byte", 1)["details"]))

    def test_refuted_spec_is_refuted_by_the_solver(self):
        self.assertTrue(any(d.startswith("Check(b, phi) = Refute on re-run")
                            for d in self.step("refuted_spec", 2)["details"]))

    def test_unlisted_file_is_refused(self):
        d = Path(self.tmp.name) / "extra"
        shutil.copytree(GOOD, d)
        (d / "mutants" / "extra.sol").write_text("// not listed\n")
        rep = verify.verify(d)
        self.assertEqual((rep["exit_code"], rep["first_failing_step"]), (3, 1))

    def test_unanticipated_exception_is_could_not_verify(self):
        # A mutant source that is not UTF-8, with every hash consistent: the
        # compile step raises; the verifier records it, never crashes or passes.
        d = Path(self.tmp.name) / "nonutf8"
        shutil.copytree(GOOD, d)
        m = tamper._load(d)
        p = d / m["evidence"]["M"][0]["path"]
        p.write_bytes(p.read_bytes() + b"// \xff\xfe\n")
        tamper._rehash(d, m)
        tamper._save(d, m)
        rep = verify.verify(d)
        self.assertEqual((rep["exit_code"], rep["first_failing_step"]), (2, 3))
        self.assertIn("internal error: UnicodeDecodeError", self.step_of(rep, 3)["details"][0])

    @staticmethod
    def step_of(rep: dict, n: int) -> dict:
        return next(s for s in rep["steps"] if s["step"] == n)


if __name__ == "__main__":
    unittest.main()
