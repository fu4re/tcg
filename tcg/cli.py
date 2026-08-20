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

from tcg.outcome import EXIT_MEANING, Exit

# Shown by `tcg --help`. Built once here so a blind agent — one that knows
# only `tcg --help` and the tool's own messages — never needs a doc it can't
# reach: the whole pipeline, in order, plus the exit-code table.
_WORKFLOW = """\
workflow, in order ("(as needed)" steps are conditional):
  tcg init                                   scaffold a workspace + pinned toolchain.lock
  tcg loop new <name>                        create a loop workspace
  tcg iface set <loop> --file <iface.json>   set the loop's interface (Pre, Post, Exit, footprint, rely, guar)
  tcg compile-claims <loop>                  canonicalize the loop's claims + content-address them
  tcg prove <loop>                           run the prover: Accept / Refute / Unknown
  tcg vacuity <loop>                         antecedent-reachability probe: refuse empty (vacuous) proofs
  tcg junction <i> <j>                       (as needed) consequence claim Post_i -> Pre_j
  tcg compat <i> <j>                         (as needed) interference obligation Guar_j -> Rely_i
  tcg graph check                            structural checks on the claim DAG
  tcg approve --reviewer <name>              human sign-off over the current root hashes
  tcg subject set --runtime <path>           install subject/runtime.bin (+ environment.json)
  tcg freeze                                 assemble the bundle: hash tree + MANIFEST
  tcg verify <bundle>                        replay every proof from the bundle alone
  tcg roots <bundle>                         render the root claims for human reading

  tcg status                                 workspace overview + next-step hint, at any point above
"""


def _exit_code_table() -> str:
    # Built from tcg.outcome.EXIT_MEANING so this help text can't drift from
    # the actual exit-code table.
    lines = ["exit codes (uniform across every command):"]
    for code in Exit:
        lines.append(f"  {int(code)}  {EXIT_MEANING[code]}")
    lines.append("")
    lines.append('"could not verify" (2) never shares a code with "found a defect" (3).')
    return "\n".join(lines)


_IFACE_HELP = """\
iface JSON keys (see `tcg loop new <name>` for a starter template):
  pre, post, exit      K predicates, as strings
  footprint             {"reads": [...], "writes": [...]}
  rely, guar             K predicates, as strings
  requires, imports      K module requires/imports (default: ["evm.md"], ["EVM"])
  claims                 [{"label": <l>, "file": <path>, "role": <opt>, "root": <opt bool>},
                           ...] — file is relative to the loop's own directory;
                           role defaults to the workspace's own role (loop/junction/
                           compat/guar/env); root defaults to true only for role "loop"
"""

_CLAIM_BODY_HELP = """\
claim body form (one K claim per file, referenced from a claims[].file entry):
  a single `claim ...` ending in a trailing attribute list — not the
  `claim [x]:` head — of the form [label(<l>), all-path], where <l> matches
  the claims[] entry's "label". No `module`/`endmodule`/`requires "..."`
  lines: the wrapper is emitted for you. `trusted` and `one-path` are refused.
"""

