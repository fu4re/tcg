#!/usr/bin/env python3
"""Append-only, hash-chained JSONL session ledger (bundle pilot, task 05 section 1).

Every line is one event, serialised as canonical JSON (sorted keys, no
whitespace, UTF-8). The chain rule:

    event[1].prev = "0" * 64                      (genesis)
    event[n].prev = sha256(bytes of line n-1)     (the line WITHOUT its "\\n")

Fields of a `run` event:
    format, kind="run", seq, prev, tool, tool_hash, argv, cwd, stdout, stderr
    (paths the command's streams were captured to, or null),
    inputs  = [{"path", "sha256"}]  hashed BEFORE the command runs,
    outputs = [{"path", "sha256"}]  hashed AFTER it exits (sha256 null if absent),
    exit, started, ended (UTC, ISO 8601, "Z"), deterministic.
A `note` event records a generator / model call or a manual step: it is never
replayed, carries deterministic=false (unless --deterministic is forced for a
pure bookkeeping note), and adds model, prompt_sha256, completion_sha256, text.

Paths (cwd, inputs, outputs) are stored relative to --root (default: the
current directory), so a ledger can travel inside a bundle and be replayed
from the bundle root. argv is stored verbatim.

Usage:
  ledger.py run  --ledger L [--root R] [--in P ...] [--out P ...]
                 [--stdout F] [--stderr F] [--nondeterministic]
                 [--tool NAME] [--tool-hash H | --tool-file PATH] -- CMD ...
  ledger.py note --ledger L [--root R] --tool NAME [--model ID]
                 [--prompt F] [--completion F] [--in P ...] [--out P ...]
                 [--text STR] [--deterministic]
  ledger.py tip  --ledger L        # print "<seq> <sha256 of last line>"

`run` exits with the wrapped command's exit code (127 if it could not be
started); the event is appended in every case. A missing --in file is an
error: nothing runs and nothing is appended (exit 2).
Stdlib only.
"""
from __future__ import annotations

import argparse
import datetime as _dt
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys

