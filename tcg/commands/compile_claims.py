"""`tcg compile-claims <loop>` — canonicalize claim bodies into content-addressed
spec modules.

The compiler invents nothing: claim bodies are authored by hand (decision D1).
Its job is form discipline and addressing:

- wrap each claim in its own spec module with pinned requires/imports;
- enforce the explicit all-path attribute on every claim;
- canonicalize text (whitespace normal form) and address by SHA-256;
- round-trip: re-read the emitted file, re-canonicalize, require the same hash;
- record loop -> claim hashes in spec/interfaces.json and nodes in graph.json.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tcg.claims import (
    canonicalize, check_claim_body, emit_module, extract_body, sha256_text,
)
from tcg.outcome import Exit
from tcg.workspace import (
    WorkspaceError, find_root, load_graph, load_loop, loop_dir, read_json,
    save_graph, save_loop, transition, upsert_node, write_json,
)


def run(args) -> int:
    try:
        root = find_root()
        loop = load_loop(root, args.loop)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    d = loop_dir(root, args.loop)
    iface = read_json(d / "iface.json")
    claims = iface.get("claims", [])
    if not claims:
        print(f"tcg: interface declares no claims; add entries to the "
              f"\"claims\" list and `tcg iface set {args.loop} --file <iface.json>` "
              "again", file=sys.stderr)
        return int(Exit.USAGE)

    requires = iface.get("requires", ["evm.md"])
    imports = iface.get("imports", ["EVM"])
    claims_dir = root / "spec" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)

    compiled: dict[str, str] = {}
    for entry in claims:
        label, rel = entry["label"], entry["file"]
        body_path = (d / rel) if not Path(rel).is_absolute() else Path(rel)
        try:
            body = body_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"tcg: {label}: cannot read body: {e} (check the claims[] "
                  f"\"file\" entry in {args.loop}'s interface — relative "
                  "paths resolve against the loop's own directory)", file=sys.stderr)
            return int(Exit.USAGE)

        errors = check_claim_body(body, label)
        if errors:
            for msg in errors:
                print(f"tcg: {label}: {msg}", file=sys.stderr)
            return int(Exit.REFUSED)

        text = emit_module(args.loop, label, requires, imports, body)
        h = sha256_text(text)
        out = claims_dir / f"{h}.k"
        out.write_text(text, encoding="utf-8")

        # Round-trip: the artifact on disk must re-canonicalize to itself.
        back = canonicalize(out.read_text(encoding="utf-8"))
        if sha256_text(back) != h or check_claim_body(extract_body(back), label):
            print(f"tcg: {label}: round-trip check failed — the emitted "
                  f"module at {out} did not re-canonicalize to its own hash; "
                  "this points at a tcg bug, not the claim body", file=sys.stderr)
            return int(Exit.REFUSED)
        compiled[label] = h
        print(f"{label} -> spec/claims/{h}.k")

    # Graph nodes: role comes from the workspace (loop/junction/compat) unless a
    # claim entry overrides it (e.g. guar, env). Only role-loop claims are roots.
    ws_role = loop.get("role", "loop")
    graph = load_graph(root)
    for entry in claims:
        role = entry.get("role", ws_role)
        node = {"role": role, "loop": args.loop, "label": entry["label"],
                "root": bool(entry.get("root", role == "loop"))}
        if "from" in loop:
            node["from"], node["to"] = loop["from"], loop["to"]
        upsert_node(graph, compiled[entry["label"]], **node)
    save_graph(root, graph)

    interfaces_path = root / "spec" / "interfaces.json"
    interfaces = read_json(interfaces_path) if interfaces_path.is_file() else {}
    interfaces[args.loop] = {
        "pre": iface["pre"], "post": iface["post"], "exit": iface["exit"],
        "footprint": iface["footprint"], "rely": iface["rely"], "guar": iface["guar"],
        "requires": requires, "imports": imports,
        "claims": compiled,
    }
    write_json(interfaces_path, interfaces)

    if loop["state"] != "Compiled":
        try:
            transition(loop, "Compiled")
        except WorkspaceError as e:
            print(f"tcg: {e}", file=sys.stderr)
            return int(Exit.USAGE)
        save_loop(root, args.loop, loop)

    print(f"compiled {len(compiled)} claim(s); {args.loop} is Compiled")
    return int(Exit.OK)
