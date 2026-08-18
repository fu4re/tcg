"""`tcg vacuity <loop>` — antecedent-reachability (vacuity) probe.

Ports the spirit of the sheaf project's Finding 0005 vacuity gate (Probe R:
`assert(false)`-proves ⇒ the asserted point is UNREACHABLE ⇒ the proof is
vacuous) into this reachability CLI. A `proved` can be EMPTY: if a claim's
initial state (its `requires` + LHS cells) is INFEASIBLE — no concrete state
satisfies it — then every property of that state proves for an empty reason.

Scope: ROOTS ONLY — exactly where freeze and verify gate vacuity. Vacuity is a
root property: the bundle's guarantee is its root claims (a verifier reads the
roots), and a vacuous root is the false green. A vacuously-true trusted lemma
is useless, not unsound (a true statement, assumed, injects no falsehood), so
non-root claims are reported informationally and NOT probed — spending a prover
run whose verdict nothing downstream consumes is waste.

The probe, per proved ROOT claim of the loop:

  1. FALSIFY the postcondition — mutate the claim to `ensures false` while
     keeping the antecedent intact (tcg.claims.falsify_body).
  2. Prove the mutant with the SAME pinned prover, judged by the SAME shared
     classifier (tcg.verdict.classify) `prove`/`verify` use.
  3. If the falsified mutant STILL proves Accept, the antecedent is infeasible
     ⇒ the original proof was VACUOUS ⇒ REFUSE. If it does NOT prove (Refute /
     Unknown), the antecedent is feasible enough that an impossible post is not
     vacuously provable ⇒ NON-vacuous w.r.t. this probe.

This is the SOLVER's judgement, never prose (judge = solver). The mutation is a
deterministic syntactic transform; the verdict is kprove's; PASS/FLAG is a
comparison of solver verdicts. The probe runs the mutant STANDALONE (no trusted
children): an infeasible antecedent proves regardless of lemmas, and true
lemmas cannot make a feasible antecedent infeasible, so children are irrelevant
to reachability and only cost prover time.

What it catches / does NOT catch (honest, see docs/findings/0002):
  * CATCHES: antecedent failure — a contradictory `requires`, or LHS cell
    constraints no reachable state satisfies. Empirically pinned on the real
    Haskell backend (a contradictory `requires` mutant proves "during
    initialization … left-hand side may be undefined" → #Top → FLAG).
  * DOES NOT catch: a claim whose antecedent is feasible but whose
    POSTcondition is a weak/proxy assertion (a live-but-useless spec). That is
    Finding 0005's Probe M (component load-bearing), which needs a curated
    adversary family and is out of scope here. It also does not catch the
    program-binding hole — that is P0-A's mechanical <program> check.
  * COST: one extra kprove run per goal claim (~one prove's wall time each).

Records `.tcg/vacuity/<h>.json` per claim; `freeze` requires every ROOT to
have a non-vacuous record and bundles it, and `verify` re-derives the probe
bundle-only for each root (it does not trust this record).
"""
from __future__ import annotations

import subprocess
import sys
import time

from tcg.claims import assemble_prove_module, extract_body, falsify_body, module_name
from tcg.outcome import Exit
from tcg.verdict import classify, to_text
from tcg.workspace import (
    WORKSPACE_DIR, WorkspaceError, find_root, load_graph, load_loop, loop_dir,
    read_json, write_json,
)


