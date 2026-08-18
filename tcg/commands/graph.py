"""`tcg graph check` — structural checks on the claim graph.

Workspace-side subset of the verifier's graph step. Any violation refuses
(exit 3); a pass here is a structural statement only — proofs are judged by
`prove`, and the transferable guarantee only exists after `freeze`/`verify`.

Checks:
- integrity: every node's claim file exists and re-hashes to its id;
- form: every claim carries the explicit all-path attribute;
- edges: endpoints resolve, types are known;
- typing: trusted-lemma targets are never zero-step (junction/compat) nodes;
- acyclicity of the trusted-lemma subgraph;
- every loop has a guar node;
- compat coverage: every ordered loop pair with observed footprint
  intersection has a compat node, and an env node exists;
- program binding (P0-A): every ROOT's <program> cell binds to
  subject/runtime.bin — checked here so `tcg graph check` and freeze agree
  (freeze calls check_graph); skipped only if no subject is installed yet
  (subject set can follow graph check in the workflow). verify re-derives the
  same check bundle-only, so it stays free of workspace imports;
- closure: at least one root; every root and everything reachable from it
  over trusted-lemma edges belongs to an Accepted workspace.
"""
from __future__ import annotations

import re
import sys
from graphlib import CycleError, TopologicalSorter

from tcg.claims import program_binding_error
from tcg.outcome import Exit
from tcg.workspace import (
    EDGE_TYPES, WorkspaceError, find_root, load_graph, load_loop, read_json,
    sha256_text,
)

_ZERO_STEP_ROLES = ("junction", "compat")


