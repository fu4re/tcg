"""`tcg init` — scaffold a workspace with a pinned toolchain.lock."""
from __future__ import annotations

import sys
from pathlib import Path

from tcg.outcome import Exit
from tcg.workspace import WORKSPACE_DIR, sha256_file, write_json

# Pinned prover toolchain. Proofs and replays are meaningful only against
# these exact versions; changing any of them is a new lock, not an edit.
TOOLCHAIN = {
    "k": "v7.1.337",
    "kore-exec": "0.1.155",
    "kontrol": "1.0.255",
    "kevm": "1.0.678",
    "foundry": "1.2.3",
    "solc": "0.8.35",
    "replay": {
        # Unknown on replay refuses the certificate; retries only absorb
        # solver nondeterminism, they never relax the verdict.
        "retries": 2,
        "timeout_seconds": 3600,
    },
}


def run(args) -> int:
    root = Path.cwd()
    ws = root / WORKSPACE_DIR
    if ws.exists():
        print(f"tcg: workspace already exists at {ws}", file=sys.stderr)
        return int(Exit.USAGE)

    (ws / "loops").mkdir(parents=True)
    (root / "spec" / "claims").mkdir(parents=True, exist_ok=True)
    (root / "theory" / "patches").mkdir(parents=True, exist_ok=True)

    # Vendor the ghost instrumentation patch shipped with the tool and pin
    # its hash: the workspace must not depend on the installation staying put.
    patches = {}
    src = Path(__file__).resolve().parents[2] / "theory" / "patches" / "ghost.diff"
    dst = root / "theory" / "patches" / "ghost.diff"
    if src.is_file():
        dst.write_bytes(src.read_bytes())
        patches["theory/patches/ghost.diff"] = sha256_file(dst)
    else:
        print("tcg: warning: ghost.diff not found in installation; "
              "vendor it into theory/patches/ before proving", file=sys.stderr)

    lock = dict(TOOLCHAIN, patches=patches)
    write_json(ws / "toolchain.lock", lock)
    write_json(root / "spec" / "interfaces.json", {})

    print(f"initialized tcg workspace at {root}")
    return int(Exit.OK)
