"""`tcg roots <bundle>` — render the root claims for human reading.

The one irreducible step: the bundle transfers that the bytecode satisfies
these claims, not that they express the property you care about. Read them.

If the bundle carries typed-stub assumptions (Mechanism B), the roots rest on
those opaque-callee summaries, so they are surfaced right next to the roots:
address + frame + which roots each is load-bearing for. Bundle-only — tcg.assume
is a pure module (no workspace/commands import), so `roots` stays bundle-only.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tcg.assume import is_assume_node, roots_injecting
from tcg.outcome import Exit


def run(args) -> int:
    import json

    bundle = Path(args.bundle)
    manifest_path = bundle / "MANIFEST.json"
    if not manifest_path.is_file():
        print(f"tcg: no MANIFEST.json in {bundle}; pass a directory produced "
              "by `tcg freeze`", file=sys.stderr)
        return int(Exit.USAGE)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    roots = manifest.get("roots", {})
    if not roots:
        print("tcg: bundle declares no roots; MANIFEST.json's \"roots\" is "
              "empty — it was frozen from a workspace with no root claims",
              file=sys.stderr)
        return int(Exit.REFUSED)

    print(f"{len(roots)} root claim(s). What is guaranteed is exactly what is "
          f"written below — no more.\n")
    for h, meta in sorted(roots.items(), key=lambda kv: (kv[1]["loop"], kv[1]["label"])):
        path = bundle / "spec" / "claims" / f"{h}.k"
        print(f"=== root {meta['loop']}/{meta['label']}  ({h}) ===")
        if path.is_file():
            print(path.read_text(encoding="utf-8"))
        else:
            print("  <claim file missing — bundle is not intact>\n")

    _print_assumptions(bundle)
    return int(Exit.OK)


def _print_assumptions(bundle: Path) -> None:
    """Surface the load-bearing author assumptions (typed stubs) next to the
    roots: address + frame + the roots each is load-bearing for. Prints nothing
    when the bundle carries no assume-node (existing bundles are unchanged)."""
    import json

    graph_path = bundle / "spec" / "graph.json"
    if not graph_path.is_file():
        return
    try:
        with open(graph_path, encoding="utf-8") as f:
            graph = json.load(f)
    except (OSError, ValueError):
        return
    nodes = graph.get("nodes", {})
    edges = graph.get("edges", [])
    assume_pairs = [(h, n) for h, n in nodes.items() if is_assume_node(n)]
    if not assume_pairs:
        return

    print(f"\n{len(assume_pairs)} load-bearing author assumption(s). The root(s) "
          "above rest on these opaque-callee summaries — ASSUMED, NOT discharged "
          "over the callee's code. Read them as part of the roots:\n")
    for h, n in sorted(assume_pairs,
                       key=lambda p: (nodes[p[0]]["loop"], nodes[p[0]]["label"])):
        a = n["assume"]
        lb = roots_injecting(h, nodes, edges)
        lb_names = ", ".join(f"{nodes[r]['loop']}/{nodes[r]['label']}"
                             for r in lb) or "(none — injected by no root)"
        print(f"=== assumption {a.get('ledger_id')}  (callee {a.get('callee_address')}) ===")
        print(f"  frame: {a.get('frame')}")
        print(f"  load-bearing for root(s): {lb_names}\n")
