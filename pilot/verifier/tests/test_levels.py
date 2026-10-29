"""Per-level checks of the verifier on the toy bundle (task 06)."""
from __future__ import annotations

import http.server
import json
import os
import re
import subprocess
import sys
import threading
import unittest

import helpers
from helpers import toy
from tcgverify import canon
from tcgverify.keccak import keccak256


class FakeRpc:
    """A local JSON-RPC endpoint serving toy chain state; records every request."""

    def __init__(self, code: dict | None = None, chain_id: int = 1, block: dict | None = None):
        self.code = {a.lower(): c for a, c in {toy.SUBJECT: toy.ARTIFACT, toy.WETH: toy.WETH_CODE,
                                               toy.VAT: toy.VAT_CODE, **(code or {})}.items()}
        self.chain_id, self.block, self.log, self.agents = chain_id, block or toy.BLOCK, [], set()
        rpc = self

        class H(http.server.BaseHTTPRequestHandler):
            def do_POST(self):
                req = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
                rpc.log.append((req["method"], req["params"]))
                rpc.agents.add(self.headers.get("User-Agent"))
                body = json.dumps({"jsonrpc": "2.0", "id": req["id"], "result": rpc.answer(req)}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def log_message(self, *a):
                pass

        self.server = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.server.serve_forever, daemon=True).start()
        self.url = f"http://127.0.0.1:{self.server.server_port}"

    def answer(self, req):
        m, p = req["method"], req["params"]
        if m == "eth_chainId":
            return hex(self.chain_id)
        if m == "eth_getBlockByNumber":
            b = self.block
            return {"number": hex(b["number"]), "hash": b["hash"], "timestamp": hex(b["timestamp"])}
        if m == "eth_getCode":
            return "0x" + self.code.get(p[0].lower(), b"").hex()
        return None

    def close(self):
        self.server.shutdown()
        self.server.server_close()


class L0Identity(helpers.ToyCase):
    def rpc_run(self, rpc, bundle=None):
        return helpers.verify(bundle or self.pristine, self.keys, ["--rpc", rpc.url])

    def test_chain_read_happens(self):
        rpc = FakeRpc()
        try:
            r = self.rpc_run(rpc)
        finally:
            rpc.close()
        self.assertEqual(r["L0"]["status"], "pass")
        reads = [p for m, p in rpc.log if m == "eth_getCode"]
        self.assertIn([toy.SUBJECT, hex(toy.BLOCK["number"])], reads)
        self.assertIn([toy.WETH, hex(toy.BLOCK["number"])], reads)
        self.assertIn("eth_chainId", [m for m, _ in rpc.log])
        self.assertEqual(rpc.agents, {"tcg-verifier/0.1"})  # not urllib's default (drpc 403s it)
        ident = r["L0"]["checks"]["identity"]
        self.assertEqual(ident["chain_keccak"], "0x" + keccak256(toy.ARTIFACT).hex())
        self.assertTrue(any("JSON-RPC" in o for o in r["outside_bundle"]))

    def test_artifact_substitution_on_chain_fails_L0(self):
        """v3 section 10: the deployment holds b' != b. Bundle untouched, chain differs."""
        rpc = FakeRpc(code={toy.SUBJECT: toy.WETH_CODE})
        try:
            r = self.rpc_run(rpc)
        finally:
            rpc.close()
        ident = r["L0"]["checks"]["identity"]
        self.assertEqual(r["L0"]["status"], "fail")
        self.assertFalse(ident["ok"])
        self.assertEqual(ident["chain_keccak"], "0x" + keccak256(toy.WETH_CODE).hex())
        self.assertEqual(ident["declared"], ident["artifact_keccak"])  # bundle is self-consistent
        self.assertEqual(r["L1"]["status"], "pass")  # the proof stands; its transfer does not

    def test_no_code_at_address_fails(self):
        rpc = FakeRpc(code={toy.SUBJECT: b""})
        try:
            r = self.rpc_run(rpc)
        finally:
            rpc.close()
        self.assertFalse(r["L0"]["checks"]["identity"]["ok"])

    def test_unreachable_rpc_fails_closed(self):
        r = helpers.verify(self.pristine, self.keys, ["--rpc", "http://127.0.0.1:9"])
        self.assertEqual(r["L0"]["status"], "fail")
        self.assertIn("chain read failed", r["L0"]["checks"]["identity"]["detail"])

    def test_environment_external_code_drift_names_field(self):
        rpc = FakeRpc(code={toy.VAT: toy.VAT_CODE + b"\x00"})
        try:
            r = self.rpc_run(rpc)
        finally:
            rpc.close()
        env = r["L0"]["checks"]["environment"]
        self.assertEqual(r["L0"]["status"], "fail")
        self.assertEqual([e["name"] for e in env["external_code"] if not e["ok"]], ["Vat"])
        self.assertTrue(r["L0"]["checks"]["identity"]["ok"])

    def test_wrong_chain_and_wrong_fork(self):
        snap = toy.snapshot(os.path.join(self._tmp.name, "snap-chain"), chain_id=10)
        r = self.run_snap(self.pristine, snap=snap)
        self.assertFalse(r["L0"]["checks"]["environment"]["chain_id"]["ok"])
        prague = dict(toy.BLOCK, timestamp=1750000000)
        snap = toy.snapshot(os.path.join(self._tmp.name, "snap-fork"), block=prague)
        r = self.run_snap(self.pristine, snap=snap)
        fork = r["L0"]["checks"]["environment"]["fork"]
        self.assertEqual((fork["derived_from_block"], fork["ok"]), ("prague", False))

    def test_snapshot_at_other_block_fails(self):
        snap = toy.snapshot(os.path.join(self._tmp.name, "snap-blk"), block=dict(toy.BLOCK, number=1))
        r = self.run_snap(self.pristine, snap=snap)
        self.assertEqual(r["L0"]["status"], "fail")

    def test_untrusted_producer_key(self):
        other = toy.make_keys(os.path.join(self._tmp.name, "other-keys"))
        keys = dict(self.keys, producer_pub=other["producer_pub"])
        r = helpers.verify(self.pristine, keys, ["--state-snapshot", self.snap])
        sig = r["L0"]["checks"]["producer_sig"]
        self.assertFalse(sig["ok"])
        self.assertFalse(sig["signature_valid_under_supplied_key"])


