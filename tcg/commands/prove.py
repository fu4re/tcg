"""`tcg prove <loop>` — run the pinned prover on a loop's claims.

Assembles one prove module per goal claim (the loop's declared children
injected as trusted lemmas, plus that single claim), invokes kprove once per
claim, and classifies each verdict independently -- classify() is validated
against real Haskell-backend kprove output, not assumed text (see
docs/substrate.md, "classify() validation").

- Accept  — exit 0 *and* a corroborated success marker; a replay record is
  written per accepted goal claim (Accept-only evidence: nothing is recorded
  for other verdicts outside the workspace).
- Refute  — the prover reached a state that structurally does not unify with
  the claimed destination; the log is the witness.
- Unknown — could not decide; classified (a) iteration bound [name retained
  as spec vocabulary only -- unreachable against the real backend, which
  emits no distinguishing text for a depth-bounded search; this module never
  passes --depth], (b) timeout, (c) solver/proof-state unknown, including a
  residual boolean implication left undischarged after the rewrite target
  was otherwise reached. All three are refusals.

Known substrate limit (docs/substrate.md §9): a claim whose target *is*
reached but whose postcondition is actually false (e.g. a wrong arithmetic
bound) looks, in kore-exec's own output, identical to a true claim that is
merely under-specified -- both are the "unifies... implication check has
failed" WarnStuckClaimState variant. On this substrate such defects surface
as Unknown(c) with a hint, not Refute; Refute is only reliably reachable via
genuine structural non-unification (see tests/control/refutable-structural.k).
Lifting this needs structured per-claim counterexample extraction (kore-rpc
implies/get-model or pyk APRProof), not attempted here.

A loop's aggregate state is the worst verdict across its goal claims: any
Refute -> Refuted, else any Unknown -> Unknown, else Accepted.
"""
from __future__ import annotations

import re
import subprocess
import sys
import time

from tcg.claims import assemble_prove_module, extract_body, module_name
from tcg.outcome import Exit
from tcg.workspace import (
    WORKSPACE_DIR, WorkspaceError, drop_edges_from, find_root, load_graph,
    load_loop, loop_dir, read_json, save_graph, save_loop, transition,
    upsert_edge, write_json,
)

# kore-exec's own success marker for a fully-discharged all-path claim (the
# pretty-printed \top formula). Pinned empirically: tests/control/logs/
# provable.log is exactly "#Top\n" with nothing else on stdout.
_ACCEPT_PATTERN = "#Top"

_WS = re.compile(r"\s+")

# "WarnStuckClaimState" covers two OPPOSITE outcomes -- "unifies... but the
# implication check has failed" (Unknown: solver-decidability gap) vs.
# "doesn't unify..." (Refute: genuine structural counterexample) -- so only
# the first phrase is a valid Unknown signal; matching the bare tag name
# swallows a found defect into a false "could not verify". Full argument,
# real log evidence, and why "stuck" must win regardless of textual position
# (not just whichever comes first) are in docs/substrate.md §4a and
# tests/test_classify.py. One precompiled case-insensitive alternation,
# matched against one whitespace-collapsed copy of the log -- not several
# lowercased copies -- since real proof logs can reach tens of MB.
_STUCK_OR_REFUTE = re.compile(
    r"(?P<stuck>unifies with the destination)|(?P<refute>cannot be rewritten further)",
    re.IGNORECASE,
)


def classify(returncode: int, log: str, timed_out: bool) -> tuple[str, str | None, str | None]:
    """(verdict, unknown_class, hint). Only exit 0 *and* a corroborated
    success marker is Accept. Validated against real Haskell-backend kprove
    output -- see tests/control/logs/ and docs/substrate.md §4.
    """
    if timed_out:
        return "Unknown", "b", None
    if returncode == 0:
        if _ACCEPT_PATTERN in log:
            return "Accept", None, None
        return "Unknown", "c", "prover exited 0 but no proof pattern found"
    norm = _WS.sub(" ", log)
    saw_refute = False
    for m in _STUCK_OR_REFUTE.finditer(norm):
        if m.group("stuck"):
            return ("Unknown", "c",
                    "residual implication undischarged — claim may need more "
                    "concretized cells; see log")
        saw_refute = True
    if saw_refute:
        return "Refute", None, None
    # Anything unrecognized stays Unknown -- never Refute. The class "a"
    # (iteration bound exhausted) this function used to detect via a
    # "depth bound"/"iteration bound"/"max iterations" text match was
    # removed: real kprove never emits that text (see docs/substrate.md §4b
    # and tcg.outcome.UNKNOWN_CLASSES, where the name is kept as spec
    # vocabulary only).
    return "Unknown", "c", None


