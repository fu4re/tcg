"""freeze + graph check for the cross-bundle linker — three-way agreement.

graph check, freeze, and verify must compute the IDENTICAL structural verdict
for a cross-bundle summary node (they call the same pure tcg.xbridge). Here a
minimal caller WORKSPACE (with a vendored dep) is driven through the REAL
`check_graph` and `freeze.run` — no prover: freeze gates on workspace state
(set to Accepted) and re-runs the structural verdict; the round-trip `verify`
uses the injected fake prover. Asserts:

  * honest: graph check clean, freeze OK, the dep is VENDORED into the bundle,
    the trust manifest names the load-bearing link, and the frozen bundle
    re-verifies (three-way agreement);
  * proxy summary: graph check AND freeze both REFUSE at the binding.

Run: PYTHONPATH=. python3 -m unittest tests.test_xfreeze
"""
from __future__ import annotations

import contextlib
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tcg.claims import sha256_text
from tcg.commands import freeze as freeze_cmd
from tcg.commands.graph import check_graph
from tcg.commands.verify import verify_bundle
from tcg.outcome import Exit
from tests.test_xbridge import (
    ADDR, CALLER_BYTES, CODE_HASH, P_HEX, _dump, _mod, _write, build_dep,
    fake_prover,
)


@contextlib.contextmanager
def _chdir(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def build_workspace(ws: Path, *, summary_fn="s.k"):
    """A minimal caller workspace with one vendored dep. Returns
    (callee_root, r2a_hash, summary_hash)."""
    stage = ws / "_depstage"
    callee_root, droot = build_dep(stage)
    shutil.move(str(stage), str(ws / "deps" / callee_root))

    smod = _mod("summary", "s", summary_fn)
    r2amod = _mod("caller_2a", "r2a", "r2a.k")
    guarmod = _mod("caller_2a", "guar", "guar2a.k")
    s_h, r2a_h, guar_h = (sha256_text(smod), sha256_text(r2amod),
                          sha256_text(guarmod))
    _write(ws, f"spec/claims/{s_h}.k", smod)
    _write(ws, f"spec/claims/{r2a_h}.k", r2amod)
    _write(ws, f"spec/claims/{guar_h}.k", guarmod)
    _write(ws, "subject/runtime.bin", CALLER_BYTES)
    _write(ws, "subject/environment.json", _dump({"external_code": {ADDR: P_HEX}}))
    _write(ws, "spec/interfaces.json", _dump({}))
    bridge = {"callee_address": ADDR, "code_hash": CODE_HASH,
              "concrete_proof": {"dep": callee_root, "root": droot}}
    _write(ws, "spec/graph.json", _dump({
        "nodes": {
            r2a_h: {"loop": "caller_2a", "label": "r2a", "role": "loop",
                    "root": True},
            guar_h: {"loop": "caller_2a", "label": "guar", "role": "guar",
                     "root": False},
            s_h: {"loop": "summary", "label": "s", "role": "guar",
                  "root": False, "bridge": bridge},
        },
        "edges": [{"from": r2a_h, "to": s_h, "type": "trusted-lemma"}],
    }))
    _write(ws, ".tcg/loops/caller_2a/loop.json", _dump({"state": "Accepted"}))
    _write(ws, ".tcg/loops/summary/loop.json", _dump({"state": "Compiled"}))
    _write(ws, f"evidence/replay/{r2a_h}.json", _dump({"verdict": "Accept"}))
    _write(ws, f"evidence/replay/{guar_h}.json", _dump({"verdict": "Accept"}))
    _write(ws, f".tcg/vacuity/{r2a_h}.json", _dump({"vacuous": False}))
    _write(ws, "assumptions/oracle-record.json",
           _dump({"roots": {r2a_h: {"loop": "caller_2a", "label": "r2a"}}}))
    _write(ws, ".tcg/toolchain.lock",
           _dump({"replay": {"retries": 0, "timeout_seconds": 60}}))
    return callee_root, r2a_h, s_h


class TestFreezeLinker(unittest.TestCase):
    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="tcg-xfreeze-"))

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_honest_graphcheck_freeze_verify_roundtrip(self):
        callee_root, _, _ = build_workspace(self.ws)

        # graph check: clean (the linker node is discharged structurally).
        self.assertEqual(check_graph(self.ws), [],
                         "honest linker workspace should pass graph check")

        # freeze: OK, and it VENDORS the dep into the bundle.
        with _chdir(self.ws):
            rc = freeze_cmd.run(SimpleNamespace())
        self.assertEqual(rc, int(Exit.OK))
        bundle = self.ws / "bundle"
        vendored = bundle / "deps" / callee_root
        self.assertTrue((vendored / "MANIFEST.json").is_file(),
                        "freeze must vendor the dep bundle into deps/<callee_root>/")

        # the dep files are hash-linked in the caller MANIFEST (integrity covers them).
        manifest = json.loads((bundle / "MANIFEST.json").read_text())
        self.assertTrue(any(k.startswith(f"deps/{callee_root}/")
                            for k in manifest["files"]),
                        "vendored dep files must be in the caller hash tree")

        # the trust manifest names the load-bearing link.
        tm = json.loads((bundle / "assumptions" / "trust-manifest.json").read_text())
        self.assertIn("link_S_from_dep", tm)
        self.assertEqual(tm["link_S_from_dep"]["links"][0]["dep"], callee_root)

        # three-way agreement: the frozen bundle re-verifies (fake prover).
        rc = verify_bundle(bundle, definition_arg="DUMMY", includes_arg=[],
                           run_prover=fake_prover)
        self.assertEqual(rc, int(Exit.OK))

    def test_proxy_summary_refused_by_graphcheck_and_freeze(self):
        build_workspace(self.ws, summary_fn="s_proxy.k")
        errs = check_graph(self.ws)
        self.assertTrue(any("storage delta differs" in e for e in errs), errs)
        with _chdir(self.ws):
            rc = freeze_cmd.run(SimpleNamespace())
        self.assertEqual(rc, int(Exit.REFUSED))
        self.assertFalse((self.ws / "bundle").exists(),
                         "freeze must not leave a bundle on refusal")


if __name__ == "__main__":
    unittest.main()
