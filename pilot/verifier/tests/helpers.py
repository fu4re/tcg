"""Shared test helpers: build the toy bundle, run verify.py as a subprocess with
the fake docker / fake Lean toolchain on PATH, compare ladders level by level."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "fixtures"))
sys.path.insert(0, os.path.dirname(HERE))

import toy_bundle as toy  # noqa: E402

VERIFY = os.path.join(os.path.dirname(HERE), "verify.py")


def fake_env(**extra) -> dict:
    env = dict(os.environ)
    env["PATH"] = toy.FAKEBIN + os.pathsep + env.get("PATH", "")
    env["TCG_FAKE_DOCKER_ID"] = toy.FAKE_IMAGE_ID
    env["TCG_LEAN_TOOLCHAINS"] = toy.FAKELEAN
    env.update(extra)
    return env


def verify(bundle: str, keys: dict, chain_args: list[str], variant: str = "A", env=None,
           oracle_pub: str | None = None, extra: list[str] | None = None) -> dict:
    out = os.path.join(tempfile.mkdtemp(prefix="ladder-"), "ladder.json")
    argv = [sys.executable, VERIFY, bundle, "--oracle-pubkey", oracle_pub or keys["oracle_pub"],
            "--producer-pubkey", keys["producer_pub"], *chain_args, "--variant", variant,
            "--out", out, *(extra or [])]
    p = subprocess.run(argv, capture_output=True, text=True, env=env or fake_env())
    if p.returncode != 0:
        raise AssertionError(f"verify.py exit {p.returncode}: {p.stderr}")
    with open(out, encoding="utf-8") as f:
        result = json.load(f)
    shutil.rmtree(os.path.dirname(out))
    return result


RANK = {"pass": 2, "partial": 1, "fail": 0, "refused": 0, "error": 0}


def measures(ladder: dict) -> dict:
    """Per-field measures used ONLY by tests to compare two ladders. Not a summary:
    each field is compared on its own, nothing is combined."""
    l2 = ladder["L2"]
    return {
        "L0": RANK[ladder["L0"]["status"]],
        "L1": RANK[ladder["L1"]["status"]],
        "L2.coverage_total": int(bool(l2.get("coverage_total"))),
        "L2.pre_witness_replays": int(bool(l2.get("pre_witness_replays"))),
        "L2.mutants_witnessed": sum(1 for m in l2.get("mutants") or []
                                    if m.get("outcome") in ("refute", "concrete_trace_violation")),
        "L2.backtranslation_present": int(l2.get("backtranslation") is not None),
        "L3": RANK[ladder["L3"]["status"]],
        "L4": RANK[ladder["L4"]["status"]],
    }


def compare(before: dict, after: dict) -> tuple[list[str], list[str]]:
    """(lowered fields, raised fields)."""
    b, a = measures(before), measures(after)
    return [k for k in b if a[k] < b[k]], [k for k in b if a[k] > b[k]]


class ToyCase(unittest.TestCase):
    """Builds keys + one pristine toy bundle per class; each test gets a fresh copy."""

    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory(prefix="toy-")
        cls.keys = toy.make_keys(os.path.join(cls._tmp.name, "keys"))
        cls.pristine = os.path.join(cls._tmp.name, "pristine")
        toy.build(cls.pristine, cls.keys)
        cls.snap = toy.snapshot(os.path.join(cls._tmp.name, "snap"))

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def fresh(self) -> str:
        d = tempfile.mkdtemp(prefix="bundle-", dir=self._tmp.name)
        shutil.rmtree(d)
        shutil.copytree(self.pristine, d)
        return d

    def run_snap(self, bundle, **kw) -> dict:
        return verify(bundle, self.keys, ["--state-snapshot", kw.pop("snap", self.snap)], **kw)
