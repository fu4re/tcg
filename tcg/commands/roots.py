"""`tcg roots <bundle>` — render the root claims for human reading.

The one irreducible step: the bundle transfers that the bytecode satisfies
these claims, not that they express the property you care about. Read them.
"""
from __future__ import annotations

import sys
from pathlib import Path

from tcg.outcome import Exit


def run(args) -> int:
    import json

    bundle = Path(args.bundle)
    manifest_path = bundle / "MANIFEST.json"
    if not manifest_path.is_file():
        print(f"tcg: no MANIFEST.json in {bundle}", file=sys.stderr)
        return int(Exit.USAGE)
    with open(manifest_path, encoding="utf-8") as f:
        manifest = json.load(f)

    roots = manifest.get("roots", {})
    if not roots:
        print("tcg: bundle declares no roots", file=sys.stderr)
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
    return int(Exit.OK)
