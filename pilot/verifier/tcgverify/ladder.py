"""Assemble ladder.json (task 06 "Output"). One key per level; no summary mark.
A level whose code raised is reported with status "error", never as a pass."""
from __future__ import annotations

import os
import time
import traceback

from . import canon, levels
from .view import View

VERIFIER_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def verifier_files() -> list[str]:
    pkg = os.path.join(VERIFIER_DIR, "tcgverify")
    names = sorted(f for f in os.listdir(pkg) if f.endswith((".py", ".json")))
    return ["verify.py"] + [f"tcgverify/{n}" for n in names]


def verifier_hash() -> str:
    """sha256 of canonical JSON [[relpath, sha256], ...] over verify.py and
    tcgverify/*.py|*.json (tests and STATUS.md excluded)."""
    return canon.sha256_bytes(canon.canonical(
        [[f, canon.sha256_file(os.path.join(VERIFIER_DIR, f))] for f in verifier_files()]))


def _guard(fn, *args, timings: dict | None = None, name: str = ""):
    t0 = time.monotonic()
    try:
        return fn(*args)
    except Exception as e:  # a crash is reported as such, never as a pass
        return {"status": "error", "error": f"{type(e).__name__}: {e}",
                "traceback": traceback.format_exc()[-3000:]}
    finally:
        if timings is not None:
            timings[name] = round(time.monotonic() - t0, 3)


def build(bundle_dir: str, oracle_pub: bytes, producer_pub: bytes, chain, variant: str,
          execute: bool = True, docker_limits: tuple = (), l4_skip_provers: bool = False) -> dict:
    view = View(bundle_dir)
    outside: list[str] = []
    vh = verifier_hash()
    try:
        man = view.manifest or {}
        try:
            root = canon.root_hash(man) if view.manifest else None
        except (ValueError, TypeError):
            root = None
        wall: dict = {}
        out = {
            "bundle_root": root,
            "bundle_root_declared": man.get("root_hash"),
            "verifier_hash": vh,
            "variant": variant,
            "self_contained": None,
            "self_contained_declared": man.get("self_contained"),
            "executed_bundle_supplied_commands": execute,
            "docker_limits": list(docker_limits),
            "l4_skip_provers": l4_skip_provers,
            "wall_s": wall,
        }
        out["L0"] = _guard(levels.level0, view, chain, producer_pub, outside, timings=wall, name="L0")
        out["L1"] = _guard(levels.level1, view, variant, vh, outside, tuple(docker_limits), timings=wall, name="L1")
        out["L2"] = _guard(levels.level2, view, execute, outside, timings=wall, name="L2")
        out["L3"] = _guard(levels.level3, view, oracle_pub, producer_pub, timings=wall, name="L3")
        out["L4"] = _guard(levels.level4, view, execute, outside, l4_skip_provers, timings=wall, name="L4")
        claims = out["L1"].get("claims") or []
        uses_external_checker = any(not c.get("self_contained", False) for c in claims) or \
            any(o.startswith(("lake dependency", "docker image")) for o in outside)
        out["self_contained"] = bool(claims) and not uses_external_checker
        seen: list[str] = []
        for o in outside:
            if o not in seen:
                seen.append(o)
        out["outside_bundle"] = seen
        return out
    finally:
        view.close()
