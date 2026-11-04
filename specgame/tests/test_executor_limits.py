"""Core v2 executor limits (protocol.json executor): the Spec harness deploys
with EIP-170 and EIP-3860 lifted; b and every mutant must still fit EIP-170;
the lift changes no observation of any committed bundle."""
import json
import unittest
from pathlib import Path

from tests._util import ROOT, core

import bundle  # noqa: E402

DEPLOYER = "0x" + "11" * 20
BIG_SPEC = ROOT / "runs" / "v3" / "vat" / "fM" / "seed_0_aborted_code_size" / "round_1" / "cand_1" / "Spec.sol"


def initcode(runtime_len: int, pad: int) -> bytes:
    """PUSH3 len PUSH1 0 RETURN (returns `runtime_len` zero bytes), then `pad`
    unreachable zero bytes, so the initcode is 7 + pad bytes."""
    return bytes([0x62]) + runtime_len.to_bytes(3, "big") + bytes([0x60, 0x00, 0xF3]) + b"\x00" * pad


def deploy(code: bytes, legacy: bool) -> str:
    evm = core._fresh_evm(legacy)
    evm.set_balance(DEPLOYER, 10 ** 30)
    addr, rdata, halt = core._exec(evm.deploy, DEPLOYER, code, gas=core.TX_GAS if legacy else core.DEPLOY_GAS)
    if addr is not None:
        return f"ok {len(evm.get_code(addr))}"
    return halt or f"revert {rdata.hex()}"


def deploy_tx_error(code: bytes, legacy: bool) -> str:
    try:
        return deploy(code, legacy)
    except core.ExecutorError as e:
        return str(e)


class Limits(unittest.TestCase):
    def test_frozen_values(self):
        ex = core.PROTOCOL["executor"]
        self.assertEqual((ex["contract_code_size_limit"], ex["initcode_size_limit"], ex["subject_runtime_limit"]),
                         (1 << 20, 1 << 21, 24576))
        self.assertEqual(ex["deploy_gas"], ex["block_env"]["gas_limit"])
        self.assertEqual(core.CORE_VERSION, 2)
        self.assertEqual(core.toolchain_fingerprint()["executor_limits"]["contract_code_size_limit"], 1 << 20)

    def test_large_runtime_and_initcode_deploy_under_v2(self):
        # runtime 30 000 > 24 576 (EIP-170) and initcode 50 007 > 49 152 (EIP-3860)
        r = deploy(initcode(30000, 50000), legacy=False)
        self.assertTrue(r.startswith("ok "), r)
        self.assertGreaterEqual(int(r.split()[1]), 30000)

    def test_negative_control_default_config_refuses(self):
        # the same contract under pyrevm's default limits: refused (initcode checked first)
        self.assertIn("CreateInitCodeSizeLimit", deploy_tx_error(initcode(30000, 50000), legacy=True))
        # runtime alone above EIP-170: CreateContractSizeLimit; the knob is what makes the difference
        self.assertEqual(deploy(initcode(30000, 0), legacy=True), "CreateContractSizeLimit")
        self.assertTrue(deploy(initcode(30000, 0), legacy=False).startswith("ok "))

    def test_v2_limits_are_still_limits(self):
        self.assertEqual(deploy(initcode((1 << 20) + 1, 0), legacy=False), "CreateContractSizeLimit")
        self.assertIn("CreateInitCodeSizeLimit", deploy_tx_error(initcode(100, (1 << 21) + 1), legacy=False))

    def test_subject_side_contract_above_eip170_is_refused(self):
        entry = core.compile_artifact(core.load_subject("vat").source_path, subject="vat")
        core.check_deployable(entry)
        fat = dict(entry, bin_runtime="00" * (core.SUBJECT_RUNTIME_LIMIT + 1))
        with self.assertRaises(core.ExecutorError):
            core.check_deployable(fat)
        sigma = {"version": 1, "deployer": "alice", "ctor": {}, "setup": core.setup_for(core.load_subject("vat"), "alice"),
                 "txs": []}
        with self.assertRaises(core.ExecutorError):
            core.run_sequence(fat, sigma)


@unittest.skipUnless(BIG_SPEC.is_file(), "aborted Vat run not present")
class RealOversizedSpec(unittest.TestCase):
    """The generator's 73-check Vat spec (runs/v3/vat/fM/seed_0_aborted_code_size):
    37 530 runtime bytes; core v1 could not deploy it, core v2 does."""

    def test_deploys_under_v2_only(self):
        vat = core.load_subject("vat")
        pair = core.compile_spec_over(BIG_SPEC, vat.source_path, subject=vat)
        self.assertGreater(len(pair["bin_runtime"]) // 2, 24576)
        sigma = {"version": 1, "deployer": "alice", "ctor": {}, "setup": core.setup_for(vat, "alice"), "txs": []}
        old = core.run_sequence(pair, sigma, legacy_executor=True)
        self.assertEqual(old.data["deploy"]["outcome"], "other")
        self.assertIn("deploy: CreateContractSizeLimit", old.log)
        new = core.run_sequence(pair, sigma)
        self.assertEqual(new.data["deploy"]["outcome"], "success")


class CommittedBundlesUnchanged(unittest.TestCase):
    """Every σ of the committed capped-token bundles (properness pairs and
    witnesses, every check) observes identically under core v1 and v2."""

    def test_capped_token_bundles(self):
        dirs = sorted(p.parent for p in (ROOT / "bundles").glob("phi_*/manifest.json")) + \
            sorted(p.parent for p in (ROOT / "runs" / "v2").glob("*/seed_*/bundle/manifest.json")) + \
            [ROOT / "tests" / "fixtures" / "bundle" / "good"]
        self.assertGreaterEqual(len(dirs), 13)
        total = 0
        for d in dirs:
            with self.subTest(bundle=str(d.relative_to(ROOT))):
                m = json.loads((d / "manifest.json").read_text())
                subj = core.load_subject(m["provenance"]["subject"])
                total += bundle.executor_migration_proof(d, m, subj)["observations_compared"]
        self.assertGreater(total, 700)

    def test_witness_evaluations_identical(self):
        d = ROOT / "bundles" / "phi_full"
        m = json.loads((d / "manifest.json").read_text())
        paths = {mu["id"]: d / mu["path"] for mu in m["evidence"]["M"]}
        for w in m["evidence"]["W"]:
            pair = core.compile_spec_over(d / m["hard"]["phi"]["path"], paths[w["mutant"]])
            old, new = core.evaluate_witness(pair, w["sigma"], legacy_executor=True), core.evaluate_witness(pair, w["sigma"])
            self.assertEqual((old.violated, old.outcomes, old.deploy_ok), (new.violated, new.outcomes, new.deploy_ok))
            self.assertTrue(new.violated)


if __name__ == "__main__":
    unittest.main()
