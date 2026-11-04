"""Protocol v3: subject profiles, the typed generator, the relaxed artifact
lint on Vat, portdiff, and the capped token's byte-identity with protocol v2."""
import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tests._util import ROOT, core, speclint

import portdiff  # noqa: E402  (tools/ is on sys.path)
import seqgen  # noqa: E402

VAT = core.load_subject("vat")
CAPPED = core.load_subject("capped_token")
SHEAF_VAT = Path("/home/vladimir/sheaf/cycle/ground_truth/dss_vat/src/Vat.sol")
# sha256 of the canonical JSON of σ_0..σ_1999 (seed 0, max_txs 6) from the
# protocol v2 seqgen (git: feat/specgames before protocol v3).
V2_SIGMAS = {"none": "f9cc3ed65b1c672d3dd5786a3324db4f30621918e12149c200605c65636827f8",
             "probe": "6d216354a06492d407ea66c777385f2b906abef75b7b29097faf75221c608b6a"}


class Profiles(unittest.TestCase):
    def test_both_subjects_load_and_are_pinned(self):
        for s in (CAPPED, VAT):
            pin = core.PROTOCOL["subjects"][s.name]
            self.assertEqual(core.sha256_file(ROOT / pin["profile"]), pin["profile_sha256"])
        self.assertEqual((VAT.unit, VAT.contract, VAT.ctor_params), ("Vat.sol", "Vat", []))
        self.assertEqual(VAT.probe_sigs, ["(address,address,uint256,uint256)", "(bytes32,address,int256,int256)"])
        self.assertEqual(CAPPED.probe_sigs, ["(address,address,uint256,uint256)"])

    def test_pin_mismatch_is_refused(self):
        saved = copy.deepcopy(core.PROTOCOL["subjects"]["vat"])
        try:
            core.PROTOCOL["subjects"]["vat"]["profile_sha256"] = "0" * 64
            core._SUBJECTS.pop("vat", None)
            with self.assertRaises(core.ProfileError):
                core.load_subject("vat")
        finally:
            core.PROTOCOL["subjects"]["vat"] = saved
            core._SUBJECTS.pop("vat", None)
            core.load_subject("vat")

    def test_structural_rules(self):
        prof = copy.deepcopy(VAT.profile)
        prof["spec"]["probes"][1][0]["name"] = "a"  # collides with the first signature
        with self.assertRaises(core.ProfileError):
            core._check_profile(prof, "vat")
        prof = copy.deepcopy(VAT.profile)
        prof["senders"].append("mallory")
        with self.assertRaises(core.ProfileError):
            core._check_profile(prof, "vat")

    def test_capped_observation_keys_are_the_v2_ones(self):
        keys = [k for k, _, _ in core.observation_keys(CAPPED)]
        self.assertEqual(keys, ["owner()", "cap()", "totalSupply()"] +
                         [f"balanceOf(address)[{n}]" for n in ("alice", "bob", "carol", "zero")])


