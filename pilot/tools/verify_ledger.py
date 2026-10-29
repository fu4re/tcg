#!/usr/bin/env python3
"""Walk a tcg-ledger/0.1 JSONL chain and fail non-zero on any break.

Checks, per line n (1-based):
  - the line is newline-terminated and parses as a JSON object;
  - the line is byte-identical to its canonical re-serialisation
    (sorted keys, no whitespace), so a hand edit cannot hide in formatting;
  - seq == n;
  - prev == "0"*64 for n == 1, else sha256(bytes of line n-1 without "\\n");
  - required fields are present with the right types.

Usage: verify_ledger.py <ledger.jsonl> [--json]
Exit 0 = chain intact; 1 = broken (every problem is printed); 2 = usage/IO.
Stdlib only. This judges chain integrity only, never the truth of an event.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verifier"))

from tcgverify.ledger_walk import walk  # noqa: E402


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--json"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(args[0], "rb") as f:
            data = f.read()
    except OSError as e:
        print(f"verify_ledger: {e}", file=sys.stderr)
        return 2
    events, errs = walk(data)
    if "--json" in argv:
        print(json.dumps({"events": len(events), "intact": not errs, "errors": errs}, indent=2))
    else:
        for e in errs:
            print(f"BROKEN: {e}")
        print(f"{len(events)} events; chain {'intact' if not errs else 'BROKEN'}")
    return 0 if not errs else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
