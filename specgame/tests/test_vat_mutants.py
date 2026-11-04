"""Vat mutant library: every mutant is a lint-clean, ABI-identical artifact
with its own runtime id, and its fault is reachable from the profile's setup
state on the hand-written σ stated in its header (replayed here with the
core, independently of the generator's coverage)."""
import unittest

from tests._util import ROOT, core

VAT = ROOT / "subjects" / "vat"
SUBJ = core.load_subject("vat")
FROB = "frob(bytes32,address,address,address,int256,int256)"
FILE3 = "file(bytes32,bytes32,uint256)"
WAD, RAY, RAD = 10**18, 10**27, 10**45
D = "carol"  # deployer = the only ward in these sigmas


def tx(sender, fn, *args):
    return {"sender": sender, "fn": fn, "args": [str(a) for a in args]}


# mutant -> (txs after the setup, index of the tx where b and the mutant first differ)
REACH = {
    "m01_slip_no_auth": ([tx("alice", "slip(bytes32,address,int256)", "GOLD", "alice", 1)], 0),
    "m02_frob_no_consent_v": ([tx("alice", FROB, "GOLD", "alice", "carol", "alice", 1, 0)], 0),
    "m03_frob_no_ceiling": ([tx(D, FILE3, "GOLD", "line", 0),
                             tx("alice", FROB, "GOLD", "alice", "alice", "alice", 1, 1)], 1),
    "m04_frob_no_safety": ([tx("alice", FROB, "GOLD", "alice", "alice", "alice", 0, 51 * WAD)], 0),
    "m05_frob_no_dust": ([tx(D, FILE3, "GOLD", "dust", 1000 * RAD),
                          tx("alice", FROB, "GOLD", "alice", "alice", "alice", 1, 1)], 1),
    "m06_fold_no_debt": ([tx("alice", FROB, "GOLD", "alice", "alice", "alice", 1, 1),
                          tx(D, "fold(bytes32,address,int256)", "GOLD", "bob", 1)], None),
    "m07_move_no_debit": ([tx("alice", "move(address,address,uint256)", "alice", "bob", 1)], None),
    "m08_grab_no_vice": ([tx("alice", FROB, "GOLD", "alice", "alice", "alice", 1, 1),
                          tx(D, "grab(bytes32,address,address,address,int256,int256)",
                             "GOLD", "alice", "bob", "carol", -1, -1)], None),
}


def sigma(txs):
    return {"version": 1, "deployer": D, "ctor": {}, "setup": core.setup_for(SUBJ, D), "txs": txs}


class VatMutants(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.b = core.compile_artifact(VAT / "Vat.sol", subject=SUBJ)

    def test_library_files(self):
        files = sorted(p.stem for p in (VAT / "mutants").glob("m*.sol"))
        self.assertEqual(files, sorted(REACH))

    def test_lint_abi_and_identity(self):
        import speclint
        ids = {self.b["runtime_sha256"]}
        for name in sorted(REACH):
            p = VAT / "mutants" / f"{name}.sol"
            self.assertEqual(speclint.lint_artifact(p.read_text(), SUBJ), [], name)
            e = core.compile_artifact(p, subject=SUBJ)
            self.assertEqual(e["abi"], self.b["abi"], name)
            self.assertNotIn(e["runtime_sha256"], ids, name)
            ids.add(e["runtime_sha256"])
            text = p.read_text()
            for label in ("// operator:", "// fault_class:", "// fault:", "// reachable:"):
                self.assertIn(label, text, name)

    def test_fault_reachable_from_setup(self):
        for name, (txs, at) in sorted(REACH.items()):
            with self.subTest(name):
                s = sigma(txs)
                core.validate_sigma(s, subject=SUBJ)
                m = core.compile_artifact(VAT / "mutants" / f"{name}.sol", subject=SUBJ)
                ob, om = core.run_sequence(self.b, s), core.run_sequence(m, s)
                self.assertFalse(core.observation_equal(ob, om))
                # every setup tx succeeds on both
                n = len(SUBJ.setup)
                for o in (ob, om):
                    steps = o.data["txs"][:n] if "setup" not in o.data else o.data["setup"]
                    self.assertTrue(all(x["outcome"] == "success" for x in steps), name)
                tb = ob.data["txs"][-len(txs):]
                tm = om.data["txs"][-len(txs):]
                if at is None:
                    # same outcomes, the fault shows in the post-state only
                    self.assertEqual(tb, tm)
                    self.assertNotEqual(ob.data["state"], om.data["state"])
                else:
                    self.assertEqual(tb[:at], tm[:at])
                    self.assertEqual((tb[at]["outcome"], tm[at]["outcome"]), ("pre_unmet", "success"), name)

    def test_setup_state_hides_ceiling_and_dust_faults(self):
        # The header claims: without a prior ward tx, the same frob behaves equally on b and m03 / m05.
        s = sigma([tx("alice", FROB, "GOLD", "alice", "alice", "alice", 1, 1)])
        for name in ("m03_frob_no_ceiling", "m05_frob_no_dust"):
            m = core.compile_artifact(VAT / "mutants" / f"{name}.sol", subject=SUBJ)
            self.assertTrue(core.observation_equal(core.run_sequence(self.b, s), core.run_sequence(m, s)), name)


if __name__ == "__main__":
    unittest.main()