class L1Checks(helpers.ToyCase):
    def edit_tb(self, bundle, fn):
        with open(os.path.join(bundle, "trusted_base.json")) as f:
            tb = json.load(f)
        fn(tb)
        toy.write_json(bundle, "trusted_base.json", tb)
        toy.resign(bundle, self.keys["producer"])

    def claim(self, r, cid):
        return [c for c in r["L1"]["claims"] if c["claim"] == cid]

    def test_refused_on_empty_assumptions(self):
        b = self.fresh()
        self.edit_tb(b, lambda tb: tb.__setitem__("assumptions", []))
        r = self.run_snap(b)
        self.assertEqual(r["L1"]["status"], "refused")
        self.assertEqual(r["L1"]["claims"], [])
        self.assertEqual(r["L1"]["refused_reason"], "empty or incomplete assumption ledger")

    def test_refused_on_unclosed_ledger(self):
        b = self.fresh()
        self.edit_tb(b, lambda tb: tb.__setitem__("assumptions", tb["assumptions"][:3]))
        r = self.run_snap(b)
        self.assertEqual(r["L1"]["status"], "refused")
        self.assertIn("annotation simp-01 not in trusted_base.assumptions", r["L1"]["refused_detail"])

    def test_refused_when_risk_missing(self):
        b = self.fresh()
        self.edit_tb(b, lambda tb: tb["assumptions"][2].pop("risk_if_false"))
        self.assertEqual(self.run_snap(b)["L1"]["status"], "refused")

    def test_image_digest_mismatch_is_not_refute(self):
        r = self.run_snap(self.pristine, env=helpers.fake_env(TCG_FAKE_DOCKER_ID="sha256:" + "dd" * 32))
        results = {c["result"] for c in r["L1"]["claims"] if c["checker"] == "kevm-prove"}
        self.assertEqual(results, {"checker_hash_mismatch"})
        self.assertEqual(r["L1"]["status"], "fail")

    def test_image_digest_checked_before_run(self):
        log = os.path.join(self._tmp.name, "docker-mismatch.log")
        self.run_snap(self.pristine, env=helpers.fake_env(TCG_FAKE_DOCKER_ID="sha256:" + "dd" * 32,
                                                          TCG_FAKE_DOCKER_LOG=log))
        with open(log) as f:
            calls = [json.loads(l)[0] for l in f]
        self.assertNotIn("run", calls)

    def test_docker_absent_is_unavailable(self):
        env = helpers.fake_env()
        env["PATH"] = os.pathsep.join(p for p in env["PATH"].split(os.pathsep)
                                      if p != toy.FAKEBIN and not os.path.exists(os.path.join(p, "docker")))
        r = self.run_snap(self.pristine, env=env)
        self.assertEqual({c["result"] for c in r["L1"]["claims"] if c["checker"] == "kevm-prove"},
                         {"checker_unavailable"})

    def test_stuck_claim_refutes_and_residual_is_unknown(self):
        for marker, want in (("TOY-STUCK", "refute"), ("something else", "unknown")):
            b = self.fresh()
            toy.write_claim(b, "claim-02", marker + "\n")
            toy.write_phi(b)
            toy.approve(b, self.keys["oracle"])
            toy.resign(b, self.keys["producer"])
            r = self.run_snap(b)
            self.assertEqual(self.claim(r, "claim-02")[0]["result"], want)
            self.assertEqual(r["L1"]["status"], "fail")
            self.assertEqual(r["L3"]["status"], "pass")

    def test_forbidden_kprove_args_refused(self):
        b = self.fresh()
        p = os.path.join(b, "hard/certs/claim-01.rediscuss.json")
        with open(p) as f:
            inv = json.load(f)
        inv["kprove_args"] = ["--definition", "/evil"]
        toy.write_json(b, "hard/certs/claim-01.rediscuss.json", inv)
        toy.resign(b, self.keys["producer"])
        self.assertEqual(self.claim(self.run_snap(b), "claim-01")[0]["result"], "malformed")

    def test_rediscuss_record_fields_checked_for_consistency(self):
        cases = {"claim_file_sha256": ("0" * 64, "malformed"), "image_id": ("sha256:" + "ee" * 32, "malformed"),
                 "argv": (["rm", "-rf", "/"], "accept")}  # argv is informational, never executed
        for field, (value, want) in cases.items():
            b = self.fresh()
            p = os.path.join(b, "hard/certs/claim-01.rediscuss.json")
            with open(p) as f:
                inv = json.load(f)
            inv[field] = value
            toy.write_json(b, "hard/certs/claim-01.rediscuss.json", inv)
            toy.resign(b, self.keys["producer"])
            self.assertEqual(self.claim(self.run_snap(b), "claim-01")[0]["result"], want, field)

    def test_lean_custom_axiom_and_sorry_rejected(self):
        cases = {"-- FAKE-AXIOMS: propext, Toy.myAxiom": ["Toy.myAxiom"],
                 "-- FAKE-AXIOMS: sorryAx": ["sorryAx"]}
        for marker, extra in cases.items():
            b = self.fresh()
            toy.write(b, "hard/certs/lean/Toy/Lemma01.lean", toy.LEMMA_SRC + marker + "\n")
            toy.resign(b, self.keys["producer"])
            c = self.claim(self.run_snap(b), "lemma-01")[0]
            self.assertEqual((c["result"], c["non_standard_axioms"]), ("not_accept", extra))

    def test_lean_source_admit_rejected_even_if_axioms_clean(self):
        b = self.fresh()
        toy.write(b, "hard/certs/lean/Toy/Lemma01.lean",
                  "namespace Toy\ntheorem lemma01 : 2 + 2 = 4 := by sorry\nend Toy\n")
        toy.resign(b, self.keys["producer"])
        c = self.claim(self.run_snap(b), "lemma-01")[0]
        self.assertEqual((c["result"], c["admits"]), ("not_accept", 1))

    def test_lean_admit_in_comment_ignored(self):
        b = self.fresh()
        toy.write(b, "hard/certs/lean/Toy/Lemma01.lean", toy.LEMMA_SRC + "-- no sorry here\n/- admit -/\n")
        toy.resign(b, self.keys["producer"])
        self.assertEqual(self.claim(self.run_snap(b), "lemma-01")[0]["result"], "accept")

    def test_lean_build_failure_not_accept(self):
        b = self.fresh()
        toy.write(b, "hard/certs/lean/Toy/Lemma01.lean", toy.LEMMA_SRC + "-- FAKE-BUILD-FAIL\n")
        toy.resign(b, self.keys["producer"])
        self.assertEqual(self.claim(self.run_snap(b), "lemma-01")[0]["result"], "not_accept")

    def test_trusted_base_cannot_widen_axioms(self):
        b = self.fresh()
        toy.write(b, "hard/certs/lean/Toy/Lemma01.lean", toy.LEMMA_SRC + "-- FAKE-AXIOMS: Toy.myAxiom\n")
        self.edit_tb(b, lambda tb: tb.__setitem__("lean_axioms", ["propext", "Toy.myAxiom"]))
        r = self.run_snap(b)
        self.assertEqual(self.claim(r, "lemma-01")[0]["result"], "not_accept")
        self.assertEqual(r["L1"]["checks"]["lean_axiom_whitelist"], ["propext"])

    def test_lean_binary_hash_mismatch(self):
        b = self.fresh()
        self.edit_tb(b, lambda tb: [c.__setitem__("hash", "0" * 64) for c in tb["checker"] if c["name"] == "lean"])
        self.assertEqual(self.claim(self.run_snap(b), "lemma-01")[0]["result"], "checker_hash_mismatch")

    def test_verifier_hash_mismatch_fails_L1(self):
        b = self.fresh()
        self.edit_tb(b, lambda tb: [c.__setitem__("hash", "0" * 64) for c in tb["checker"]
                                    if c["name"] == "tcg-verifier"])
        r = self.run_snap(b)
        self.assertFalse(r["L1"]["checks"]["verifier_hash"]["ok"])
        self.assertEqual(r["L1"]["status"], "fail")

    def test_docker_limits_reach_docker_run_and_bad_ones_rejected(self):
        log = os.path.join(self._tmp.name, "docker-limits.log")
        r = self.run_snap(self.pristine, env=helpers.fake_env(TCG_FAKE_DOCKER_LOG=log),
                          extra=["--docker-limit=--memory=6g", "--docker-limit=--cpus=2"])
        with open(log) as f:
            runs = [json.loads(l) for l in f if json.loads(l)[0] == "run"]
        self.assertTrue(runs)
        self.assertTrue(all(a[2:4] == ["--memory=6g", "--cpus=2"] for a in runs))
        self.assertEqual(r["docker_limits"], ["--memory=6g", "--cpus=2"])
        with self.assertRaises(AssertionError):  # verify.py exits 2
            self.run_snap(self.pristine, extra=["--docker-limit=--network=host"])

    def test_variant_B_does_not_use_kevm(self):
        log = os.path.join(self._tmp.name, "docker-B.log")
        r = self.run_snap(self.pristine, variant="B", env=helpers.fake_env(TCG_FAKE_DOCKER_LOG=log))
        self.assertFalse(os.path.exists(log))
        self.assertEqual({c["claim"]: c["result"] for c in r["L1"]["claims"]},
                         {"claim-01": "not_checked", "claim-02": "not_checked", "lemma-01": "accept"})
        self.assertEqual(r["L1"]["status"], "fail")
        self.assertFalse(any("docker" in o for o in r["outside_bundle"]))

    def test_outside_bundle_variant_A(self):
        r = self.run_snap(self.pristine)
        self.assertFalse(r["self_contained"])
        self.assertTrue(any(o.startswith("KEVM checker docker image " + toy.FAKE_IMAGE_ID) for o in r["outside_bundle"]))
        self.assertTrue(any(o.startswith("consumer state snapshot") for o in r["outside_bundle"]))


