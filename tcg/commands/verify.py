"""`tcg verify <bundle>` — the verifier protocol, bundle-only.

Reads nothing but the bundle (plus a kompiled definition for replay). Steps
are strictly ordered; the first failing step refuses the certificate.

1. Integrity  — recompute the hash tree from MANIFEST.json.
2. Identity   — subject identity is machine-checkable but needs chain access;
                printed as a verifier action, per the trust manifest.
3. Theory     — re-hash vendored patches against toolchain.lock.
4. Graph      — structural discipline over bundle content only, PLUS program
                binding (P0-A): every root's <program> cell must equal
                subject/runtime.bin, re-derived bundle-only (text + byte
                compare, no prover). A root about a different program than the
                installed subject is refused here.
5. Replay     — topological re-proof of every node, children as trusted,
                judged by the SAME classifier `prove` uses (tcg.verdict) --
                same judge, same discipline, on both sides. Accept closes the
                node; Refute is a genuine structural counterexample and is
                never retried (exit REFUSED, 3); Unknown (timeout, an
                undischarged implication, or unrecognized output) absorbs up
                to toolchain.lock's retries and, if still Unknown, refuses
                conservatively at exit UNKNOWN (2) -- distinct from Refute,
                because "could not re-verify" is not "replay refuted".
   Step 5v   — vacuity re-derivation (P0-B): for each root, falsify its
                postcondition (ensures false) and re-prove; if the falsified
                form STILL proves Accept, the antecedent is infeasible and the
                proof is vacuous — REFUSED at step 5-vacuity. Re-derived
                bundle-only; the bundled evidence/vacuity record is not trusted.

Step 6 (reading the roots) is `tcg roots`.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from tcg.bridge import is_bridge_node, structural_errors as bridge_structural_errors
from tcg.claims import (
    assemble_prove_module, extract_body, falsify_body, module_header,
    program_binding_error, sha256_text,
)
from tcg.outcome import Exit
from tcg.verdict import classify, to_text

_ZERO_STEP_ROLES = ("junction", "compat")


def _read_json(path: Path) -> dict:
    import json
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _sha256_file(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fail(step: str, msgs: list[str]) -> int:
    for m in msgs:
        print(f"verify[{step}]: {m}", file=sys.stderr)
    print(f"verify: certificate REFUSED at step {step} — do not rely on this "
          "bundle; if you produced it, fix the workspace and re-run "
          "`tcg freeze`", file=sys.stderr)
    return int(Exit.REFUSED)


def run(args) -> int:
    bundle = Path(args.bundle)
    manifest_path = bundle / "MANIFEST.json"
    if not manifest_path.is_file():
        print(f"tcg: no MANIFEST.json in {bundle}; pass a directory produced "
              "by `tcg freeze`", file=sys.stderr)
        return int(Exit.USAGE)
    manifest = _read_json(manifest_path)

    # --- Step 1: integrity -------------------------------------------------
    errors = []
    for rel, expected in manifest.get("files", {}).items():
        if rel.split("/")[0] == "nav":
            errors.append(f"hash tree references nav/: {rel}")
            continue
        path = bundle / rel
        if not path.is_file():
            errors.append(f"missing file: {rel}")
        elif _sha256_file(path) != expected:
            errors.append(f"hash mismatch: {rel}")
    if errors:
        return _fail("1-integrity", errors)
    print(f"step 1 integrity: OK ({len(manifest['files'])} file(s))")

    # --- Step 2: identity --------------------------------------------------
    print("step 2 identity: verifier action — compare keccak(subject/runtime.bin) "
          "with the on-chain code hash (see assumptions/trust-manifest.json)")

    # --- Step 3: theory ----------------------------------------------------
    lock = _read_json(bundle / "theory" / "toolchain.lock")
    for rel, expected in lock.get("patches", {}).items():
        path = bundle / rel
        if not path.is_file() or _sha256_file(path) != expected:
            errors.append(f"patch does not match toolchain.lock: {rel}")
    if not (bundle / "theory" / "semantics").is_dir():
        print("step 3 theory: semantics not vendored — replay uses the local "
              "definition; the trust manifest records this as assumed")
    if errors:
        return _fail("3-theory", errors)
    print("step 3 theory: OK (patch hashes match toolchain.lock)")

    # --- Step 4: graph -----------------------------------------------------
    graph = _read_json(bundle / "spec" / "graph.json")
    nodes, edges = graph["nodes"], graph["edges"]
    for h, n in nodes.items():
        path = bundle / "spec" / "claims" / f"{h}.k"
        if not path.is_file():
            errors.append(f"{h[:12]}: claim file missing")
            continue
        text = path.read_text(encoding="utf-8")
        if sha256_text(text) != h:
            errors.append(f"{h[:12]}: content does not match its hash")
        if not re.search(r"\[[^\[\]]*all-path[^\[\]]*\]", text):
            errors.append(f"{h[:12]}: missing all-path attribute")
        # An abstract-summary node carries no replay evidence — it is bridge-
        # discharged, never directly proved (checked below + in step 5).
        if (not is_bridge_node(n)
                and not (bundle / "evidence" / "replay" / f"{h}.json").is_file()):
            errors.append(f"{h[:12]}: no replay evidence")
    for e in edges:
        if e["from"] not in nodes or e["to"] not in nodes:
            errors.append(f"edge endpoint not in graph: {e['from'][:12]}->{e['to'][:12]}")
        elif (e["type"] == "trusted-lemma"
              and nodes[e["to"]].get("role") in _ZERO_STEP_ROLES):
            errors.append(f"trusted-lemma edge targets zero-step node {e['to'][:12]}")

    ts = TopologicalSorter()
    for h in nodes:
        ts.add(h)
    for e in edges:
        if e["type"] == "trusted-lemma" and e["from"] in nodes and e["to"] in nodes:
            ts.add(e["from"], e["to"])
    order: list[str] = []
    try:
        order = list(ts.static_order())  # children before parents
    except CycleError as exc:
        errors.append("trusted-lemma subgraph has a cycle: "
                      + " -> ".join(h[:12] for h in exc.args[1]))

    roots = set(manifest.get("roots", {}))
    graph_roots = {h for h, n in nodes.items() if n.get("root")}
    if roots != graph_roots:
        errors.append("MANIFEST roots do not match graph roots")
    record = _read_json(bundle / "assumptions" / "oracle-record.json")
    if set(record.get("roots", {})) != roots:
        errors.append("oracle record does not cover the MANIFEST roots")
    if not roots:
        errors.append("bundle has no roots")

    # P0-A program binding, re-derived bundle-only: every ROOT's <program> cell
    # must equal subject/runtime.bin. A root proving a property of a DIFFERENT
    # program than the installed subject is worthless (Hole 1). Non-roots are
    # not subject-bound (see freeze.py / bundle-spec §9). Cheap: text + a byte
    # compare, no prover.
    subject_bin = bundle / "subject" / "runtime.bin"
    if not subject_bin.is_file():
        errors.append("subject/runtime.bin missing — cannot check root program binding")
    else:
        subject_bytes = subject_bin.read_bytes()
        for h in sorted(roots):
            claim_path = bundle / "spec" / "claims" / f"{h}.k"
            if not claim_path.is_file():
                continue  # already reported as missing above
            reason = program_binding_error(claim_path.read_text(encoding="utf-8"),
                                           subject_bytes)
            if reason:
                n = nodes.get(h, {})
                errors.append(f"root {n.get('loop')}/{n.get('label')}: {reason}")

    # Bridge S<==D, re-derived bundle-only (structural + keccak; no prover): for
    # each abstract-summary node, re-check that its bridge discharges it — S
    # abstracts only its <program>, the anti-proxy binding S<=>B holds, and
    # code-identity keccak256(external_code[callee]) == the declared code_hash.
    # D and B are replayed in step 5 like any node; this is the structural half
    # that a self-consistent hash tree does not launder (cf. root program
    # binding). Same tcg.bridge verdict freeze and `graph check` computed.
    env_path = bundle / "subject" / "environment.json"
    environment = _read_json(env_path) if env_path.is_file() else {}

    def _bridge_claim_text(h: str) -> str:
        return (bundle / "spec" / "claims" / f"{h}.k").read_text(encoding="utf-8")

    for h, n in nodes.items():
        if is_bridge_node(n):
            berrs, _ = bridge_structural_errors(
                h, nodes, _bridge_claim_text, environment)
            errors.extend(berrs)
    if errors:
        return _fail("4-graph", errors)
    bridge_count = sum(1 for n in nodes.values() if is_bridge_node(n))
    bridge_note = (f"; {bridge_count} abstract-summary node(s) bridge-discharged "
                   "S<==D") if bridge_count else ""
    print(f"step 4 graph: OK ({len(nodes)} node(s), {len(roots)} root(s); "
          f"root <program> cells bind to subject/runtime.bin{bridge_note})")

    # --- Step 5: replay ----------------------------------------------------
    definition = args.definition or lock.get("definition")
    if not definition:
        print("verify: no kompiled definition for replay; pass "
              "--definition PATH, or add \"definition\" to the bundle's "
              "theory/toolchain.lock", file=sys.stderr)
        return int(Exit.USAGE)
    includes = list(args.include or []) + list(lock.get("includes", []))
    retries = int(lock.get("replay", {}).get("retries", 0))
    timeout = lock.get("replay", {}).get("timeout_seconds", 3600)

    children: dict[str, list[str]] = {h: [] for h in nodes}
    for e in edges:
        if e["type"] == "trusted-lemma":
            children[e["from"]].append(e["to"])

    def claim_text(h: str) -> str:
        return (bundle / "spec" / "claims" / f"{h}.k").read_text(encoding="utf-8")

    # Replay modules go to a scratch dir: verify never writes into the bundle.
    scratch = Path(tempfile.mkdtemp(prefix="tcg-replay-"))

    for idx, h in enumerate(order, 1):
        # An abstract-summary node is discharged by its bridge S<==D (step 4),
        # never by direct replay — its symbolic <program> cannot Accept. It is
        # still injected as a trusted child into its caller's replay below
        # (children[caller] includes it), exactly as at prove time; its
        # soundness rides on the bridge, which D and B (replayed here) close.
        if is_bridge_node(nodes[h]):
            print(f"step 5 replay [{idx}/{len(order)}]: "
                  f"{nodes[h]['loop']}/{nodes[h]['label']} bridge-discharged "
                  "(S<==D; not replayed directly)")
            continue
        goal = claim_text(h)
        reqs, imps = module_header(goal)
        trusted_bodies = []
        for c in children[h]:
            child_text = claim_text(c)
            creqs, cimps = module_header(child_text)
            reqs += [r for r in creqs if r not in reqs]
            imps += [i for i in cimps if i not in imps]
            trusted_bodies.append(extract_body(child_text))
        module_text = assemble_prove_module(
            "REPLAY-NODE", reqs, imps, trusted_bodies, [extract_body(goal)])
        spec = scratch / f"replay-{h[:12]}.k"
        spec.write_text(module_text, encoding="utf-8")

        argv = ["kprove", str(spec), "--definition", str(definition),
                "--spec-module", "REPLAY-NODE"]
        for inc in includes:
            argv += ["-I", str(inc)]

        # Retries absorb solver nondeterminism on an UNDECIDED result only --
        # Accept and Refute are both final on the first attempt. Re-running a
        # deterministic prover against the same fixed claim hoping a genuine
        # structural refutation goes away on attempt 2 would not be a retry,
        # it would be forum shopping.
        verdict = ucls = hint = None
        for attempt in range(retries + 1):
            timed_out = False
            try:
                proc = subprocess.run(argv, capture_output=True, text=True,
                                      timeout=timeout)
                returncode, log = proc.returncode, proc.stdout + proc.stderr
            except subprocess.TimeoutExpired as e:
                returncode, log, timed_out = (
                    -1, to_text(e.stdout) + to_text(e.stderr), True)
            except FileNotFoundError:
                print("verify: kprove not found on PATH; install/activate the "
                      "pinned K toolchain (see theory/toolchain.lock in the "
                      "bundle)", file=sys.stderr)
                return int(Exit.USAGE)
            verdict, ucls, hint = classify(returncode, log, timed_out)
            if verdict != "Unknown":
                break
        spec.unlink(missing_ok=True)

        n = nodes[h]
        if verdict == "Accept":
            print(f"step 5 replay [{idx}/{len(order)}]: "
                  f"{n['loop']}/{n['label']} Accept")
            continue
        if verdict == "Unknown":
            hint_note = f" — {hint}" if hint else ""
            print(f"verify[5-replay]: {n['loop']}/{n['label']} Unknown({ucls}) "
                  f"after {retries + 1} attempt(s){hint_note} — conservative "
                  "refusal", file=sys.stderr)
            print("verify: certificate UNVERIFIED at step 5-replay — could "
                  "not decide (this is not a refutation); raise "
                  "replay.timeout_seconds/retries in toolchain.lock and "
                  "re-run `tcg verify`, or investigate the claim",
                  file=sys.stderr)
            return int(Exit.UNKNOWN)
        # verdict == "Refute": a genuine structural counterexample.
        return _fail("5-replay",
                     [f"{n['loop']}/{n['label']} did not replay to Accept "
                      "(Refute — prover reached a state that does not "
                      "unify with the claimed destination)"])

    print(f"step 5 replay: OK ({len(order)} node(s) re-proved)")

    # --- Step 5v: vacuity re-derivation over roots -------------------------
    # P0-B, bundle-only: for each ROOT, falsify its postcondition (ensures
    # false) and re-prove the mutant. If the falsified claim STILL proves
    # Accept, the root's antecedent is infeasible ⇒ the proof is vacuous ⇒
    # REFUSE. verify does NOT trust the bundled evidence/vacuity record; it
    # re-derives the mutant from the root claim text and re-runs the prover.
    # Single attempt, no retry: Accept is the only outcome that flags vacuity;
    # Refute/Unknown both mean "not vacuously provable" (the safe direction).
    for h in sorted(roots):
        goal = claim_text(h)
        reqs, imps = module_header(goal)
        mutant = assemble_prove_module(
            "REPLAY-VACUITY", reqs, imps, [], [falsify_body(extract_body(goal))])
        spec = scratch / f"vacuity-{h[:12]}.k"
        spec.write_text(mutant, encoding="utf-8")
        argv = ["kprove", str(spec), "--definition", str(definition),
                "--spec-module", "REPLAY-VACUITY"]
        for inc in includes:
            argv += ["-I", str(inc)]
        timed_out = False
        try:
            proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
            returncode, log = proc.returncode, proc.stdout + proc.stderr
        except subprocess.TimeoutExpired as e:
            returncode, log, timed_out = -1, to_text(e.stdout) + to_text(e.stderr), True
        except FileNotFoundError:
            print("verify: kprove not found on PATH; install/activate the "
                  "pinned K toolchain (see theory/toolchain.lock in the "
                  "bundle)", file=sys.stderr)
            return int(Exit.USAGE)
        spec.unlink(missing_ok=True)
        verdict, _, _ = classify(returncode, log, timed_out)
        n = nodes[h]
        if verdict == "Accept":
            return _fail("5-vacuity",
                         [f"root {n['loop']}/{n['label']} is VACUOUS — its "
                          "falsified form (ensures false) still proves Accept, "
                          "so the antecedent is infeasible and the proof is "
                          "empty; a vacuous proof is a refusal, never a pass"])
        print(f"step 5v vacuity [{n['loop']}/{n['label']}]: OK "
              f"(falsified form does not prove: {verdict})")

    print("certificate holds; step 6 is yours: `tcg roots <bundle>`")
    return int(Exit.OK)
