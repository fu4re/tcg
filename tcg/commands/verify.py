"""`tcg verify <bundle>` — the verifier protocol, bundle-only.

Reads nothing but the bundle (plus a kompiled definition for replay). Steps
are strictly ordered; the first failing step refuses the certificate.

1. Integrity  — recompute the hash tree from MANIFEST.json (covers vendored
                deps/** too — every dep file is hash-linked in the caller
                MANIFEST).
2. Identity   — subject identity is machine-checkable but needs chain access;
                printed as a verifier action, per the trust manifest.
3. Theory     — re-hash vendored patches against toolchain.lock.
4. Graph      — structural discipline over bundle content only, PLUS program
                binding (P0-A): every root's <program> cell must equal
                subject/runtime.bin, re-derived bundle-only (text + byte
                compare, no prover). A root about a different program than the
                installed subject is refused here. For a cross-bundle (REUSE)
                summary node, step 4 ALSO recurses into each vendored dep
                bundle deps/<callee_root>/ and runs the FULL protocol on it
                first (post-order) — an unverifiable dep refuses the caller —
                then re-derives the linker's structural discharge (dep-root
                membership, code-identity, and the anti-proxy binding S<=>D).
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

The prover invocation is factored behind a `run_prover` seam so the cross-bundle
recursion and its control flow can be exercised in a unit test WITHOUT kprove
(production always calls the real subprocess seam). The seam is a test aid only:
a fake that Accepts everything makes step 5v (vacuity) refuse, never pass, so it
cannot manufacture a false green.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from tcg.assume import (
    consistency_errors, is_assume_node, roots_injecting,
    structural_errors as assume_structural_errors,
)
from tcg.bridge import is_bridge_node, structural_errors as bridge_structural_errors
from tcg.claims import (
    assemble_prove_module, extract_body, falsify_body, module_header,
    program_binding_error, sha256_text,
)
from tcg.outcome import Exit
from tcg.verdict import classify, to_text
from tcg.xbridge import (
    is_xbridge_node, structural_errors as xbridge_structural_errors,
    xbundle_deps,
)

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


def _subprocess_prover(argv: list[str], timeout: int) -> tuple[int, str, bool]:
    """Default prover seam: run kprove, return (returncode, log, timed_out).
    Raises FileNotFoundError if kprove is not on PATH (the caller maps that to
    a USAGE exit). This is the ONLY place production verify shells out; the
    recursion and unit tests thread a substitute through `run_prover`."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, proc.stdout + proc.stderr, False
    except subprocess.TimeoutExpired as e:
        return -1, to_text(e.stdout) + to_text(e.stderr), True


def _prove(run_prover, argv: list[str], timeout: int, retries: int):
    """Run `argv` up to retries+1 times, absorbing an UNDECIDED result only --
    Accept and Refute are both final on the first attempt (re-running a
    deterministic prover against the same fixed claim hoping a genuine
    refutation goes away would be forum shopping, not a retry). Returns
    (verdict, unknown_class, hint) from the shared judge tcg.verdict.classify.
    May raise FileNotFoundError (kprove missing)."""
    verdict = ucls = hint = None
    for _ in range(retries + 1):
        returncode, log, timed_out = run_prover(argv, timeout)
        verdict, ucls, hint = classify(returncode, log, timed_out)
        if verdict != "Unknown":
            break
    return verdict, ucls, hint


def run(args) -> int:
    """CLI entry: verify the bundle with the real (subprocess) prover seam."""
    return verify_bundle(
        Path(args.bundle),
        definition_arg=args.definition,
        includes_arg=args.include,
        strict=getattr(args, "strict", False),
        run_prover=_subprocess_prover,
    )