FORMAT = "tcg-ledger/0.1"
GENESIS = "0" * 64


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical_line(event: dict) -> bytes:
    return json.dumps(event, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def utc_now() -> str:
    return _dt.datetime.now(_dt.timezone.utc).isoformat(
        timespec="milliseconds").replace("+00:00", "Z")


def rel(path: str, root: str) -> str:
    return os.path.relpath(os.path.abspath(path), os.path.abspath(root))


def hash_paths(paths: list[str], root: str, must_exist: bool) -> list[dict]:
    out = []
    for p in paths:
        if os.path.isfile(p):
            digest = sha256_file(p)
        elif must_exist:
            raise FileNotFoundError(p)
        else:
            digest = None
        out.append({"path": rel(p, root), "sha256": digest})
    return out


def _last_line(fh) -> bytes | None:
    fh.seek(0)
    last = None
    for line in fh:
        if line.strip():
            last = line
    if last is None:
        return None
    if not last.endswith(b"\n"):
        raise ValueError("ledger's last line is not newline-terminated "
                         "(truncated write?); refusing to append")
    return last[:-1]


def append_event(ledger: str, event: dict) -> dict:
    """Assign seq/prev under an exclusive lock and append one line."""
    os.makedirs(os.path.dirname(os.path.abspath(ledger)), exist_ok=True)
    with open(ledger, "a+b") as fh:
        fcntl.flock(fh, fcntl.LOCK_EX)
        try:
            last = _last_line(fh)
            if last is None:
                seq, prev = 1, GENESIS
            else:
                seq = int(json.loads(last)["seq"]) + 1
                prev = hashlib.sha256(last).hexdigest()
            event = dict(event, seq=seq, prev=prev, format=FORMAT)
            fh.seek(0, os.SEEK_END)
            fh.write(canonical_line(event) + b"\n")
            fh.flush()
            os.fsync(fh.fileno())
        finally:
            fcntl.flock(fh, fcntl.LOCK_UN)
    return event


def resolve_tool(argv0: str) -> str | None:
    found = shutil.which(argv0)
    return os.path.realpath(found) if found else None


def cmd_run(a) -> int:
    if not a.cmd:
        print("ledger.py run: no command after --", file=sys.stderr)
        return 2
    root = a.root
    try:
        inputs = hash_paths(a.inputs, root, must_exist=True)
    except FileNotFoundError as e:
        print(f"ledger.py run: input not found: {e}", file=sys.stderr)
        return 2
    if a.tool_hash:
        tool_hash = a.tool_hash
    else:
        tool_file = a.tool_file or resolve_tool(a.cmd[0])
        tool_hash = sha256_file(tool_file) if tool_file and os.path.isfile(tool_file) else None
    outs = list(a.outputs)
    for extra in (a.stdout, a.stderr):
        if extra and extra not in outs:
            outs.append(extra)
    started = utc_now()
    so = open(a.stdout, "wb") if a.stdout else None
    se = open(a.stderr, "wb") if a.stderr else None
    try:
        rc = subprocess.call(a.cmd, stdout=so, stderr=se)
    except OSError as e:
        print(f"ledger.py run: cannot start {a.cmd[0]!r}: {e}", file=sys.stderr)
        rc = 127
    finally:
        for f in (so, se):
            if f:
                f.close()
    ended = utc_now()
    event = {
        "kind": "run",
        "tool": a.tool or os.path.basename(a.cmd[0]),
        "tool_hash": tool_hash,
        "argv": list(a.cmd),
        "cwd": rel(os.getcwd(), root),
        "inputs": inputs,
        "outputs": hash_paths(outs, root, must_exist=False),
        "stdout": rel(a.stdout, root) if a.stdout else None,
        "stderr": rel(a.stderr, root) if a.stderr else None,
        "exit": rc,
        "started": started,
        "ended": ended,
        "deterministic": not a.nondeterministic,
    }
    ev = append_event(a.ledger, event)
    print(f"ledger: seq={ev['seq']} exit={rc}", file=sys.stderr)
    return rc


def cmd_note(a) -> int:
    try:
        inputs = hash_paths(a.inputs, a.root, must_exist=True)
        prompt = sha256_file(a.prompt) if a.prompt else None
        completion = sha256_file(a.completion) if a.completion else None
    except FileNotFoundError as e:
        print(f"ledger.py note: file not found: {e}", file=sys.stderr)
        return 2
    now = utc_now()
    event = {
        "kind": "note",
        "tool": a.tool,
        "tool_hash": a.tool_hash,
        "model": a.model,
        "prompt_sha256": prompt,
        "completion_sha256": completion,
        "text": a.text,
        "argv": None,
        "cwd": rel(os.getcwd(), a.root),
        "inputs": inputs,
        "outputs": hash_paths(a.outputs, a.root, must_exist=False),
        "exit": None,
        "started": a.started or now,
        "ended": a.ended or now,
        "deterministic": bool(a.deterministic),
    }
    ev = append_event(a.ledger, event)
    print(f"ledger: seq={ev['seq']} note", file=sys.stderr)
    return 0


def cmd_tip(a) -> int:
    if not os.path.exists(a.ledger):
        print(f"0 {GENESIS}")
        return 0
    with open(a.ledger, "rb") as fh:
        last = _last_line(fh)
    if last is None:
        print(f"0 {GENESIS}")
    else:
        print(f"{json.loads(last)['seq']} {hashlib.sha256(last).hexdigest()}")
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="ledger.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="sub", required=True)

    def common(sp):
        sp.add_argument("--ledger", required=True)
        sp.add_argument("--root", default=".", help="paths are stored relative to this dir")
        sp.add_argument("--in", dest="inputs", nargs="*", default=[], action="extend")
        sp.add_argument("--out", dest="outputs", nargs="*", default=[], action="extend")

    r = sub.add_parser("run")
    common(r)
    r.add_argument("--nondeterministic", action="store_true")
    r.add_argument("--stdout")
    r.add_argument("--stderr")
    r.add_argument("--tool")
    r.add_argument("--tool-hash", help="explicit tool hash, e.g. a docker image digest")
    r.add_argument("--tool-file", help="file whose sha256 is the tool hash")
    r.add_argument("cmd", nargs=argparse.REMAINDER)

    n = sub.add_parser("note")
    common(n)
    n.add_argument("--tool", required=True)
    n.add_argument("--tool-hash")
    n.add_argument("--model")
    n.add_argument("--prompt")
    n.add_argument("--completion")
    n.add_argument("--text")
    n.add_argument("--started")
    n.add_argument("--ended")
    n.add_argument("--deterministic", action="store_true")

    t = sub.add_parser("tip")
    t.add_argument("--ledger", required=True)

    a = p.parse_args(argv)
    if a.sub == "run":
        if a.cmd and a.cmd[0] == "--":
            a.cmd = a.cmd[1:]
        return cmd_run(a)
    if a.sub == "note":
        return cmd_note(a)
    return cmd_tip(a)


if __name__ == "__main__":
    sys.exit(main())
