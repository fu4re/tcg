"""`tcg init` — scaffold a workspace with a pinned toolchain.lock."""
from __future__ import annotations

import os
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


# Vendored, pinned prover patches shipped inside the package as tcg._data/*.diff
# and re-materialized into a fresh workspace's theory/patches/ at init. Order is
# the apply order (ghost first, then lemmas): the lemma driver imports EDSL,
# which pulls in the ghost-instrumented evm.md when ghost.diff is applied first.
# See docs/findings/0003 (the wall) and 0004 (the lemma inclusion).
VENDORED_PATCHES = ("ghost.diff", "lemmas.diff")


def _read_patch(name: str) -> bytes | None:
    """A vendored prover patch, packaged as tcg._data.

    Resolved via importlib.resources rather than a path relative to this
    file's location on disk: a non-editable `pip install` unpacks into
    site-packages with no theory/ tree present at all, so
    `Path(__file__).resolve().parents[2] / "theory" / ...` never resolves
    for an installed tcg — only for a checkout run in place.
    """
    try:
        return resources.files("tcg._data").joinpath(name).read_bytes()
    except (FileNotFoundError, ModuleNotFoundError, NotADirectoryError):
        return None


def run(args) -> int:
    root = Path.cwd()
    ws = root / WORKSPACE_DIR
    if ws.exists():
        print(f"tcg: workspace already exists at {ws}; run `tcg status` to "
              "see it, or remove it to start over", file=sys.stderr)
        return int(Exit.USAGE)

    (ws / "loops").mkdir(parents=True)
    (root / "spec" / "claims").mkdir(parents=True, exist_ok=True)
    (root / "theory" / "patches").mkdir(parents=True, exist_ok=True)

    # Vendor every prover patch shipped with the tool and pin each hash: the
    # workspace must not depend on the installation staying put, and no trusted
    # input (ghost instrumentation, simplification lemmas) may enter silently.
    patches = {}
    for name in VENDORED_PATCHES:
        dst = root / "theory" / "patches" / name
        data = _read_patch(name)
        if data is not None:
            dst.write_bytes(data)
            patches[f"theory/patches/{name}"] = sha256_file(dst)
        else:
            print(f"tcg: warning: {name} not found in installation; "
                  "vendor it into theory/patches/ before proving", file=sys.stderr)

    # Definition discovery happens exactly once, here, at init time (decision
    # D4 in docs/decisions.md): a flag beats the environment, and whatever is
    # resolved is written into the lock verbatim. `prove`/`verify` never
    # re-discover it themselves — every proof run is attributable to this one
    # pinned record, not to whatever the shell happened to export that day.
    definition = args.definition or os.environ.get("TCG_DEFINITION") or None
    includes = list(args.include or [])

    lock = dict(TOOLCHAIN, patches=patches, definition=definition, includes=includes)
    write_json(ws / "toolchain.lock", lock)
    write_json(root / "spec" / "interfaces.json", {})

    print(f"initialized tcg workspace at {root}")
    if definition:
        print(f"definition pinned: {definition}")
    else:
        print("no definition pinned; edit .tcg/toolchain.lock directly, or "
              "pass --definition PATH (or set $TCG_DEFINITION) next time you "
              "`tcg init` a fresh workspace")
    return int(Exit.OK)
