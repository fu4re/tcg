"""`tcg loop new <name>` — create a loop workspace."""
from __future__ import annotations

import re
import sys

from tcg.outcome import Exit
from tcg.workspace import WorkspaceError, find_root, loop_dir, save_loop, write_json

_NAME = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_-]*$")

# Interface template: the six-part loop contract. Claim bodies are separate
# .k files referenced from `claims` (see `tcg compile-claims`).
IFACE_TEMPLATE = {
    "pre": "",
    "post": "",
    "exit": "",
    "footprint": {"reads": [], "writes": []},
    "rely": "",
    "guar": "",
    "requires": ["evm.md"],
    "imports": ["EVM"],
    "claims": [],
}


def run(args) -> int:
    if getattr(args, "loop_command", None) != "new":
        print("usage: tcg loop new <name>", file=sys.stderr)
        return int(Exit.USAGE)
    if not _NAME.match(args.name):
        print(f"tcg: invalid loop name: {args.name!r}", file=sys.stderr)
        return int(Exit.USAGE)

    try:
        root = find_root()
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    d = loop_dir(root, args.name)
    if d.exists():
        print(f"tcg: loop already exists: {args.name}", file=sys.stderr)
        return int(Exit.USAGE)

    save_loop(root, args.name, {"name": args.name, "state": "Draft"})
    write_json(d / "iface.json", IFACE_TEMPLATE)
    (d / "claims").mkdir()

    print(f"created loop {args.name} (Draft); edit {d / 'iface.json'}")
    return int(Exit.OK)
