"""Producer tools on the toy bundle: assemble.py, coverage.py, mutant_witness.py,
plus the consumer README's verifier-hash recipe."""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import helpers
from helpers import toy
from tcgverify import canon, ed25519, ladder

PILOT = os.path.dirname(os.path.dirname(helpers.HERE))
TOOLS = os.path.join(PILOT, "tools")


def tool(name, *args, **kw):
    return subprocess.run([sys.executable, os.path.join(TOOLS, name), *args], capture_output=True,
                          text=True, **kw)


def manifest_bytes(b):
    with open(os.path.join(b, "manifest.json"), "rb") as f:
        return f.read()


class Assemble(helpers.ToyCase):
    def refuses(self, b, needle):
        before = manifest_bytes(b)
        r = tool("assemble.py", b, "--key", self.keys["producer"])
        self.assertEqual(r.returncode, 1, r.stdout)
        self.assertIn(needle, r.stdout)
        self.assertIn("nothing written", r.stdout)
        self.assertEqual(manifest_bytes(b), before)

    def test_roles_classes_claims(self):
        with open(os.path.join(self.pristine, "manifest.json")) as f:
            man = json.load(f)
        by = {c["path"]: c for c in man["children"]}
        self.assertEqual((by["hard/artifact.bin"]["role"], by["hard/artifact.bin"]["class"]), ("b", "T"))
        self.assertEqual(by["hard/spec/claim-01.k"]["claim"], "claim-01")
        self.assertNotIn("claim", by["hard/spec/phi.json"])
        self.assertEqual(by["hard/certs/claim-02.rediscuss.json"]["media"], "application/vnd.tcg.rediscuss+json")
        lean = by["hard/certs/lean/Toy/Lemma01.lean"]
        self.assertEqual((lean["role"], lean["claim"], lean["theorem"]), ("c", "lemma-01", "Toy.lemma01"))
        self.assertNotIn("claim", by["hard/certs/lean/lakefile.lean"])
        self.assertEqual((by["evidence/approval.sig"]["class"], by["DECISIONS.md"]["class"]), ("T*", "U"))
        self.assertFalse(man["self_contained"])
        self.assertIn("claim-01, claim-02", man["self_contained_reason"])
        self.assertEqual(man["root_hash"], canon.root_hash(man))
        self.assertTrue(ed25519.verify(bytes.fromhex(man["producer_sig"]["pubkey"]), man["root_hash"].encode(),
                                       bytes.fromhex(man["producer_sig"]["sig"])))
        r = tool("lint_manifest.py", os.path.join(self.pristine, "manifest.json"))
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_reassembly_is_deterministic(self):
        b = self.fresh()
        before = json.loads(manifest_bytes(b))
        self.assertEqual(tool("assemble.py", b, "--key", self.keys["producer"]).returncode, 0)
        self.assertEqual(json.loads(manifest_bytes(b))["root_hash"], before["root_hash"])

    def test_check_writes_nothing(self):
        b = self.fresh()
        os.remove(os.path.join(b, "manifest.json"))
        r = tool("assemble.py", b, "--check")
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertFalse(os.path.exists(os.path.join(b, "manifest.json")))

    def test_refuses_unclaimed_file(self):
        b = self.fresh()
        toy.write(b, "HARD_STATUS.md", "working notes\n")
        self.refuses(b, "HARD_STATUS.md: not claimed by any role rule")

    def test_refuses_missing_d_row(self):
        b = self.fresh()
        p = os.path.join(b, "DECISIONS.md")
        with open(p) as f:
            text = f.read()
        toy.write(b, "DECISIONS.md", text.replace("| D7 | toy | toy |\n", ""))
        self.refuses(b, "DECISIONS.md: no row for D7")

    def test_refuses_missing_required_role(self):
        b = self.fresh()
        os.remove(os.path.join(b, "checker/kevm-prove.image.json"))
        self.refuses(b, "required role checker has no file")

    def test_refuses_rule2_violation(self):
        b = self.fresh()
        with open(os.path.join(b, "trusted_base.json")) as f:
            tb = json.load(f)
        tb["claims_without_certificate"] = tb["claims_without_certificate"][:1]
        toy.write_json(b, "trusted_base.json", tb)
        self.refuses(b, "claim-02: no certificate and not in claims_without_certificate")

    def test_refuses_stale_claim_file_hash(self):
        b = self.fresh()
        with open(os.path.join(b, "hard/spec/claim-02.k"), "a") as f:
            f.write("// edited\n")
        self.refuses(b, "phi.json claim claim-02: sha256 differs")

    def test_refuses_symlink_and_broken_ledger(self):
        b = self.fresh()
        os.symlink("/etc/hostname", os.path.join(b, "evidence/link"))
        self.refuses(b, "evidence/link: symlink")
        b = self.fresh()
        with open(os.path.join(b, "provenance/ledger.jsonl"), "ab") as f:
            f.write(b"{}\n")
        self.refuses(b, "provenance/ledger.jsonl:")

    def test_refuses_bad_theorems_sidecar(self):
        b = self.fresh()
        toy.write_json(b, "hard/certs/lean/theorems.json",
                       [{"claim": "lemma-01", "theorem": "Toy.lemma01", "source": "hard/certs/lean/Nope.lean"}])
        self.refuses(b, "hard/certs/lean/theorems.json: entry")

    def test_warns_on_unclosed_annotations(self):
        b = self.fresh()
        with open(os.path.join(b, "hard/annotations.json")) as f:
            anns = json.load(f)
        anns["annotations"].append({"id": "simp-99", "statement": "x", "used_by": [], "justification": "x", "class": "T"})
        toy.write_json(b, "hard/annotations.json", anns)
        r = tool("assemble.py", b, "--key", self.keys["producer"])
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn("WARN: annotation simp-99 not in trusted_base.assumptions", r.stdout)
        self.assertEqual(self.run_snap(b)["L1"]["status"], "refused")


