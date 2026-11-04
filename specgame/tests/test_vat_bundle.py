"""Protocol v3: a minimal Vat bundle (two mutants of the Vat library, a
one-check spec, one hand witness) is assembled and HOLDS; σ in a bundle are
validated against the bundle's subject, so a capped-token σ in a Vat bundle is
refused at step 0."""
import contextlib
import copy
import dataclasses
import io
import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from tests._util import ROOT, core

import bundle  # noqa: E402
import properness  # noqa: E402
import verify  # noqa: E402

VAT = core.load_subject("vat")
MUTANTS = [VAT.mutants_dir / "m01_slip_no_auth.sol", VAT.mutants_dir / "m07_move_no_debit.sol"]
SPEC = """// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    /// Only a ward can create free collateral.
    function check_slip_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }
}
"""
CAPPED_SIGMA = {"version": 1, "deployer": "alice", "ctor": {"cap": "100"},
                "txs": [{"sender": "alice", "fn": "mint(address,uint256)", "args": ["bob", "60"]}]}


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a)


class _VatBundleBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        t = Path(cls.tmp.name)
        doc, _ = properness.build(VAT.source_path, MUTANTS, 0, 500, 6, subject=VAT)
        assert [m["status"] for m in doc["mutants"]] == ["included", "included"], doc["mutants"]
        (t / "mutants.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        (t / "spec.sol").write_text(SPEC)
        m01 = doc["mutants"][0]
        pair = core.compile_spec_over(t / "spec.sol", ROOT / m01["path"], subject=VAT)
        sigma = {"version": 1, "deployer": "alice", "ctor": {}, "setup": core.setup_for(VAT, "alice"), "txs": [],
                 "probe": {"sender": "bob", "a": "alice", "b": "bob", "x": "0", "y": "0",
                           "i": "GOLD", "u": "bob", "dx": "1", "dy": "0", "check": "check_slip_needs_auth"}}
        assert core.evaluate_witness(pair, sigma).violated
        w = {"version": 1, "mutant": m01["id"], "sigma": sigma,
             "observed": {"spec_source_sha256": core.sha256_file(t / "spec.sol"),
                          "pair_runtime_sha256": pair["runtime_sha256"], "check": "check_slip_needs_auth",
                          "outcome": "violation"}}
        (t / "w.json").write_text(json.dumps([w], indent=1) + "\n")
        cls.bundle = t / "bundle"
        cls.code = quiet(bundle.main, ["--out", str(cls.bundle), "--subject", "vat", "--artifact", str(VAT.source_path),
                                       "--spec", str(t / "spec.sol"), "--mutants", str(t / "mutants.json"),
                                       "--witnesses", str(t / "w.json"), "--adversary-id", "hand-witness",
                                       "--adversary-source", __file__, "--adversary-seed", "0",
                                       "--adversary-budget", "1"])

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def tampered(self, fn):
        d = Path(self.tmp.name) / f"t{id(fn)}"
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(self.bundle, d)
        m = json.loads((d / "manifest.json").read_text())
        fn(m)
        (d / "manifest.json").write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
        return verify.verify(d)



@unittest.skipUnless(all(p.is_file() for p in MUTANTS), "Vat mutant library not present")
class VatBundle(_VatBundleBase):
    def test_vat_bundle_holds(self):
        self.assertEqual(self.code, 0)
        m = json.loads((self.bundle / "manifest.json").read_text())
        self.assertEqual(m["provenance"]["subject"], "vat")
        self.assertIn("b/Vat.sol", m["files"])
        rep = verify.verify(self.bundle)
        self.assertEqual((rep["verdict"], rep["exit_code"]), ("HOLDS", 0), rep["steps"])
        self.assertEqual(rep["ms_cert"], {"killed": 1, "total": 2})

    def test_capped_token_properness_sigma_is_refused(self):
        def put(m):
            m["evidence"]["M"][0]["properness_sigma"][0] = copy.deepcopy(CAPPED_SIGMA)
        rep = self.tampered(put)
        self.assertEqual((rep["verdict"], rep["first_failing_step"]), ("REFUSED", 0))
        self.assertTrue(any("properness_sigma[0]" in d for d in rep["steps"][0]["details"]), rep["steps"][0])

    def test_capped_token_witness_sigma_is_refused(self):
        def put(m):
            m["evidence"]["W"][0]["sigma"] = {**copy.deepcopy(CAPPED_SIGMA),
                                              "probe": {"sender": "bob", "a": "alice", "b": "bob", "x": "1", "y": "0"}}
        rep = self.tampered(put)
        self.assertEqual((rep["verdict"], rep["first_failing_step"]), ("REFUSED", 0))

    def test_bundle_carries_the_pinned_profile(self):
        m = json.loads((self.bundle / "manifest.json").read_text())
        path = m["provenance"]["subject_profile_path"]
        self.assertEqual(core.sha256_file(self.bundle / path), core.PROTOCOL["subjects"]["vat"]["profile_sha256"])
        self.assertEqual(m["files"][path], core.PROTOCOL["subjects"]["vat"]["profile_sha256"])

    def test_edited_bundled_profile_is_refused(self):
        d = Path(self.tmp.name) / "edited_profile"
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(self.bundle, d)
        prof = json.loads((d / "subject" / "profile.json").read_text())
        prof["senders"] = ["alice", "bob"]
        (d / "subject" / "profile.json").write_text(json.dumps(prof, indent=1) + "\n")
        rep = verify.verify(d)
        self.assertEqual((rep["verdict"], rep["first_failing_step"]), ("REFUSED", 0))
        self.assertTrue(any("bundled subject profile refused" in x for x in rep["steps"][0]["details"]))

    def test_missing_bundled_profile_is_refused(self):
        d = Path(self.tmp.name) / "no_profile"
        if d.exists():
            shutil.rmtree(d)
        shutil.copytree(self.bundle, d)
        (d / "subject" / "profile.json").unlink()
        rep = verify.verify(d)
        self.assertEqual((rep["verdict"], rep["first_failing_step"]), ("REFUSED", 0))

    def test_vat_sigma_without_setup_is_refused(self):
        def put(m):
            m["evidence"]["W"][0]["sigma"].pop("setup")
        rep = self.tampered(put)
        self.assertEqual((rep["verdict"], rep["first_failing_step"]), ("REFUSED", 0))


def record_unknown(m):
    """The bundle's per-check table and aggregate say Unknown (unproved)."""
    c = m["hard"]["c"]
    for row in c["checks"]:
        row["verdict"], row["reason"] = "Unknown", "unproved"
    c["verdict"], c["reason"] = "Unknown", "unproved"


def rerun_as(verdict, reason):
    """The verifier's re-run, with every check's verdict replaced (a slower or
    different machine); the solc inputs are the real ones."""
    real = core.smtcheck_isolated

    def fake(*a, **kw):
        r = real(*a, **kw)
        checks = [{**rr, "result": {**rr["result"], "verdict": verdict, "reason": reason}} for rr in r.checks]
        return dataclasses.replace(r, verdict=verdict, reason=reason, checks=checks)
    return mock.patch.object(verify.core, "smtcheck_isolated", fake)


@unittest.skipUnless(all(p.is_file() for p in MUTANTS), "Vat mutant library not present")
class VatNotCertified(_VatBundleBase):
    """Exit semantics of a non-Accept Check (verifier/README.md): a recorded
    Unknown that the re-run reproduces is NOT_CERTIFIED (exit 2) with ms_cert
    still recomputed; every other disagreement or any Refute is REFUSED."""

    def test_recorded_unknown_reproduced_is_not_certified_with_score(self):
        with rerun_as("Unknown", "unproved"):
            rep = self.tampered(record_unknown)
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["first_failing_step"]), ("NOT_CERTIFIED", 2, 2),
                         rep["steps"])
        self.assertEqual(rep["failing_steps"], [2])
        self.assertEqual({s["step"]: s["status"] for s in rep["steps"]},
                         {0: "pass", 1: "pass", 2: "not_certified", 3: "pass", 4: "pass", 5: "pass", 6: "pass"})
        self.assertEqual(rep["ms_cert"], {"killed": 1, "total": 2})
        self.assertEqual(len(rep["kill_set"]), 1)

    def test_recorded_accept_rerun_unknown_is_refused(self):
        with rerun_as("Unknown", "budget"):
            rep = verify.verify(self.bundle)
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["first_failing_step"]), ("REFUSED", 3, 2))
        self.assertTrue(any("records Check(check_slip_needs_auth) = Accept but the re-run gives Unknown" in d
                            for d in rep["steps"][2]["details"]), rep["steps"][2])

    def test_recorded_unknown_rerun_refute_is_refused(self):
        with rerun_as("Refute", "counterexample"):
            rep = self.tampered(record_unknown)
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["first_failing_step"]), ("REFUSED", 3, 2))

    def test_recorded_unknown_rerun_accept_could_not_verify(self):
        rep = self.tampered(record_unknown)  # the real re-run: Accept
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["first_failing_step"]), ("COULD_NOT_VERIFY", 2, 2))

    def test_aggregate_not_combining_from_table_is_refused(self):
        def put(m):
            m["hard"]["c"]["verdict"], m["hard"]["c"]["reason"] = "Unknown", "unproved"
        rep = self.tampered(put)
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["first_failing_step"]), ("REFUSED", 3, 2))


LADDER_UNKNOWN = ROOT / "bundles" / "vat" / "phi_auth"


@unittest.skipUnless((LADDER_UNKNOWN / "manifest.json").is_file(), "Vat ladder bundles not present")
class VatLadderUnknownBundle(unittest.TestCase):
    """A committed Vat ladder bundle whose Check(b) is Unknown (one check,
    check_file_ilk_needs_auth, unproved under CHC): the real re-run reproduces
    it, so the verdict is NOT_CERTIFIED, exit 2, with the claimed score."""

    def test_phi_auth_not_certified_with_score(self):
        m = json.loads((LADDER_UNKNOWN / "manifest.json").read_text())
        self.assertEqual(m["hard"]["c"]["verdict"], "Unknown")
        rep = verify.verify(LADDER_UNKNOWN)
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["failing_steps"]), ("NOT_CERTIFIED", 2, [2]),
                         rep["steps"])
        self.assertEqual(rep["ms_cert"], m["claimed"]["ms_cert"])
        self.assertEqual(rep["kill_set"], m["claimed"]["kill_set"])


if __name__ == "__main__":
    unittest.main()
