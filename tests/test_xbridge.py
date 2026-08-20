"""tcg.xbridge — the cross-bundle linker (REUSE) structural discharge + the
verify recursion control flow, both exercised WITHOUT a prover.

Two layers, mirroring test_bridge.py:

  * TestStructural — the pure `xbridge.structural_errors` verdict (shared by
    graph check / freeze / verify) over tiny SYNTHETIC bundles on disk: a
    2-op-ish dep runtime, a trivial dep MANIFEST + one root claim, a caller
    referencing it. Honest composition is clean; every discriminator in the
    composition contract refuses.

  * TestVerifyRecursion — `verify.verify_bundle` end-to-end with an INJECTED
    prover seam (no kprove). The seam is a test aid only: `fake_prover` Accepts
    replay goals and makes the vacuity mutant NOT prove, modelling a real,
    non-vacuous, provable claim. It cannot manufacture a false green — a fake
    that Accepted the vacuity mutant would make step 5v REFUSE, and every
    discriminator here refuses at step 1 or step 4 (before any replay), so the
    refusal is structural regardless of what the prover would say.

The REAL prover-in-the-loop half (the dep actually proving over P, the caller
Accepting with S injected) is the orchestrator's reproduction via
tests/reference/callext/run-tcg-linker-discriminators.sh on the KEVM backend.

Run: PYTHONPATH=. python3 -m unittest tests.test_xbridge
"""
from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from tcg import xbridge
from tcg.claims import emit_module, sha256_text
from tcg.commands.verify import verify_bundle
from tcg.keccak import keccak256_hex
from tcg.outcome import Exit

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "tests" / "reference" / "callext" / "tcg" / "src"

P_HEX = "60005460050160005500"                       # the concrete callee code P
P_BYTES = bytes.fromhex(P_HEX)
CODE_HASH = keccak256_hex(P_BYTES)                   # a7d0…f512
CALLER_BYTES = bytes.fromhex("6000600060006000600060C86000F100")
ADDR = "0x00000000000000000000000000000000000000c8"  # 200
NONROOT_HASH = sha256_text("definitely not a dep root\n")


def _body(fn: str) -> str:
    return (SRC / fn).read_text(encoding="utf-8")


def _mod(loop: str, label: str, fn: str) -> str:
    return emit_module(loop, label, ["evm.md"], ["EVM"], _body(fn))


def _write(root: Path, rel: str, data) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(data, bytes):
        p.write_bytes(data)
    else:
        p.write_text(data, encoding="utf-8")


