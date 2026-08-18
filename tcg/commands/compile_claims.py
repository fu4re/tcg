"""`tcg compile-claims <loop>` — canonicalize claim bodies into content-addressed
spec modules.

The compiler invents nothing: claim bodies are authored by hand (decision D1).
Its job is form discipline and addressing:

- wrap each claim in its own spec module with pinned requires/imports;
- enforce the explicit all-path attribute on every claim;
- canonicalize text (whitespace normal form) and address by SHA-256;
- round-trip: re-canonicalize the emitted module, require the same hash;
- record loop -> claim hashes in spec/interfaces.json and nodes in graph.json.

Atomicity (Hole 2 from gate G3): the transition legality is checked and ALL
claim bodies are validated + emitted IN MEMORY *before* any file is written, so
a refusal (illegal state, bad body, round-trip failure) leaves the workspace
byte-for-byte as it was. Exit code and on-disk effect always agree.

Re-compiling is a legal, intended operation (a real audit iterates). Re-compile
INVALIDATES prior proof state: the loop returns to Compiled, its stale Accept /
vacuity evidence and graph edges are dropped, its old claim nodes are replaced,
and any OTHER loop that trusted one of its claims as a lemma is marked Stale
(its parent proof no longer stands on a proved child). Content-addressing could
skip re-proving a claim whose body (hash) is unchanged; that optimization is
deferred — for now re-compile conservatively returns the loop to Compiled.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tcg.claims import (
    canonicalize, check_claim_body, emit_module, extract_body, sha256_text,
)
from tcg.outcome import Exit
from tcg.workspace import (
    TRANSITIONS, WORKSPACE_DIR, WorkspaceError, drop_edges_touching, find_root,
    load_graph, load_loop, loop_dir, read_json, save_graph, save_loop,
    transition, transition_allowed, upsert_node, write_json,
)


def run(args) -> int:
    try:
        root = find_root()
        loop = load_loop(root, args.loop)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    # Atomicity guard (Hole 2): refuse an illegal transition BEFORE any write.
    if not transition_allowed(loop["state"], "Compiled"):
        allowed = sorted(TRANSITIONS.get(loop["state"], set()))
        print(f"tcg: cannot compile-claims while {args.loop} is "
              f"{loop['state']} (allowed next: {allowed or 'none'}); nothing "
              "was written — wait for the in-flight `tcg prove` to finish",
              file=sys.stderr)
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

    # --- Phase 1: validate + emit every claim IN MEMORY (no side effects) ---
    prepared: list[tuple[dict, str, str, str]] = []  # (entry, label, hash, text)
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
        # Round-trip against the emitted module (re-canonicalize; re-check form)
        # — done in memory so a failure writes nothing (D1's guard, kept atomic).
        back = canonicalize(text)
        if sha256_text(back) != h or check_claim_body(extract_body(back), label):
            print(f"tcg: {label}: round-trip check failed — the emitted "
                  "module did not re-canonicalize to its own hash; this points "
                  "at a tcg bug, not the claim body", file=sys.stderr)
            return int(Exit.REFUSED)
        prepared.append((entry, label, h, text))

    compiled = {label: h for (_, label, h, _) in prepared}

    # --- Phase 2: commit (all writes happen here, only after validation) ---
    claims_dir = root / "spec" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)
    for _, label, h, text in prepared:
        (claims_dir / f"{h}.k").write_text(text, encoding="utf-8")
        print(f"{label} -> spec/claims/{h}.k")

    graph = load_graph(root)
    new_hashes = set(compiled.values())
    old_hashes = {h for h, n in graph["nodes"].items()
                  if n.get("loop") == args.loop}
    used_by_others = {h for h, n in graph["nodes"].items()
                      if n.get("loop") != args.loop}

    # Cascade set: OTHER loops whose node trusted one of this loop's (old)
    # claims as a lemma. Recompiling a child un-proves it, so those parents no
    # longer stand on a proved child and must be re-proved.
    parent_loops: set[str] = set()
    for e in graph["edges"]:
        if (e["type"] == "trusted-lemma" and e["to"] in old_hashes
                and e["from"] not in old_hashes):
            pl = graph["nodes"].get(e["from"], {}).get("loop")
            if pl and pl != args.loop:
                parent_loops.add(pl)

    # Replace this loop's nodes; drop every edge touching its old claims.
    for h in old_hashes:
        graph["nodes"].pop(h, None)
    drop_edges_touching(graph, old_hashes)
    ws_role = loop.get("role", "loop")
    for entry in claims:
        role = entry.get("role", ws_role)
        node = {"role": role, "loop": args.loop, "label": entry["label"],
                "root": bool(entry.get("root", role == "loop"))}
        if "from" in loop:
            node["from"], node["to"] = loop["from"], loop["to"]
        upsert_node(graph, compiled[entry["label"]], **node)
    save_graph(root, graph)

    # Drop this loop's now-stale Accept + vacuity evidence (per-hash; keep a
    # hash still owned by another loop's node).
    ev_replay = root / "evidence" / "replay"
    ev_vac = root / WORKSPACE_DIR / "vacuity"
    for h in old_hashes:
        if h in used_by_others:
            continue
        (ev_replay / f"{h}.json").unlink(missing_ok=True)
        (ev_vac / f"{h}.json").unlink(missing_ok=True)

    # Cascade: mark dependent parents Stale and drop their Accept evidence.
    for pl in sorted(parent_loops):
        try:
            pl_loop = load_loop(root, pl)
        except WorkspaceError:
            continue
        if pl_loop.get("state") == "Accepted":
            transition(pl_loop, "Stale")
            save_loop(root, pl, pl_loop)
            for h, n in graph["nodes"].items():
                if n.get("loop") == pl:
                    (ev_replay / f"{h}.json").unlink(missing_ok=True)
                    (ev_vac / f"{h}.json").unlink(missing_ok=True)
        print(f"tcg: note: {pl} trusted a claim of {args.loop} as a lemma; "
              f"marked Stale — re-run `tcg compile-claims {pl}` then "
              f"`tcg prove {pl}`", file=sys.stderr)

    interfaces_path = root / "spec" / "interfaces.json"
    interfaces = read_json(interfaces_path) if interfaces_path.is_file() else {}
    interfaces[args.loop] = {
        "pre": iface["pre"], "post": iface["post"], "exit": iface["exit"],
        "footprint": iface["footprint"], "rely": iface["rely"], "guar": iface["guar"],
        "requires": requires, "imports": imports,
        "claims": compiled,
    }
    write_json(interfaces_path, interfaces)

    prev_state = loop["state"]
    transition(loop, "Compiled")
    save_loop(root, args.loop, loop)

    note = ""
    if prev_state in ("Accepted", "Refuted", "Unknown"):
        note = (f" (was {prev_state}; prior proof state invalidated — "
                f"re-run `tcg prove {args.loop}`)")
    print(f"compiled {len(compiled)} claim(s); {args.loop} is Compiled{note}")
    return int(Exit.OK)