def check_graph(root) -> list[str]:
    graph = load_graph(root)
    nodes, edges = graph["nodes"], graph["edges"]
    errors: list[str] = []

    if not nodes:
        return ["graph is empty; run `tcg compile-claims <loop>` first"]

    # Integrity + form of every node's claim artifact.
    for h, node in nodes.items():
        path = root / "spec" / "claims" / f"{h}.k"
        if not path.is_file():
            errors.append(f"{h[:12]}: claim file missing")
            continue
        text = path.read_text(encoding="utf-8")
        if sha256_text(text) != h:
            errors.append(f"{h[:12]}: content does not match its hash")
        if not re.search(r"\[[^\[\]]*all-path[^\[\]]*\]", text):
            errors.append(f"{h[:12]}: missing all-path attribute")

    # Edges: resolution, typing, zero-step discipline.
    for e in edges:
        if e["type"] not in EDGE_TYPES:
            errors.append(f"edge {e['from'][:12]}->{e['to'][:12]}: "
                          f"unknown type {e['type']}")
        for end in ("from", "to"):
            if e[end] not in nodes:
                errors.append(f"edge endpoint not in graph: {e[end][:12]}")
        if (e["type"] == "trusted-lemma"
                and nodes.get(e["to"], {}).get("role") in _ZERO_STEP_ROLES):
            errors.append(
                f"trusted-lemma edge targets zero-step node {e['to'][:12]} "
                f"({nodes[e['to']]['role']})")

    # Acyclicity of the trusted-lemma subgraph.
    ts = TopologicalSorter()
    for h in nodes:
        ts.add(h)
    for e in edges:
        if e["type"] == "trusted-lemma" and e["from"] in nodes and e["to"] in nodes:
            ts.add(e["from"], e["to"])
    try:
        ts.prepare()
    except CycleError as exc:
        cyc = " -> ".join(h[:12] for h in exc.args[1])
        errors.append(f"trusted-lemma subgraph has a cycle: {cyc}")

    # Every loop has a guar node.
    loops = {n["loop"] for n in nodes.values() if n["role"] == "loop"}
    guars = {n["loop"] for n in nodes.values() if n["role"] == "guar"}
    for lp in sorted(loops - guars):
        errors.append(f"loop {lp} has no guar node; add a claims[] entry "
                      f"with \"role\": \"guar\" to {lp}'s interface and "
                      f"`tcg compile-claims {lp}`")

    # Compat coverage over observed footprint intersections + env presence.
    interfaces = read_json(root / "spec" / "interfaces.json")
    compat_pairs = {(n["from"], n["to"]) for n in nodes.values()
                    if n["role"] == "compat" and "from" in n}
    has_env = any(n["role"] == "env" for n in nodes.values())
    needs_env = False
    for i in sorted(loops):
        for j in sorted(loops):
            if i == j:
                continue
            fi = interfaces.get(i, {}).get("footprint", {})
            fj = interfaces.get(j, {}).get("footprint", {})
            observed = set(fj.get("writes", [])) & (
                set(fi.get("reads", [])) | set(fi.get("writes", [])))
            if observed:
                needs_env = True
                if (i, j) not in compat_pairs:
                    errors.append(
                        f"loops ({i}, {j}) share footprint {sorted(observed)} "
                        f"but have no compat node")
    if needs_env and not has_env:
        errors.append("compat coverage required but no env node exists; add "
                      "a claims[] entry with \"role\": \"env\" to some "
                      "interface and compile it")

    # Closure: roots exist; roots and their trusted-lemma reachability are
    # Accepted. "Couldn't check a state" is a violation, not a pass.
    roots = [h for h, n in nodes.items() if n.get("root")]
    if not roots:
        errors.append("graph has no roots; a compiled claims[] entry with "
                      "\"role\": \"loop\" (the default) defaults to root: "
                      "true — check that at least one exists and isn't "
                      "overridden to root: false")
    children = {h: [] for h in nodes}
    for e in edges:
        if e["type"] == "trusted-lemma" and e["from"] in children:
            children[e["from"]].append(e["to"])
    seen: set[str] = set()
    stack = list(roots)
    while stack:
        h = stack.pop()
        if h in seen or h not in nodes:
            continue
        seen.add(h)
        lp = nodes[h]["loop"]
        try:
            state = load_loop(root, lp)["state"]
        except WorkspaceError:
            state = "missing"
        if state != "Accepted":
            kind = "root" if h in roots else "trusted child"
            errors.append(f"{kind} {nodes[h]['label']} ({lp}) is {state}, "
                          f"not Accepted — run `tcg prove {lp}`")
        stack.extend(children[h])

    # Program binding (P0-A): every ROOT's <program> cell must equal
    # subject/runtime.bin. Only ROOTS are subject-bound (a frame/guar lemma may
    # prove a sub-program; consequence nodes carry no <program> cell) — the
    # guarantee is exactly the roots. Skipped when no subject is installed yet
    # (subject set can follow graph check); freeze re-runs check_graph once the
    # subject exists, and verify re-derives it bundle-only.
    subject_bin = root / "subject" / "runtime.bin"
    if subject_bin.is_file():
        subject_bytes = subject_bin.read_bytes()
        for h in roots:
            claim_path = root / "spec" / "claims" / f"{h}.k"
            if not claim_path.is_file():
                continue  # already reported by the integrity check above
            reason = program_binding_error(
                claim_path.read_text(encoding="utf-8"), subject_bytes)
            if reason:
                errors.append(f"root {nodes[h]['loop']}/{nodes[h]['label']}: {reason}")

    return errors


def run(args) -> int:
    if getattr(args, "graph_command", None) != "check":
        print("usage: tcg graph check", file=sys.stderr)
        return int(Exit.USAGE)
    try:
        root = find_root()
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    errors = check_graph(root)
    if errors:
        for msg in errors:
            print(f"graph check: {msg}", file=sys.stderr)
        print(f"graph check: REFUSED ({len(errors)} violation(s)); "
              "`tcg status` shows what's next per loop", file=sys.stderr)
        return int(Exit.REFUSED)

    graph = load_graph(root)
    roots = [h for h, n in graph["nodes"].items() if n.get("root")]
    print(f"graph check: OK ({len(graph['nodes'])} node(s), "
          f"{len(graph['edges'])} edge(s), {len(roots)} root(s))")
    return int(Exit.OK)
