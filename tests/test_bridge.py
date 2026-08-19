"""tcg.bridge — the bridge S<==D structural discharge (pure; no prover).

Exercises the anti-proxy binding and code-identity on the REAL callext claim
files. The prover-in-the-loop half (bridge-s-at-p Accepts over P; the +6 / no-op
bridges REFUTE; the caller root Accepts with S injected) lives in
tests/reference/callext/run-tcg-bridge.sh and run-tcg-bridge-discriminators.sh,
which run the real Haskell backend. Here we pin that the STRUCTURAL verdict —
which graph check, freeze, and verify all share — is clean for the honest
bridge and refuses every tamper.

Run: PYTHONPATH=. python3 -m unittest tests.test_bridge
"""
from __future__ import annotations

import copy
import unittest
from pathlib import Path

from tcg.bridge import (
    is_bridge_node, program_is_abstract_var, resolve_ref, structural_errors,
)
from tcg.claims import emit_module, sha256_text

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "tests" / "reference" / "callext" / "tcg" / "src"

CALLEE_P = "60005460050160005500"
CODE_HASH = "a7d0eaef07694abd7dcad44e621c06a9dc7be164317d98d005a14caa63ecf512"
ADDR = "0x00000000000000000000000000000000000000c8"
ENV = {"external_code": {ADDR: CALLEE_P}}

GOOD_BRIDGE = {
    "callee_address": ADDR,
    "code_hash": CODE_HASH,
    "concrete_proof": {"loop": "callee", "label": "d"},
    "at_program_proof": {"loop": "bridge", "label": "sbridge"},
}


def _body(fn: str) -> str:
    return (SRC / fn).read_text(encoding="utf-8")


def build(summary_fn="s.k", bridge_fn="sbridge.k", d_fn="d.k",
          bridge=GOOD_BRIDGE, env=ENV):
    """Assemble a (summary_hash, nodes, claim_text_of, env) fixture from the
    real committed claim bodies, mirroring what compile-claims produces."""
    texts: dict[str, str] = {}
    nodes: dict[str, dict] = {}

    def add(loop, label, fn, role="guar", root=False, br=None):
        txt = emit_module(loop, label, ["evm.md"], ["EVM"], _body(fn))
        h = sha256_text(txt)
        texts[h] = txt
        n = {"loop": loop, "label": label, "role": role, "root": root}
        if br is not None:
            n["bridge"] = copy.deepcopy(br)
        nodes[h] = n
        return h

    add("callee", "d", d_fn)
    add("bridge", "sbridge", bridge_fn)
    sh = add("summary", "s", summary_fn, br=bridge)
    add("caller_2a", "r2a", "r2a.k", role="loop", root=True)
    return sh, nodes, texts.__getitem__, env


class TestHelpers(unittest.TestCase):
    def test_program_is_abstract_var(self):
        self.assertTrue(program_is_abstract_var(emit_module(
            "summary", "s", ["evm.md"], ["EVM"], _body("s.k"))))
        # a concrete-program claim is NOT abstract
        self.assertFalse(program_is_abstract_var(emit_module(
            "callee", "d", ["evm.md"], ["EVM"], _body("d.k"))))

    def test_is_bridge_node(self):
        self.assertTrue(is_bridge_node({"bridge": {}}))
        self.assertFalse(is_bridge_node({"role": "guar"}))

    def test_resolve_ref(self):
        _, nodes, _, _ = build()
        h = resolve_ref(nodes, {"loop": "callee", "label": "d"})
        self.assertIsNotNone(h)
        self.assertEqual(nodes[h]["loop"], "callee")
        self.assertIsNone(resolve_ref(nodes, {"loop": "nope", "label": "x"}))


class TestGoodBridge(unittest.TestCase):
    def test_honest_bridge_is_clean(self):
        sh, nodes, get, env = build()
        errs, refs = structural_errors(sh, nodes, get, env)
        self.assertEqual(errs, [], f"honest bridge should be clean: {errs}")
        self.assertIn("concrete", refs)
        self.assertIn("at_program", refs)


class TestDiscriminators(unittest.TestCase):
    def _refused(self, **kw):
        sh, nodes, get, env = build(**kw)
        errs, _ = structural_errors(sh, nodes, get, env)
        self.assertTrue(errs, "expected the bridge to be REFUSED")
        return errs

    def test_broken_summary_plus6(self):
        # B asserts +6 while S asserts +5: the storage-delta binding catches it.
        errs = self._refused(bridge_fn="sbridge6.k")
        self.assertTrue(any("storage delta differs" in e for e in errs), errs)

    def test_proxy_swap_noop(self):
        # S is a plausible no-op (+0); its at-P bridge is the real +5: mismatch.
        errs = self._refused(summary_fn="s_proxy.k")
        self.assertTrue(any("storage delta differs" in e for e in errs), errs)

    def test_wrong_code_identity(self):
        errs = self._refused(env={"external_code": {ADDR: "600154600501600155"}})
        self.assertTrue(any("code-identity FAILED" in e for e in errs), errs)

    def test_tampered_code_hash(self):
        bad = copy.deepcopy(GOOD_BRIDGE)
        bad["code_hash"] = "deadbeef" * 8
        errs = self._refused(bridge=bad)
        self.assertTrue(any("code-identity FAILED" in e for e in errs), errs)

    def test_undischarged_no_bridge(self):
        errs = self._refused(bridge=None)
        self.assertTrue(any("no bridge block" in e for e in errs), errs)

    def test_concrete_program_summary(self):
        # a summary whose <program> is concrete is not an abstract summary.
        errs = self._refused(summary_fn="d.k")
        self.assertTrue(any("not a bare variable" in e for e in errs), errs)

    def test_missing_external_code_entry(self):
        errs = self._refused(env={"external_code": {}})
        self.assertTrue(any("no entry for callee" in e for e in errs), errs)

    def test_unresolved_bridge_ref(self):
        bad = copy.deepcopy(GOOD_BRIDGE)
        bad["at_program_proof"] = {"loop": "ghost", "label": "nope"}
        errs = self._refused(bridge=bad)
        self.assertTrue(any("does not" in e and "resolve" in e for e in errs),
                        errs)


class TestBindingGenerality(unittest.TestCase):
    """B must be at least as GENERAL as S at entry: a bridge that PINS a cell
    the summary frames (a concrete literal where S has none) is refused, so B
    cannot prove the delta for a narrower entry than S claims."""

    def test_bridge_pinning_extra_entry_is_refused(self):
        sh, nodes, get, env = build()
        # find the bridge node's text and pin its <gas> entry to a literal
        # (the honest sbridge.k frames it as `_ => ?_`).
        b_hash = resolve_ref(nodes, {"loop": "bridge", "label": "sbridge"})
        pinned = get(b_hash).replace("<gas> _ => ?_", "<gas> 100000 => ?_")
        texts = {h: get(h) for h in nodes}
        texts[b_hash] = pinned
        errs, _ = structural_errors(sh, nodes, texts.__getitem__, env)
        self.assertTrue(any("at least as general" in e for e in errs), errs)


if __name__ == "__main__":
    unittest.main()
