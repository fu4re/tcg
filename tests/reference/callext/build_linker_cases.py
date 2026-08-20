"""Build the cross-bundle linker (REUSE) discriminator bundles on disk, for
`tcg verify` to judge with the REAL prover (run-tcg-linker-discriminators.sh).

Reuses the synthetic-bundle builder from tests/test_xbridge.py (the same tiny
dep + caller used by the fast unit tests) and writes each case under
WORKROOT/<name>/caller. Prints one line per case:

    <name> <expected_exit> <caller_path>

Only the honest case reaches step-5 replay (real kprove); every discriminator
refuses at step 1 (integrity) or step 4 (graph / deps), BEFORE any prover call,
so the discriminators are deterministic with or without the toolchain.

Usage:  python3 -m tests.reference.callext.build_linker_cases <WORKROOT>
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tests.test_xbridge import Composition, NONROOT_HASH

# (name, expected `tcg verify` exit, knobs, post-build tamper)
#   0 = certificate holds; 3 = REFUSED.
_CASES = [
    ("honest", 0, {}, None),
    ("proxy-summary", 3, {"summary_fn": "s_proxy.k"}, None),
    ("code-hash-mismatch", 3, {"code_hash": "deadbeef" * 8}, None),
    ("external-code-mismatch", 3, {"ext_hex": "600154600501600155"}, None),
    ("nonroot-ref", 3, {"dep_root_ref": NONROOT_HASH}, None),
    ("missing-dep", 3, {"place_dep": False}, None),
    ("manifest-hash-mismatch", 3,
     {"dep_dirname": "0" * 64, "dep_ref_dir": "0" * 64}, None),
    ("dep-fails-own-verify", 3, {"bad_oracle_in_dep": True}, None),
    ("tampered-dep-byte", 3, {}, "flip_dep_runtime"),
]


def _flip_dep_runtime(comp: Composition) -> None:
    """Tamper a vendored dep file WITHOUT updating the caller MANIFEST — the
    deps/** are hash-linked, so the caller's step-1 integrity refuses."""
    runtime = comp.caller / "deps" / comp.callee_root / "subject" / "runtime.bin"
    runtime.write_bytes(bytes.fromhex("60005460050160005501"))


_TAMPERS = {"flip_dep_runtime": _flip_dep_runtime}


def main(workroot: Path) -> int:
    shutil.rmtree(workroot, ignore_errors=True)
    workroot.mkdir(parents=True)
    for name, expected, knobs, tamper in _CASES:
        case_dir = workroot / name
        comp = Composition(case_dir, **knobs)
        if tamper:
            _TAMPERS[tamper](comp)
        print(f"{name} {expected} {comp.caller}")
    return 0


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__.strip().splitlines()[-1], file=sys.stderr)
        raise SystemExit(2)
    raise SystemExit(main(Path(sys.argv[1]).resolve()))
