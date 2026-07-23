"""Workspace layout and loop state machine.

A workspace mirrors the bundle layout (spec/, theory/) plus `.tcg/` for
mutable state. `verify` never reads any of this — it takes only a bundle.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

WORKSPACE_DIR = ".tcg"

# Loop lifecycle. Stale marks a loop whose interface changed after compile.
STATES = ("Draft", "Compiled", "Proving", "Accepted", "Refuted", "Unknown", "Stale")

TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"Compiled"},
    "Compiled": {"Proving", "Stale"},
    "Proving": {"Accepted", "Refuted", "Unknown"},
    "Accepted": {"Stale"},
    "Refuted": {"Draft", "Stale"},
    "Unknown": {"Draft", "Stale"},
    "Stale": {"Compiled"},
}


class WorkspaceError(Exception):
    pass


def find_root(start: Path | None = None) -> Path:
    """Walk up from `start` (default cwd) to the directory holding `.tcg/`."""
    cur = (start or Path.cwd()).resolve()
    for p in (cur, *cur.parents):
        if (p / WORKSPACE_DIR).is_dir():
            return p
    raise WorkspaceError("not inside a tcg workspace (run `tcg init` first)")


def loop_dir(root: Path, name: str) -> Path:
    return root / WORKSPACE_DIR / "loops" / name


def read_json(path: Path) -> dict:
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, sort_keys=True)
        f.write("\n")


def load_loop(root: Path, name: str) -> dict:
    path = loop_dir(root, name) / "loop.json"
    if not path.is_file():
        raise WorkspaceError(f"no such loop: {name}")
    return read_json(path)


def save_loop(root: Path, name: str, state: dict) -> None:
    write_json(loop_dir(root, name) / "loop.json", state)


def transition(loop: dict, new_state: str) -> None:
    cur = loop.get("state", "Draft")
    if new_state not in TRANSITIONS.get(cur, set()):
        raise WorkspaceError(f"illegal state transition: {cur} -> {new_state}")
    loop["state"] = new_state


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
