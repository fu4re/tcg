"""Gate coherence fixes (coordinator review of Finding 0002):

- Fix 4: program binding is enforced inside `check_graph`, so `tcg graph check`
  (not only freeze) refuses a root whose <program> != subject/runtime.bin.
- Fix 3: `tcg vacuity` gates ROOTS only (matching freeze/verify) and does not
  spend a prover run on a non-root claim whose verdict nothing consumes.
- Fix 2: `tcg prove` drops each goal claim's vacuity record, tying its
  lifecycle to replay evidence so freeze's gate and verify's re-derivation
  cannot disagree on a stale record.

Fix 2's test drives the real `tcg prove` against a STUB `kprove` (prints
`#Top`) — no real prover — so it stays fast and deterministic while exercising
the actual code path. Run: PYTHONPATH=. python3 -m unittest tests.test_gate_lifecycle
"""
from __future__ import annotations

import contextlib
import io
import json
import os
import shutil
import stat
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from tcg.commands import compile_claims as cmd_compile
from tcg.commands import graph as cmd_graph
from tcg.commands import iface as cmd_iface
from tcg.commands import init as cmd_init
from tcg.commands import loop as cmd_loop
from tcg.commands import prove as cmd_prove
from tcg.commands import vacuity as cmd_vacuity
from tcg.outcome import Exit
from tcg.workspace import load_loop, read_json, save_loop, write_json


@contextlib.contextmanager
def capture():
    out, err = io.StringIO(), io.StringIO()
    with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
        yield out, err


def body(label="main", prog="00"):
    return (f'claim <k> A => B </k> <program> #parseByteStack("{prog}") '
            f'</program>\n [label({label}), all-path]')


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp(prefix="tcg-gate-")).resolve()
        self._cwd = os.getcwd()
        os.chdir(self.tmp)
        with capture():
            cmd_init.run(SimpleNamespace(definition="dummy-def", include=None))

    def tearDown(self):
        os.chdir(self._cwd)
        shutil.rmtree(self.tmp, ignore_errors=True)

    def make_loop(self, name, prog="00", label="main", root=True, role="loop"):
        with capture():
            cmd_loop.run(SimpleNamespace(loop_command="new", name=name))
        d = self.tmp / ".tcg" / "loops" / name
        (d / f"{label}.k").write_text(body(label, prog))
        iface = read_json(d / "iface.json")
        iface["claims"] = [{"label": label, "file": f"{label}.k",
                            "role": role, "root": root}]
        f = self.tmp / f"{name}-iface.json"
        f.write_text(json.dumps(iface))
        with capture():
            cmd_iface.run(SimpleNamespace(iface_command="set", loop=name, file=str(f)))
            cmd_compile.run(SimpleNamespace(loop=name))

    def set_subject(self, hexbytes):
        p = self.tmp / "subject" / "runtime.bin"
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(bytes.fromhex(hexbytes))

    def hash_of(self, name, label="main"):
        return read_json(self.tmp / "spec" / "interfaces.json")[name]["claims"][label]


class TestGraphCheckProgramBinding(Base):
    def test_graph_check_refuses_root_program_not_subject(self):
        self.make_loop("debit", prog="00")       # root program = 00
        self.set_subject("6000")                  # subject != 00
        with capture() as (out, err):
            rc = cmd_graph.run(SimpleNamespace(graph_command="check"))
        self.assertEqual(rc, int(Exit.REFUSED))
        self.assertIn("does not match subject/runtime.bin", out.getvalue() + err.getvalue())

    def test_graph_check_binding_silent_when_program_matches(self):
        self.make_loop("debit", prog="6000")      # root program = subject
        self.set_subject("6000")
        with capture() as (out, err):
            cmd_graph.run(SimpleNamespace(graph_command="check"))
        # still refuses (Compiled, not Accepted) but NOT for program binding
        self.assertNotIn("does not match subject/runtime.bin",
                         out.getvalue() + err.getvalue())


class TestVacuityScope(Base):
    def test_no_root_claims_passes_without_probing(self):
        # a loop whose only claim is a non-root lemma: nothing to probe, so
        # `tcg vacuity` must exit OK WITHOUT invoking the prover.
        self.make_loop("frameonly", label="base", root=False, role="frame")
        self.set_state_accepted("frameonly")
        h = self.hash_of("frameonly", "base")
        with capture() as (out, err):
            rc = cmd_vacuity.run(SimpleNamespace(loop="frameonly",
                                                 definition=None, include=None))
        self.assertEqual(rc, int(Exit.OK))
        text = out.getvalue() + err.getvalue()
        self.assertIn("no root claims to probe", text)
        self.assertIn("not probing non-root", text)
        # no probe was run, so no record was written (no wasted prover run)
        self.assertFalse((self.tmp / ".tcg" / "vacuity" / f"{h}.json").exists())

    def set_state_accepted(self, name):
        lp = load_loop(self.tmp, name)
        lp["state"] = "Accepted"
        save_loop(self.tmp, name, lp)


class TestProveDropsVacuity(Base):
    def _stub_kprove(self):
        bindir = self.tmp / "stubbin"
        bindir.mkdir()
        k = bindir / "kprove"
        k.write_text("#!/usr/bin/env python3\nprint('#Top')\n")
        k.chmod(k.stat().st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)
        return bindir

    def test_prove_invalidates_stale_vacuity_record(self):
        self.make_loop("demo", prog="00")
        h = self.hash_of("demo")
        # a stale vacuity record from a prior probe
        write_json(self.tmp / ".tcg" / "vacuity" / f"{h}.json",
                   {"claim": h, "vacuous": False})
        bindir = self._stub_kprove()
        old_path = os.environ["PATH"]
        os.environ["PATH"] = f"{bindir}{os.pathsep}{old_path}"
        try:
            with capture():
                rc = cmd_prove.run(SimpleNamespace(target="demo",
                                                   definition=None, include=None))
        finally:
            os.environ["PATH"] = old_path

        self.assertEqual(rc, int(Exit.OK))
        self.assertEqual(load_loop(self.tmp, "demo")["state"], "Accepted")
        # replay evidence refreshed on the SAME event that dropped the vacuity
        # record -> freeze cannot pass a stale non-vacuous record
        self.assertTrue((self.tmp / "evidence" / "replay" / f"{h}.json").exists())
        self.assertFalse((self.tmp / ".tcg" / "vacuity" / f"{h}.json").exists())


if __name__ == "__main__":
    unittest.main()