class TypedGenerator(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.entry = core.compile_artifact(VAT.source_path, subject=VAT)
        cls.fns = seqgen.tx_functions(cls.entry, VAT)

    def test_capped_sigmas_identical_to_v2(self):
        fns = seqgen.tx_functions(core.compile_artifact(CAPPED.source_path))
        a = [seqgen.gen_sigma(0, i, fns, 6) for i in range(2000)]
        b = [seqgen.gen_sigma(0, i, fns, 6, probe_checks=["check_a", "check_b"]) for i in range(2000)]
        self.assertEqual(core.json_sha256(a), V2_SIGMAS["none"])
        self.assertEqual(core.json_sha256(b), V2_SIGMAS["probe"])

    def test_deterministic_and_typed(self):
        sig = [seqgen.gen_sigma(3, i, self.fns, 6, ["check_x"], VAT) for i in range(300)]
        self.assertEqual(sig, [seqgen.gen_sigma(3, i, self.fns, 6, ["check_x"], VAT) for i in range(300)])
        ints, b32 = [], []
        for s in sig:
            core.validate_sigma(s, need_probe=True, subject=VAT)
            self.assertEqual(set(s["probe"]), {"sender", "a", "b", "x", "y", "i", "u", "dx", "dy", "check"})
            for tx in s["txs"]:
                for t, v in zip(core.sig_types(tx["fn"]), tx["args"]):
                    (ints if t == "int256" else b32 if t == "bytes32" else []).append(v)
        self.assertTrue(any(v.startswith("-") for v in ints))
        self.assertTrue(set(b32) <= set(VAT.pool("bytes32")))
        self.assertTrue(all(core.INT256_MIN <= int(v) <= core.INT256_MAX for v in ints))

    def test_setup_and_observation_run(self):
        s = seqgen.gen_sigma(0, 0, self.fns, 0, None, VAT)
        o = core.run_sequence(self.entry, s)
        self.assertEqual([x["outcome"] for x in o.data["setup"]], ["success"] * len(VAT.setup))
        self.assertEqual(len(o.data["state"]), len(core.observation_keys(VAT)))
        self.assertEqual(int(o.data["state"]["ilks(bytes32)[GOLD]"]["return"][64:128], 16), 10**27)  # rate after init

    def test_setup_is_part_of_sigma_and_enforced(self):
        s = seqgen.gen_sigma(0, 7, self.fns, 3, ["check_x"], VAT)
        self.assertEqual(s["setup"], core.setup_for(VAT, s["deployer"]))
        self.assertIn("setup", list(s)[:4])  # canonical position, hashed with the rest
        tampered = copy.deepcopy(s)
        tampered["setup"][2]["args"][1] = "1"
        with self.assertRaises(core.SigmaError):
            core.validate_sigma(tampered, need_probe=True, subject=VAT)
        missing = {k: v for k, v in s.items() if k != "setup"}
        with self.assertRaises(core.SigmaError):
            core.validate_sigma(missing, need_probe=True, subject=VAT)
        capped = seqgen.gen_sigma(0, 7, ["mint(address,uint256)", "transfer(address,uint256)"], 3)
        self.assertNotIn("setup", capped)
        with self.assertRaises(core.SigmaError):
            core.validate_sigma({**capped, "setup": []})

    def test_repeat_and_negate_unwind(self):
        unwinds = 0
        for i in range(600):
            s = seqgen.gen_sigma(0, i, self.fns, 6, None, VAT)
            vals = [int(v) for tx in s["txs"] for t, v in zip(core.sig_types(tx["fn"]), tx["args"]) if t == "int256"]
            unwinds += any(v != 0 and -v in vals for v in vals)
        self.assertGreater(unwinds, 0)
        gen = seqgen.distribution_id(self.fns, 6, VAT)["generator"]
        self.assertEqual(gen["kind"], "typed-v2")
        self.assertTrue({"repeat", "negate"} <= set(gen["int256"]) and {"repeat", "negate"} <= set(gen["uint256"]))

    def test_sigma_validation_is_typed(self):
        s = {"version": 1, "deployer": "alice", "ctor": {}, "setup": core.setup_for(VAT, "alice"),
             "txs": [{"sender": "alice", "fn": "slip(bytes32,address,int256)", "args": ["GOLD", "bob", "-5"]}]}
        core.validate_sigma(s, subject=VAT)
        for bad in (["GOLDEN", "bob", "-5"], ["GOLD", "bob", "05"], ["GOLD", "bob", str(2**255)], ["GOLD", "GOLD", "1"]):
            with self.assertRaises(core.SigmaError, msg=bad):
                core.validate_sigma({**s, "txs": [{**s["txs"][0], "args": bad}]}, subject=VAT)


class VatCoverage(unittest.TestCase):
    """Acceptance gate for the Vat adversary's σ stream (protocol v3): enough
    successful calls that a kill set is not a search artifact (Thm 8.4)."""
    GATE = {"frob(bytes32,address,address,address,int256,int256)": 0.25,
            "fork(bytes32,address,address,int256,int256)": 0.10,
            "grab(bytes32,address,address,address,int256,int256)": 0.10,
            "move(address,address,uint256)": 0.20,
            "fold(bytes32,address,int256)": 0.20,
            "slip(bytes32,address,int256)": 0.20,
            "flux(bytes32,address,address,uint256)": 0.20}

    def test_gate_2000_sigmas(self):
        doc = seqgen.coverage("vat", 2000, 0, 6)
        self.assertEqual(doc["setup_failures"], 0)
        for fn, floor in self.GATE.items():
            r = doc["per_function"][fn]
            self.assertGreaterEqual(r["successes"] / r["calls"], floor, f"{fn}: {r}")

    def test_hoped_follows_the_setup(self):
        setup = core.setup_for(VAT, "alice")
        self.assertEqual(seqgen.hoped_by(setup), {"bob": ["alice"], "carol": ["bob"]})


class VatKappa(unittest.TestCase):
    def test_committed_havoc_base_is_current(self):
        import kappa
        self.assertEqual(kappa.generate_havoc(VAT.source_path, subject=VAT),
                         (VAT.specs_dir / "havoc" / "Vat.sol").read_text(), "stale: run kappa.py --subject vat --write-havoc")

    def test_kappa_is_determined_on_the_measurement_spec(self):
        import kappa
        res = kappa.kappa(VAT.specs_dir / "measurement" / "vat_measure.sol", VAT.source_path, 2000, 120,
                          cache_dir=None, subject=VAT)
        self.assertTrue(res["determined"], res["check_over_H"])
        self.assertEqual(res["asserts"], 4)
        self.assertEqual(res["kappa"], 4)  # no assert of the measurement spec is a tautology over H


class VatLint(unittest.TestCase):
    def test_vat_is_accepted(self):
        self.assertEqual(speclint.lint_artifact(VAT.source_path.read_text(), VAT), [])

    @unittest.skipUnless(SHEAF_VAT.is_file(), "sheaf repo not present")
    def test_sheaf_port_with_external_functions_is_rejected(self):
        rules = {v.rule for v in speclint.lint_artifact(SHEAF_VAT.read_text(), VAT)}
        self.assertIn("A3", rules)

    def test_external_call_is_rejected(self):
        text = VAT.source_path.read_text().replace(
            "function cage() public auth {\n        live = 0;",
            'function cage() public auth {\n        (bool ok, ) = address(0).call("");\n        live = 0;')
        self.assertIn("A3", {v.rule for v in speclint.lint_artifact(text, VAT)})

    def test_measurement_spec_lints_and_struct_writes_are_caught(self):
        names = speclint.names_from_entry(core.compile_artifact(VAT.source_path, subject=VAT))
        spec = (VAT.specs_dir / "measurement" / "vat_measure.sol").read_text()
        self.assertEqual(speclint.lint_spec(spec, names, VAT), [])
        bad = spec.replace("uint256 total0 = ilks[i].Art;", "uint256 total0 = ilks[i].Art;\n        ilks[i].rate = 0;")
        self.assertIn("S7", {v.rule for v in speclint.lint_spec(bad, names, VAT)})
        wrong_sig = spec.replace("(bytes32 i, address u, int256 dx, int256 dy)", "(bytes32 i, address u, uint256 dx, int256 dy)")
        self.assertIn("S4", {v.rule for v in speclint.lint_spec(wrong_sig, names, VAT)})

    def test_pragma_ranges(self):
        for expr, ok in (("^0.8.0", True), ("0.8.35", True), (">=0.8.0 <0.9.0", True), ("^0.6.12", False),
                         ("0.8.34", False), (">=0.8.36", False)):
            self.assertEqual(speclint.pragma_admits(expr, "0.8.35"), ok, expr)


class PortDiff(unittest.TestCase):
    @unittest.skipUnless(SHEAF_VAT.is_file(), "sheaf repo not present")
    def test_equivalent_port(self):
        doc = portdiff.portdiff(SHEAF_VAT, VAT.source_path, VAT, 0, 40, 6)
        self.assertTrue(doc["equal"])

    def test_nonequivalent_edit_fails(self):
        with tempfile.TemporaryDirectory() as t:
            m = Path(t) / "Vat.sol"
            m.write_text(VAT.source_path.read_text().replace(
                "function hope(address usr) public { can[msg.sender][usr] = 1; }",
                "function hope(address usr) public { can[msg.sender][usr] = 2; }"))
            doc = portdiff.portdiff(VAT.source_path, m, VAT, 0, 500, 6)
        self.assertFalse(doc["equal"])
        self.assertIn("can(address,address)", doc["divergence"]["first_difference"])


if __name__ == "__main__":
    unittest.main()