_SUBJECT_HELP = """\
--runtime accepts either raw bytecode bytes, or a text file holding a
0x-prefixed or plain hex string — both decode to the same installed bytes.
--environment, if omitted and none is installed yet, is written as a
skeleton with null fields: chainid, fork, fee_schedule, constructor_args,
immutables, external_code.
"""


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        prog="tcg",
        description="Build and verify proof-carrying bundles for EVM contracts.",
        epilog=_WORKFLOW + "\n" + _exit_code_table(),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = ap.add_subparsers(dest="command", metavar="<command>")

    it = sub.add_parser(
        "init", help="scaffold a workspace + pinned toolchain.lock",
        epilog="--definition/$TCG_DEFINITION are read once, here, at init "
               "time (flag wins); prove/verify never re-read the "
               "environment, only the lock or their own --definition.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    it.add_argument("--definition", default=None,
                    help="kompiled definition dir to pin into toolchain.lock "
                         "(also honors $TCG_DEFINITION; flag wins)")
    it.add_argument("-I", "--include", action="append", default=None,
                    help="include dir to pin into toolchain.lock (repeatable)")

    sub.add_parser(
        "status",
        help="workspace overview: loop states, graph, oracle, subject, next-step hints",
    )

    lp = sub.add_parser("loop", help="manage loop workspaces")
    lp_sub = lp.add_subparsers(dest="loop_command", metavar="<subcommand>")
    lp_new = lp_sub.add_parser("new", help="create a loop workspace")
    lp_new.add_argument("name")

    ifc = sub.add_parser("iface", help="manage loop interfaces")
    ifc_sub = ifc.add_subparsers(dest="iface_command", metavar="<subcommand>")
    ifc_set = ifc_sub.add_parser(
        "set", help="set (Pre, Post, Exit, footprint, rely, guar) for a loop",
        epilog=_IFACE_HELP, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    ifc_set.add_argument("loop")
    ifc_set.add_argument("--file", required=True, help="interface JSON to install")

    cc = sub.add_parser(
        "compile-claims",
        help="compile a loop interface into canonical claims (+ round-trip check)",
        epilog=_CLAIM_BODY_HELP, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    cc.add_argument("loop")

    apv = sub.add_parser(
        "approve", help="record human sign-off over the current root hashes"
    )
    apv.add_argument("--reviewer", required=True,
                     help="the human attesting the roots")
    apv.add_argument("--statement", default=None,
                     help="attestation text (a default is provided)")

    pv = sub.add_parser(
        "prove", help="run the prover on a loop or junction; Accept/Refute/Unknown"
    )
    pv.add_argument("target", help="loop or junction name")
    pv.add_argument("--definition", default=None,
                    help="kompiled definition dir (or set in toolchain.lock)")
    pv.add_argument("-I", "--include", action="append", default=None,
                    help="include dir for the prover (repeatable)")

    vac = sub.add_parser(
        "vacuity",
        help="antecedent-reachability probe: refuse vacuous (empty) proofs",
        epilog="Falsifies each proved claim's postcondition (ensures false) and "
               "re-proves; if the falsified claim STILL proves, the antecedent "
               "is infeasible and the original proof was vacuous — a refusal. "
               "One extra prover run per claim. Records .tcg/vacuity/<h>.json "
               "that freeze requires for every root and verify re-derives.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    vac.add_argument("loop", help="loop whose proved claims to probe")
    vac.add_argument("--definition", default=None,
                     help="kompiled definition dir (or set in toolchain.lock)")
    vac.add_argument("-I", "--include", action="append", default=None,
                     help="include dir for the prover (repeatable)")

    jn = sub.add_parser("junction", help="consequence claim: Post_i implies Pre_j")
    jn.add_argument("i")
    jn.add_argument("j")

    cp = sub.add_parser("compat", help="interference obligation: Guar_j implies Rely_i")
    cp.add_argument("i")
    cp.add_argument("j")

    sj = sub.add_parser("subject", help="manage the subject bytecode and environment")
    sj_sub = sj.add_subparsers(dest="subject_command", metavar="<subcommand>")
    sj_set = sj_sub.add_parser(
        "set", help="install subject/runtime.bin (+ subject/environment.json)",
        epilog=_SUBJECT_HELP, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sj_set.add_argument("--runtime", required=True,
                        help="bytecode file: raw bytes, or 0x-prefixed/plain hex text")
    sj_set.add_argument("--environment", default=None,
                        help="environment.json to install (must parse as JSON); "
                             "omit to write a documented null-field skeleton if "
                             "none exists yet")

    gr = sub.add_parser("graph", help="claim-graph operations")
    gr_sub = gr.add_subparsers(dest="graph_command", metavar="<subcommand>")
    gr_sub.add_parser("check", help="structural checks on the claim DAG")

    sub.add_parser("freeze", help="assemble the bundle: hash tree + MANIFEST")

    vf = sub.add_parser(
        "verify", help="run the verifier protocol on a bundle (bundle-only input)"
    )
    vf.add_argument("bundle", help="path to a bundle directory")
    vf.add_argument("--definition", default=None,
                    help="kompiled definition dir for replay")
    vf.add_argument("-I", "--include", action="append", default=None,
                    help="include dir for the prover (repeatable)")
    vf.add_argument("--strict", action="store_true",
                    help="refuse (exit 3) any bundle carrying an author-chosen "
                         "typed-stub assumption (an opaque callee summary that is "
                         "assumed, not proved over the callee's code) — for an "
                         "auditor who wants a fully-discharged certificate. "
                         "Default: exit 0 with a prominent ⚠ section enumerating "
                         "each load-bearing assumption.")

    rt = sub.add_parser("roots", help="render a bundle's root claims for reading")
    rt.add_argument("bundle", help="path to a bundle directory")

    return ap


# command name → module in tcg.commands
_DISPATCH: dict[str, str] = {
    "init": "init",
    "status": "status",
    "loop": "loop",
    "iface": "iface",
    "compile-claims": "compile_claims",
    "approve": "approve",
    "prove": "prove",
    "vacuity": "vacuity",
    "junction": "junction",
    "compat": "compat",
    "graph": "graph",
    "subject": "subject",
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
