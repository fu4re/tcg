"""WP7 generator loop: prompt rendering, feedback, selection, and the candidate
post-processing end to end on canned replies (no network, no API key)."""
import contextlib
import copy
import io
import json
import re
import sys
import textwrap
import tempfile
import unittest
from pathlib import Path

from tests._util import ROOT, core, speclint

sys.path.insert(0, str(ROOT / "generator"))
import loop  # noqa: E402

FIX = ROOT / "tests" / "fixtures" / "generator" / "canned_replies.json"
MUTANT_IDS = [m["id"] for m in json.loads(loop.MUTANTS.read_text())["mutants"] if m["status"] == "included"]
LABELS = {m["id"]: m["fault_class"] for m in json.loads(loop.MUTANTS.read_text())["mutants"]}


class FakeClient:
    sdk_version = "fake"

    def __init__(self, replies):
        self.replies = list(replies)
        self.bodies = []

    def create(self, body):
        self.bodies.append(copy.deepcopy(body))
        return copy.deepcopy(self.replies.pop(0))


def score(acc, killed=0, errors=(), reason=None):
    return {"acc": acc, "check_reason": reason, "errors": list(errors),
            "ms_cert": {"killed": killed, "total": len(MUTANT_IDS)},
            "kill_set": MUTANT_IDS[:killed], "survivors": MUTANT_IDS[killed:], "not_proved": []}


class Prompts(unittest.TestCase):
    def test_dry_run_all_conditions_no_network(self):
        for c in loop.CONDITIONS:
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                code = loop.run(c, 0, 3, 2, Path("/nonexistent-out"), dry_run=True, client=None)
            self.assertEqual(code, 0)
            self.assertIn("round-1 request", buf.getvalue())
            self.assertIn("EXAMPLE score", buf.getvalue())

    def test_round1_shows_contract_and_intent_not_mutants_or_ladder(self):
        p = loop.round1_prompt(3)
        self.assertIn("function mint(address to, uint256 amount) public onlyOwner", p)
        self.assertIn("discriminating power", p)
        self.assertNotIn("$", p)
        everything = loop.system_prompt() + p
        for f in sorted((ROOT / "subjects" / "capped_token" / "mutants").glob("m*.sol")):
            self.assertNotIn(f.stem, everything)
        ladder_checks = set()
        for f in sorted((ROOT / "subjects" / "capped_token" / "specs").glob("phi_*.sol")):
            ladder_checks |= set(re.findall(r"function (check_\w+)", f.read_text()))
        for name in ladder_checks:
            self.assertNotIn(name, everything, name)

    def test_system_prompt_examples_are_valid_specs(self):
        sysp = loop.system_prompt()
        checks = re.findall(r"```solidity\n( *function check_.*?\n *\})\n *```", sysp, re.S)
        self.assertEqual(len(checks), 3)
        body = "\n\n".join(textwrap.indent(textwrap.dedent(c), "    ") for c in checks)
        spec = ('// SPDX-License-Identifier: MIT\npragma solidity 0.8.35;\n\nimport "./CappedToken.sol";\n\n'
                "contract Spec is CappedToken {\n    constructor(uint256 cap_) CappedToken(cap_) {}\n\n"
                + body + "\n}\n")
        self.assertEqual(speclint.lint_spec(spec), [])
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "Spec.sol"
            p.write_text(spec)
            r = core.smtcheck(p, loop.B, 20000, 300)
        self.assertEqual(r.verdict, "Accept", r.targets)

    def test_prompt_hashes_cover_every_file(self):
        self.assertEqual(sorted(loop.prompt_hashes()), sorted(p.name for p in loop.PROMPTS.glob("*.md")))