def _dump(obj) -> str:
    return json.dumps(obj, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def _finalize(root: Path, roots_map: dict) -> str:
    """Write MANIFEST.json (hash tree over every file but MANIFEST/nav) and
    return sha256(MANIFEST.json) — the bundle identity."""
    files = {}
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if p.is_file() and p.name != "MANIFEST.json" and "nav" not in rel.parts:
            files[str(rel)] = hashlib.sha256(p.read_bytes()).hexdigest()
    raw = _dump({"cert_version": "1", "roots": roots_map, "files": files})
    (root / "MANIFEST.json").write_text(raw, encoding="utf-8")
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def build_dep(stage: Path, *, root_fn="sbridge.k", runtime=P_BYTES,
              bad_oracle=False) -> tuple[str, str]:
    """A minimal, self-contained callee bundle at `stage`. Returns
    (callee_root, dep_root_hash). Its root claim is a concrete-P execution proof
    shaped to bind the summary S; runtime.bin is P. Passes the full verifier
    protocol under the fake prover."""
    dmod = _mod("callee", "d", root_fn)
    droot = sha256_text(dmod)
    _write(stage, f"spec/claims/{droot}.k", dmod)
    _write(stage, "subject/runtime.bin", runtime)
    _write(stage, "subject/environment.json", _dump({}))
    _write(stage, "spec/interfaces.json", _dump({}))
    _write(stage, "spec/graph.json", _dump({
        "nodes": {droot: {"loop": "callee", "label": "d", "role": "loop",
                          "root": True}},
        "edges": [],
    }))
    _write(stage, f"evidence/replay/{droot}.json", _dump({"verdict": "Accept"}))
    _write(stage, "theory/toolchain.lock",
           _dump({"replay": {"retries": 0, "timeout_seconds": 60}}))
    oracle_roots = {} if bad_oracle else {droot: {"loop": "callee", "label": "d"}}
    _write(stage, "assumptions/oracle-record.json", _dump({"roots": oracle_roots}))
    callee_root = _finalize(stage, {droot: {"loop": "callee", "label": "d"}})
    return callee_root, droot


class Composition:
    """A caller bundle + one vendored dep, with knobs for each discriminator."""

    def __init__(self, tmp: Path, *, summary_fn="s.k", dep_root_fn="sbridge.k",
                 code_hash=CODE_HASH, ext_hex=P_HEX, dep_runtime=P_BYTES,
                 dep_root_ref=None, place_dep=True, dep_dirname=None,
                 dep_ref_dir=None, bad_oracle_in_dep=False):
        self.tmp = tmp
        self.caller = tmp / "caller"
        stage = tmp / "_dep_stage"
        self.callee_root, self.droot = build_dep(
            stage, root_fn=dep_root_fn, runtime=dep_runtime,
            bad_oracle=bad_oracle_in_dep)

        smod = _mod("summary", "s", summary_fn)
        r2amod = _mod("caller_2a", "r2a", "r2a.k")
        self.s_h, self.r2a_h = sha256_text(smod), sha256_text(r2amod)
        _write(self.caller, f"spec/claims/{self.s_h}.k", smod)
        _write(self.caller, f"spec/claims/{self.r2a_h}.k", r2amod)
        _write(self.caller, "subject/runtime.bin", CALLER_BYTES)
        self.environment = {"external_code": {ADDR: ext_hex}}
        _write(self.caller, "subject/environment.json", _dump(self.environment))
        _write(self.caller, "spec/interfaces.json", _dump({}))
        bridge = {"callee_address": ADDR, "code_hash": code_hash,
                  "concrete_proof": {"dep": dep_ref_dir or self.callee_root,
                                     "root": dep_root_ref or self.droot}}
        self.nodes = {
            self.r2a_h: {"loop": "caller_2a", "label": "r2a", "role": "loop",
                         "root": True},
            self.s_h: {"loop": "summary", "label": "s", "role": "guar",
                       "root": False, "bridge": bridge},
        }
        _write(self.caller, "spec/graph.json", _dump({
            "nodes": self.nodes,
            "edges": [{"from": self.r2a_h, "to": self.s_h,
                       "type": "trusted-lemma"}],
        }))
        _write(self.caller, f"evidence/replay/{self.r2a_h}.json",
               _dump({"verdict": "Accept"}))
        _write(self.caller, "theory/toolchain.lock",
               _dump({"replay": {"retries": 0, "timeout_seconds": 60}}))
        _write(self.caller, "assumptions/oracle-record.json",
               _dump({"roots": {self.r2a_h: {"loop": "caller_2a",
                                             "label": "r2a"}}}))
        if place_dep:
            shutil.copytree(stage, self.caller / "deps" /
                            (dep_dirname or self.callee_root))
        shutil.rmtree(stage)
        self.caller_root = _finalize(
            self.caller, {self.r2a_h: {"loop": "caller_2a", "label": "r2a"}})

    def claim_text_of(self, h: str) -> str:
        return (self.caller / "spec" / "claims" / f"{h}.k").read_text(
            encoding="utf-8")

    def structural(self):
        return xbridge.structural_errors(
            self.s_h, self.nodes, self.claim_text_of, self.environment,
            self.caller / "deps")


def fake_prover(argv, timeout):
    """Accept replay goals; make the vacuity mutant NOT prove (the safe
    direction). Models a genuine, non-vacuous, provable claim."""
    if "REPLAY-VACUITY" in " ".join(argv):
        return (1, "cannot be rewritten further", False)   # Refute -> not vacuous
    return (0, "#Top", False)                               # Accept


def yes_prover(argv, timeout):
    """Accepts EVERYTHING, including the vacuity mutant. Used to show a
    discriminator refuses structurally (before replay) regardless of the
    prover — and that an honest bundle would be caught at 5v by such a prover,
    so the seam cannot launder a false green."""
    return (0, "#Top", False)


class TestStructural(unittest.TestCase):
    """The pure linker verdict, shared by graph check / freeze / verify."""

    def setUp(self):
        self._dir = Path(tempfile.mkdtemp(prefix="tcg-xbridge-"))

    def tearDown(self):
        shutil.rmtree(self._dir, ignore_errors=True)

    def _mk(self, **kw):
        d = Path(tempfile.mkdtemp(dir=self._dir))
        return Composition(d, **kw)

    def test_honest_is_clean(self):
        errs, ref = self._mk().structural()
        self.assertEqual(errs, [], f"honest linker should be clean: {errs}")
        self.assertEqual(set(ref), {"dep", "root"})

    def test_code_hash_mismatch(self):
        errs, _ = self._mk(code_hash="deadbeef" * 8).structural()
        self.assertTrue(any("code-identity FAILED" in e for e in errs), errs)

    def test_external_code_mismatch(self):
        # keccak(dep runtime) still == code_hash, so this isolates external_code.
        errs, _ = self._mk(ext_hex="600154600501600155").structural()
        self.assertTrue(any("external_code" in e and "did NOT prove over" in e
                            for e in errs), errs)

    def test_flipped_dep_byte(self):
        # A dep whose runtime is P' (one op changed): keccak mismatch AND its
        # bytes disagree with external_code[callee].
        errs, _ = self._mk(dep_runtime=bytes.fromhex("60005460050160005501"),
                           ext_hex="60005460050160005501").structural()
        self.assertTrue(any("code-identity FAILED" in e for e in errs), errs)

    def test_nonroot_ref(self):
        errs, _ = self._mk(dep_root_ref=NONROOT_HASH).structural()
        self.assertTrue(any("not one of the dep bundle's declared roots" in e
                            for e in errs), errs)

    def test_proxy_delta(self):
        # S asserts a no-op (+0); the dep root D delivers +5: the binding
        # storage-delta check catches the proxy.
        errs, _ = self._mk(summary_fn="s_proxy.k").structural()
        self.assertTrue(any("storage delta differs" in e for e in errs), errs)

    def test_missing_dep(self):
        errs, _ = self._mk(place_dep=False).structural()
        self.assertTrue(any("is absent" in e for e in errs), errs)

    def test_manifest_hash_ne_callee_root(self):
        errs, _ = self._mk(dep_dirname="0" * 64).structural()
        # concrete_proof.dep still names the real callee_root, whose directory
        # is now absent -> "absent"; place it under the real name but tamper is
        # exercised in the dir-mismatch variant below.
        self.assertTrue(errs, errs)

    def test_manifest_hash_ne_callee_root_named(self):
        # Vendor the dep under a WRONG directory name AND point the ref at that
        # name: load_dep finds a MANIFEST whose hash != the directory name.
        errs, _ = self._mk(dep_dirname="0" * 64, dep_ref_dir="0" * 64).structural()
        self.assertTrue(any("is not content-addressed" in e or "MANIFEST hash"
                            in e for e in errs), errs)

    def test_concrete_program_summary_needs_no_bridge(self):
        # A summary whose <program> is concrete is not an abstract summary.
        errs, _ = self._mk(summary_fn="d.k").structural()
        self.assertTrue(any("not a bare variable" in e for e in errs), errs)

    def test_at_program_proof_must_be_omitted(self):
        comp = self._mk()
        comp.nodes[comp.s_h]["bridge"]["at_program_proof"] = {"loop": "x",
                                                              "label": "y"}
        errs, _ = comp.structural()
        self.assertTrue(any("must OMIT at_program_proof" in e for e in errs), errs)


class TestVerifyRecursion(unittest.TestCase):
    """verify_bundle end-to-end with the injected prover seam (no kprove)."""

    def setUp(self):
        self._dir = Path(tempfile.mkdtemp(prefix="tcg-xverify-"))

    def tearDown(self):
        shutil.rmtree(self._dir, ignore_errors=True)

    def _mk(self, **kw):
        d = Path(tempfile.mkdtemp(dir=self._dir))
        return Composition(d, **kw)

    def _verify(self, comp, prover=fake_prover):
        return verify_bundle(comp.caller, definition_arg="DUMMY-DEF",
                             includes_arg=[], run_prover=prover)

    def test_honest_composition_verifies(self):
        comp = self._mk()
        self.assertEqual(self._verify(comp), int(Exit.OK))

    def test_honest_refused_by_always_accept_prover_at_vacuity(self):
        # A prover that Accepts even the falsified form is caught at 5v — the
        # seam cannot be abused to force a green.
        comp = self._mk()
        self.assertEqual(self._verify(comp, prover=yes_prover),
                         int(Exit.REFUSED))

    def test_dep_that_fails_its_own_verify_refuses_caller(self):
        # The dep's oracle-record does not cover its roots: the dep fails its
        # OWN step 4, and the post-order recursion refuses the caller — while
        # the caller's own linker structural check is otherwise clean.
        comp = self._mk(bad_oracle_in_dep=True)
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))

    def test_flipped_dep_byte_caught_by_caller_integrity(self):
        # Tamper a vendored dep file WITHOUT updating the caller MANIFEST: the
        # deps/** are hash-linked, so caller step 1 integrity refuses.
        comp = self._mk()
        runtime = comp.caller / "deps" / comp.callee_root / "subject" / "runtime.bin"
        runtime.write_bytes(bytes.fromhex("60005460050160005501"))
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))

    def test_missing_dep_refused_at_recursion(self):
        comp = self._mk(place_dep=False)
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))

    def test_code_hash_mismatch_refused(self):
        comp = self._mk(code_hash="deadbeef" * 8)
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))

    def test_external_code_mismatch_refused(self):
        comp = self._mk(ext_hex="600154600501600155")
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))

    def test_proxy_summary_refused(self):
        comp = self._mk(summary_fn="s_proxy.k")
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))

    def test_nonroot_ref_refused(self):
        comp = self._mk(dep_root_ref=NONROOT_HASH)
        self.assertEqual(self._verify(comp), int(Exit.REFUSED))


if __name__ == "__main__":
    unittest.main()