class Coverage(helpers.ToyCase):
    def edit_phi(self, b, fn, reqs_extra=""):
        with open(os.path.join(b, "hard/spec/phi.json")) as f:
            phi = json.load(f)
        fn(phi)
        toy.write_json(b, "hard/spec/phi.json", phi)
        if reqs_extra:
            toy.write(b, "hard/spec/requirements.md", toy.REQUIREMENTS + reqs_extra)

    def cov(self, b):
        out = os.path.join(b, "cov.json")
        r = tool("coverage.py", b, "--out", out)
        with open(out) as f:
            return r, json.load(f)

    def test_matches_verifier_recomputation(self):
        with open(os.path.join(self.pristine, "evidence/coverage.json")) as f:
            stored = json.load(f)
        self.assertTrue(stored["total"])
        self.assertTrue(self.run_snap(self.pristine)["L2"]["coverage"]["stored_coverage_matches"])

    def test_gaps_both_ways_exit_zero(self):
        b = self.fresh()
        self.edit_phi(b, lambda phi: phi["claims"][1].__setitem__("requirements", []),
                      "- **R4.** A requirement nobody covers.\n- **R5.** A declared blind spot.\n")
        self.edit_phi(b, lambda phi: phi.__setitem__("declared_blind_spots",
                                                     [{"requirement": "R5", "reason": "Stage C open"},
                                                      {"requirement": "R9", "reason": "typo"}]))
        r, cov = self.cov(b)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["uncovered_undeclared"], ["R2", "R4"])
        self.assertEqual(cov["unreferenced_clauses"], ["claim-02"])
        self.assertEqual(cov["declared_blind_spots"], {"R5": {"reason": "Stage C open", "partial": False},
                                                       "R9": {"reason": "typo", "partial": False}})
        self.assertEqual((cov["covered"], cov["partial"], cov["blind"]), (["R1", "R3"], [], ["R2", "R4", "R5"]))
        self.assertEqual(cov["blind_spots_not_in_requirements"], ["R9"])
        self.assertFalse(cov["total"])

    def test_partial_is_first_class_and_never_total(self):
        """WS-H's real shape: R4/R5 claimed AND listed as partial blind spots."""
        b = self.fresh()
        self.edit_phi(b, lambda phi: (phi["claims"][0]["requirements"].append("R4"),
                                      phi["claims"][1]["requirements"].append("R5"),
                                      phi.__setitem__("declared_blind_spots", [
                                          {"requirement": "R4", "partial": True, "reason": "only the revert path"},
                                          {"requirement": "R5", "reason": "declared blind but claimed"},
                                          {"requirement": "R6", "reason": "Stage C open"}])),
                      "- **R4.** Partly covered.\n- **R5.** Inconsistent.\n- **R6.** Blind.\n")
        r, cov = self.cov(b)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(cov["requirement_state"],
                         {"R1": "covered", "R2": "covered", "R3": "covered", "R4": "partial",
                          "R5": "partial", "R6": "blind"})
        self.assertEqual((cov["covered"], cov["partial"], cov["blind"]), (["R1", "R2", "R3"], ["R4", "R5"], ["R6"]))
        self.assertEqual(cov["blind_spots_actually_covered"], ["R5"])  # partial flag missing: flagged
        self.assertEqual(cov["uncovered_undeclared"], [])
        self.assertEqual(cov["declared_blind_spots"]["R4"], {"reason": "only the revert path", "partial": True})
        self.assertFalse(cov["total"])
        self.assertIn("2 partial", r.stdout)
        os.replace(os.path.join(b, "cov.json"), os.path.join(b, "evidence/coverage.json"))
        toy.approve(b, self.keys["oracle"])
        toy.write_manifest(b, self.keys["producer"])
        l2 = self.run_snap(b)["L2"]["coverage"]
        self.assertEqual({k: l2[k] for k in ("covered", "partial", "blind", "total")},
                         {k: cov[k] for k in ("covered", "partial", "blind", "total")})
        self.assertTrue(l2["stored_coverage_matches"])

    def test_malformed_input_exit_one_nothing_written(self):
        b = self.fresh()
        toy.write(b, "hard/spec/phi.json", "{not json")
        out = os.path.join(b, "cov.json")
        r = tool("coverage.py", b, "--out", out)
        self.assertEqual(r.returncode, 1)
        self.assertFalse(os.path.exists(out))


