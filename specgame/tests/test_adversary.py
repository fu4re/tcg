"""adversary: determinism, the replay gate, witness shape, the m08 survivor."""
import json
import unittest
from pathlib import Path
from unittest import mock

from tests._util import ROOT, TOKEN, core
import adversary

import verify

SPECS = ROOT / "subjects" / "capped_token" / "specs"
MUTANTS = adversary.included_mutants(ROOT / "subjects" / "capped_token" / "mutants" / "mutants.json")
BY_NAME = {m["name"]: m for m in MUTANTS}


class Adversary(unittest.TestCase):
    def test_same_seed_same_W(self):
        ms = [BY_NAME["m02_mint_no_cap"], BY_NAME["m03_mint_cap_off_by_one"], BY_NAME["m01_mint_no_owner"]]
        w1, l1 = adversary.search(SPECS / "phi_cap.sol", ms, TOKEN, seed=0, budget=60)
        w2, l2 = adversary.search(SPECS / "phi_cap.sol", ms, TOKEN, seed=0, budget=60)
        self.assertEqual(core.canonical_json(w1), core.canonical_json(w2))
        self.assertEqual([m["sigmas_tried"] for m in l1["mutants"]], [m["sigmas_tried"] for m in l2["mutants"]])
        self.assertEqual(l1["adversary_id"], l2["adversary_id"])
        self.assertEqual(sorted(w["mutant"] for w in w1), sorted([ms[0]["id"], ms[1]["id"]]))
        w3, _ = adversary.search(SPECS / "phi_cap.sol", ms, TOKEN, seed=1, budget=60)
        self.assertNotEqual(core.canonical_json(w1), core.canonical_json(w3))

    def test_witnesses_are_schema_valid_and_replay(self):
        W, log = adversary.search(SPECS / "phi_owner.sol", [BY_NAME["m01_mint_no_owner"]], TOKEN, budget=50)
        (w,) = W
        val = verify.SchemaValidator(verify.SCHEMA_DIR)
        self.assertEqual(val.validate(w, "witness.schema.json"), [])
        self.assertEqual(w["sigma"]["probe"]["check"], w["observed"]["check"])
        entry = core.compile_spec_over(SPECS / "phi_owner.sol", BY_NAME["m01_mint_no_owner"]["path"])
        self.assertEqual(w["observed"]["pair_runtime_sha256"], entry["runtime_sha256"])
        ev = core.evaluate_witness(entry, w["sigma"])
        self.assertTrue(ev.violated)
        self.assertEqual(ev.outcomes[w["observed"]["check"]], "violation")
        self.assertEqual(log["discarded"], [])

    def test_replay_gate_rejects_a_non_violating_pair(self):
        # The owner mints within the cap: no check of phi_cap panics on m01.
        sigma = {"version": 1, "deployer": "alice", "ctor": {"cap": "10"},
                 "txs": [{"sender": "alice", "fn": "mint(address,uint256)", "args": ["bob", "3"]}],
                 "probe": {"sender": "alice", "a": "bob", "b": "zero", "x": "1", "y": "0"}}
        g = adversary.replay_gate(SPECS / "phi_cap.sol", BY_NAME["m01_mint_no_owner"]["path"], sigma)
        self.assertFalse(g["kept"])
        self.assertNotIn("violation", g["outcomes"].values())

    def test_search_discards_a_candidate_that_fails_the_replay(self):
        # First evaluation forged as a violation; the gate's real replay must discard it.
        real = core.evaluate_witness
        calls = {"n": 0}

        def forged(entry, sigma):
            calls["n"] += 1
            ev = real(entry, sigma)
            if calls["n"] == 1:
                return core.WitnessEval(True, {k: "violation" for k in ev.outcomes}, True, [])
            return ev
        m08 = BY_NAME["m08_mint_always_reverts"]
        with mock.patch.object(adversary.core, "evaluate_witness", side_effect=forged):
            W, log = adversary.search(SPECS / "phi_cap.sol", [m08], TOKEN, budget=3)
        self.assertEqual(W, [])
        (d,) = log["discarded"]
        self.assertEqual((d["mutant"], d["sigma_index"]), (m08["id"], 0))
        self.assertTrue(d["reason"].startswith("replay gate"))
        self.assertEqual(log["kill_set"], [])

    def test_m08_survives_phi_full_within_budget(self):
        m08 = BY_NAME["m08_mint_always_reverts"]
        W, log = adversary.search(SPECS / "phi_full.sol", [m08], TOKEN)
        self.assertEqual(W, [])
        self.assertEqual(log["mutants"][0]["sigmas_tried"], adversary.DEFAULT_BUDGET)
        self.assertNotIn("violation", log["mutants"][0]["check_outcome_counts"])

    def test_adversary_id(self):
        fns = ["mint(address,uint256)", "transfer(address,uint256)"]
        p = adversary.params(0, 2000, 6, 1, fns)
        self.assertEqual(adversary.adversary_id(p), adversary.adversary_id(json.loads(json.dumps(p))))
        self.assertNotEqual(adversary.adversary_id(p), adversary.adversary_id(adversary.params(0, 1999, 6, 1, fns)))
        self.assertNotEqual(adversary.adversary_id(p), adversary.adversary_id(adversary.params(1, 2000, 6, 1, fns)))
        # the id does not depend on the spec: the same A plays against every phi
        _, l1 = adversary.search(SPECS / "phi_top.sol", [BY_NAME["m01_mint_no_owner"]], TOKEN, budget=2)
        _, l2 = adversary.search(SPECS / "phi_cap.sol", [BY_NAME["m01_mint_no_owner"]], TOKEN, budget=2)
        self.assertEqual(l1["adversary_id"], l2["adversary_id"])


if __name__ == "__main__":
    unittest.main()
