"""Argument parsing and routing only.

Every gate decision lives in its command module; every exit code comes from
`tcg.outcome.Exit`, so success is minted in exactly one place. stdlib argparse
only: a verifier re-implementing the format must not need our dependencies.

`verify` and `roots` read only a bundle, never the workspace — keep their
modules free of workspace imports.
"""
from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence

from tcg.outcome import Exit


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tcg",
        description="Build and verify proof-carrying bundles for EVM contracts.",
    )
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    sub.add_parser("init", help="scaffold a workspace + pinned toolchain.lock")

    lp = sub.add_parser("loop", help="manage loop workspaces")
    lp_sub = lp.add_subparsers(dest="loop_command", metavar="<subcommand>")
    lp_new = lp_sub.add_parser("new", help="create a loop workspace")
    lp_new.add_argument("name")

    ifc = sub.add_parser("iface", help="manage loop interfaces")
    ifc_sub = ifc.add_subparsers(dest="iface_command", metavar="<subcommand>")
    ifc_set = ifc_sub.add_parser(
        "set", help="set (Pre, Post, Exit, footprint, rely, guar) for a loop"
    )
    ifc_set.add_argument("loop")

    cc = sub.add_parser(
        "compile-claims",
        help="compile a loop interface into canonical claims (+ round-trip check)",
    )
    cc.add_argument("loop")

    sub.add_parser(
        "approve", help="record human sign-off over the current root hashes"
    )

    pv = sub.add_parser(
        "prove", help="run the prover on a loop or junction; Accept/Refute/Unknown"
    )
    pv.add_argument("target", help="loop or junction name")

    jn = sub.add_parser("junction", help="consequence claim: Post_i implies Pre_j")
    jn.add_argument("i")
    jn.add_argument("j")

    cp = sub.add_parser("compat", help="interference obligation: Guar_j implies Rely_i")
    cp.add_argument("i")
    cp.add_argument("j")

    gr = sub.add_parser("graph", help="claim-graph operations")
    gr_sub = gr.add_subparsers(dest="graph_command", metavar="<subcommand>")
    gr_sub.add_parser("check", help="structural checks on the claim DAG")

    sub.add_parser("freeze", help="assemble the bundle: hash tree + MANIFEST")

    vf = sub.add_parser(
        "verify", help="run the verifier protocol on a bundle (bundle-only input)"
    )
    vf.add_argument("bundle", help="path to a bundle directory")

    rt = sub.add_parser("roots", help="render a bundle's root claims for reading")
    rt.add_argument("bundle", help="path to a bundle directory")

    return ap


# command name → module in tcg.commands
_DISPATCH: dict[str, str] = {
    "init": "init",
    "loop": "loop",
    "iface": "iface",
    "compile-claims": "compile_claims",
    "approve": "approve",
    "prove": "prove",
    "junction": "junction",
    "compat": "compat",
    "graph": "graph",
    "freeze": "freeze",
    "verify": "verify",
    "roots": "roots",
}


def main(argv: Sequence[str] | None = None) -> int:
    ap = build_parser()
    args = ap.parse_args(argv)

    if args.command is None:
        ap.print_help(sys.stderr)
        return int(Exit.USAGE)

    module_name = _DISPATCH[args.command]
    try:
        # Lazy import: `tcg --help` must not pay for the prover stack.
        module = __import__(f"tcg.commands.{module_name}", fromlist=["run"])
    except ModuleNotFoundError:
        print(f"tcg: '{args.command}' is not implemented yet", file=sys.stderr)
        return int(Exit.USAGE)
    return int(module.run(args))


def entry() -> None:
    raise SystemExit(main())
