"""`tcg verify <bundle>` — the verifier protocol, bundle-only.

Reads nothing but the bundle (plus a kompiled definition for replay). Steps
are strictly ordered; the first failing step refuses the certificate.

1. Integrity  — recompute the hash tree from MANIFEST.json.
2. Identity   — subject identity is machine-checkable but needs chain access;
                printed as a verifier action, per the trust manifest.
3. Theory     — re-hash vendored patches against toolchain.lock.
4. Graph      — structural discipline over bundle content only.
5. Replay     — topological re-proof of every node, children as trusted.
                Unknown is refusal (retries per toolchain.lock).

Step 6 (reading the roots) is `tcg roots`.
"""
from __future__ import annotations

import re
import subprocess
import sys
import tempfile
from graphlib import CycleError, TopologicalSorter
from pathlib import Path

from tcg.claims import assemble_prove_module, extract_body, module_header, sha256_text
from tcg.outcome import Exit

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
    print(f"verify: certificate REFUSED at step {step}", file=sys.stderr)
    return int(Exit.REFUSED)


def run(args) -> int:
    bundle = Path(args.bundle)
    manifest_path = bundle / "MANIFEST.json"
    if not manifest_path.is_file():
        print(f"tcg: no MANIFEST.json in {bundle}", file=sys.stderr)
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
        if not (bundle / "evidence" / "replay" / f"{h}.json").is_file():
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
    if errors:
        return _fail("4-graph", errors)
    print(f"step 4 graph: OK ({len(nodes)} node(s), {len(roots)} root(s))")

    # --- Step 5: replay ----------------------------------------------------
    definition = args.definition or lock.get("definition")
    if not definition:
        print("verify: no kompiled definition for replay; pass --definition",
              file=sys.stderr)
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

        verdict = None
        for attempt in range(retries + 1):
            try:
                proc = subprocess.run(argv, capture_output=True, text=True,
                                      timeout=timeout)
            except subprocess.TimeoutExpired:
                verdict = "unknown"
                continue
            except FileNotFoundError:
                print("verify: kprove not found on PATH", file=sys.stderr)
                return int(Exit.USAGE)
            verdict = "accept" if proc.returncode == 0 else "failed"
            break
        spec.unlink(missing_ok=True)

        n = nodes[h]
        if verdict == "accept":
            print(f"step 5 replay [{idx}/{len(order)}]: "
                  f"{n['loop']}/{n['label']} Accept")
            continue
        if verdict == "unknown":
            print(f"verify[5-replay]: {n['loop']}/{n['label']} Unknown after "
                  f"{retries + 1} attempt(s) — conservative refusal", file=sys.stderr)
            print("verify: certificate REFUSED at step 5-replay", file=sys.stderr)
            return int(Exit.UNKNOWN)
        return _fail("5-replay",
                     [f"{n['loop']}/{n['label']} did not replay to Accept"])

    print(f"step 5 replay: OK ({len(order)} node(s) re-proved)")
    print("certificate holds; step 6 is yours: `tcg roots <bundle>`")
    return int(Exit.OK)