class Feedback(unittest.TestCase):
    def test_f0_reveals_no_score(self):
        fb = loop.feedback_prompt("f0", 1, 3, score("Refute", 3), LABELS)
        self.assertIn("not accepted", fb)
        self.assertNotIn("ms_cert", fb)
        self.assertNotRegex(fb, r"\b3 of 8\b")
        for i in MUTANT_IDS:
            self.assertNotIn(i[:12], fb)

    def test_fM_reveals_score_only(self):
        fb = loop.feedback_prompt("fM", 2, 3, score("Accept", 3), LABELS)
        self.assertIn("Checker verdict: Accept", fb)
        self.assertIn("3 of 8", fb)
        self.assertIn("ms_cert = 3/8", fb)
        for i in MUTANT_IDS:
            self.assertNotIn(i[:12], fb)
        self.assertIn("Revisions left after this one: 1", fb)

    def test_fMplus_lists_survivor_ids_and_fault_classes_only(self):
        fb = loop.feedback_prompt("fMplus", 1, 3, score("Accept", 2), LABELS)
        for i in MUTANT_IDS[2:]:
            self.assertIn(f"- {i[:12]} ({LABELS[i]})", fb)
        for i in MUTANT_IDS[:2]:
            self.assertNotIn(i[:12], fb)
        for f in sorted((ROOT / "subjects" / "capped_token" / "mutants").glob("m*.sol")):
            self.assertNotIn(f.stem, fb)
        self.assertNotIn("function", fb)

    def test_lint_errors_are_shown_under_every_condition(self):
        s = score("lint_rejected", 0, ["S7 line 9: write to token state `totalSupply`"])
        for c in loop.CONDITIONS:
            self.assertIn("S7 line 9", loop.feedback_prompt(c, 1, 3, s, LABELS))


class Selection(unittest.TestCase):
    def test_f0(self):
        self.assertEqual(loop.select("f0", [score("Refute", 7), score("Accept", 0)]), 1)
        self.assertEqual(loop.select("f0", [score("lint_rejected", 0, ["a", "b"]),
                                            score("lint_rejected", 0, ["a"])]), 1)
        self.assertEqual(loop.select("f0", [score("lint_rejected", 0, ["a"]), score("Unknown", 5)]), 1)
        # the score is invisible under f0: ties go to the first candidate
        self.assertEqual(loop.select("f0", [score("Accept", 1), score("Accept", 7)]), 0)

    def test_fM_and_fMplus(self):
        for c in ("fM", "fMplus"):
            self.assertEqual(loop.select(c, [score("Accept", 1), score("Accept", 4)]), 1)
            self.assertEqual(loop.select(c, [score("Refute", 7), score("Accept", 0)]), 1)
            self.assertEqual(loop.select(c, [score("Unknown", 2), score("Refute", 5)]), 1)
            self.assertEqual(loop.select(c, [score("Accept", 3), score("Accept", 3)]), 0)


