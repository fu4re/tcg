"""Smoke check for the Specification Games toolchain (`make check`).

Runs the shared core (tools/specgame_core.py) end to end on the pinned
toolchain. Steps, each printed as PASS or FAIL; exit 1 if any step fails:

  (0)  toolchain: pinned solc, z3 and pyrevm versions.
  (a)  compile subjects/capped_token/CappedToken.sol with the pinned settings, verify the
       settings from the emitted metadata, print sha256 of the runtime bytecode
       (the artifact identity), and check it does not depend on the file path.
  (b0) negative control: Check with no z3 on PATH must be Unknown
       (solc 0.8.35 then silently skips CHC and exits 0).
  (b)  Check on smoke/ProvedTautology.sol over CappedToken: expected Accept.
  (c)  Check on smoke/ReachableFalse.sol over CappedToken: expected Refute;
       the counterexample's x is replayed on pyrevm as a σ and must be a
       witness (the probe ends in Panic(0x01)).
  (d)  pyrevm: deploy CappedToken, mint as the owner, read totalSupply; a
       non-owner mint and an over-cap mint end in pre_unmet.

The verdicts come from the core's strict classifier: Unknown (unproved,
timeout, solver unavailable, unparsed, a target without a result line) is
never Accept.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import tempfile
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent  # specgame/
sys.path.insert(0, str(ROOT / "tools"))
import specgame_core as core  # noqa: E402

MC_TIMEOUT_MS = 20000  # smoke-test value; the protocol value is in protocol.md
WALL_TIMEOUT_S = 300
TOKEN = ROOT / "subjects" / "capped_token" / "CappedToken.sol"
TAUTOLOGY = ROOT / "smoke" / "ProvedTautology.sol"
FALSE = ROOT / "smoke" / "ReachableFalse.sol"
CAP, MINT = 1000, 700


class StepFailed(Exception):
    pass


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except ValueError:
        return str(p)


def step_toolchain(ctx: dict) -> list[str]:
    problems = core.toolchain_problems(ctx["tc"])
    if problems:
        raise StepFailed("; ".join(problems))
    fp = core.toolchain_fingerprint(ctx["tc"])
    return [f"solc {fp['solc']['version']} sha256 {fp['solc']['sha256']}",
            f"z3 {rel(ctx['tc'].z3)}: {fp['z3']['version']}",
            f"python {fp['python']}, pyrevm {fp['pyrevm']}, spec_id {fp['spec_id']}"]


def step_compile(ctx: dict) -> list[str]:
    entry = core.compile_artifact(TOKEN, ctx["tc"])
    s = json.loads(entry["metadata"])["settings"]
    checks = {
        "evmVersion": s.get("evmVersion") == core.EVM_VERSION,
        "optimizer.enabled": s.get("optimizer", {}).get("enabled") is False,
        "metadata.bytecodeHash": s.get("metadata", {}).get("bytecodeHash") == "none",
    }
    if [k for k, ok in checks.items() if not ok]:
        raise StepFailed(f"metadata settings mismatch: {json.dumps(s)}")
    if json.loads(entry["metadata"])["compiler"]["version"] != core.SOLC_VERSION:
        raise StepFailed("metadata compiler version mismatch")
    with tempfile.TemporaryDirectory(prefix="specgame-check-") as tmp:
        copy = Path(tmp) / "elsewhere.sol"
        shutil.copy(TOKEN, copy)
        if core.compile_artifact(copy, ctx["tc"])["runtime_sha256"] != entry["runtime_sha256"]:
            raise StepFailed("runtime bytecode depends on the source path")
    build = ROOT / "build"
    build.mkdir(exist_ok=True)
    (build / "CappedToken.json").write_text(json.dumps(entry, indent=1, sort_keys=True) + "\n")
    ctx["token"] = entry
    return [f"solc --standard-json, unit {core.ARTIFACT_UNIT}, input sha256 {entry['solc_input_sha256']}",
            "settings (from metadata): evmVersion=cancun optimizer.enabled=false bytecodeHash=none",
            f"runtime bytecode: {len(entry['bin_runtime']) // 2} bytes",
            f"sha256(runtime) = {entry['runtime_sha256']}",
            "same sha256 when compiled from another path: yes",
            "written: build/CappedToken.json"]


def step_no_z3(ctx: dict) -> list[str]:
    tc = core.Toolchain(ctx["tc"].solc, None)
    r = core.smtcheck(TAUTOLOGY, TOKEN, MC_TIMEOUT_MS, WALL_TIMEOUT_S, tc)
    if r.verdict != core.Verdict.UNKNOWN.value:
        raise StepFailed(f"verdict {r.verdict} with no solver available")
    return [f"verdict: {r.verdict} ({r.reason}), as required",
            *[f"solc said: {d}" for d in r.diagnostics if any(m in d for m in core.NO_SOLVER_MARKERS)]]


def step_accept(ctx: dict) -> list[str]:
    r = core.smtcheck(TAUTOLOGY, TOKEN, MC_TIMEOUT_MS, WALL_TIMEOUT_S, ctx["tc"])
    if r.verdict != core.Verdict.ACCEPT.value:
        raise StepFailed(f"verdict {r.verdict} ({r.reason}), want Accept; targets {r.targets}")
    return [f"Check({rel(TOKEN)}, {rel(TAUTOLOGY)}): {r.verdict} ({r.reason}), "
            f"timeout {r.timeout_ms} ms, input sha256 {r.solc_input_sha256}",
            *[f"target {t['function']} line {t['line']}: {t['status']}" for t in r.targets]]


def step_refute(ctx: dict) -> list[str]:
    r = core.smtcheck(FALSE, TOKEN, MC_TIMEOUT_MS, WALL_TIMEOUT_S, ctx["tc"])
    if r.verdict != core.Verdict.REFUTE.value:
        raise StepFailed(f"verdict {r.verdict} ({r.reason}), want Refute; targets {r.targets}")
    t = next(t for t in r.targets if t["status"] == "violated")
    xs = [re.match(r"^x = (\d+)$", a) for a in t["counterexample"]["assignments"]]
    xs = [m.group(1) for m in xs if m]
    if len(xs) != 1:
        raise StepFailed(f"no unique x in counterexample {t['counterexample']}")
    x = xs[0]
    if not int(x) > 5:
        raise StepFailed(f"counterexample x = {x} violates require(x > 5)")
    sigma = {"version": 1, "deployer": "alice", "ctor": {"cap": str(CAP)}, "txs": [],
             "probe": {"sender": "alice", "a": "alice", "b": "alice", "x": x, "y": "0",
                       "check": t["function"]}}
    spec_entry = core.compile_spec_over(FALSE, TOKEN, ctx["tc"])
    w = core.evaluate_witness(spec_entry, sigma)
    if not w.violated:
        raise StepFailed(f"replay is not a witness: {w.outcomes}")
    return [f"Check({rel(TOKEN)}, {rel(FALSE)}): {r.verdict}, {t['function']} line {t['line']}, x = {x}",
            f"trace: {' ; '.join(l.strip() for l in t['counterexample']['trace'])}",
            f"pyrevm replay of σ: {w.log[-1]}"]


def step_pyrevm(ctx: dict) -> list[str]:
    entry = ctx.get("token")
    if entry is None:
        raise StepFailed("no compiled CappedToken (step (a) failed)")
    mint = "mint(address,uint256)"
    sigma = {"version": 1, "deployer": "alice", "ctor": {"cap": str(CAP)}, "txs": [
        {"sender": "alice", "fn": mint, "args": ["bob", str(MINT)]},
        {"sender": "bob", "fn": mint, "args": ["bob", "1"]},
        {"sender": "alice", "fn": mint, "args": ["bob", str(CAP - MINT + 1)]},
    ]}
    o1 = core.run_sequence(entry, sigma)
    o2 = core.run_sequence(entry, sigma)
    if not core.observation_equal(o1, o2) or o1.log != o2.log:
        raise StepFailed("same σ gave different observations")
    outcomes = [t["outcome"] for t in o1.data["txs"]]
    if outcomes != ["success", "pre_unmet", "pre_unmet"]:
        raise StepFailed(f"tx outcomes {outcomes}")
    st = o1.data["state"]
    ts = int(st["totalSupply()"]["return"], 16)
    bal = int(st["balanceOf(address)[bob]"]["return"], 16)
    owner = st["owner()"]["return"][-40:]
    if ts != MINT or bal != MINT or "0x" + owner != core.POOL["alice"]:
        raise StepFailed(f"post-state totalSupply={ts} balanceOf(bob)={bal} owner=0x{owner}")
    return [f"σ: alice deploys (cap={CAP}), mints {MINT} to bob; bob mints 1; alice mints over cap",
            *[f"  {l}" for l in o1.log],
            f"totalSupply() = {ts}, balanceOf(bob) = {bal}, owner() = alice",
            f"tx outcomes {outcomes}; observation sha256 {o1.sha256()} (identical on a second run)"]


STEPS = [
    ("(0) toolchain pins", step_toolchain),
    ("(a) compile CappedToken", step_compile),
    ("(b0) negative control: no z3 on PATH is Unknown", step_no_z3),
    ("(b) Check tautology -> Accept", step_accept),
    ("(c) Check reachable assert(false) -> Refute, witness replayed", step_refute),
    ("(d) pyrevm deploy + owner mint + totalSupply", step_pyrevm),
]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--solc", required=True)
    ap.add_argument("--z3", required=True)
    a = ap.parse_args()
    ctx = {"tc": core.Toolchain(Path(a.solc).resolve(), Path(a.z3).resolve())}
    failed = 0
    for title, fn in STEPS:
        try:
            details, status = fn(ctx), "PASS"
        except StepFailed as e:
            details, status = [str(e)], "FAIL"
        except Exception as e:  # any crash in a step is a FAIL, never a skip
            details, status = [f"{type(e).__name__}: {e}"] + traceback.format_exc().splitlines()[-3:], "FAIL"
        failed += status == "FAIL"
        print(f"[{status}] {title}")
        for d in details:
            print(f"       {d}")
    print(f"check: {len(STEPS) - failed}/{len(STEPS)} PASS" + (f", {failed} FAIL" if failed else ""))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