class L2Checks(helpers.ToyCase):
    def test_baseline(self):
        l2 = self.run_snap(self.pristine)["L2"]
        self.assertTrue(l2["coverage_total"])
        self.assertTrue(l2["pre_witness_replays"])
        self.assertEqual([m["outcome"] for m in l2["mutants"]], ["refute"])
        self.assertEqual(l2["no_witness"], ["claim-02", "lemma-01"])
        self.assertTrue(l2["coverage"]["stored_coverage_matches"])

    def test_blind_spot_reported_not_total(self):
        b = self.fresh()
        toy.write(b, "hard/spec/requirements.md", toy.REQUIREMENTS + "- **R4.** Not covered by any claim.\n")
        toy.approve(b, self.keys["oracle"])
        toy.resign(b, self.keys["producer"])
        cov = self.run_snap(b)["L2"]["coverage"]
        self.assertFalse(cov["total"])
        self.assertEqual(cov["uncovered_undeclared"], ["R4"])

    def test_no_exec_runs_nothing(self):
        r = self.run_snap(self.pristine, extra=["--no-exec"])
        self.assertFalse(r["L2"]["pre_witness_replays"])
        self.assertEqual(r["L2"]["mutants"][0]["outcome"], "not_run")
        self.assertEqual(r["L4"]["status"], "partial")
        self.assertFalse(r["executed_bundle_supplied_commands"])


