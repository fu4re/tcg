"""`tcg compat <i> <j>` — scaffold the interference obligation Guar_j implies Rely_i.

Scaffolds a workspace with role `compat` for the ordered pair (i, j). The
environment node is a separate claim with role `env` (declare `"role": "env"`
on a claim entry in any interface); `tcg graph check` requires it whenever any
pair needs compat coverage.
"""
from __future__ import annotations

from tcg.commands.junction import scaffold


def run(args) -> int:
    return scaffold("compat", args.i, args.j)
