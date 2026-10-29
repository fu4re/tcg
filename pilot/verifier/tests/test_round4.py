"""L4 stand-ins and --l4-skip-provers, mainnet fork derivation, and (opt-in) the
real Lean kernel path."""
from __future__ import annotations

import os
import shutil
import tempfile
import unittest

import helpers
from helpers import toy
from tcgverify import canon, checkers
from tcgverify.chain import blob_param_fork_for, fork_for

TOOL_SH = "#!/bin/sh\nod -An -tx1 hard/artifact.bin | tr -d ' \\n'; echo\n"


class StandIns(helpers.ToyCase):
    def add_tool_event(self, b, recorded_tool_hash=None, stdout_hash=None):
        """Bundle provenance/tools/t.sh; record an event that ran it as ../tools/t.sh."""
        import ledger
        import subprocess
        toy.write(b, "provenance/tools/t.sh", TOOL_SH)
        out = subprocess.run(["sh", "provenance/tools/t.sh"], cwd=b, capture_output=True).stdout
        toy.write(b, "provenance/t.out", out)
        ledger.append_event(os.path.join(b, "provenance/ledger.jsonl"), {
            "kind": "run", "tool": "t", "tool_hash": canon.sha256_file(shutil.which("sh")),
            "argv": ["sh", "../tools/t.sh"], "cwd": ".",
            "inputs": [{"path": "../tools/t.sh", "sha256": recorded_tool_hash or toy.sha(b, "provenance/tools/t.sh")},
                       {"path": "hard/artifact.bin", "sha256": toy.sha(b, "hard/artifact.bin")}],
            "outputs": [{"path": "provenance/t.out", "sha256": stdout_hash or toy.sha(b, "provenance/t.out")}],
            "stdout": "provenance/t.out", "stderr": None, "exit": 0, "started": "x", "ended": "x",
            "deterministic": True})

    def test_outside_input_replayed_from_byte_identical_child(self):
        b = self.fresh()
        self.add_tool_event(b)
        toy.write_manifest(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual(l4["status"], "pass", l4)
        self.assertEqual(l4["replayed_with_stand_ins"], [{"seq": 4, "stand_ins": {"../tools/t.sh": "provenance/tools/t.sh"}}])
        self.assertEqual(l4["counts"]["replayed_matched"], 3)

    def test_no_byte_identical_child_is_outside_bucket(self):
        b = self.fresh()
        self.add_tool_event(b, recorded_tool_hash="7" * 64)
        toy.write_manifest(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual(l4["status"], "partial")
        e = l4["not_replayable_outside_bundle"][0]
        self.assertEqual(e["why"], {"../tools/t.sh": "no bundle child has the recorded sha256"})
        self.assertEqual(e["paths"]["argv"], ["../tools/t.sh"])

    def test_forged_output_with_stand_in_is_a_mismatch(self):
        """Monotonicity: a stand-in replay checks outputs like any other replay."""
        b = self.fresh()
        self.add_tool_event(b, stdout_hash="e" * 64)
        toy.write(b, "provenance/t.out", b"forged\n")  # bundle agrees with nothing
        toy.write_manifest(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual(l4["status"], "fail")
        self.assertEqual([(m["seq"], m["used_stand_ins"]) for m in l4["mismatches"]], [(4, True)])

    def test_undeclared_import_shows_in_mismatch(self):
        """WS-H's real case: the bundled script needs a file the event did not record."""
        b = self.fresh()
        self.add_tool_event(b)
        toy.write(b, "provenance/tools/t.sh", TOOL_SH.replace("od ", ". ../lib/undeclared.sh; od "))
        import json
        led = os.path.join(b, "provenance/ledger.jsonl")
        with open(led) as f:
            lines = f.read().splitlines()
        ev = json.loads(lines[-1])
        ev = {k: v for k, v in ev.items() if k not in ("seq", "prev", "format")}
        ev["inputs"][0]["sha256"] = toy.sha(b, "provenance/tools/t.sh")
        with open(led, "w") as f:
            f.write("\n".join(lines[:-1]) + "\n")
        import ledger
        ledger.append_event(led, ev)
        toy.write_manifest(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual(l4["status"], "fail")
        m = l4["mismatches"][0]
        self.assertTrue(m["used_stand_ins"])
        self.assertIn("undeclared.sh", m["replay_stderr_tail"])


class ToolHashConventions(helpers.ToyCase):
    def test_script_hash_and_docker_image_id(self):
        import ledger
        b = self.fresh()
        toy.write(b, "provenance/tools/t.sh", TOOL_SH)
        led = os.path.join(b, "provenance/ledger.jsonl")
        base = {"kind": "run", "cwd": ".", "outputs": [], "stdout": None, "stderr": None, "exit": 0,
                "started": "x", "ended": "x", "deterministic": True}
        h = toy.sha(b, "provenance/tools/t.sh")
        ledger.append_event(led, dict(base, tool="t", tool_hash=h, argv=["sh", "provenance/tools/t.sh"],
                                      inputs=[{"path": "provenance/tools/t.sh", "sha256": h}]))
        ledger.append_event(led, dict(base, tool="probe", tool_hash=toy.FAKE_IMAGE_ID, argv=["true"], inputs=[]))
        ledger.append_event(led, dict(base, tool="t", tool_hash="9" * 64, argv=["sh", "provenance/tools/t.sh"],
                                      inputs=[{"path": "provenance/tools/t.sh", "sha256": h}]))
        toy.write_manifest(b, self.keys["producer"])
        r = self.run_snap(b)
        l4 = r["L4"]
        self.assertEqual(l4["counts"]["replayed_matched"], 4, l4)  # 2 toy events + script hash + image Id
        self.assertEqual([(e["seq"], e["reason"]) for e in l4["not_replayed"]],
                         [(6, "tool 'sh' not available by hash " + "9" * 64)])
        self.assertTrue(any(o.startswith("docker image " + toy.FAKE_IMAGE_ID) for o in r["outside_bundle"]))


class BacktranslationKeys(helpers.ToyCase):
    def test_claims_key_read_entries_fallback(self):
        self.assertEqual(len(self.run_snap(self.pristine)["L2"]["backtranslation"]), 1)  # toy uses "entries"
        b = self.fresh()
        toy.write_json(b, "evidence/backtranslation.json", {"translator": {"model": "toy"}, "claims": [
            {"claim": "claim-01", "translation": "t1", "agreement": "unclear"},
            {"claim": "claim-02", "translation": "t2", "agreement": "unclear"}]})
        toy.write_manifest(b, self.keys["producer"])
        l2 = self.run_snap(b)["L2"]
        self.assertEqual([e["claim"] for e in l2["backtranslation"]], ["claim-01", "claim-02"])
        self.assertEqual(l2["backtranslation_meta"], {"translator": {"model": "toy"}})


class SkipProvers(helpers.ToyCase):
    def test_prover_events_skipped_only_on_request(self):
        import ledger
        b = self.fresh()
        ledger.append_event(os.path.join(b, "provenance/ledger.jsonl"), {
            "kind": "run", "tool": "kevm-prove", "tool_hash": "sha256:" + "ab" * 32,
            "argv": ["sh", "provenance/tools/run-claim.sh"], "cwd": ".", "inputs": [], "outputs": [],
            "stdout": None, "stderr": None, "exit": 0, "started": "x", "ended": "x", "deterministic": True})
        toy.resign(b, self.keys["producer"])
        skipped = self.run_snap(b, extra=["--l4-skip-provers"])
        l4 = skipped["L4"]
        self.assertTrue(skipped["l4_skip_provers"])
        self.assertEqual(l4["skipped_by_consumer"], [{"seq": 4, "reason": "not replayed: skipped by consumer"}])
        self.assertEqual((l4["status"], l4["counts"]["skipped_by_consumer"], l4["counts"]["replayed_matched"]),
                         ("partial", 1, 2))
        plain = self.run_snap(b)["L4"]
        self.assertEqual(plain["skipped_by_consumer"], [])
        self.assertEqual([e["seq"] for e in plain["not_replayed"]], [4])  # tried: image not present


class MainnetForks(unittest.TestCase):
    def test_boundaries_from_geth_mainnet_json(self):
        self.assertEqual(fork_for(1, 26298481, 1793277911), "osaka")  # the pilot's pinned block
        self.assertEqual(blob_param_fork_for(1, 1793277911), "bpo2")
        self.assertEqual((fork_for(1, 0, 1764798550), fork_for(1, 0, 1764798551)), ("prague", "osaka"))
        self.assertEqual((blob_param_fork_for(1, 1765290070), blob_param_fork_for(1, 1765290071)), (None, "bpo1"))
        self.assertEqual(fork_for(1, 0, 1767747671), "osaka")  # BPO2 is not an execution fork
        self.assertIsNone(fork_for(10, 0, 1793277911))


LEAN_TOOLCHAIN = "leanprover/lean4:v4.22.0"
LAKEFILE = "import Lake\nopen Lake DSL\n\npackage toy\n\n@[default_target]\nlean_lib Toy\n"


@unittest.skipUnless(os.environ.get("TCG_REAL_LEAN") == "1" and
                     os.path.isfile(os.path.join(checkers.lean_toolchain_dir(LEAN_TOOLCHAIN), "bin", "lean")),
                     "real-kernel test is opt-in: TCG_REAL_LEAN=1 under ~/pilot-locks/with-slot.sh lean")
class RealLeanKernel(unittest.TestCase):
    """The same code path as L1 (checkers.lean_project) against the real Lean 4 kernel."""

    def test_accept_sorry_and_custom_axiom(self):
        lean = os.path.join(checkers.lean_toolchain_dir(LEAN_TOOLCHAIN), "bin", "lean")
        entry = {"name": "lean", "hash": canon.sha256_file(lean)}
        cases = {
            "Ok": ("theorem ok : 2 + 2 = 4 := rfl\n", "accept", []),
            "Sorry": ("theorem ok : 2 + 2 = 5 := by sorry\n", "not_accept", ["sorryAx"]),
            "Ax": ("axiom cheat : False\ntheorem ok : 2 + 2 = 5 := cheat.elim\n", "not_accept", ["Toy.Ax.cheat"]),
        }
        with tempfile.TemporaryDirectory() as d:
            with open(os.path.join(d, "lean-toolchain"), "w") as f:
                f.write(LEAN_TOOLCHAIN + "\n")
            with open(os.path.join(d, "lakefile.lean"), "w") as f:
                f.write(LAKEFILE)
            os.makedirs(os.path.join(d, "Toy"))
            thms = []
            for mod, (body, _, _) in cases.items():
                with open(os.path.join(d, "Toy", f"{mod}.lean"), "w") as f:
                    f.write(f"namespace Toy.{mod}\n{body}end Toy.{mod}\n")
                thms.append((mod, f"Toy.{mod}.ok", os.path.join(d, "Toy", f"{mod}.lean")))
            with open(os.path.join(d, "Toy.lean"), "w") as f:
                f.write("".join(f"import Toy.{m}\n" for m in cases))
            outside: list[str] = []
            res = {r["claim"]: r for r in checkers.lean_project(d, thms, entry, checkers.STANDARD_LEAN_AXIOMS,
                                                                  outside, timeout=1800)}
        for mod, (_, want, extra) in cases.items():
            self.assertEqual(res[mod]["result"], want, res[mod])
            self.assertEqual(res[mod]["non_standard_axioms"], extra, res[mod])
        self.assertTrue(any(o.startswith(f"Lean toolchain {LEAN_TOOLCHAIN}") for o in outside))


if __name__ == "__main__":
    unittest.main()
