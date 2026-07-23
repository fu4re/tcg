"""`tcg iface set <loop> --file <iface.json>` — set the loop interface."""
from __future__ import annotations

import sys

from tcg.outcome import Exit
from tcg.workspace import (
    WorkspaceError, find_root, load_loop, loop_dir, read_json, save_loop, write_json,
)

REQUIRED_KEYS = ("pre", "post", "exit", "footprint", "rely", "guar", "claims")


def validate(iface: dict) -> list[str]:
    errors = []
    for key in REQUIRED_KEYS:
        if key not in iface:
            errors.append(f"missing key: {key}")
    fp = iface.get("footprint")
    if fp is not None and (
        not isinstance(fp, dict)
        or not isinstance(fp.get("reads"), list)
        or not isinstance(fp.get("writes"), list)
    ):
        errors.append("footprint must be {reads: [...], writes: [...]}")
    for i, claim in enumerate(iface.get("claims", [])):
        if not isinstance(claim, dict) or "label" not in claim or "file" not in claim:
            errors.append(f"claims[{i}] must have 'label' and 'file'")
    return errors


def run(args) -> int:
    if getattr(args, "iface_command", None) != "set":
        print("usage: tcg iface set <loop> --file <iface.json>", file=sys.stderr)
        return int(Exit.USAGE)

    try:
        root = find_root()
        loop = load_loop(root, args.loop)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    try:
        iface = read_json(args.file)
    except (OSError, ValueError) as e:
        print(f"tcg: cannot read interface: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    errors = validate(iface)
    if errors:
        for e in errors:
            print(f"tcg: interface invalid: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    write_json(loop_dir(root, args.loop) / "iface.json", iface)

    # Changing the interface of a compiled/proved loop invalidates its claims.
    if loop["state"] not in ("Draft", "Stale"):
        loop["state"] = "Stale"
    save_loop(root, args.loop, loop)

    print(f"interface set for {args.loop} (state: {loop['state']})")
    return int(Exit.OK)
