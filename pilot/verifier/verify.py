#!/usr/bin/env python3
"""tcg bundle verifier (bundle pilot, task 06). Stdlib-only Python 3.12.

  verify.py <bundle-dir> --oracle-pubkey <file> --producer-pubkey <file>
            (--rpc <url> | --state-snapshot <dir>) --variant A|B --out ladder.json
            [--no-exec] [--l4-skip-provers] [--docker-limit=--memory=6g --docker-limit=--cpus=2]
  verify.py --self-hash        print the verifier hash to record in trusted_base.json
                               (checker entry named "tcg-verifier")

Exit 0 whenever the verifier ran to completion, whatever the levels say; the
levels are in ladder.json, never in the exit code. Exit 2 = usage / input error.
--docker-limit adds a resource limit to every KEVM `docker run` (only --memory=<n>[bkmg]
and --cpus=<n> are accepted; nothing that loosens the sandbox).
--l4-skip-provers does not replay recorded prover/container runs in L4; they are
counted as "not replayed: skipped by consumer" (L4 at best partial), never as passed.
--no-exec skips every bundle-supplied command (evidence replay.sh scripts and
ledger replays); the affected fields then report "not run", never success.
The verifier runs bundle-supplied scripts (L2) and recorded commands (L4) by
default, as task 06 asks; run it as an isolated user.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tcgverify import chain as chain_mod, checkers, ed25519, ladder  # noqa: E402


def main(argv=None) -> int:
    if argv is None:
        argv = sys.argv[1:]
    if argv == ["--self-hash"]:
        print(ladder.verifier_hash())
        return 0
    p = argparse.ArgumentParser(prog="verify.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bundle")
    p.add_argument("--oracle-pubkey", required=True)
    p.add_argument("--producer-pubkey", required=True)
    src = p.add_mutually_exclusive_group(required=True)
    src.add_argument("--rpc")
    src.add_argument("--state-snapshot")
    p.add_argument("--variant", choices=("A", "B"), required=True)
    p.add_argument("--out", required=True)
    p.add_argument("--no-exec", action="store_true")
    p.add_argument("--docker-limit", action="append", default=[])
    p.add_argument("--l4-skip-provers", action="store_true")
    a = p.parse_args(argv)
    bad = [x for x in a.docker_limit if not checkers.DOCKER_LIMIT.match(x)]
    if bad:
        print(f"verify.py: --docker-limit accepts only --memory=<n> / --cpus=<n>, got {bad}", file=sys.stderr)
        return 2
    try:
        with open(a.oracle_pubkey, "rb") as f:
            oracle = ed25519.load_pubkey(f.read())
        with open(a.producer_pubkey, "rb") as f:
            producer = ed25519.load_pubkey(f.read())
        source = chain_mod.RpcSource(a.rpc) if a.rpc else chain_mod.SnapshotSource(a.state_snapshot)
    except (OSError, ValueError, chain_mod.ChainError) as e:
        print(f"verify.py: {e}", file=sys.stderr)
        return 2
    result = ladder.build(a.bundle, oracle, producer, source, a.variant, execute=not a.no_exec,
                          docker_limits=a.docker_limit, l4_skip_provers=a.l4_skip_provers)
    with open(a.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
        f.write("\n")
    for lv in ("L0", "L1", "L2", "L3", "L4"):
        st = result[lv].get("status", "n/a (reported for H)" if lv == "L2" else "?")
        print(f"{lv}: {st}")
    print(f"outside_bundle: {len(result['outside_bundle'])} item(s); ladder written to {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