def _text(x: str | bytes | None) -> str:
    """subprocess.TimeoutExpired's e.stdout/e.stderr may be str (text-mode
    Popen) or bytes, depending on how far communicate() got -- don't assume."""
    if x is None:
        return ""
    return x.decode(errors="replace") if isinstance(x, bytes) else x


def run(args) -> int:
    try:
        root = find_root()
        loop = load_loop(root, args.target)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    if loop["state"] not in ("Compiled", "Accepted", "Refuted", "Unknown"):
        print(f"tcg: loop {args.target} is {loop['state']}; run "
              f"`tcg compile-claims {args.target}` first", file=sys.stderr)
        return int(Exit.USAGE)

    interfaces = read_json(root / "spec" / "interfaces.json")
    entry = interfaces.get(args.target)
    if not entry:
        print(f"tcg: {args.target} has no compiled interface; run "
              f"`tcg compile-claims {args.target}`", file=sys.stderr)
        return int(Exit.USAGE)

    lock = read_json(root / WORKSPACE_DIR / "toolchain.lock")
    definition = args.definition or lock.get("definition")
    if not definition:
        print("tcg: no kompiled definition; pass --definition, or set it at "
              "init (`tcg init --definition PATH` or $TCG_DEFINITION) or "
              "edit .tcg/toolchain.lock", file=sys.stderr)
        return int(Exit.USAGE)
    includes = list(args.include or []) + list(lock.get("includes", []))

    iface = read_json(loop_dir(root, args.target) / "iface.json")
    claims_dir = root / "spec" / "claims"

    def body_of(h: str) -> str:
        return extract_body((claims_dir / f"{h}.k").read_text(encoding="utf-8"))

    # Children as trusted: resolve each declared ref to its compiled claim.
    trusted_hashes: list[str] = []
    trusted_bodies: list[str] = []
    for ref in iface.get("trusted", []):
        child = interfaces.get(ref.get("loop", ""), {})
        h = child.get("claims", {}).get(ref.get("label", ""))
        if not h:
            print(f"tcg: trusted ref not compiled: {ref}; run "
                  f"`tcg compile-claims {ref.get('loop', '<loop>')}` first",
                  file=sys.stderr)
            return int(Exit.USAGE)
        trusted_hashes.append(h)
        trusted_bodies.append(body_of(h))

    goal_hashes = entry["claims"]  # label -> hash
    requires = iface.get("requires", ["evm.md"])
    imports = iface.get("imports", ["EVM"])

    build_dir = root / WORKSPACE_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    log_dir = root / WORKSPACE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    timeout = lock.get("replay", {}).get("timeout_seconds", 3600)

    transition(loop, "Proving")
    save_loop(root, args.target, loop)

    graph = load_graph(root)
    drop_edges_from(graph, set(goal_hashes.values()))

    # One kprove invocation per goal claim -- a single run-wide call would
    # let one stuck/refuted claim mask a sibling's genuine result, and
    # evidence/graph edges are per-claim data anyway (see module docstring).
    # N x kprove startup cost; correctness over speed.
    results: dict[str, str] = {}
    for label, h in goal_hashes.items():
        mod = module_name(args.target, f"{label}-prove")[: -len("-SPEC")]
        spec_path = build_dir / f"{args.target}-{label}-prove.k"
        spec_path.write_text(
            assemble_prove_module(mod, requires, imports, trusted_bodies, [body_of(h)]),
            encoding="utf-8")
        log_path = log_dir / f"{args.target}-{label}-prove.log"

        argv = ["kprove", str(spec_path), "--definition", str(definition),
                "--spec-module", mod]
        for inc in includes:
            argv += ["-I", str(inc)]

        started = time.monotonic()
        timed_out = False
        try:
            proc = subprocess.run(argv, capture_output=True, text=True,
                                   timeout=timeout, cwd=build_dir)
            returncode, log = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as e:
            returncode, log, timed_out = -1, _text(e.stdout) + _text(e.stderr), True
        except FileNotFoundError:
            print("tcg: kprove not found on PATH; install/activate the pinned K "
                  "toolchain (versions are in .tcg/toolchain.lock)", file=sys.stderr)
            transition(loop, "Unknown")
            save_loop(root, args.target, loop)
            return int(Exit.USAGE)
        duration = round(time.monotonic() - started, 3)
        log_path.write_text(log, encoding="utf-8")

        # A crash mid-search (docs/substrate.md §5) can drop a debug bundle
        # in kprove's cwd; collect it next to this claim's log rather than
        # leaving it in the workspace build dir. Never a classify() signal.
        crash = build_dir / "kore-exec.tar.gz"
        crash_note = ""
        if crash.is_file():
            crash_dest = log_dir / f"{args.target}-{label}-kore-exec.tar.gz"
            crash.replace(crash_dest)
            crash_note = f"; backend crash report: {crash_dest}"

        verdict, ucls, hint = classify(returncode, log, timed_out)
        results[label] = verdict

        if verdict == "Accept":
            for child in trusted_hashes:
                upsert_edge(graph, h, child, "trusted-lemma")
            write_json(root / "evidence" / "replay" / f"{h}.json", {
                "claim": h, "label": label, "spec_module": mod,
                "spec_file": str(spec_path.relative_to(root)),
                "definition": str(definition),
                "includes": [str(i) for i in includes],
                "trusted": trusted_hashes, "expected": "Accept",
                "toolchain": {k: lock[k] for k in
                              ("k", "kore-exec", "kontrol", "kevm") if k in lock},
                "duration_seconds": duration,
            })
            print(f"Accept: {args.target}/{label} "
                  f"({len(trusted_hashes)} trusted child(ren), {duration}s)")
            continue

        # Non-Accept invalidates any earlier Accept evidence for this claim.
        (root / "evidence" / "replay" / f"{h}.json").unlink(missing_ok=True)
        if verdict == "Refute":
            print(f"Refute: {args.target}/{label} — prover left a residual "
                  f"goal; witness log: {log_path}{crash_note}; revise the "
                  f"interface/claim body and re-run `tcg iface set` + "
                  f"`tcg compile-claims {args.target}`", file=sys.stderr)
        else:
            hint_note = f" — {hint}" if hint else ""
            print(f"Unknown({ucls}): {args.target}/{label} — refusal"
                  f"{hint_note}; log: {log_path}{crash_note}; re-run "
                  f"`tcg prove {args.target}` (consider raising "
                  "replay.timeout_seconds in toolchain.lock), or revise "
                  "the claim", file=sys.stderr)

    save_graph(root, graph)

    # Aggregate = worst verdict across goal claims; any Refute -> Refuted,
    # else any Unknown -> Unknown, else Accepted. Never a silent average.
    verdicts = set(results.values())
    aggregate = ("Refute" if "Refute" in verdicts else
                 "Unknown" if "Unknown" in verdicts else "Accept")
    transition(loop, {"Accept": "Accepted", "Refute": "Refuted",
                      "Unknown": "Unknown"}[aggregate])
    save_loop(root, args.target, loop)

    tally = {v: sum(1 for x in results.values() if x == v)
             for v in ("Accept", "Refute", "Unknown")}
    print(f"{aggregate}: {args.target} ({len(goal_hashes)} claim(s): "
          f"{tally['Accept']} accepted, {tally['Refute']} refuted, "
          f"{tally['Unknown']} unknown)",
          file=(sys.stdout if aggregate == "Accept" else sys.stderr))

    return int({"Accept": Exit.OK, "Refute": Exit.REFUSED,
                "Unknown": Exit.UNKNOWN}[aggregate])
