"""tcg.assume — the typed-stub assumption (STUB, Mechanism B), exercised WITHOUT
a prover, mirroring docs/e2e/composition-matrix.md rows B0–B5.

Three layers, like test_xbridge.py / test_xfreeze.py:

  * TestStructural — the pure `assume.structural_errors` / `consistency_errors`
    verdict (shared by graph check / freeze / verify) over tiny synthetic
    graphs. An honest stub is clean; every malformation refuses.

  * TestVerify — `verify.verify_bundle` end-to-end on synthetic caller bundles
    with an INJECTED prover seam (no kprove). The assume-node is SKIPPED in
    replay (its symbolic <program> cannot Accept) and injected as a trusted
    child, so an all-Accept fake models a real, non-vacuous root. The seam
    cannot manufacture a false green: a fake that Accepted the vacuity mutant
    would make step 5v REFUSE (asserted), and every refusal row here refuses at
    step 4 (structural/consistency) before any replay verdict matters.

  * TestFreezeRoundtrip — the three-way agreement: a caller WORKSPACE with an
    assume-node passes `check_graph`, `freeze` writes the A_callee_ ledger entry
    ONLY when a stub exists, and the frozen bundle re-verifies.

Rows:
  B0 honest stub          → verify exit 0 AND a ⚠ section names it (stdout)
  B1 same bundle, --strict → exit 3
  B2 stub present, ledger entry deleted → exit 3 (consistency: missing)
  B3 orphan A_callee_ entry, no stub    → exit 3 (consistency: orphan)
  B4 `tcg roots`          → output surfaces the load-bearing assumption
  B5 zero-stub bundle     → exit 0 and NO extra output (regression guard)

Run: PYTHONPATH=. python3 -m unittest tests.test_assume
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tcg import assume
from tcg.assume import ledger_id_for
from tcg.claims import sha256_text
from tcg.commands import roots as roots_cmd
from tcg.commands.verify import verify_bundle
from tcg.outcome import Exit
from tests.test_xbridge import (
    ADDR, CALLER_BYTES, _dump, _mod, _write, fake_prover, yes_prover,
)

FRAME = ("opaque callee at 0xc8: MAY NOT write caller storage (storage-frame: "
         "caller slots untouched); MAY NOT reenter the caller (reentrancy: "
         "none). Conservative typed frame.")
LEDGER_ID = ledger_id_for(ADDR)

# A minimal baseline trust manifest (the kind freeze always writes). Its non-
# A_callee_ keys must be IGNORED by ledger consistency — proves the stub check
# distinguishes author-chosen assumptions from the baseline environment ones.
BASELINE_TM = {
    "A_simp_lemmas": {"status": "proven-upstream + assumed-consistent"},
    "reading_discipline": ["a prover Accept is a derivation"],
}


def _finalize(root: Path, roots_map: dict) -> str:
    """MANIFEST.json over every file but MANIFEST/nav; returns its sha256."""
    import hashlib
    files = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and p.name != "MANIFEST.json" and "nav" not in rel.parts:
            files[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
    raw = _dump({"cert_version": "1", "roots": roots_map, "files": files})
    (root / "MANIFEST.json").write_text(raw, encoding="utf-8")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_caller(caller: Path, *, summary_fn="s.k", with_assume=True,
                 with_ledger=True, ledger_id=LEDGER_ID, callee_address=ADDR,
                 frame=FRAME, extra_ledger_id=None):
    """A synthetic caller bundle on disk.

    with_assume: the graph carries the assume-node (S) + the trusted-lemma edge
                 injecting it into the root.
    with_ledger: trust-manifest.json carries the A_callee_ entry for the stub.
    extra_ledger_id: inject an ADDITIONAL A_callee_ entry (for the orphan row).
    Returns (s_hash|None, r2a_hash, ledger_id).
    """
    r2amod = _mod("caller_2a", "r2a", "r2a.k")
    r2a_h = sha256_text(r2amod)
    _write(caller, f"spec/claims/{r2a_h}.k", r2amod)
    _write(caller, "subject/runtime.bin", CALLER_BYTES)
    _write(caller, "subject/environment.json",
           _dump({"external_code": {ADDR: "60005460050160005500"}}))
    _write(caller, "spec/interfaces.json", _dump({}))
    _write(caller, f"evidence/replay/{r2a_h}.json", _dump({"verdict": "Accept"}))
    _write(caller, "theory/toolchain.lock",
           _dump({"replay": {"retries": 0, "timeout_seconds": 60}}))
    _write(caller, "assumptions/oracle-record.json",
           _dump({"roots": {r2a_h: {"loop": "caller_2a", "label": "r2a"}}}))

    nodes = {r2a_h: {"loop": "caller_2a", "label": "r2a", "role": "loop",
                     "root": True}}
    edges = []
    s_h = None
    if with_assume:
        smod = _mod("summary", "s", summary_fn)
        s_h = sha256_text(smod)
        _write(caller, f"spec/claims/{s_h}.k", smod)
        nodes[s_h] = {"loop": "summary", "label": "s", "role": "guar",
                      "root": False,
                      "assume": {"callee_address": callee_address,
                                 "frame": frame, "ledger_id": ledger_id}}
        edges.append({"from": r2a_h, "to": s_h, "type": "trusted-lemma"})
    _write(caller, "spec/graph.json", _dump({"nodes": nodes, "edges": edges}))

    tm = dict(BASELINE_TM)
    if with_assume and with_ledger:
        tm[ledger_id] = assume.ledger_entry(nodes[s_h], [r2a_h])
    if extra_ledger_id is not None:
        tm[extra_ledger_id] = {
            "status": "assumed-callee (AUTHOR-CHOSEN, load-bearing)",
            "callee_address": "0x00000000000000000000000000000000000000ff",
            "frame": "orphan", "load_bearing_for": []}
    _write(caller, "assumptions/trust-manifest.json", _dump(tm))

    _finalize(caller, {r2a_h: {"loop": "caller_2a", "label": "r2a"}})
    return s_h, r2a_h, ledger_id


class TestStructural(unittest.TestCase):
    """The pure stub verdict, shared by graph check / freeze / verify."""

    def _graph(self, **kw):
        r2a_h = sha256_text("root")
        s_h = sha256_text("summary")
        a = {"callee_address": kw.get("callee_address", ADDR),
             "frame": kw.get("frame", FRAME),
             "ledger_id": kw.get("ledger_id", LEDGER_ID)}
        for drop in kw.get("drop_keys", []):
            a.pop(drop, None)
        node = {"loop": "summary", "label": "s", "root": False, "assume": a}
        if kw.get("also_bridge"):
            node["bridge"] = {"callee_address": ADDR}
        nodes = {r2a_h: {"loop": "caller_2a", "label": "r2a", "root": True},
                 s_h: node}
        summary_fn = kw.get("summary_fn", "s.k")
        texts = {s_h: _mod("summary", "s", summary_fn),
                 r2a_h: _mod("caller_2a", "r2a", "r2a.k")}
        return s_h, nodes, (lambda h: texts[h])

    def test_honest_is_clean(self):
        s_h, nodes, ct = self._graph()
        self.assertEqual(assume.structural_errors(s_h, nodes, ct), [])

    def test_missing_key_refuses(self):
        s_h, nodes, ct = self._graph(drop_keys=["frame"])
        errs = assume.structural_errors(s_h, nodes, ct)
        self.assertTrue(any("missing 'frame'" in e for e in errs), errs)

    def test_empty_frame_refuses(self):
        s_h, nodes, ct = self._graph(frame="   ")
        errs = assume.structural_errors(s_h, nodes, ct)
        self.assertTrue(any("non-empty" in e for e in errs), errs)

    def test_bad_ledger_id_refuses(self):
        s_h, nodes, ct = self._graph(ledger_id="A_callee_wrong")
        errs = assume.structural_errors(s_h, nodes, ct)
        self.assertTrue(any("not the canonical" in e for e in errs), errs)

    def test_both_assume_and_bridge_refuses(self):
        s_h, nodes, ct = self._graph(also_bridge=True)
        errs = assume.structural_errors(s_h, nodes, ct)
        self.assertTrue(any("BOTH" in e for e in errs), errs)

    def test_concrete_program_summary_refuses(self):
        # d.k has a concrete <program> — not an abstract summary.
        s_h, nodes, ct = self._graph(summary_fn="d.k")
        errs = assume.structural_errors(s_h, nodes, ct)
        self.assertTrue(any("not a bare variable" in e for e in errs), errs)

    def test_consistency_missing_entry(self):
        _s, nodes, _ct = self._graph()
        errs = assume.consistency_errors(nodes, dict(BASELINE_TM))
        self.assertTrue(any("absent from" in e for e in errs), errs)

    def test_consistency_orphan_entry(self):
        # No assume-node, but an A_callee_ ledger entry — orphan.
        nodes = {sha256_text("r"): {"loop": "l", "label": "r", "root": True}}
        tm = dict(BASELINE_TM, **{LEDGER_ID: {"status": "x"}})
        errs = assume.consistency_errors(nodes, tm)
        self.assertTrue(any("orphan" in e for e in errs), errs)

    def test_consistency_clean(self):
        _s, nodes, _ct = self._graph()
        tm = dict(BASELINE_TM, **{LEDGER_ID: {"status": "x"}})
        self.assertEqual(assume.consistency_errors(nodes, tm), [])

    def test_roots_injecting(self):
        r2a_h, s_h = sha256_text("root"), sha256_text("summary")
        nodes = {r2a_h: {"loop": "c", "label": "r", "root": True},
                 s_h: {"loop": "s", "label": "s", "root": False,
                       "assume": {}}}
        edges = [{"from": r2a_h, "to": s_h, "type": "trusted-lemma"}]
        self.assertEqual(assume.roots_injecting(s_h, nodes, edges), [r2a_h])
        # An unreferenced stub is load-bearing for no root.
        self.assertEqual(assume.roots_injecting(s_h, nodes, []), [])


class TestVerify(unittest.TestCase):
    """verify_bundle end-to-end with the injected prover seam (no kprove)."""

    def setUp(self):
        self._dir = Path(tempfile.mkdtemp(prefix="tcg-assume-"))

    def tearDown(self):
        shutil.rmtree(self._dir, ignore_errors=True)

    def _caller(self, **kw):
        d = Path(tempfile.mkdtemp(dir=self._dir)) / "caller"
        build_caller(d, **kw)
        return d

    def _verify(self, caller, *, strict=False, prover=fake_prover):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = verify_bundle(caller, definition_arg="DUMMY", includes_arg=[],
                               strict=strict, run_prover=prover)
        return rc, out.getvalue()

    def test_B0_honest_stub_exit0_and_warning(self):
        rc, out = self._verify(self._caller())
        self.assertEqual(rc, int(Exit.OK))
        self.assertIn("⚠", out)
        self.assertIn("author-chosen assumption", out)
        self.assertIn(ADDR, out)                     # names the callee address
        self.assertIn("storage-frame", out)          # surfaces the frame text
        self.assertIn("caller_2a/r2a", out)          # names the load-bearing root

    def test_B0_seam_cannot_force_green(self):
        # An all-Accept prover (Accepts even the vacuity mutant) is caught at 5v
        # — the injected seam cannot launder a false green for a stub bundle.
        rc, _ = self._verify(self._caller(), prover=yes_prover)
        self.assertEqual(rc, int(Exit.REFUSED))

    def test_B1_strict_refuses(self):
        rc, _ = self._verify(self._caller(), strict=True)
        self.assertEqual(rc, int(Exit.REFUSED))

    def test_B2_deleted_ledger_entry_refuses(self):
        # Stub present, its A_callee_ entry removed from the ledger (MANIFEST
        # re-finalized so integrity still passes) → consistency: missing.
        rc, out = self._verify(self._caller(with_ledger=False))
        self.assertEqual(rc, int(Exit.REFUSED))

    def test_B3_orphan_ledger_entry_refuses(self):
        # No stub, but an A_callee_ ledger entry → consistency: orphan.
        rc, _ = self._verify(self._caller(with_assume=False,
                                          extra_ledger_id=LEDGER_ID))
        self.assertEqual(rc, int(Exit.REFUSED))

    def test_B5_zero_stub_exit0_and_no_extra_output(self):
        rc, out = self._verify(self._caller(with_assume=False))
        self.assertEqual(rc, int(Exit.OK))
        # Hard regression guard: a zero-stub bundle prints NOTHING extra.
        self.assertNotIn("⚠", out)
        self.assertNotIn("author-chosen", out)
        self.assertNotIn("load-bearing", out)

    def test_strict_on_zero_stub_bundle_still_exit0(self):
        # --strict changes nothing when there is no stub to refuse.
        rc, out = self._verify(self._caller(with_assume=False), strict=True)
        self.assertEqual(rc, int(Exit.OK))
        self.assertNotIn("⚠", out)


class TestRoots(unittest.TestCase):
    """B4: `tcg roots` surfaces the load-bearing author assumption."""

    def setUp(self):
        self._dir = Path(tempfile.mkdtemp(prefix="tcg-assume-roots-"))

    def tearDown(self):
        shutil.rmtree(self._dir, ignore_errors=True)

    def _roots(self, caller):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            rc = roots_cmd.run(SimpleNamespace(bundle=str(caller)))
        return rc, out.getvalue()

    def test_B4_roots_surfaces_assumption(self):
        caller = Path(tempfile.mkdtemp(dir=self._dir)) / "caller"
        build_caller(caller)
        rc, out = self._roots(caller)
        self.assertEqual(rc, int(Exit.OK))
        self.assertIn("load-bearing author assumption", out)
        self.assertIn(LEDGER_ID, out)
        self.assertIn("storage-frame", out)          # the frame
        self.assertIn("caller_2a/r2a", out)           # the root it bears

    def test_B5_roots_zero_stub_no_assumptions_section(self):
        caller = Path(tempfile.mkdtemp(dir=self._dir)) / "caller"
        build_caller(caller, with_assume=False)
        rc, out = self._roots(caller)
        self.assertEqual(rc, int(Exit.OK))
        self.assertNotIn("author assumption", out)


@contextlib.contextmanager
def _chdir(path: Path):
    prev = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(prev)


def build_workspace(ws: Path, *, summary_fn="s.k"):
    """A minimal caller WORKSPACE with an assume-node (no dep, no bridge)."""
    smod = _mod("summary", "s", summary_fn)
    r2amod = _mod("caller_2a", "r2a", "r2a.k")
    guarmod = _mod("caller_2a", "guar", "guar2a.k")
    s_h, r2a_h, guar_h = (sha256_text(smod), sha256_text(r2amod),
                          sha256_text(guarmod))
    _write(ws, f"spec/claims/{s_h}.k", smod)
    _write(ws, f"spec/claims/{r2a_h}.k", r2amod)
    _write(ws, f"spec/claims/{guar_h}.k", guarmod)
    _write(ws, "subject/runtime.bin", CALLER_BYTES)
    _write(ws, "subject/environment.json",
           _dump({"external_code": {ADDR: "60005460050160005500"}}))
    _write(ws, "spec/interfaces.json", _dump({}))
    _write(ws, "spec/graph.json", _dump({
        "nodes": {
            r2a_h: {"loop": "caller_2a", "label": "r2a", "role": "loop",
                    "root": True},
            guar_h: {"loop": "caller_2a", "label": "guar", "role": "guar",
                     "root": False},
            s_h: {"loop": "summary", "label": "s", "role": "guar", "root": False,
                  "assume": {"callee_address": ADDR, "frame": FRAME,
                             "ledger_id": LEDGER_ID}},
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
    return s_h, r2a_h, LEDGER_ID


class TestFreezeRoundtrip(unittest.TestCase):
    """Three-way agreement: graph check clean, freeze writes the ledger entry
    ONLY when a stub exists, and the frozen bundle re-verifies (exit 0 + ⚠)."""

    def setUp(self):
        self.ws = Path(tempfile.mkdtemp(prefix="tcg-assume-freeze-"))

    def tearDown(self):
        shutil.rmtree(self.ws, ignore_errors=True)

    def test_honest_graphcheck_freeze_verify_roundtrip(self):
        from tcg.commands import freeze as freeze_cmd
        from tcg.commands.graph import check_graph

        build_workspace(self.ws)
        self.assertEqual(check_graph(self.ws), [],
                         "honest stub workspace should pass graph check")

        with _chdir(self.ws):
            rc = freeze_cmd.run(SimpleNamespace())
        self.assertEqual(rc, int(Exit.OK))
        bundle = self.ws / "bundle"

        # freeze wrote the A_callee_ ledger entry, marked author-chosen +
        # load-bearing, naming the root it bears.
        tm = json.loads(
            (bundle / "assumptions" / "trust-manifest.json").read_text())
        self.assertIn(LEDGER_ID, tm)
        self.assertIn("AUTHOR-CHOSEN", tm[LEDGER_ID]["status"])
        self.assertEqual(len(tm[LEDGER_ID]["load_bearing_for"]), 1)

        # three-way agreement: the frozen bundle re-verifies (fake prover), and
        # --strict refuses it.
        rc = verify_bundle(bundle, definition_arg="DUMMY", includes_arg=[],
                           run_prover=fake_prover)
        self.assertEqual(rc, int(Exit.OK))
        rc = verify_bundle(bundle, definition_arg="DUMMY", includes_arg=[],
                           strict=True, run_prover=fake_prover)
        self.assertEqual(rc, int(Exit.REFUSED))

    def test_bad_ledger_id_refused_by_graphcheck_and_freeze(self):
        from tcg.commands import freeze as freeze_cmd
        from tcg.commands.graph import check_graph

        build_workspace(self.ws)
        # Corrupt the ledger_id in the graph: structural check must refuse.
        graph_path = self.ws / "spec" / "graph.json"
        graph = json.loads(graph_path.read_text())
        for n in graph["nodes"].values():
            if "assume" in n:
                n["assume"]["ledger_id"] = "A_callee_bogus"
        graph_path.write_text(_dump(graph), encoding="utf-8")

        errs = check_graph(self.ws)
        self.assertTrue(any("not the canonical" in e for e in errs), errs)
        with _chdir(self.ws):
            rc = freeze_cmd.run(SimpleNamespace())
        self.assertEqual(rc, int(Exit.REFUSED))
        self.assertFalse((self.ws / "bundle").exists())


if __name__ == "__main__":
    unittest.main()
