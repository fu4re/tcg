#!/usr/bin/env python3
"""Print the tree hash of a directory, as trusted_base.json semantics[].hash
expects: sha256 of canonical JSON [[relpath, sha256(file)], ...] sorted by
'/'-separated relpath (same function the verifier uses). Symlinks are refused.

Usage: tree_hash.py <dir>
"""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verifier"))

from tcgverify.canon import tree_hash  # noqa: E402

if __name__ == "__main__":
    if len(sys.argv) != 2 or not os.path.isdir(sys.argv[1]):
        print(__doc__, file=sys.stderr)
        sys.exit(2)
    print(tree_hash(sys.argv[1]))
