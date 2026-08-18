"""`tcg status` — read-only workspace overview and next-step hints.

For an agent that knows nothing about the project beyond `tcg --help`: this is
the one command that answers "where am I and what do I do next" at any point
in the pipeline. It reads workspace state only (loops, graph, oracle record,
subject, toolchain.lock) and never invokes the prover — always exit 0 once a
workspace is found.

Every "next:" line is derived mechanically from the loop state machine
(`tcg.workspace.TRANSITIONS`) and from the freeze/graph-check preconditions,
not from prose judgment — so it stays truthful as the workspace evolves.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tcg.commands.graph import check_graph
from tcg.outcome import Exit
from tcg.workspace import (
    WORKSPACE_DIR, WorkspaceError, find_root, load_graph, read_json,
)

# One template per loop state; {name} is filled with the loop's own name.
# Mirrors tcg.workspace.TRANSITIONS — every state that machine can hold has an
# entry here so `next:` never falls through to a guess.
_NEXT_BY_STATE: dict[str, str] = {
    "Draft": "set an interface: tcg iface set {name} --file <iface.json>",
    "Compiled": "tcg prove {name}",
    "Stale": "interface changed since compile: tcg compile-claims {name}",
    "Proving": "tcg prove {name} (a previous run may not have finished; safe to re-run)",
    "Accepted": "accepted; counts once `tcg graph check` / `tcg freeze` pass "
                "for the whole workspace",
    "Refuted": "revise and recompile: tcg iface set {name} --file <iface.json>, "
               "then tcg compile-claims {name}",
    "Unknown": "tcg prove {name} again (or raise replay.timeout_seconds in "
               "toolchain.lock)",
}


def _loop_next(name: str, state: str) -> str:
    return _NEXT_BY_STATE.get(state, f"tcg prove {name}").format(name=name)


def _entries(root: Path) -> list[dict]:
    loops_dir = root / WORKSPACE_DIR / "loops"
    if not loops_dir.is_dir():
        return []
    out = []
    for d in sorted(loops_dir.iterdir()):
        f = d / "loop.json"
        if f.is_file():
            out.append(read_json(f))
    return out


def _workspace_next(root: Path, entries: list[dict],
                    oracle_ok: bool, subject_ok: bool) -> str:
    if not entries:
        return "tcg loop new <name>"

    by_state: dict[str, list[str]] = {}
    for e in entries:
        by_state.setdefault(e.get("state", "Draft"), []).append(e["name"])

    # Priority follows the documented workflow order: resolve the
    # earliest-stage loop first. "Accepted" is deliberately absent here — an
    # Accepted loop needs nothing further of its own.
    for state in ("Draft", "Stale", "Compiled", "Refuted", "Unknown", "Proving"):
        if state in by_state:
            return _loop_next(sorted(by_state[state])[0], state)

    # Every loop is Accepted: the workspace-level gates take over, in the
    # order `tcg freeze` itself checks them.
    if check_graph(root):
        return "tcg graph check (see violations)"
    if not oracle_ok:
        return "tcg approve --reviewer <name>"
    if not subject_ok:
        return "tcg subject set --runtime <path>"
    if (root / "bundle").exists():
        return ("bundle already assembled; tcg verify bundle (or remove "
                "bundle/ and re-run tcg freeze after changes)")
    return "tcg freeze"


def run(args) -> int:
    try:
        root = find_root()
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    entries = _entries(root)
    interfaces_path = root / "spec" / "interfaces.json"
    interfaces = read_json(interfaces_path) if interfaces_path.is_file() else {}
    graph = load_graph(root)
    lock_path = root / WORKSPACE_DIR / "toolchain.lock"
    lock = read_json(lock_path) if lock_path.is_file() else {}

    print(f"tcg: workspace at {root}")
    print()
    if entries:
        print("loops:")
        for e in entries:
            name = e["name"]
            role = e.get("role", "loop")
            state = e.get("state", "Draft")
            claims = interfaces.get(name, {}).get("claims", {})
            claims_str = ",".join(
                f"{lbl}={h[:12]}" for lbl, h in sorted(claims.items())
            ) or "none"
            print(f"  {name}  role={role}  state={state}  claims={claims_str}")
            print(f"    next: {_loop_next(name, state)}")
    else:
        print("loops: (none)")
    print()

    nodes, edges = graph["nodes"], graph["edges"]
    roots = {h for h, n in nodes.items() if n.get("root")}
    print(f"graph: {len(nodes)} node(s), {len(edges)} edge(s), {len(roots)} root(s)")

    record_path = root / "assumptions" / "oracle-record.json"
    oracle_ok = False
    if record_path.is_file():
        approved = set(read_json(record_path).get("roots", {}))
        oracle_ok = approved == roots
        if oracle_ok:
            print("oracle record: present, covers current roots")
        else:
            print("oracle record: present, STALE — does not cover current "
                  "roots (tcg approve --reviewer <name>)")
    else:
        print("oracle record: missing (tcg approve --reviewer <name>)")

    has_runtime = (root / "subject" / "runtime.bin").is_file()
    has_env = (root / "subject" / "environment.json").is_file()
    subject_ok = has_runtime and has_env
    hint = "" if subject_ok else "  (tcg subject set --runtime <path>)"
    print(f"subject: runtime.bin {'present' if has_runtime else 'missing'}, "
          f"environment.json {'present' if has_env else 'missing'}{hint}")

    definition = lock.get("definition")
    if definition:
        print(f"definition: configured ({definition})")
    else:
        print("definition: not configured (tcg init --definition PATH or "
              "$TCG_DEFINITION at init time; or edit .tcg/toolchain.lock)")

    print()
    print(f"next: {_workspace_next(root, entries, oracle_ok, subject_ok)}")
    return int(Exit.OK)
