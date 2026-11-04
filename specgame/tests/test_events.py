"""events: set relations on hand-made kill sets, the events document, pools,
and kill sets computed by replay (Prop. 6.3 on a small real pool)."""
import unittest

from tests._util import ROOT, TOKEN, core
import adversary
import events
import verify

SPECS = ROOT / "subjects" / "capped_token" / "specs"
A, B, C, D = ("a" * 64, "b" * 64, "c" * 64, "d" * 64)


class Relations(unittest.TestCase):
    def test_four_kinds(self):
        self.assertEqual(events.relation({A, B}, {A}), {"kind": "weakening", "lost": [B], "gained": []})
        self.assertEqual(events.relation({A}, {A, B}), {"kind": "strengthening", "lost": [], "gained": [B]})
        self.assertEqual(events.relation({A, B}, {A, C}), {"kind": "shift", "lost": [B], "gained": [C]})
        self.assertEqual(events.relation({A, B}, {B, A}), {"kind": "unchanged", "lost": [], "gained": []})
        self.assertEqual(events.relation(set(), set())["kind"], "unchanged")
        self.assertEqual(events.relation({A}, set())["kind"], "weakening")
        self.assertEqual(events.relation(set(), {A})["kind"], "strengthening")

    def test_trajectory_document(self):
        M = [D, C, B, A]
        rounds = [{"t": 0, "phi_source_sha256": A, "acc": "Accept", "kill_set": [A, B]},
                  {"t": 1, "phi_source_sha256": B, "acc": "Unknown", "kill_set": [A]},
                  {"t": 2, "phi_source_sha256": C, "acc": "lint_rejected", "kill_set": []},
                  {"t": 3, "phi_source_sha256": D, "acc": "Refute", "kill_set": [C, D]}]
        doc = events.trajectory("f0", 1, M, [], rounds)
        self.assertEqual(verify.SchemaValidator(verify.SCHEMA_DIR).validate(doc, "events.schema.json"), [])
        self.assertEqual([e["kind"] for e in doc["events"]], ["weakening", "weakening", "strengthening"])
        self.assertEqual([e["acc_t"] for e in doc["events"]], ["Accept", "Unknown", "lint_rejected"])
        self.assertEqual(doc["events"][0]["lost"], [B])
        self.assertEqual(doc["rounds"][3]["ms_cert"], {"killed": 2, "total": 4})
        self.assertEqual(doc["M"], sorted(M))
        with self.assertRaises(events.EventsError):
            events.trajectory("f0", 1, M, [], [{"t": 0, "phi_source_sha256": A, "acc": "lint_rejected",
                                                "kill_set": [A]}])
        with self.assertRaises(events.EventsError):
            events.trajectory("f0", 1, [A], [], [{"t": 0, "phi_source_sha256": A, "acc": "Accept",
                                                  "kill_set": [B]}])

    def test_pool_dedup_and_hash(self):
        s = {"version": 1, "deployer": "alice", "ctor": {"cap": "1"}, "txs": []}
        w1 = {"mutant": A, "sigma": s, "observed": {"check": "check_x"}}
        w2 = {"mutant": A, "sigma": dict(s), "observed": {"check": "check_y"}}
        w3 = {"mutant": B, "sigma": s, "observed": {}}
        p = events.pool_from([[w3, w1], [w2]])
        self.assertEqual(p, [{"mutant": A, "sigma": s}, {"mutant": B, "sigma": s}])
        self.assertEqual(events.pool_sha256(p), events.pool_sha256(list(reversed(p))))


class ReplayedKillSets(unittest.TestCase):
    def test_kill_sets_by_replay_and_conjunction(self):
        ms = events.load_mutants(ROOT / "subjects" / "capped_token" / "mutants" / "mutants.json")
        by = {m["name"]: m for m in ms}
        sub = [by["m01_mint_no_owner"], by["m02_mint_no_cap"]]
        w_owner, _ = adversary.search(SPECS / "phi_owner.sol", sub, TOKEN, budget=40)
        w_cap, _ = adversary.search(SPECS / "phi_cap.sol", sub, TOKEN, budget=40)
        pool = events.pool_from([w_owner, w_cap])
        sc = events.Scorer(ms)
        k_owner = sc.kill_set(SPECS / "phi_owner.sol", pool)[0]
        k_cap = sc.kill_set(SPECS / "phi_cap.sol", pool)[0]
        k_both = sc.kill_set(SPECS / "phi_both.sol", pool)[0]
        self.assertEqual(k_owner, [by["m01_mint_no_owner"]["id"]])
        self.assertEqual(k_cap, [by["m02_mint_no_cap"]["id"]])
        self.assertEqual(k_both, sorted(set(k_owner) | set(k_cap)))
        self.assertEqual(sc.kill_set(SPECS / "phi_top.sol", pool)[0], [])
        # restricting M' to m01 (Prop. 6.2 measurement shape)
        mp = {by["m01_mint_no_owner"]["id"]}
        self.assertEqual(sc.kill_set(SPECS / "phi_cap.sol", pool, restrict=mp)[0], [])


if __name__ == "__main__":
    unittest.main()


class LadderConfigs(unittest.TestCase):
    def test_vat_relations(self):
        cfg = events.LADDERS["vat"]
        specs, nest = cfg["specs"], set(cfg["nesting"])
        self.assertEqual((specs[0], specs[-1]), ("phi_top", "phi_full"))
        for r in specs[1:-1]:
            self.assertIn(("phi_top", r), nest)
            self.assertIn((r, "phi_full"), nest)
            self.assertTrue((SPECS.parent.parent / "vat" / "specs" / f"{r}.sol").is_file(), r)
        a, b, ab = cfg["prop63"]
        self.assertEqual((a, b, ab), ("phi_frob", "phi_frob_guards", "phi_frob_both"))
        self.assertIn((a, ab), nest)
        self.assertIn((b, ab), nest)
        self.assertIsNone(cfg["prop62"])

    def test_capped_token_ladder_unchanged(self):
        cfg = events.LADDERS["capped_token"]
        self.assertEqual(cfg["specs"], events.LADDER)
        self.assertEqual(cfg["nesting"], events.NESTING)
        self.assertEqual(cfg["prop63"], ("phi_owner", "phi_cap", "phi_both"))
