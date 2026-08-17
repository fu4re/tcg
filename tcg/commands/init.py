"""`tcg init` — scaffold a workspace with a pinned toolchain.lock."""
from __future__ import annotations

import sys
from importlib import resources
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


def _read_ghost_diff() -> bytes | None:
    """The ghost-instrumentation patch, packaged as tcg._data.

    Resolved via importlib.resources rather than a path relative to this
    file's location on disk: a non-editable `pip install` unpacks into
    site-packages with no theory/ tree present at all, so
    `Path(__file__).resolve().parents[2] / "theory" / ...` never resolves
    for an installed tcg — only for a checkout run in place.
    """
    try:
        return resources.files("tcg._data").joinpath("ghost.diff").read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError):
        return None


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
    dst = root / "theory" / "patches" / "ghost.diff"
    data = _read_ghost_diff()
    if data is not None:
        dst.write_bytes(data)
        patches["theory/patches/ghost.diff"] = sha256_file(dst)
    else:
        print("tcg: warning: ghost.diff not found in installation; "
              "vendor it into theory/patches/ before proving", file=sys.stderr)

    lock = dict(TOOLCHAIN, patches=patches)
    write_json(ws / "toolchain.lock", lock)
    write_json(root / "spec" / "interfaces.json", {})

    print(f"initialized tcg workspace at {root}")
    return int(Exit.OK)
