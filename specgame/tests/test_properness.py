"""properness: identity rejection, exclusion reasons, re-checked pairs, duplicate
flags, determinism, and that the committed mutants/mutants.json is current."""
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests._util import ROOT, TOKEN, core
import properness

MUTANTS = ROOT / "subjects" / "capped_token" / "mutants"
M01 = MUTANTS / "m01_mint_no_owner.sol"
M02 = MUTANTS / "m02_mint_no_cap.sol"
HEADER = "// operator: test\n// fault_class: test\n"
BUDGET = 150


def variant(src: Path, old: str, new: str, header: str = HEADER) -> str:
    text = src.read_text()
    assert text.count(old) == 1, old
    return header + text.replace(old, new)


class Properness(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def put(self, name: str, text: str) -> Path:
        p = self.dir / name
        p.write_text(text)
        return p

    def build(self, *paths: Path) -> tuple[dict, dict]:
        return properness.build(TOKEN, list(paths), seed=0, budget=BUDGET)

    def by_path(self, log: dict) -> dict:
        return {Path(r["path"]).name: r for r in log["mutants"]}

    def test_comment_only_change_is_rejected_by_runtime_hash(self):
        p = self.put("m90_comment.sol", variant(TOKEN, "/// Only the owner mints", "/// Only the owner (and nobody else) mints"))
        self.assertNotEqual(core.sha256_file(p), core.sha256_file(TOKEN))
        doc, log = self.build(p)
        self.assertEqual(doc["mutants"], [])
        r = self.by_path(log)["m90_comment.sol"]
        self.assertEqual((r["status"], r["reason"]), ("rejected", "runtime_sha256_equals"))
        self.assertEqual(r["id"], doc["base"]["runtime_sha256"])
        self.assertEqual(log["rejected"][0]["reason"], "runtime_sha256_equals")

    def test_same_bytecode_as_another_mutant_is_rejected(self):
        a = self.put("m91_a.sol", HEADER + M01.read_text())
        b = self.put("m92_b.sol", HEADER + M01.read_text().replace("// fault:", "// fault (copy):"))
        doc, log = self.build(a, b)
        self.assertEqual([m["path"] for m in doc["mutants"]], [properness.rel(a)])
        r = self.by_path(log)["m92_b.sol"]
        self.assertEqual((r["status"], r["equals"]), ("rejected", properness.rel(a)))

    def test_known_proper_mutant_gets_a_rechecked_pair(self):
        doc, log = self.build(M01)
        (m,) = doc["mutants"]
        self.assertEqual(m["status"], "included")
        self.assertEqual((m["operator"], m["fault_class"]), ("remove-modifier", "access-control"))
        self.assertEqual(m["id"], core.compile_artifact(M01)["runtime_sha256"])
        sigma = m["properness"]["sigma"]
        core.validate_sigma(sigma)
        self.assertNotIn("probe", sigma)
        # independent re-check here: the stored hashes are the observations
        ob = core.run_sequence(core.compile_artifact(TOKEN), sigma)
        om = core.run_sequence(core.compile_artifact(M01), sigma)
        self.assertFalse(core.observation_equal(ob, om))
        self.assertEqual((ob.sha256(), om.sha256()),
                         (m["properness"]["obs_base_sha256"], m["properness"]["obs_mutant_sha256"]))
        pair = self.by_path(log)["m01_mint_no_owner.sol"]["pair"]
        self.assertEqual(pair["replay1"], pair["replay2"])
        self.assertGreaterEqual(self.by_path(log)["m01_mint_no_owner.sol"]["sigmas_tried"], 1)

    def test_equivalent_with_different_bytecode_is_excluded(self):
        # Only a revert message differs: proper bytecode, but revert payloads are
        # not observed (protocol.md section 6), so no pair exists.
        p = self.put("m93_msg.sol", variant(TOKEN, '"insufficient balance"', '"low balance"'))
        doc, log = self.build(p)
        (m,) = doc["mutants"]
        self.assertNotEqual(m["id"], doc["base"]["runtime_sha256"])
        self.assertEqual((m["status"], m["exclusion_reason"], m["properness"]),
                         ("excluded", "no_properness_pair", None))
        self.assertEqual(self.by_path(log)["m93_msg.sol"]["sigmas_tried"], BUDGET)
        self.assertEqual(log["excluded"], [{"path": m["path"], "id": m["id"], "reason": "no_properness_pair"}])

    def test_abi_change_is_excluded(self):
        p = self.put("m94_abi.sol", variant(TOKEN, "    constructor(uint256 cap_) {",
                                            "    function burn() public {}\n\n    constructor(uint256 cap_) {"))
        doc, _ = self.build(p)
        self.assertEqual(doc["mutants"][0]["exclusion_reason"], "abi_differs")

    def test_lint_failure_is_excluded(self):
        p = self.put("m95_lint.sol", variant(TOKEN, "        totalSupply += amount;\n",
                                             "        totalSupply += amount;\n        assert(totalSupply <= cap);\n"))
        doc, log = self.build(p)
        self.assertEqual(doc["mutants"][0]["exclusion_reason"], "lint")
        self.assertTrue(any("A3" in d for d in self.by_path(log)["m95_lint.sol"]["detail"]))

    def test_constructor_revert_is_excluded_as_does_not_deploy(self):
        # The revert message change only makes the runtime differ from b's (see
        # the next test); the first observable difference is the failed deploy.
        text = variant(TOKEN, "        cap = cap_;\n", '        require(cap_ != 0, "zero cap");\n        cap = cap_;\n')
        p = self.put("m98_ctor.sol", text.replace('"insufficient balance"', '"low balance"'))
        doc, log = self.build(p)
        self.assertEqual(doc["mutants"][0]["exclusion_reason"], "does_not_deploy")
        self.assertIsNone(doc["mutants"][0]["properness"])
        self.assertTrue(self.by_path(log)["m98_ctor.sol"]["pair"]["first_difference"].startswith("deploy:"))

    def test_constructor_only_fault_has_b_identity(self):
        # Known gap of "id = runtime sha256" (protocol.md section 10): a fault
        # only in the constructor (here cap = cap_ + 1) changes behaviour but
        # not the runtime bytecode, so it is rejected as b itself.
        p = self.put("m99_ctor_cap.sol", variant(TOKEN, "        cap = cap_;\n", "        cap = cap_ + 1;\n"))
        sigma = {"version": 1, "deployer": "alice", "ctor": {"cap": "5"}, "txs": []}
        self.assertFalse(core.observation_equal(core.run_sequence(core.compile_artifact(TOKEN), sigma),
                                                core.run_sequence(core.compile_artifact(p), sigma)))
        doc, log = self.build(p)
        self.assertEqual(doc["mutants"], [])
        self.assertEqual(self.by_path(log)["m99_ctor_cap.sol"]["reason"], "runtime_sha256_equals")

    def test_missing_header_is_a_build_error(self):
        p = self.put("m96_nohdr.sol", TOKEN.read_text().replace("<= cap,", "<= cap + 2,"))
        with self.assertRaises(properness.BuildError):
            self.build(p)

    def test_behavioural_duplicates_are_flagged_not_merged(self):
        # m02 and a copy differing only in a revert message: distinct ids, equal
        # observations on every sigma.
        twin = self.put("m97_twin.sol", variant(M02, '"insufficient balance"', '"low balance"', header=""))
        doc, log = self.build(M02, twin)
        a, b = doc["mutants"]
        self.assertEqual((a["status"], b["status"]), ("included", "included"))
        self.assertEqual(a["behavioural_duplicate_of"], [b["id"]])
        self.assertEqual(b["behavioural_duplicate_of"], [a["id"]])
        (check,) = log["duplicate_checks"]
        self.assertTrue(check["duplicate"])
        self.assertFalse(check["separation"]["separated"])

    def test_build_is_deterministic(self):
        d1, l1 = self.build(M01, M02)
        d2, l2 = self.build(M01, M02)
        self.assertEqual(properness.dump(d1), properness.dump(d2))
        self.assertEqual(properness.dump(l1), properness.dump(l2))

    def test_committed_library_is_current(self):
        """mutants/mutants.json equals a rebuild with the defaults of mk/wp12.mk."""
        mk = (ROOT / "mk" / "wp12.mk").read_text()
        for var, val in (("PROPERNESS_SEED", properness.DEFAULT_SEED),
                         ("PROPERNESS_BUDGET", properness.DEFAULT_BUDGET),
                         ("PROPERNESS_MAX_TXS", properness.seqgen.DEFAULT_MAX_TXS)):
            self.assertRegex(mk, rf"(?m)^{var}\s+\?=\s+{val}$")
        doc, log = properness.build(TOKEN, sorted(MUTANTS.glob("m*.sol")))
        self.assertEqual(properness.dump(doc), (MUTANTS / "mutants.json").read_text(),
                         "stale: run `make mutants`")
        self.assertEqual(log["summary"]["rejected"], 0)
        for m in json.loads((MUTANTS / "mutants.json").read_text())["mutants"]:
            self.assertEqual(m["status"], "included", m["path"])
            core.validate_sigma(m["properness"]["sigma"])


if __name__ == "__main__":
    unittest.main()
