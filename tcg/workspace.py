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

# Re-compiling is a legal, intended operation: a real audit iterates, and
# re-compiling INVALIDATES any prior proof state (the loop returns to Compiled
# and its stale Accept evidence + graph edges are dropped — see
# tcg/commands/compile_claims.py). So Compiled is reachable from every terminal
# proof state, and from Compiled itself (idempotent re-compile). The one state
# that must NOT jump to Compiled is Proving: a compile mid-prove is refused
# BEFORE any write, so exit code and on-disk effect always agree (Hole 2).
TRANSITIONS: dict[str, set[str]] = {
    "Draft": {"Compiled"},
    "Compiled": {"Compiled", "Proving", "Stale"},
    "Proving": {"Accepted", "Refuted", "Unknown"},
    "Accepted": {"Compiled", "Proving", "Stale"},
    "Refuted": {"Compiled", "Proving", "Draft", "Stale"},
    "Unknown": {"Compiled", "Proving", "Draft", "Stale"},
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
        raise WorkspaceError(
            f"no such loop: {name} (run `tcg loop new {name}`, or check the "
            "name with `tcg status`)"
        )
    return read_json(path)


def save_loop(root: Path, name: str, state: dict) -> None:
    write_json(loop_dir(root, name) / "loop.json", state)


def transition_allowed(cur: str, new_state: str) -> bool:
    """Whether cur -> new_state is legal, WITHOUT mutating anything. Callers
    that must not write on an illegal transition (compile-claims, Hole 2)
    check this first, before any side effect."""
    return new_state in TRANSITIONS.get(cur, set())


def transition(loop: dict, new_state: str) -> None:
    cur = loop.get("state", "Draft")
    if not transition_allowed(cur, new_state):
        allowed = TRANSITIONS.get(cur, set())
        raise WorkspaceError(
            f"illegal state transition: {cur} -> {new_state} "
            f"(from {cur}, allowed: {sorted(allowed) or 'none'})"
        )
    loop["state"] = new_state


EDGE_TYPES = ("trusted-lemma", "consequence", "compat")


def load_graph(root: Path) -> dict:
    path = root / "spec" / "graph.json"
    if path.is_file():
        return read_json(path)
    return {"nodes": {}, "edges": []}


def save_graph(root: Path, graph: dict) -> None:
    write_json(root / "spec" / "graph.json", graph)


def upsert_node(graph: dict, claim_hash: str, **fields) -> None:
    graph["nodes"][claim_hash] = fields


def upsert_edge(graph: dict, frm: str, to: str, edge_type: str) -> None:
    edge = {"from": frm, "to": to, "type": edge_type}
    if edge not in graph["edges"]:
        graph["edges"].append(edge)


def drop_edges_from(graph: dict, sources: set[str]) -> None:
    graph["edges"] = [e for e in graph["edges"] if e["from"] not in sources]


def drop_edges_touching(graph: dict, hashes: set[str]) -> None:
    """Drop every edge with either endpoint in `hashes` — used when a loop is
    re-compiled and its old claim nodes are invalidated (both the edges it
    owns and the trusted-lemma edges parents pointed at it)."""
    graph["edges"] = [
        e for e in graph["edges"]
        if e["from"] not in hashes and e["to"] not in hashes
    ]


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()
