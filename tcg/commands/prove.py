"""`tcg prove <loop>` — run the pinned prover on a loop's claims.

Assembles a prove module from the loop's canonical claims plus its declared
children injected as trusted lemmas, runs kprove, and classifies the verdict:

- Accept  — exit 0; a replay record is written per goal claim (Accept-only
  evidence: nothing is recorded for other verdicts outside the workspace).
- Refute  — the prover failed with a residual goal; the log is the witness.
- Unknown — could not decide; classified (a) iteration bound, (b) timeout,
  (c) solver unknown. All three are refusals.
"""
from __future__ import annotations

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


def classify(returncode: int, log: str, timed_out: bool) -> tuple[str, str | None]:
    """(verdict, unknown_class). Only exit 0 is Accept."""
    if timed_out:
        return "Unknown", "b"
    if returncode == 0:
        return "Accept", None
    low = log.lower()
    if "cannot be\nrewritten further" in low or "cannot be rewritten further" in low \
            or "implication check failed" in low or "#not" in low:
        return "Refute", None
    if "depth bound" in low or "iteration bound" in low or "max iterations" in low:
        return "Unknown", "a"
    if "unknown" in low:
        return "Unknown", "c"
    return "Unknown", "c"


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
    goal_bodies = [body_of(h) for h in goal_hashes.values()]

    mod = module_name(args.target, "prove")[: -len("-SPEC")]  # <TARGET>-PROVE
    module_text = assemble_prove_module(
        mod, iface.get("requires", ["evm.md"]), iface.get("imports", ["EVM"]),
        trusted_bodies, goal_bodies,
    )

    build_dir = root / WORKSPACE_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    spec_path = build_dir / f"{args.target}-prove.k"
    spec_path.write_text(module_text, encoding="utf-8")

    argv = ["kprove", str(spec_path), "--definition", str(definition),
            "--spec-module", mod]
    for inc in includes:
        argv += ["-I", str(inc)]

    timeout = lock.get("replay", {}).get("timeout_seconds", 3600)
    log_dir = root / WORKSPACE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    log_path = log_dir / f"{args.target}-prove.log"

    transition(loop, "Proving")
    save_loop(root, args.target, loop)

    started = time.monotonic()
    timed_out = False
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        returncode, log = proc.returncode, proc.stdout + proc.stderr
    except subprocess.TimeoutExpired as e:
        returncode = -1
        log = ((e.stdout or b"").decode(errors="replace")
               + (e.stderr or b"").decode(errors="replace"))
        timed_out = True
    except FileNotFoundError:
        print("tcg: kprove not found on PATH; install/activate the pinned K "
              "toolchain (versions are in .tcg/toolchain.lock)", file=sys.stderr)
        transition(loop, "Unknown")
        save_loop(root, args.target, loop)
        return int(Exit.USAGE)
    duration = round(time.monotonic() - started, 3)
    log_path.write_text(log, encoding="utf-8")

    verdict, ucls = classify(returncode, log, timed_out)
    transition(loop, {"Accept": "Accepted", "Refute": "Refuted",
                      "Unknown": "Unknown"}[verdict])
    save_loop(root, args.target, loop)

    # The proof structure is part of the record: trusted-lemma edges exist
    # exactly for claims whose current verdict is Accept.
    graph = load_graph(root)
    drop_edges_from(graph, set(goal_hashes.values()))
    if verdict == "Accept":
        for h in goal_hashes.values():
            for child in trusted_hashes:
                upsert_edge(graph, h, child, "trusted-lemma")
    save_graph(root, graph)

    if verdict == "Accept":
        # Accept-only evidence: the exact replayable invocation per goal claim.
        for label, h in goal_hashes.items():
            write_json(root / "evidence" / "replay" / f"{h}.json", {
                "claim": h,
                "label": label,
                "spec_module": mod,
                "spec_file": str(spec_path.relative_to(root)),
                "definition": str(definition),
                "includes": [str(i) for i in includes],
                "trusted": trusted_hashes,
                "expected": "Accept",
                "toolchain": {k: lock[k] for k in
                              ("k", "kore-exec", "kontrol", "kevm") if k in lock},
                "duration_seconds": duration,
            })
        print(f"Accept: {args.target} "
              f"({len(goal_hashes)} claim(s), {len(trusted_hashes)} trusted child(ren), "
              f"{duration}s)")
        return int(Exit.OK)

    # Non-Accept invalidates any earlier Accept evidence for these claims.
    for h in goal_hashes.values():
        (root / "evidence" / "replay" / f"{h}.json").unlink(missing_ok=True)

    if verdict == "Refute":
        print(f"Refute: {args.target} — prover left a residual goal; "
              f"witness log: {log_path}; revise the interface/claim body "
              f"and re-run `tcg iface set` + `tcg compile-claims {args.target}`",
              file=sys.stderr)
        return int(Exit.REFUSED)

    print(f"Unknown({ucls}): {args.target} — refusal; log: {log_path}; "
          f"re-run `tcg prove {args.target}` (consider raising "
          "replay.timeout_seconds in toolchain.lock), or revise the claim",
          file=sys.stderr)
    return int(Exit.UNKNOWN)