class EndToEnd(unittest.TestCase):
    def test_canned_trajectory(self):
        replies = json.loads(FIX.read_text())["replies"]
        fake = FakeClient(replies)
        with tempfile.TemporaryDirectory() as t:
            out = Path(t)
            with contextlib.redirect_stdout(io.StringIO()):
                code = loop.run("fM", 7, 2, 2, out, dry_run=False, client=fake)
            self.assertEqual(code, 0)
            tdir = out / "fM" / "seed_7"
            s11 = json.loads((tdir / "round_1" / "cand_1" / "score.json").read_text())
            self.assertEqual(s11["acc"], "lint_rejected")
            self.assertTrue(any(e.startswith("S4") for e in s11["errors"]))
            self.assertFalse((tdir / "round_1" / "cand_1" / "check.json").exists())
            s12 = json.loads((tdir / "round_1" / "cand_2" / "score.json").read_text())
            self.assertEqual((s12["acc"], s12["ms_cert"]["killed"]), ("Accept", 0))
            self.assertEqual(json.loads((tdir / "round_1" / "selected.json").read_text())["selected"], 2)
            for j, why in ((1, "0 `solidity` code blocks"), (2, "2 `solidity` code blocks")):
                s = json.loads((tdir / "round_2" / f"cand_{j}" / "score.json").read_text())
                self.assertEqual(s["acc"], "lint_rejected")
                self.assertIn(why, s["errors"][0])
            # round 2 replays round 1's selected reply verbatim, then the feedback
            msgs = fake.bodies[2]["messages"]
            self.assertEqual([m["role"] for m in msgs], ["user", "assistant", "user"])
            self.assertEqual(msgs[1]["content"], replies[1]["content"])
            self.assertIn("Mutation score: 0 of 8", msgs[2]["content"])
            self.assertEqual(fake.bodies[0]["messages"], fake.bodies[1]["messages"])
            self.assertNotIn("temperature", fake.bodies[0])
            self.assertEqual(fake.bodies[0]["output_config"], {"effort": "high"})
            self.assertEqual(fake.bodies[0]["max_tokens"], 16000)
            ev = json.loads((tdir / "events.json").read_text())
            self.assertEqual([r["acc"] for r in ev["rounds"]], ["Accept", "lint_rejected"])
            self.assertEqual(ev["rounds"][1]["kill_set"], [])
            self.assertEqual(ev["events"][0]["kind"], "unchanged")
            self.assertGreaterEqual(ev["pool"]["size"], 7)  # contains the ladder's W*
            meta = json.loads((tdir / "trajectory.json").read_text())
            self.assertEqual(meta["result"]["status"], "bundle_refused")
            self.assertEqual(meta["tokens"], {"input": 400, "output": 200, "thinking": 0, "total": 600})
            self.assertTrue((tdir / "trajectory.md").is_file())
            # refuses to overwrite an existing trajectory
            with contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(loop.run("fM", 7, 2, 2, out, dry_run=False, client=FakeClient(replies)), 1)

    def test_key_scan(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "x.json"
            p.write_text('{"a": "FAKE-KEY-FOR-SCAN-TEST-123"}')
            with self.assertRaises(loop.LoopError):
                loop.assert_no_key([Path(t)], "FAKE-KEY-FOR-SCAN-TEST-123")
            loop.assert_no_key([Path(t)], "FAKE-KEY-OTHER")


class CodegenError(unittest.TestCase):
    """A spec that lints and passes SMTChecker's compile (no code generation)
    but whose Spec over b does not compile to bytecode ("Stack too deep") is
    scored as compile_error before Check, never crashes the trajectory
    (runs/v3/vat/fM/seed_0_aborted_stack_too_deep)."""

    def test_stack_too_deep_is_compile_error_without_check(self):
        locs = "\n".join(f"        uint256 v{i} = x + {i};" for i in range(16))
        s = " + ".join(f"v{i}" for i in range(16))
        spec = ('// SPDX-License-Identifier: MIT\npragma solidity 0.8.35;\n\nimport "./CappedToken.sol";\n\n'
                "contract Spec is CappedToken {\n    constructor(uint256 cap_) CappedToken(cap_) {}\n\n"
                "    /// Deep: many locals.\n"
                "    function check_deep(address a, address b, uint256 x, uint256 y) external {\n"
                f"        require(x < 1000 && y < 1000 && a != b);\n{locs}\n"
                f"        assert({s} + balanceOf[a] >= {s});\n    }}\n}}\n")
        self.assertEqual(speclint.lint_spec(spec), [])
        with tempfile.TemporaryDirectory() as t:
            cdir = Path(t) / "cand_1"
            sc = loop.process_candidate(f"Here it is.\n\n```solidity\n{spec}```\n", cdir, [{"id": "x"}], "end_turn")
            self.assertEqual((sc["acc"], sc["check_reason"]), ("Unknown", "compile_error"))
            self.assertIn("Stack too deep", sc["errors"][0])
            self.assertFalse((cdir / "check.json").exists())
            self.assertEqual(json.loads((cdir / "witnesses.json").read_text()), [])
            self.assertIn("The file does not compile", loop.feedback_prompt("fM", 1, 3, sc, LABELS))


class Isolation(unittest.TestCase):
    def test_judge_path_never_imports_the_generator(self):
        for f in sorted((ROOT / "tools").glob("*.py")):
            text = f.read_text()
            self.assertNotRegex(text, r"^\s*(import|from)\s+(loop|anthropic|generator)\b", f.name)


if __name__ == "__main__":
    unittest.main()


class ProtocolRecordsPrompts(unittest.TestCase):
    def test_protocol_hashes_match_prompt_files(self):
        text = (ROOT / "protocol.md").read_text()
        for name, h in loop.prompt_hashes().items():
            self.assertIn(f"| `generator/prompts/{name}` | `{h}` |", text, name)
        self.assertIn(f"`{loop.prompts_sha256()}`", text)


class VatPrompts(unittest.TestCase):
    """Subject vat (protocol v3): its own system and round-1 prompts, the
    shared feedback templates, and the readiness gate for live runs."""

    def setUp(self):
        self.saved = (loop.SUBJECT, loop.B, loop.INTENT, loop.MUTANTS, loop.FROZEN)
        loop.SUBJECT = core.load_subject("vat")
        loop.B, loop.INTENT = loop.SUBJECT.source_path, loop.SUBJECT.intent_path
        loop.MUTANTS = loop.SUBJECT.mutants_dir / "mutants.json"
        loop.FROZEN = loop.frozen_for("vat")

    def tearDown(self):
        loop.SUBJECT, loop.B, loop.INTENT, loop.MUTANTS, loop.FROZEN = self.saved

    def test_prompt_files_and_hashes(self):
        g = core.PROTOCOL["subjects"]["vat"]["generator"]
        self.assertEqual(loop.prompt_hashes(), g["prompts"])
        self.assertEqual(loop.prompts_sha256(), g["prompts_sha256"])
        self.assertEqual(loop.prompt_path("system.md"), ROOT / "subjects" / "vat" / "prompts" / "system.md")
        self.assertEqual(loop.prompt_path("feedback_fM.md"), loop.PROMPTS / "feedback_fM.md")
        cg = core.PROTOCOL["subjects"]["capped_token"]["generator"]
        for k in ("rounds", "k", "seeds", "conditions", "model", "output_config"):
            self.assertEqual(g[k], cg[k], k)
        # budget only: vat 64 000 (round-1 replies exhausted 16 000 in thinking), capped token unchanged
        self.assertEqual((g["max_tokens"], cg["max_tokens"]), (64000, 16000))
        self.assertEqual(loop.frozen_for("vat")["effort"], loop.frozen_for("capped_token")["effort"])

    def test_round1_embeds_vat_intent_and_signatures(self):
        p = loop.round1_prompt(3)
        self.assertIn("function frob(bytes32 i, address u, address v, address w, int dink, int dart) public", p)
        self.assertIn("Books balance", p)
        self.assertIn("`(bytes32 i, address u, int256 dx, int256 dy)`", p)
        self.assertNotIn("$", p)

    def test_system_prompt_examples_lint_and_accept(self):
        V = loop.SUBJECT
        checks = re.findall(r"```solidity\n( *function check_.*?\n *\})\n *```", loop.system_prompt(), re.S)
        self.assertEqual(len(checks), 3)
        spec = V.header() + "\n\n    ".join(textwrap.dedent(c).replace("\n", "\n    ") for c in checks) + "\n}\n"
        names = speclint.names_from_entry(core.compile_artifact(V.source_path, subject=V))
        self.assertEqual(speclint.lint_spec(spec, names, V), [])
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "Spec.sol"
            p.write_text(spec)
            r = core.smtcheck_isolated(p, V.source_path, core.CHECK_TIMEOUT_MS, core.CHECK_WALL_TIMEOUT_S, subject=V)
        self.assertEqual(r.verdict, "Accept", [(c["check"], c["result"]["reason"]) for c in r.checks])

    def test_dry_run_and_live_refusal_without_mutants_or_ladder(self):
        for c in loop.CONDITIONS:
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(loop.run(c, 0, 3, 2, Path("/nonexistent-out"), dry_run=True, client=None), 0)
        if loop.MUTANTS.is_file() and any(loop.ladder_pool()):
            self.skipTest("vat mutants and ladder present: nothing to refuse")
        err = io.StringIO()
        with contextlib.redirect_stderr(err), tempfile.TemporaryDirectory() as t:
            self.assertEqual(loop.run("fM", 0, 3, 2, Path(t), dry_run=False, client=FakeClient([])), 1)
        self.assertIn("not ready for a live run", err.getvalue())
