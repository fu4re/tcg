"""Check' instances for L1 (DECISIONS D6, D7). Each returns a per-claim result
dict whose "result" is one of RESULTS; the values are never merged.

  accept                 checker accepted (KEVM: exit 0 + #Top; Lean: kernel
                         accepted, axioms within the standard set, no admits)
  refute                 KEVM symbolic stuck state ("cannot be rewritten
                         further"); no concrete counterexample is produced
  unknown                timeout, residual implication, unrecognised output
  not_accept             Lean: build failed, admitted hole or non-standard axiom
  checker_hash_mismatch  the checker found is not the one T_hat names; not run
  checker_unavailable    the named checker could not be located; not run
  malformed              the certificate / invocation file is unusable; not run
  not_checked            no certificate checkable under the selected variant
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import time

from . import canon

RESULTS = ("accept", "refute", "unknown", "not_accept", "checker_hash_mismatch",
           "checker_unavailable", "malformed", "not_checked")
STANDARD_LEAN_AXIOMS = frozenset({"propext", "Classical.choice", "Quot.sound"})
# Fixed kprove argv inside the pinned image (mirrors pilot/checker/run-claim.sh).
KPROVE_FIXED = ["--definition", "/opt/kevm/haskell",
                "-I", "/opt/kevm/evm-semantics-source", "-I", "/opt/kevm/plugin"]
KPROVE_FORBIDDEN_ARGS = ("--definition", "--directory", "-d", "--output-file", "-o")


def run(argv, cwd=None, timeout=None, env=None):
    """(returncode, stdout, stderr, timed_out, wall_s). Never raises for the tool's own failure."""
    t0 = time.monotonic()
    try:
        p = subprocess.run(argv, cwd=cwd, timeout=timeout, env=env, capture_output=True)
        return p.returncode, p.stdout.decode(errors="replace"), p.stderr.decode(errors="replace"), \
            False, round(time.monotonic() - t0, 3)
    except subprocess.TimeoutExpired as e:
        out = e.stdout.decode(errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
        return None, out, "", True, round(time.monotonic() - t0, 3)
    except OSError as e:
        return None, "", str(e), False, round(time.monotonic() - t0, 3)


# --- KEVM verdict judge: ported from tcg/verdict.py classify() (validated there
# against real Haskell-backend kprove logs, tests/test_classify.py). -----------
_WS = re.compile(r"\s+")
_STUCK_OR_REFUTE = re.compile(
    r"(?P<stuck>unifies with the destination)|(?P<refute>cannot be rewritten further)", re.IGNORECASE)


def classify_kprove(returncode, log: str, timed_out: bool) -> str:
    if timed_out:
        return "unknown"
    if returncode == 0:
        return "accept" if "#Top" in log else "unknown"
    saw_refute = False
    for m in _STUCK_OR_REFUTE.finditer(_WS.sub(" ", log)):
        if m.group("stuck"):
            return "unknown"
        saw_refute = True
    return "refute" if saw_refute else "unknown"


def _hashes(entry) -> list[str]:
    h = entry.get("hash")
    return [h] if isinstance(h, str) else [x for x in (h or []) if isinstance(x, str)]


def docker_image_identity(entry: dict, outside: list[str]):
    """Locate the pinned image locally and compare its digest with T_hat.
    Returns (image_id or None, status in {"ok", "checker_hash_mismatch", "checker_unavailable"}, detail)."""
    want = _hashes(entry)
    ref = entry.get("image") or (want[0] if want else None)
    if not ref:
        return None, "checker_unavailable", "T_hat names no image hash"
    rc, out, err, _, _ = run(["docker", "image", "inspect", ref], timeout=120)
    if rc != 0:
        rc, _, perr, _, _ = run(["docker", "pull", ref], timeout=3600)
        if rc != 0:
            return None, "checker_unavailable", f"docker inspect/pull {ref} failed: {(err or perr).strip()[:300]}"
        outside.append(f"docker image pulled from registry: {ref}")
        rc, out, err, _, _ = run(["docker", "image", "inspect", ref], timeout=120)
        if rc != 0:
            return None, "checker_unavailable", err.strip()[:300]
    try:
        info = json.loads(out)[0]
    except (ValueError, IndexError, KeyError) as e:
        return None, "checker_unavailable", f"docker image inspect output unreadable: {e}"
    found = [info.get("Id")] + [d.split("@", 1)[1] for d in info.get("RepoDigests") or [] if "@" in d]
    if not any(f in want for f in found if f):
        return None, "checker_hash_mismatch", f"T_hat {want} vs local image {found}"
    return info["Id"], "ok", f"image {info['Id']}"


DOCKER_LIMIT = re.compile(r"^--(memory|cpus)=[0-9][0-9.]*[bkmg]?$")


def kevm_claim(claim: str, invocation_path: str, claim_file_path: str, image_id: str, inv: dict,
               limits: tuple = ()) -> dict:
    """Re-discharge one claim in the image (variant A). The verifier, not the
    bundle, sets every docker flag; the bundle contributes only the claim directory,
    spec module and extra kprove args (some of which are refused)."""
    res = {"claim": claim, "checker": "kevm-prove", "self_contained": False,
           "invocation": invocation_path, "image": image_id}
    extra = inv.get("kprove_args") or []
    if not isinstance(inv.get("spec_module"), str) or not all(isinstance(a, str) for a in extra):
        return dict(res, result="malformed", detail="spec_module / kprove_args malformed")
    bad = [a for a in extra if a.split("=", 1)[0] in KPROVE_FORBIDDEN_ARGS]
    if bad:
        return dict(res, result="malformed", detail=f"refused kprove args {bad}")
    timeout = inv.get("timeout_s") if isinstance(inv.get("timeout_s"), int) else 1800
    with tempfile.TemporaryDirectory() as tmp, tempfile.TemporaryDirectory() as scratch:
        # the claim's directory in the hash-verified view (only verified children), as run-claim.sh mounts it
        claim_dir = shutil.copytree(os.path.dirname(claim_file_path), os.path.join(tmp, "claim"))
        argv = ["docker", "run", "--rm", *limits, "--platform", "linux/amd64", "--network", "none",
                "--user", f"{os.getuid()}:{os.getgid()}", "-e", "HOME=/tmp",
                "-v", f"{claim_dir}:/claim:ro", "-v", f"{scratch}:/work", "-w", "/work", image_id,
                "kprove", f"/claim/{os.path.basename(claim_file_path)}", *KPROVE_FIXED,
                "--spec-module", inv["spec_module"], *extra]
        rc, out, err, timed_out, wall = run(argv, timeout=timeout)
    return dict(res, result=classify_kprove(rc, out, timed_out), exit=rc, timed_out=timed_out,
                wall_s=wall, stdout_sha256=canon.sha256_bytes(out.encode()),
                stderr_tail=err[-2000:], argv=argv)


# --- Lean ------------------------------------------------------------------
_LINE_COMMENT = re.compile(r"--[^\n]*")
_BLOCK_COMMENT = re.compile(r"/-.*?-/", re.DOTALL)
_ADMIT = re.compile(r"\b(sorry|admit)\b")
_AXIOMS = re.compile(r"'([^']+)' depends on axioms: \[([^\]]*)\]")
_NO_AXIOMS = re.compile(r"'([^']+)' does not depend on any axioms")


def count_admits(source: str) -> int:
    return len(_ADMIT.findall(_LINE_COMMENT.sub("", _BLOCK_COMMENT.sub("", source))))


def lean_toolchain_dir(toolchain: str) -> str:
    """elan's on-disk name for a toolchain: '/' -> '--', ':' -> '---'."""
    base = os.environ.get("TCG_LEAN_TOOLCHAINS", os.path.expanduser("~/.elan/toolchains"))
    return os.path.join(base, toolchain.strip().replace("/", "--").replace(":", "---"))


def lean_project(project_dir: str, theorems: list[tuple[str, str, str]], entry: dict,
                 allowed: frozenset, outside: list[str], timeout: int = 3600) -> list[dict]:
    """Rebuild a Lean project from source in a scratch copy and print axioms.
    theorems = [(claim, theorem name, source path in view)]. Shipped .olean /
    .lake build outputs are deleted first: the kernel re-checks from source."""
    base = [{"claim": c, "checker": "lean", "theorem": t, "self_contained": True} for c, t, _ in theorems]
    try:
        with open(os.path.join(project_dir, "lean-toolchain"), encoding="utf-8") as f:
            toolchain = f.read().strip()
    except OSError:
        return [dict(b, result="malformed", detail="no lean-toolchain in project") for b in base]
    lean_bin = os.path.join(lean_toolchain_dir(toolchain), "bin", "lean")
    lake_bin = os.path.join(lean_toolchain_dir(toolchain), "bin", "lake")
    if not (os.path.isfile(lean_bin) and os.path.isfile(lake_bin)):
        return [dict(b, result="checker_unavailable", detail=f"toolchain {toolchain} not installed") for b in base]
    lean_hash = canon.sha256_file(lean_bin)
    if lean_hash not in _hashes(entry):
        return [dict(b, result="checker_hash_mismatch",
                     detail=f"lean binary sha256 {lean_hash} not in T_hat {_hashes(entry)}") for b in base]
    outside.append(f"Lean toolchain {toolchain} at {lean_bin} (sha256 {lean_hash})")
    results = []
    with tempfile.TemporaryDirectory() as tmp:
        work = os.path.join(tmp, "proj")
        shutil.copytree(project_dir, work, symlinks=False)
        shutil.rmtree(os.path.join(work, ".lake", "build"), ignore_errors=True)
        for dp, _, fs in os.walk(work):
            for f in fs:
                if f.endswith((".olean", ".ilean", ".olean.hash", ".trace")):
                    os.remove(os.path.join(dp, f))
        try:
            with open(os.path.join(work, "lake-manifest.json"), encoding="utf-8") as f:
                pkgs = json.load(f).get("packages", [])
        except (OSError, ValueError):
            pkgs = []
        for pk in pkgs:
            if pk.get("type") == "git":
                outside.append(f"lake dependency {pk.get('name')} @ {pk.get('rev')} from {pk.get('url')}")
        env = dict(os.environ, PATH=os.path.dirname(lean_bin) + os.pathsep + os.environ.get("PATH", ""))
        rc, out, err, timed_out, wall = run([lake_bin, "build"], cwd=work, timeout=timeout, env=env)
        if rc != 0:
            r = "unknown" if timed_out else "not_accept"
            return [dict(b, result=r, detail="lake build failed", build_tail=(out + err)[-2000:],
                         wall_s=wall) for b in base]
        for b, (_, thm, src) in zip(base, theorems):
            with open(src, encoding="utf-8", errors="replace") as f:
                admits = count_admits(f.read())
            mod = os.path.splitext(os.path.relpath(src, project_dir))[0].replace(os.sep, ".")
            check = os.path.join(work, "TcgAxiomCheck.lean")
            with open(check, "w", encoding="utf-8") as f:
                f.write(f"import {mod}\n#print axioms {thm}\n")
            rc, out, err, timed_out, w2 = run([lake_bin, "env", lean_bin, check], cwd=work,
                                              timeout=timeout, env=env)
            axioms = None
            m, n = _AXIOMS.search(out), _NO_AXIOMS.search(out)
            if m and m.group(1).removeprefix("_root_.") == thm.removeprefix("_root_."):
                axioms = sorted(a.strip() for a in m.group(2).split(",") if a.strip())
            elif n:
                axioms = []
            if rc != 0 or axioms is None:
                results.append(dict(b, result="unknown" if timed_out else "not_accept",
                                    detail="#print axioms failed", output_tail=(out + err)[-2000:],
                                    admits=admits, axioms=axioms))
                continue
            extra = sorted(set(axioms) - allowed)
            ok = not extra and admits == 0
            results.append(dict(b, result="accept" if ok else "not_accept", axioms=axioms,
                                non_standard_axioms=extra, admits=admits, wall_s=round(wall + w2, 3)))
    return results