VIOLATION_REPLAY = """#!/bin/sh
od -An -tx1 mutant.bin | tr -d ' \\n'; echo
echo "TCG-VIOLATION: slot 1 == 0 after run, claim-02 requires 1"
"""
RESIDUAL_REPLAY = """#!/bin/sh
echo "Claim unifies with the destination but the implication check has failed"
exit 1
"""
ACCEPT_REPLAY = "#!/bin/sh\necho '#Top'\n"
UNSTABLE_REPLAY = "#!/bin/sh\nod -An -tx1 -N8 /dev/urandom\necho 'cannot be rewritten further'\nexit 1\n"


class MutantWitness(helpers.ToyCase):
    def add(self, b, name, replay, mutant=b"\x60\x00\x00"):
        d = f"evidence/mutants/{name}/"
        toy.write(b, d + "mutant.bin", mutant)
        toy.write(b, d + "replay.sh", replay)

    def record(self, b, name, claim, kind):
        return tool("mutant_witness.py", "record", b, name, "--claim", claim, "--kind", kind)

    def test_three_kinds_stay_distinct_in_L2(self):
        b = self.fresh()
        self.add(b, "claim-02", VIOLATION_REPLAY)
        self.add(b, "lemma-01", RESIDUAL_REPLAY)
        for name, claim, kind in (("claim-02", "claim-02", "concrete_trace_violation"),
                                  ("lemma-01", "lemma-01", "not_accept")):
            r = self.record(b, name, claim, kind)
            self.assertEqual(r.returncode, 0, r.stdout)
        self.assertEqual(tool("mutant_witness.py", "check", b).returncode, 0)
        toy.write_manifest(b, self.keys["producer"])
        l2 = self.run_snap(b)["L2"]
        self.assertEqual({m["claim"]: m["outcome"] for m in l2["mutants"]},
                         {"claim-01": "refute", "claim-02": "concrete_trace_violation", "lemma-01": "not_accept"})
        self.assertEqual(l2["no_witness"], ["lemma-01"])  # not_accept is never a witness
        cv = [m for m in l2["mutants"] if m["claim"] == "claim-02"][0]
        self.assertIn("claim-02 requires 1", cv["violation"])

    def test_record_refuses_wrong_kind_unstable_output_identical_mutant(self):
        b = self.fresh()
        self.add(b, "a", ACCEPT_REPLAY)
        self.assertIn("rule does not hold", self.record(b, "a", "claim-02", "refute").stdout)
        self.assertIn("rule does not hold", self.record(b, "a", "claim-02", "not_accept").stdout)
        self.add(b, "u", UNSTABLE_REPLAY)
        self.assertIn("not byte-stable", self.record(b, "u", "claim-02", "refute").stdout)
        self.add(b, "same", RESIDUAL_REPLAY, mutant=toy.ARTIFACT)
        self.assertIn("byte-identical to the artefact", self.record(b, "same", "claim-02", "not_accept").stdout)
        for n in ("a", "u", "same"):
            self.assertFalse(os.path.exists(os.path.join(b, f"evidence/mutants/{n}/refutation.json")))

    def test_verifier_rejects_identical_mutant(self):
        b = self.fresh()
        self.add(b, "same", RESIDUAL_REPLAY, mutant=toy.ARTIFACT)
        toy.write_json(b, "evidence/mutants/same/refutation.json",
                       {"claim": "claim-02", "kind": "refute", "output_sha256": "0" * 64})
        toy.write_manifest(b, self.keys["producer"])
        m = [m for m in self.run_snap(b)["L2"]["mutants"] if m["dir"].endswith("/same/")][0]
        self.assertEqual(m["outcome"], "malformed")


class ConsumerReadme(helpers.ToyCase):
    def test_self_hash_recipe_matches(self):
        verifier = os.path.dirname(helpers.HERE)
        with open(os.path.join(verifier, "README.md"), encoding="utf-8") as f:
            text = f.read()
        recipe = re.search(r"<!-- self-hash-recipe -->\n```sh\n(.*?)```", text, re.DOTALL).group(1)
        out = subprocess.run(["sh", "-c", recipe], cwd=verifier, capture_output=True, text=True, check=True)
        self.assertEqual(out.stdout.strip(), ladder.verifier_hash())


if __name__ == "__main__":
    import unittest
    unittest.main()