def run(args) -> int:
    try:
        root = find_root()
        loop = load_loop(root, args.loop)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    if loop["state"] != "Accepted":
        print(f"tcg: loop {args.loop} is {loop['state']}, not Accepted — the "
              f"vacuity probe only applies to proved claims; run `tcg prove "
              f"{args.loop}` first", file=sys.stderr)
        return int(Exit.USAGE)

    interfaces = read_json(root / "spec" / "interfaces.json")
    entry = interfaces.get(args.loop)
    if not entry:
        print(f"tcg: {args.loop} has no compiled interface; run "
              f"`tcg compile-claims {args.loop}`", file=sys.stderr)
        return int(Exit.USAGE)

    lock = read_json(root / WORKSPACE_DIR / "toolchain.lock")
    definition = args.definition or lock.get("definition")
    if not definition:
        print("tcg: no kompiled definition; pass --definition, or set it at "
              "init (`tcg init --definition PATH` or $TCG_DEFINITION) or "
              "edit .tcg/toolchain.lock", file=sys.stderr)
        return int(Exit.USAGE)
    includes = list(args.include or []) + list(lock.get("includes", []))

    iface = read_json(loop_dir(root, args.loop) / "iface.json")
    requires = iface.get("requires", ["evm.md"])
    imports = iface.get("imports", ["EVM"])
    claims_dir = root / "spec" / "claims"
    graph = load_graph(root)

    build_dir = root / WORKSPACE_DIR / "build"
    build_dir.mkdir(exist_ok=True)
    log_dir = root / WORKSPACE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    vac_dir = root / WORKSPACE_DIR / "vacuity"
    vac_dir.mkdir(exist_ok=True)
    timeout = lock.get("replay", {}).get("timeout_seconds", 3600)

    # Vacuity is a ROOT property, gated exactly where freeze and verify gate it
    # (roots only). A vacuously-true trusted lemma is useless, not unsound (a
    # true statement, assumed, injects no falsehood); a vacuous ROOT is the
    # false green. So probe ONLY roots — spending a prover run on a non-root
    # whose verdict nothing downstream consumes is waste — and report any
    # non-root claims as informational, not probed, not gating.
    roots = [(label, h) for label, h in entry["claims"].items()
             if graph["nodes"].get(h, {}).get("root")]
    non_roots = [label for label, h in entry["claims"].items()
                 if not graph["nodes"].get(h, {}).get("root")]
    if non_roots:
        print(f"vacuity: not probing non-root claim(s) {sorted(non_roots)} "
              "(vacuity gates roots only; a vacuous lemma is useless, not "
              "unsound)")
    if not roots:
        print(f"vacuity: OK ({args.loop} has no root claims to probe)")
        return int(Exit.OK)

    any_vacuous = False
    for label, h in roots:
        module_text = (claims_dir / f"{h}.k").read_text(encoding="utf-8")
        mod = module_name(args.loop, f"{label}-vacuity")[: -len("-SPEC")]
        mutant = assemble_prove_module(
            mod, requires, imports, [], [falsify_body(extract_body(module_text))])
        spec_path = build_dir / f"{args.loop}-{label}-vacuity.k"
        spec_path.write_text(mutant, encoding="utf-8")
        log_path = log_dir / f"{args.loop}-{label}-vacuity.log"

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
            returncode, log, timed_out = -1, to_text(e.stdout) + to_text(e.stderr), True
        except FileNotFoundError:
            print("tcg: kprove not found on PATH; install/activate the pinned K "
                  "toolchain (versions are in .tcg/toolchain.lock)", file=sys.stderr)
            return int(Exit.USAGE)
        duration = round(time.monotonic() - started, 3)
        log_path.write_text(log, encoding="utf-8")

        crash = build_dir / "kore-exec.tar.gz"
        crash_note = ""
        if crash.is_file():
            crash_dest = log_dir / f"{args.loop}-{label}-vacuity-kore-exec.tar.gz"
            crash.replace(crash_dest)
            crash_note = f"; backend crash report: {crash_dest}"

        verdict, ucls, _ = classify(returncode, log, timed_out)
        # The falsified mutant proving Accept means the antecedent is infeasible
        # ⇒ the original proof is vacuous. Any non-Accept means feasible.
        vacuous = verdict == "Accept"
        any_vacuous = any_vacuous or vacuous

        write_json(vac_dir / f"{h}.json", {
            "claim": h, "label": label, "loop": args.loop,
            "probe": "ensures-false",
            "mutant_verdict": verdict,
            "mutant_unknown_class": ucls,
            "vacuous": vacuous,
            "root": True,
            "spec_module": mod,
            "definition": str(definition),
            "duration_seconds": duration,
        })

        if vacuous:
            print(f"VACUOUS: {args.loop}/{label} — the falsified claim (ensures "
                  f"false) STILL proves Accept, so its antecedent is infeasible "
                  f"and the proof is empty; log: {log_path}{crash_note}; fix the "
                  f"claim's `requires`/initial cells so the initial state is "
                  f"reachable, then re-prove", file=sys.stderr)
        else:
            print(f"non-vacuous: {args.loop}/{label} — falsified mutant did not "
                  f"prove ({verdict}{'('+ucls+')' if ucls else ''}), antecedent "
                  f"feasible ({duration}s)")

    if any_vacuous:
        print(f"vacuity: REFUSED — at least one root of {args.loop} is vacuous; "
              "a vacuous proof is a refusal, never a pass", file=sys.stderr)
        return int(Exit.REFUSED)
    print(f"vacuity: OK ({len(roots)} root(s) probed, none vacuous)")
    return int(Exit.OK)