class L3Checks(helpers.ToyCase):
    def test_pass(self):
        l3 = self.run_snap(self.pristine)["L3"]
        self.assertEqual((l3["status"], l3["signer"]), ("pass", "oracle"))
        self.assertEqual(l3["approved_hash"], l3["proven_hash"])

    def test_signed_by_producer(self):
        b = self.fresh()
        toy.approve(b, self.keys["producer"])
        toy.resign(b, self.keys["producer"])
        l3 = self.run_snap(b)["L3"]
        self.assertEqual((l3["status"], l3["reason"]), ("fail", "approval signed by producer"))

    def test_approved_then_weakened_shows_both_hashes(self):
        b = self.fresh()
        approved = canon.sha256_file(os.path.join(b, "hard/spec/phi.json"))
        with open(os.path.join(b, "hard/spec/phi.json")) as f:
            phi = json.load(f)
        phi["claims"][0]["post"] = "true"
        toy.write_json(b, "hard/spec/phi.json", phi)
        toy.resign(b, self.keys["producer"])
        l3 = self.run_snap(b)["L3"]
        self.assertEqual(l3["status"], "fail")
        self.assertEqual(l3["approved_hash"], approved)
        self.assertNotEqual(l3["proven_hash"], approved)

    def test_same_key_for_oracle_and_producer_fails(self):
        r = helpers.verify(self.pristine, self.keys, ["--state-snapshot", self.snap],
                           oracle_pub=self.keys["producer_pub"])
        self.assertIn("oracle key equals producer key", r["L3"]["reason"])


