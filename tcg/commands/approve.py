"""`tcg approve` — record the human sign-off over the current root hashes.

The one non-formal act in the pipeline. The record binds the approval to the
roots' hashes at this moment; `freeze` refuses if the roots drift afterwards.
The record is dated and attributed — a verifier does not trust it (their own
reading of the roots replaces it), but it makes trust transfer auditable.
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone

from tcg.outcome import Exit
from tcg.workspace import WorkspaceError, find_root, load_graph, write_json


def run(args) -> int:
    if not args.reviewer:
        print("tcg: --reviewer is required: approval must be attributed",
              file=sys.stderr)
        return int(Exit.USAGE)
    try:
        root = find_root()
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    graph = load_graph(root)
    roots = {h: {"loop": n["loop"], "label": n["label"]}
             for h, n in graph["nodes"].items() if n.get("root")}
    if not roots:
        print("tcg: no root claims to approve (compile claims first)",
              file=sys.stderr)
        return int(Exit.USAGE)

    write_json(root / "assumptions" / "oracle-record.json", {
        "reviewer": args.reviewer,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "statement": args.statement
        or "I have read the root claims listed by hash below and attest that "
           "they express the intended property.",
        "roots": roots,
    })

    for h, meta in sorted(roots.items(), key=lambda kv: kv[1]["label"]):
        print(f"approved root {meta['loop']}/{meta['label']} {h[:12]}")
    print(f"oracle record written for {len(roots)} root(s) by {args.reviewer}")
    return int(Exit.OK)
