"""Monotonicity suite (task 06; TCG v3 section 6): take a bundle on which every
level passes, apply each mutation one at a time, and require that at least one
level is lowered and none is raised.

Each of the five mutations is tried twice where it makes sense:
  naive    - the bytes are changed and the manifest is left as signed;
  resigned - an adversarial PRODUCER changes the bytes, re-hashes and re-signs
             the manifest with its own (trusted) key. This is the harder case:
             L0's root/signature checks pass again, so a lower level must catch it.
The oracle key is never available to the adversary.
"""
from __future__ import annotations

import json
import os

import helpers
from helpers import toy

GARBAGE = b"\x00garbage\xff" * 7


class Monotonicity(helpers.ToyCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.base = cls.run_snap_static(cls.pristine)
        m = helpers.measures(cls.base)
        assert m["L0"] == m["L1"] == m["L3"] == m["L4"] == 2, f"baseline is not all-pass: {m}"
        assert m["L2.coverage_total"] and m["L2.pre_witness_replays"] and m["L2.mutants_witnessed"]

    @classmethod
    def run_snap_static(cls, bundle):
        return helpers.verify(bundle, cls.keys, ["--state-snapshot", cls.snap])

    def assert_monotone(self, bundle, label, must_lower=None):
        after = self.run_snap(bundle)
        lowered, raised = helpers.compare(self.base, after)
        self.assertEqual(raised, [], f"{label}: raised {raised}")
        self.assertTrue(lowered, f"{label}: nothing lowered")
        if must_lower:
            self.assertIn(must_lower, lowered, f"{label}: lowered {lowered}")
        return after

    def resign(self, b):
        toy.resign(b, self.keys["producer"])

    # 1. replace a child with garbage --------------------------------------
    def test_garbage_child_naive_every_child(self):
        with open(os.path.join(self.pristine, "manifest.json")) as f:
            paths = [c["path"] for c in json.load(f)["children"]]
        for p in paths:
            with self.subTest(child=p):
                b = self.fresh()
                toy.write(b, p, GARBAGE)
                self.assert_monotone(b, f"garbage {p}", must_lower="L0")

    def test_garbage_child_resigned(self):
        expect = {
            "hard/artifact.bin": "L0",
            "hard/spec/claim-01.k": "L1",
            "hard/certs/claim-01.rediscuss.json": "L1",
            "hard/certs/lean/Toy/Lemma01.lean": "L1",
            "hard/annotations.json": "L1",
            "trusted_base.json": "L0",
            "hard/spec/phi.json": "L3",
            "hard/spec/requirements.md": "L3",
            "evidence/approval.sig": "L3",
            "evidence/coverage.json": None,  # stored copy only; recomputation is what counts
            "evidence/backtranslation.json": "L2.backtranslation_present",
            "evidence/mutants/claim-01/replay.sh": "L2.mutants_witnessed",
            "evidence/pre_witness/replay.sh": "L2.pre_witness_replays",
            "provenance/ledger.jsonl": "L4",
            "provenance/artifact.hex": "L4",
        }
        for p, level in expect.items():
            with self.subTest(child=p):
                b = self.fresh()
                toy.write(b, p, GARBAGE)
                self.resign(b)
                if level is None:
                    after = self.run_snap(b)
                    self.assertEqual(helpers.compare(self.base, after)[1], [], f"{p}: raised")
                    self.assertFalse(after["L2"]["coverage"]["stored_coverage_matches"])
                else:
                    self.assert_monotone(b, f"resigned garbage {p}", must_lower=level)

    def test_dropping_a_child_resigned(self):
        for p in ("evidence/approval.sig", "provenance/ledger.jsonl", "hard/certs/claim-02.rediscuss.json"):
            with self.subTest(child=p):
                b = self.fresh()
                os.remove(os.path.join(b, p))
                self.resign(b)
                self.assert_monotone(b, f"dropped {p}")

    # 2. forge the approval with the producer key ---------------------------
    def test_approval_forged_with_producer_key(self):
        for resigned in (False, True):
            with self.subTest(resigned=resigned):
                b = self.fresh()
                toy.approve(b, self.keys["producer"])
                if resigned:
                    self.resign(b)
                after = self.assert_monotone(b, "forged approval", must_lower="L3")
                if resigned:
                    self.assertEqual(after["L3"]["reason"], "approval signed by producer")

    # 3. add a fabricated ledger event --------------------------------------
    def fabricate(self, b, deterministic=True):
        led = os.path.join(b, "provenance/ledger.jsonl")
        with open(led, "rb") as f:
            first = json.loads(f.read().split(b"\n")[0])
        ev = {k: v for k, v in first.items() if k not in ("seq", "prev", "format")}
        ev["outputs"] = [{"path": "provenance/artifact.sha256", "sha256": "f" * 64}]
        ev["deterministic"] = deterministic
        import sys
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(helpers.HERE)), "tools"))
        import ledger
        ledger.append_event(led, ev)

    def test_fabricated_ledger_event(self):
        for resigned in (False, True):
            with self.subTest(resigned=resigned):
                b = self.fresh()
                self.fabricate(b)
                if resigned:
                    self.resign(b)
                self.assert_monotone(b, "fabricated event", must_lower="L4" if resigned else "L0")

    def test_fabricated_event_with_broken_chain(self):
        b = self.fresh()
        with open(os.path.join(b, "provenance/ledger.jsonl"), "ab") as f:
            f.write(b'{"seq":4,"prev":"' + b"0" * 64 + b'","kind":"note"}\n')
        self.resign(b)
        self.assert_monotone(b, "fabricated unchained event", must_lower="L4")

    def test_fabricated_nondeterministic_note_cannot_raise(self):
        """Known limit: a fabricated, chained, non-replayable note cannot be
        detected (it is counted, not replayed). It must still not raise anything."""
        b = self.fresh()
        self.fabricate(b, deterministic=False)
        self.resign(b)
        lowered, raised = helpers.compare(self.base, self.run_snap(b))
        self.assertEqual(raised, [])

    def test_fabricated_event_with_outside_input_cannot_raise(self):
        """An event reading a file outside the bundle is not replayable: it may lower
        L4 (pass -> partial), never raise it, and never count as replayed."""
        for resigned in (False, True):
            with self.subTest(resigned=resigned):
                b = self.fresh()
                self.fabricate(b)
                led = os.path.join(b, "provenance/ledger.jsonl")
                with open(led, "rb") as f:
                    lines = f.read().split(b"\n")
                ev = json.loads(lines[-2])
                ev = {k: v for k, v in ev.items() if k not in ("seq", "prev", "format")}
                ev["inputs"] = [{"path": "../../../../pilot-checker/pins.json", "sha256": "5" * 64}]
                ev["outputs"] = []
                with open(led, "wb") as f:
                    f.write(b"\n".join(lines[:-2]) + b"\n")
                import ledger
                ledger.append_event(led, ev)
                if resigned:
                    self.resign(b)
                after = self.assert_monotone(b, "outside-input event", must_lower="L4" if resigned else "L0")
                if resigned:
                    l4 = after["L4"]
                    self.assertEqual(l4["status"], "partial")
                    self.assertEqual(l4["events_replayed"], self.base["L4"]["events_replayed"])
                    self.assertEqual([e["seq"] for e in l4["not_replayable_outside_bundle"]], [4])

    def test_outside_input_cannot_mask_a_fabricated_output(self):
        """Adding an outside input does not hide a recorded output that disagrees with the bundle."""
        b = self.fresh()
        import ledger
        ledger.append_event(os.path.join(b, "provenance/ledger.jsonl"), {
            "kind": "run", "tool": "x", "tool_hash": "3" * 64, "argv": ["x"], "cwd": ".",
            "inputs": [{"path": "/etc/hostname", "sha256": "5" * 64}],
            "outputs": [{"path": "provenance/artifact.sha256", "sha256": "f" * 64}],
            "stdout": None, "stderr": None, "exit": 0, "started": "x", "ended": "x", "deterministic": True})
        self.resign(b)
        after = self.assert_monotone(b, "masked output", must_lower="L4")
        self.assertEqual(after["L4"]["status"], "fail")
        self.assertEqual([i["path"] for i in after["L4"]["inconsistent_outputs"]], ["provenance/artifact.sha256"])

    # 4. edit phi.json after signing ----------------------------------------
    def test_phi_edited_after_approval(self):
        for resigned in (False, True):
            with self.subTest(resigned=resigned):
                b = self.fresh()
                with open(os.path.join(b, "hard/spec/phi.json")) as f:
                    phi = json.load(f)
                phi["claims"][0]["post"] = "true"  # weakened after H signed
                toy.write_json(b, "hard/spec/phi.json", phi)
                if resigned:
                    self.resign(b)
                self.assert_monotone(b, "phi edited", must_lower="L3" if resigned else "L0")

    # 5. swap artifact.bin for WETH9's bytecode (toy stand-in) --------------
    def test_artifact_swapped_for_weth(self):
        for variant in ("naive", "resigned", "resigned_with_identity"):
            with self.subTest(variant=variant):
                b = self.fresh()
                toy.write(b, "hard/artifact.bin", toy.WETH_CODE)
                if variant == "resigned_with_identity":
                    with open(os.path.join(b, "trusted_base.json")) as f:
                        tb = json.load(f)
                    tb["identity"]["value"] = "0x" + toy.keccak256(toy.WETH_CODE).hex()
                    toy.write_json(b, "trusted_base.json", tb)
                if variant != "naive":
                    self.resign(b)
                after = self.assert_monotone(b, f"WETH swap {variant}", must_lower="L0")
                ident = after["L0"]["checks"]["identity"]
                self.assertFalse(ident["ok"])
                self.assertEqual(ident["chain_keccak"], "0x" + toy.keccak256(toy.ARTIFACT).hex())


if __name__ == "__main__":
    import unittest
    unittest.main()