class L4Checks(helpers.ToyCase):
    def append_event(self, b, event):
        led = os.path.join(b, "provenance/ledger.jsonl")
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(helpers.HERE)), "tools"))
        import ledger
        ledger.append_event(led, event)

    def test_pass_and_counts(self):
        l4 = self.run_snap(self.pristine)["L4"]
        self.assertEqual((l4["status"], l4["events_total"], l4["events_replayed"]), ("pass", 3, 2))

    def test_fabricated_deterministic_event_mismatches(self):
        b = self.fresh()
        with open(os.path.join(b, "provenance/ledger.jsonl"), "rb") as f:
            ev = json.loads(f.read().split(b"\n")[0])
        ev["outputs"] = [{"path": "provenance/artifact.sha256", "sha256": "1" * 64}]
        for k in ("seq", "prev", "format"):
            ev.pop(k)
        self.append_event(b, ev)
        toy.resign(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertTrue(l4["chain_intact"])
        self.assertEqual(l4["status"], "fail")
        self.assertEqual([m["seq"] for m in l4["mismatches"]], [4])

    def test_broken_chain_fails(self):
        b = self.fresh()
        p = os.path.join(b, "provenance/ledger.jsonl")
        with open(p, "rb") as f:
            lines = f.read().split(b"\n")
        with open(p, "wb") as f:
            f.write(b"\n".join([lines[1], lines[0], lines[2], b""]))
        toy.resign(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual((l4["status"], l4["chain_intact"]), ("fail", False))

    def test_output_outside_bundle_not_replayed(self):
        b = self.fresh()
        with open(os.path.join(b, "provenance/ledger.jsonl"), "rb") as f:
            ev = json.loads(f.read().split(b"\n")[0])
        ev = {k: v for k, v in ev.items() if k not in ("seq", "prev", "format")}
        ev["outputs"] = [{"path": "../../outside.log", "sha256": None}]
        ev["stdout"] = None
        self.append_event(b, ev)
        toy.resign(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual(l4["status"], "partial")
        self.assertEqual(l4["not_replayed"], [])
        self.assertEqual(l4["not_replayable_outside_bundle"],
                         [{"seq": 4, "reason": "not_replayable: output outside bundle",
                           "paths": {"outputs": ["../../outside.log"]},
                           "why": {"../../outside.log": "output outside the bundle"}}])

    def test_inputs_outside_bundle_bucket(self):
        """WS-H's real cases: an input above the root, an absolute input, a tool script
        outside the bundle named in argv. Never a mismatch, never a pass."""
        b = self.fresh()
        base = {"kind": "run", "tool": "x", "tool_hash": "3" * 64, "cwd": ".", "outputs": [],
                "stdout": None, "stderr": None, "exit": 0, "started": "x", "ended": "x", "deterministic": True}
        self.append_event(b, dict(base, argv=["python3", "../tools/assemble_hard.py", "tbase"],
                                  inputs=[{"path": "../tools/assemble_hard.py", "sha256": "4" * 64},
                                          {"path": "../../../../pilot-checker/pins.json", "sha256": "5" * 64}]))
        self.append_event(b, dict(base, argv=["python3", "/home/someone/edit.py"],
                                  inputs=[{"path": "hard/annotations.json", "sha256": "6" * 64}]))
        toy.resign(b, self.keys["producer"])
        for extra in ([], ["--no-exec"]):
            r = self.run_snap(b, extra=extra)
            l4 = r["L4"]
            self.assertEqual(l4["status"], "partial")
            self.assertEqual(l4["mismatches"], [])
            got = {e["seq"]: (e["reason"], e["paths"]) for e in l4["not_replayable_outside_bundle"]}
            self.assertEqual(got[4], ("not_replayable: input outside bundle",
                                      {"inputs": ["../tools/assemble_hard.py", "../../../../pilot-checker/pins.json"],
                                       "argv": ["../tools/assemble_hard.py"]}))
            self.assertEqual(got[5], ("not_replayable: input outside bundle", {"argv": ["/home/someone/edit.py"]}))
            self.assertEqual(l4["counts"]["not_replayable_outside_bundle"], 2)
            self.assertTrue(any("../../../../pilot-checker/pins.json, outside the bundle" in o
                                for o in r["outside_bundle"]))
        self.assertEqual(self.run_snap(b)["L4"]["counts"]["replayed_matched"], 2)

    def test_tool_not_available_by_hash_is_partial(self):
        b = self.fresh()
        self.append_event(b, {"kind": "run", "tool": "nosuchtool", "tool_hash": "2" * 64,
                              "argv": ["nosuchtool"], "cwd": ".", "inputs": [], "outputs": [],
                              "stdout": None, "stderr": None, "exit": 0, "started": "x", "ended": "x",
                              "deterministic": True})
        toy.resign(b, self.keys["producer"])
        l4 = self.run_snap(b)["L4"]
        self.assertEqual(l4["status"], "partial")
        self.assertEqual(l4["not_replayed"][0]["seq"], 4)


class NoSummaryMark(helpers.ToyCase):
    SRC = [os.path.join(os.path.dirname(helpers.HERE), "verify.py")] + sorted(
        os.path.join(os.path.dirname(helpers.HERE), "tcgverify", f)
        for f in os.listdir(os.path.join(os.path.dirname(helpers.HERE), "tcgverify")) if f.endswith(".py"))
    COLLAPSE = re.compile(r"overall|summary|bundle_(ok|pass|status|verdict|valid)|all_pass|final_verdict|"
                          r"is_valid_bundle|def\s+\w*(verdict|grade|score)\w*\(", re.IGNORECASE)

    def test_source_has_no_collapse(self):
        for path in self.SRC:
            with open(path, encoding="utf-8") as f:
                for n, line in enumerate(f, 1):
                    code = line.split("#", 1)[0]
                    if '"""' in line:
                        continue
                    self.assertIsNone(self.COLLAPSE.search(code), f"{path}:{n}: {line.strip()}")

    def test_ladder_has_levels_and_no_top_level_status(self):
        r = self.run_snap(self.pristine)
        self.assertEqual(set(r), {"bundle_root", "bundle_root_declared", "verifier_hash", "variant",
                                  "self_contained", "self_contained_declared",
                                  "executed_bundle_supplied_commands", "docker_limits", "l4_skip_provers", "wall_s", "L0", "L1", "L2", "L3", "L4",
                                  "outside_bundle"})

    def test_wall_time_per_level(self):
        w = self.run_snap(self.pristine)["wall_s"]
        self.assertEqual(sorted(w), ["L0", "L1", "L2", "L3", "L4"])
        self.assertTrue(all(isinstance(v, float) and v >= 0 for v in w.values()))

    def test_exit_zero_even_when_every_level_fails(self):
        b = self.fresh()
        with open(os.path.join(b, "manifest.json"), "w") as f:
            f.write("not json")
        r = self.run_snap(b)
        self.assertEqual([r[l].get("status") for l in ("L0", "L1", "L3", "L4")], ["fail", "refused", "fail", "fail"])

    def test_verifier_self_hash_cli(self):
        out = subprocess.run([sys.executable, helpers.VERIFY, "--self-hash"], capture_output=True, text=True)
        self.assertRegex(out.stdout.strip(), "^[0-9a-f]{64}$")


if __name__ == "__main__":
    unittest.main()
