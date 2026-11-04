"""protocol.json (authoritative values) vs protocol.md (prose): the code reads
the values, bundles record both hashes, the verifier compares only the JSON,
and `bundle.py --restamp` moves provenance without re-running anything."""
import contextlib
import io
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

from tests._util import FIXTURES, ROOT, core

sys.path.insert(0, str(ROOT / "generator"))
import adversary  # noqa: E402
import bundle  # noqa: E402
import check as check_cli  # noqa: E402
import loop  # noqa: E402
import seqgen  # noqa: E402
import verify  # noqa: E402

P = json.loads((ROOT / "protocol.json").read_text())
GOOD = FIXTURES / "bundle" / "good"


class ValuesAgree(unittest.TestCase):
    def test_core_reads_protocol_json_and_profiles(self):
        prof = json.loads((ROOT / P["subjects"]["capped_token"]["profile"]).read_text())
        self.assertEqual(P["protocol_version"], 3)
        self.assertEqual(core.POOL, prof["pools"]["address"])
        self.assertEqual(list(core.SENDERS), prof["senders"])
        self.assertEqual((core.TX_GAS, core.BLOCK_ENV, core.CHAIN_ID, core.SPEC_ID),
                         (P["executor"]["tx_gas"], P["executor"]["block_env"], P["executor"]["chain_id"],
                          P["executor"]["spec_id"]))
        self.assertEqual(core.BASE_SETTINGS, P["compiler"]["settings"])
        self.assertEqual((check_cli.DEFAULT_TIMEOUT_MS, check_cli.DEFAULT_WALL_TIMEOUT_S),
                         (P["check"]["timeout_ms"], P["check"]["wall_timeout_s"]))

    def test_generator_reads_protocol_json(self):
        g = P["subjects"]["capped_token"]["generator"]
        self.assertEqual((loop.FROZEN["model"], loop.FROZEN["max_tokens"], loop.FROZEN["effort"],
                          loop.FROZEN["rounds"], loop.FROZEN["k"]),
                         (g["model"], g["max_tokens"], g["output_config"]["effort"], g["rounds"], g["k"]))
        self.assertEqual(loop.prompt_hashes(), g["prompts"])
        self.assertEqual(loop.prompts_sha256(), g["prompts_sha256"])

    def test_adversary_ids_are_the_frozen_ones(self):
        for name in ("capped_token", "vat"):
            a, subj = P["subjects"][name]["adversary"], core.load_subject(name)
            fns = seqgen.tx_functions(core.compile_artifact(subj.source_path, subject=subj), subj)
            got = adversary.adversary_id(adversary.params(a["seed_A"], a["B_A"], a["max_txs"], a["per_mutant"],
                                                          fns, subj))
            self.assertEqual(got, a["id"], name)
        # the ladder bundles were produced under protocol v2's adversary (same σ, other source hash)
        for m in sorted((ROOT / "bundles").glob("phi_*/manifest.json")):
            self.assertEqual(json.loads(m.read_text())["evidence"]["adversary"]["id"],
                             P["subjects"]["capped_token"]["adversary"]["id_v2"], m.parent.name)

    def test_committed_bundles_record_both_hashes_and_the_subject(self):
        for m in [GOOD / "manifest.json", *sorted((ROOT / "bundles").glob("phi_*/manifest.json"))]:
            prov = json.loads(m.read_text())["provenance"]
            self.assertEqual(prov["protocol_json_sha256"], core.sha256_file(ROOT / "protocol.json"), m)
            self.assertEqual(prov["subject"], "capped_token", m)
            self.assertNotIn("protocol_sha256", prov)


def quiet(fn, *a):
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
        return fn(*a)


class Restamp(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.b = Path(self.tmp.name) / "good"
        shutil.copytree(GOOD, self.b)
        self.m = lambda: json.loads((self.b / "manifest.json").read_text())

    def tearDown(self):
        self.tmp.cleanup()

    def edit(self, fn):
        m = self.m()
        fn(m)
        (self.b / "manifest.json").write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")

    def test_current_bundle_is_unchanged(self):
        before = (self.b / "manifest.json").read_bytes()
        self.assertEqual(quiet(bundle.main, ["--restamp", str(self.b)]), 0)
        self.assertEqual((self.b / "manifest.json").read_bytes(), before)

    def test_old_provenance_is_migrated_without_touching_evidence(self):
        before = self.m()

        def old_style(m):
            p = m["provenance"]
            p["protocol_sha256"] = "0" * 64
            del p["protocol_json_sha256"], p["protocol_md_sha256"]
            p["verifier_sha256"] = "1" * 64
        self.edit(old_style)
        self.assertEqual(quiet(bundle.main, ["--restamp", str(self.b)]), 0)
        self.assertEqual(self.m(), before)

    def test_modified_file_is_refused(self):
        p = self.b / "phi" / "Spec.sol"
        p.write_text(p.read_text() + "\n")
        before = (self.b / "manifest.json").read_bytes()
        self.assertEqual(quiet(bundle.main, ["--restamp", str(self.b)]), 1)
        self.assertEqual((self.b / "manifest.json").read_bytes(), before)

    def test_semantics_change_is_refused(self):
        self.edit(lambda m: m["provenance"]["toolchain"].update(pyrevm="0.3.8"))
        with self.assertRaises(bundle.BundleError):
            bundle.restamp(self.b)

    def test_changed_solc_input_is_refused(self):
        def bump(m):
            m["hard"]["c"]["timeout_ms"] += 1
        self.edit(bump)
        with self.assertRaisesRegex(bundle.BundleError, "solc input"):
            bundle.restamp(self.b)


class VerifierComparesOnlyTheJson(unittest.TestCase):
    def run_on(self, fn):
        with tempfile.TemporaryDirectory() as t:
            b = Path(t) / "good"
            shutil.copytree(GOOD, b)
            m = json.loads((b / "manifest.json").read_text())
            fn(m["provenance"])
            (b / "manifest.json").write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")
            return verify.verify(b)

    def test_protocol_json_mismatch_is_refused(self):
        rep = self.run_on(lambda p: p.update(protocol_json_sha256="0" * 64))
        self.assertEqual((rep["verdict"], rep["exit_code"], rep["first_failing_step"]), ("REFUSED", 3, 1))

    def test_protocol_md_mismatch_is_ignored(self):
        rep = self.run_on(lambda p: p.update(protocol_md_sha256="0" * 64))
        self.assertEqual((rep["verdict"], rep["exit_code"]), ("HOLDS", 0))


if __name__ == "__main__":
    unittest.main()