def verify_bundle(bundle: Path, *, definition_arg=None, includes_arg=None,
                  strict=False, run_prover=_subprocess_prover,
                  _seen: set | None = None) -> int:
    """The verifier protocol on one bundle. Recurses (post-order) into every
    vendored cross-bundle dep. `_seen` dedups deps already verified OK in this
    run (content-addressing already forbids a cycle). `run_prover(argv, timeout)
    -> (returncode, log, timed_out)` is the injectable prover boundary.

    `strict`: refuse (exit 3) any bundle carrying an author-chosen typed-stub
    assumption (Mechanism B) — "the auditor asked for a fully-discharged
    certificate". Propagated into deps so a stub hidden in a vendored callee
    also refuses. Default False: a stub bundle exits 0 but with a prominent
    trailing ⚠ section enumerating each load-bearing assumption."""
    if _seen is None:
        _seen = set()
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

    # 4a. Cross-bundle recursion (REUSE, verify obligation #1): verify every
    # vendored dep bundle FULLY, post-order, BEFORE the caller's own replay. A
    # dep that does not itself verify refuses the caller — and the dep's exit
    # code is propagated verbatim, so a dep Unknown stays Unknown (2) rather
    # than being laundered into a Refute (3): "could not verify the dep" is not
    # "the dep refuted".
    xdeps = sorted(xbundle_deps(nodes))
    if xdeps:
        print(f"step 4 (deps): {len(xdeps)} cross-bundle dep(s) — verifying each "
              "with the full protocol first (post-order)")
        for cr in xdeps:
            if cr in _seen:
                print(f"step 4 (deps): dep {cr[:12]} already verified in this run")
                continue
            dep_dir = bundle / "deps" / cr
            if not (dep_dir / "MANIFEST.json").is_file():
                return _fail("4-deps", [
                    f"cross-bundle dep deps/{cr}/ is absent (no MANIFEST) — the "
                    "caller is not self-contained; re-freeze to vendor it"])
            print(f"step 4 (deps): --> recursing into deps/{cr[:12]}/")
            rc = verify_bundle(dep_dir, definition_arg=definition_arg,
                               includes_arg=includes_arg, strict=strict,
                               run_prover=run_prover, _seen=_seen)
            if rc != int(Exit.OK):
                print(f"verify[4-deps]: dep {cr[:12]} did NOT itself verify "
                      f"(exit {rc}) — a caller cannot reuse an unverified callee; "
                      "REFUSING the caller", file=sys.stderr)
                return rc
            _seen.add(cr)
            print(f"step 4 (deps): <-- dep {cr[:12]} verified OK")

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
        # An abstract-summary node (in-graph bridge, cross-bundle linker, OR
        # typed stub) carries no replay evidence — it is discharged structurally
        # (bridge/linker) or by a named assumption (stub), never directly proved
        # (checked below + in step 5).
        if (not is_bridge_node(n) and not is_assume_node(n)
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

    # Bridge / linker discharge, re-derived bundle-only (structural + keccak; no
    # prover): for each abstract-summary node, re-check that it is discharged —
    # S abstracts only its <program>, the anti-proxy binding holds, and
    # code-identity keccak256(callee code) == the declared code_hash. In-graph
    # bridge nodes bind against their at-P proof B; cross-bundle (REUSE) nodes
    # bind against the vendored dep's root D (deps/<callee_root>/), which the
    # 4a recursion just re-verified. Same tcg.bridge / tcg.xbridge verdict that
    # freeze and `graph check` computed (three-way agreement).
    env_path = bundle / "subject" / "environment.json"
    environment = _read_json(env_path) if env_path.is_file() else {}

    def _bridge_claim_text(h: str) -> str:
        return (bundle / "spec" / "claims" / f"{h}.k").read_text(encoding="utf-8")

    for h, n in nodes.items():
        if is_xbridge_node(n):
            berrs, _ = xbridge_structural_errors(
                h, nodes, _bridge_claim_text, environment, bundle / "deps")
            errors.extend(berrs)
        elif is_bridge_node(n):
            berrs, _ = bridge_structural_errors(
                h, nodes, _bridge_claim_text, environment)
            errors.extend(berrs)
        elif is_assume_node(n):
            # Typed stub (STUB): structural half of its discharge (same pure
            # tcg.assume verdict graph check / freeze computed). The frame is
            # SURFACED, never interpreted — validating it would be unsound.
            errors.extend(assume_structural_errors(h, nodes, _bridge_claim_text))

    # Ledger consistency (STUB): every assume-node's ledger_id must be present
    # in trust-manifest.json, and every A_callee_* entry must be referenced by
    # some assume-node. A missing or orphan entry REFUSES — a stub is never a
    # silent pass, and the ledger cannot drift from the graph. (graph check
    # cannot run this — the ledger only exists post-freeze; freeze writes it
    # consistent by construction, verify re-checks it.) A zero-stub bundle with
    # no A_callee_* entries yields no errors: existing bundles are unaffected.
    tm_path = bundle / "assumptions" / "trust-manifest.json"
    trust_manifest = _read_json(tm_path) if tm_path.is_file() else {}
    errors.extend(consistency_errors(nodes, trust_manifest))
    if errors:
        return _fail("4-graph", errors)
    bridge_count = sum(1 for n in nodes.values()
                       if is_bridge_node(n) and not is_xbridge_node(n))
    xbridge_count = sum(1 for n in nodes.values() if is_xbridge_node(n))
    disc = []
    if bridge_count:
        disc.append(f"{bridge_count} abstract-summary node(s) bridge-discharged S<==D")
    if xbridge_count:
        disc.append(f"{xbridge_count} node(s) linker-discharged S<==D (REUSE)")
    disc_note = ("; " + "; ".join(disc)) if disc else ""
    print(f"step 4 graph: OK ({len(nodes)} node(s), {len(roots)} root(s); "
          f"root <program> cells bind to subject/runtime.bin{disc_note})")

    # --- Step 5: replay ----------------------------------------------------
    definition = definition_arg or lock.get("definition")
    if not definition:
        print("verify: no kompiled definition for replay; pass "
              "--definition PATH, or add \"definition\" to the bundle's "
              "theory/toolchain.lock", file=sys.stderr)
        return int(Exit.USAGE)
    includes = list(includes_arg or []) + list(lock.get("includes", []))
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

    try:
        for idx, h in enumerate(order, 1):
            # An abstract-summary node is discharged structurally (step 4) or by
            # a named assumption (stub), never by direct replay — its symbolic
            # <program> cannot Accept. It is still injected as a trusted child
            # into its caller's replay below (children[caller] includes it),
            # exactly as at prove time.
            if is_bridge_node(nodes[h]) or is_assume_node(nodes[h]):
                if is_assume_node(nodes[h]):
                    how = "assumed-callee (STUB; author-chosen, not replayed)"
                elif is_xbridge_node(nodes[h]):
                    how = "linker-discharged (REUSE; dep re-verified)"
                else:
                    how = "bridge-discharged (S<==D; not replayed directly)"
                print(f"step 5 replay [{idx}/{len(order)}]: "
                      f"{nodes[h]['loop']}/{nodes[h]['label']} {how}")
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

            verdict, ucls, hint = _prove(run_prover, argv, timeout, retries)
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

        # --- Step 5v: vacuity re-derivation over roots ---------------------
        # P0-B, bundle-only: for each ROOT, falsify its postcondition (ensures
        # false) and re-prove the mutant. If the falsified claim STILL proves
        # Accept, the root's antecedent is infeasible ⇒ the proof is vacuous ⇒
        # REFUSE. verify does NOT trust the bundled evidence/vacuity record; it
        # re-derives the mutant from the root claim text and re-runs the prover.
        # Single attempt, no retry: Accept is the only outcome that flags
        # vacuity; Refute/Unknown both mean "not vacuously provable" (safe).
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
            verdict, _, _ = _prove(run_prover, argv, timeout, 0)
            spec.unlink(missing_ok=True)
            n = nodes[h]
            if verdict == "Accept":
                return _fail("5-vacuity",
                             [f"root {n['loop']}/{n['label']} is VACUOUS — its "
                              "falsified form (ensures false) still proves Accept, "
                              "so the antecedent is infeasible and the proof is "
                              "empty; a vacuous proof is a refusal, never a pass"])
            print(f"step 5v vacuity [{n['loop']}/{n['label']}]: OK "
                  f"(falsified form does not prove: {verdict})")
    except FileNotFoundError:
        print("verify: kprove not found on PATH; install/activate the pinned K "
              "toolchain (see theory/toolchain.lock in the bundle)",
              file=sys.stderr)
        return int(Exit.USAGE)

    # --- Typed-stub assumptions (STUB, Mechanism B) ------------------------
    # Fires ONLY after steps 1–5v pass — a stub bundle that also fails
    # integrity/replay/vacuity/consistency is refused for THAT reason first
    # (above). A bundle with ZERO assume-nodes reaches neither branch and prints
    # nothing extra (hard regression requirement: no behavior change).
    assume_pairs = [(h, n) for h, n in nodes.items() if is_assume_node(n)]
    if assume_pairs and strict:
        return _fail("strict", [
            f"{len(assume_pairs)} author-chosen typed-stub assumption(s) present, "
            "but --strict asked for a fully-discharged certificate — an opaque "
            "callee summary is ASSUMED, not proved over the callee's code. "
            "Re-run without --strict to accept the bundle WITH its load-bearing "
            "assumption(s) (they will be enumerated)."])

    print("certificate holds; step 6 is yours: `tcg roots <bundle>`")
    if assume_pairs:
        print(f"\n⚠ {len(assume_pairs)} author-chosen assumption(s) "
              "load-bearing:")
        for h, n in sorted(assume_pairs,
                           key=lambda p: (nodes[p[0]]["loop"], nodes[p[0]]["label"])):
            a = n["assume"]
            lb = roots_injecting(h, nodes, edges)
            lb_names = ", ".join(f"{nodes[r]['loop']}/{nodes[r]['label']}"
                                 for r in lb) or "(none — injected by no root)"
            print(f"  - callee {a['callee_address']}  (ledger {a['ledger_id']})")
            print(f"      frame: {a['frame']}")
            print(f"      load-bearing for root(s): {lb_names}")
        print("  these are NOT discharged over the callee's code; re-run with "
              "--strict to refuse any bundle that carries one.")
    return int(Exit.OK)
