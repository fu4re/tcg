"""Deterministic executor: σ validation, run_sequence determinism, properness
observation, witness evaluation."""
import copy
import re
import tempfile
import unittest
from pathlib import Path

from tests._util import FALSE, TOKEN, core

MINT = "mint(address,uint256)"
TRANSFER = "transfer(address,uint256)"
SIGMA = {
    "version": 1, "deployer": "alice", "ctor": {"cap": "100"},
    "txs": [
        {"sender": "alice", "fn": MINT, "args": ["bob", "60"]},
        {"sender": "bob", "fn": TRANSFER, "args": ["carol", "25"]},
        {"sender": "carol", "fn": MINT, "args": ["carol", "1"]},
        {"sender": "alice", "fn": MINT, "args": ["zero", "41"]},
    ],
    "probe": {"sender": "bob", "a": "carol", "b": "zero", "x": "7", "y": "0", "check": "check_reachable"},
}


class Executor(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.token = core.compile_artifact(TOKEN)
        cls.spec = core.compile_spec_over(FALSE, TOKEN)
        # A mutant: the access control on mint removed.
        cls.tmp = tempfile.TemporaryDirectory()
        m = Path(cls.tmp.name) / "m_no_owner.sol"
        m.write_text(TOKEN.read_text().replace("public onlyOwner {", "public {"))
        cls.mutant = core.compile_artifact(m)

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_deterministic(self):
        o1 = core.run_sequence(self.token, SIGMA)
        o2 = core.run_sequence(self.token, copy.deepcopy(SIGMA))
        self.assertEqual(core.canonical_json(o1.data), core.canonical_json(o2.data))
        self.assertEqual(o1.log, o2.log)
        p1 = core.run_sequence(self.spec, SIGMA, probe_check="check_reachable")
        p2 = core.run_sequence(self.spec, SIGMA, probe_check="check_reachable")
        self.assertEqual(core.canonical_json(p1.data), core.canonical_json(p2.data))

    def test_observation_content(self):
        o = core.run_sequence(self.token, SIGMA)
        self.assertEqual([t["outcome"] for t in o.data["txs"]], ["success", "success", "pre_unmet", "pre_unmet"])
        self.assertEqual(o.data["txs"][1]["return"], "00" * 31 + "01")  # transfer returns true
        st = o.data["state"]
        self.assertEqual(int(st["totalSupply()"]["return"], 16), 60)
        self.assertEqual(int(st["balanceOf(address)[bob]"]["return"], 16), 35)
        self.assertEqual(int(st["balanceOf(address)[carol]"]["return"], 16), 25)
        self.assertEqual(sorted(st), sorted(["owner()", "cap()", "totalSupply()"] +
                                            [f"balanceOf(address)[{n}]" for n in core.POOL]))

    def test_properness_pair(self):
        ob = core.run_sequence(self.token, SIGMA)
        om = core.run_sequence(self.mutant, SIGMA)
        self.assertFalse(core.observation_equal(ob, om))  # carol's mint succeeds on the mutant
        quiet = {**SIGMA, "txs": SIGMA["txs"][:2]}
        self.assertTrue(core.observation_equal(core.run_sequence(self.token, quiet),
                                               core.run_sequence(self.mutant, quiet)))

    def test_witness_evaluation(self):
        w = core.evaluate_witness(self.spec, SIGMA)
        self.assertTrue(w.violated)
        self.assertEqual(w.outcomes, {"check_reachable": "violation"})
        pre = copy.deepcopy(SIGMA)
        pre["probe"]["x"] = "5"  # require(x > 5) fails: Pre unmet, not a witness
        w = core.evaluate_witness(self.spec, pre)
        self.assertFalse(w.violated)
        self.assertEqual(w.outcomes, {"check_reachable": "pre_unmet"})

    def test_failed_deploy_is_never_a_witness(self):
        spec = dict(self.spec)
        spec["bin"] = "60006000fd"  # init code: revert()
        w = core.evaluate_witness(spec, SIGMA)
        self.assertFalse(w.violated)
        self.assertFalse(w.deploy_ok)

    def test_sigma_validation(self):
        bad = {
            "extra key": {**SIGMA, "gas": "1"},
            "deployer not a sender": {**SIGMA, "deployer": "zero"},
            "uint as int": {**SIGMA, "ctor": {"cap": 100}},
            "uint leading zero": {**SIGMA, "ctor": {"cap": "0100"}},
            "uint overflow": {**SIGMA, "ctor": {"cap": str(2**256)}},
            "unknown address": {**SIGMA, "txs": [{"sender": "alice", "fn": MINT, "args": ["0x1234", "1"]}]},
            "tx calls a probe": {**SIGMA, "txs": [{"sender": "alice", "fn": "check_x(address,address,uint256,uint256)",
                                                   "args": ["alice", "alice", "1", "1"]}]},
            "arity": {**SIGMA, "txs": [{"sender": "alice", "fn": MINT, "args": ["bob"]}]},
            "unsupported type": {**SIGMA, "txs": [{"sender": "alice", "fn": "f(bool)", "args": ["true"]}]},
            "probe missing y": {**SIGMA, "probe": {"sender": "bob", "a": "carol", "b": "zero", "x": "7"}},
            "version": {**SIGMA, "version": 2},
        }
        for name, s in bad.items():
            with self.assertRaises(core.SigmaError, msg=name):
                core.validate_sigma(s)
        core.validate_sigma(SIGMA)
        no_probe = {k: v for k, v in SIGMA.items() if k != "probe"}
        core.validate_sigma(no_probe)
        with self.assertRaises(core.SigmaError):
            core.validate_sigma(no_probe, need_probe=True)

    def test_schema_example_is_valid_sigma(self):
        import json
        from tests._util import ROOT
        schema = json.loads((ROOT / "schemas" / "sigma.schema.json").read_text())
        for ex in schema["examples"]:
            core.validate_sigma(ex, need_probe=True)
        name = re.compile(schema["$defs"]["name"]["pattern"])
        for n in list(core.SENDERS) + list(core.POOL):
            self.assertTrue(name.match(n), n)

    def test_unknown_function_is_executor_error(self):
        s = {**SIGMA, "txs": [{"sender": "alice", "fn": "burn(uint256)", "args": ["1"]}]}
        with self.assertRaises(core.ExecutorError):
            core.run_sequence(self.token, s)


if __name__ == "__main__":
    unittest.main()
