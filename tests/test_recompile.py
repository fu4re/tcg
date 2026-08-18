"""P1 (Hole 2): compile-claims is atomic w.r.t. its verdict, and re-compiling
a proved/refuted/unknown loop is a supported, coherent operation.

Gate G3 found that compile-claims wrote claim files, graph nodes, and
interfaces.json and THEN raised on an illegal transition — exit 1 ("failed")
while the workspace said "done." These tests pin: (1) an illegal compile
(from Proving) writes NOTHING and exits USAGE; (2) re-compiling from a terminal
proof state exits OK, returns the loop to Compiled, and drops the now-stale
Accept/vacuity evidence; (3) re-compiling a child cascades its dependent
parent to Stale. No prover — pure workspace state. Run:
PYTHONPATH=. python3 -m unittest tests.test_recompile
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

from tcg.commands import compile_claims as cmd_compile
from tcg.commands import iface as cmd_iface
from tcg.commands import init as cmd_init
from tcg.commands import loop as cmd_loop
from tcg.outcome import Exit
from tcg.workspace import load_graph, load_loop, read_json, save_loop, write_json

def mkbody(label="main", prog="00"):
    return (f'claim <k> A => B </k> <program> #parseByteStack("{prog}") '
            f'</program>\n [label({label}), all-path]')


@contextlib.contextmanager
def quiet():
    with contextlib.redirect_stdout(io.StringIO()), \
            contextlib.redirect_stderr(io.StringIO()):
        yield


def snapshot(root: Path) -> dict[str, bytes]:
    return {str(p.relative_to(root)): p.read_bytes()
            for p in sorted(root.rglob("*")) if p.is_file()}


class RecompileBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tcg-recompile-")).resolve()
        self._cwd = os.getcwd()
        os.chdir(self.tmp)
        with quiet():
            cmd_init.run(SimpleNamespace(definition=None, include=None))

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def new_loop(self, name, prog="00", label="main", root=True, role="loop"):
        with quiet():
            cmd_loop.run(SimpleNamespace(loop_command="new", name=name))
        d = self.tmp / ".tcg" / "loops" / name
        (d / f"{label}.k").write_text(mkbody(label, prog))
        iface = read_json(d / "iface.json")
        iface["claims"] = [{"label": label, "file": f"{label}.k",
                            "role": role, "root": root}]
        ifile = self.tmp / f"{name}-iface.json"
        ifile.write_text(json.dumps(iface))
        with quiet():
            cmd_iface.run(SimpleNamespace(iface_command="set", loop=name,
                                          file=str(ifile)))

    def compile(self, name):
        with quiet():
            return cmd_compile.run(SimpleNamespace(loop=name))

    def set_state(self, name, state):
        lp = load_loop(self.tmp, name)
        lp["state"] = state
        save_loop(self.tmp, name, lp)

    def claim_hash(self, name, label="main"):
        return read_json(self.tmp / "spec" / "interfaces.json")[name]["claims"][label]

    def write_evidence(self, h):
        write_json(self.tmp / "evidence" / "replay" / f"{h}.json", {"claim": h})
        write_json(self.tmp / ".tcg" / "vacuity" / f"{h}.json",
                   {"claim": h, "vacuous": False})


class TestAtomicity(RecompileBase):
    def test_illegal_compile_from_proving_writes_nothing(self):
        self.new_loop("demo")
        self.assertEqual(self.compile("demo"), int(Exit.OK))
        self.set_state("demo", "Proving")

        before = snapshot(self.tmp)
        rc = self.compile("demo")
        after = snapshot(self.tmp)

        self.assertEqual(rc, int(Exit.USAGE))                 # exit says "failed"
        self.assertEqual(load_loop(self.tmp, "demo")["state"], "Proving")
        self.assertEqual(before, after)                        # ...and effect agrees


class TestRecompileInvalidates(RecompileBase):
    def test_recompile_from_unknown_returns_compiled_and_drops_evidence(self):
        self.new_loop("demo")
        self.compile("demo")
        h = self.claim_hash("demo")
        self.set_state("demo", "Unknown")
        self.write_evidence(h)

        rc = self.compile("demo")

        self.assertEqual(rc, int(Exit.OK))                     # exit says "done"
        self.assertEqual(load_loop(self.tmp, "demo")["state"], "Compiled")
        # stale Accept + vacuity evidence dropped (recompile invalidates proof)
        self.assertFalse((self.tmp / "evidence" / "replay" / f"{h}.json").exists())
        self.assertFalse((self.tmp / ".tcg" / "vacuity" / f"{h}.json").exists())
        # the node is still present (same body -> same hash)
        self.assertIn(h, load_graph(self.tmp)["nodes"])

    def test_recompile_changed_body_drops_old_node_and_evidence(self):
        self.new_loop("demo")
        self.compile("demo")
        h1 = self.claim_hash("demo")
        self.set_state("demo", "Accepted")
        self.write_evidence(h1)
        # author edits the claim body, then re-compiles from Accepted
        (self.tmp / ".tcg" / "loops" / "demo" / "main.k").write_text(mkbody("main", "6000"))

        rc = self.compile("demo")
        h2 = self.claim_hash("demo")

        self.assertEqual(rc, int(Exit.OK))
        self.assertNotEqual(h1, h2)
        self.assertEqual(load_loop(self.tmp, "demo")["state"], "Compiled")
        nodes = load_graph(self.tmp)["nodes"]
        self.assertIn(h2, nodes)
        self.assertNotIn(h1, nodes)                            # old node gone
        self.assertFalse((self.tmp / "evidence" / "replay" / f"{h1}.json").exists())


class TestCascade(RecompileBase):
    def test_recompiling_child_marks_dependent_parent_stale(self):
        self.new_loop("child", prog="00", label="base", root=False, role="frame")
        self.compile("child")
        hc = self.claim_hash("child", "base")
        self.new_loop("parent", prog="6000", label="main", root=True, role="loop")
        self.compile("parent")
        hp = self.claim_hash("parent", "main")

        # simulate: both proved, parent trusts child as a lemma (edge p->c)
        self.set_state("child", "Accepted")
        self.set_state("parent", "Accepted")
        self.write_evidence(hc)
        self.write_evidence(hp)
        graph = load_graph(self.tmp)
        graph["edges"].append({"from": hp, "to": hc, "type": "trusted-lemma"})
        write_json(self.tmp / "spec" / "graph.json", graph)

        rc = self.compile("child")

        self.assertEqual(rc, int(Exit.OK))
        self.assertEqual(load_loop(self.tmp, "child")["state"], "Compiled")
        # the dependent parent is cascaded to Stale and its evidence dropped
        self.assertEqual(load_loop(self.tmp, "parent")["state"], "Stale")
        self.assertFalse((self.tmp / "evidence" / "replay" / f"{hp}.json").exists())
        # the stale edge into the child is dropped
        edges = load_graph(self.tmp)["edges"]
        self.assertFalse(any(e["to"] == hc for e in edges))


if __name__ == "__main__":
    unittest.main()
