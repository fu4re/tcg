"""`tcg junction <i> <j>` — scaffold the consequence claim Post_i implies Pre_j.

A junction is a workspace like a loop, with role `junction` and the pair it
connects. Its claim is zero-step in content; on the prover it is encoded over
a checker step, so the same compile/prove pipeline applies. Junction claims
must never be used as trusted lemmas (`tcg graph check` enforces this).
"""
from __future__ import annotations

import sys

from tcg.commands.loop import IFACE_TEMPLATE
from tcg.outcome import Exit
from tcg.workspace import (
    WorkspaceError, find_root, load_loop, loop_dir, save_loop, write_json,
)


def scaffold(role: str, i: str, j: str) -> int:
    try:
        root = find_root()
        load_loop(root, i)
        load_loop(root, j)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    name = f"{role}-{i}-{j}"
    d = loop_dir(root, name)
    if d.exists():
        print(f"tcg: {name} already exists (see its state with `tcg status`, "
              "or `tcg iface set` to redefine it)", file=sys.stderr)
        return int(Exit.USAGE)

    save_loop(root, name, {
        "name": name, "state": "Draft", "role": role, "from": i, "to": j,
    })
    write_json(d / "iface.json", IFACE_TEMPLATE)
    (d / "claims").mkdir()

    print(f"created {role} {name} (Draft); edit {d / 'iface.json'}")
    return int(Exit.OK)


def run(args) -> int:
    return scaffold("junction", args.i, args.j)
