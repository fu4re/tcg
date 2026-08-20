"""`tcg freeze` — assemble the bundle: hash tree + MANIFEST.

Freeze refuses unless the workspace is fully coherent:

- `tcg graph check` passes (which now includes ROOT <program> binding to
  subject/runtime.bin — P0-A, Hole 1);
- every graph node belongs to an Accepted workspace and has Accept evidence;
- every ROOT has passed a non-vacuous vacuity probe (P0-B, Hole 1);
- the oracle record exists and covers exactly the current roots (drift check);
- subject/runtime.bin and subject/environment.json exist.

The bundle carries only certificate material plus `nav/` outside the hash
tree. The certificate identity is the SHA-256 of MANIFEST.json.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tcg.assume import (
    is_assume_node, ledger_entry, roots_injecting,
    structural_errors as assume_structural_errors,
)
from tcg.bridge import is_bridge_node, structural_errors as bridge_structural_errors
from tcg.commands.graph import check_graph
from tcg.outcome import Exit
from tcg.workspace import (
    WORKSPACE_DIR, WorkspaceError, find_root, load_graph, load_loop, read_json,
    sha256_file, write_json,
)
from tcg.xbridge import (
    is_xbridge_node, structural_errors as xbridge_structural_errors,
    xbundle_deps,
)


def run(args) -> int:
    try:
        root = find_root()
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    errors = check_graph(root)
    graph = load_graph(root)
    nodes = graph["nodes"]

    environment = {}
    env_path = root / "subject" / "environment.json"
    if env_path.is_file():
        try:
            environment = read_json(env_path)
        except ValueError:
            environment = {}

    def claim_text_of(h: str) -> str:
        return (root / "spec" / "claims" / f"{h}.k").read_text(encoding="utf-8")

    # Every node — not only the root-reachable ones — must be Accepted with
    # evidence: the bundle carries Accept material only. The one exception is an
    # abstract-summary node (free <program>): it can never be Accepted, so it is
    # discharged by its bridge S<==D instead (its concrete proof D and bridge-at-P
    # proof B are ordinary nodes in this same loop, so they still get the
    # Accept+evidence gate below). The bridge structural check is re-run here so
    # freeze and `tcg graph check` agree.
    for h, n in nodes.items():
        if is_xbridge_node(n):
            # Cross-bundle (REUSE) summary: discharged by a vendored callee
            # bundle under deps/<callee_root>/ (checked against the WORKSPACE
            # deps/ tree here; the same tree is copied into the bundle below, so
            # verify re-derives an identical verdict). No Accept/evidence gate —
            # like any bridge node, S can never Accept.
            berrs, _ = xbridge_structural_errors(
                h, nodes, claim_text_of, environment, root / "deps")
            errors.extend(berrs)
            continue
        if is_bridge_node(n):
            berrs, _ = bridge_structural_errors(
                h, nodes, claim_text_of, environment)
            errors.extend(berrs)
            continue
        if is_assume_node(n):
            # Typed stub (STUB): an opaque callee summary discharged by a named
            # assumption. Like a bridge node, S can never Accept — so no
            # Accept/evidence gate; its discharge is the structural check + the
            # ledger entry emitted below.
            errors.extend(assume_structural_errors(h, nodes, claim_text_of))
            continue
        try:
            state = load_loop(root, n["loop"])["state"]
        except WorkspaceError:
            state = "missing"
        if state != "Accepted":
            errors.append(f"node {n['loop']}/{n['label']} is {state}, "
                          f"not Accepted — run `tcg prove {n['loop']}`")
        if not (root / "evidence" / "replay" / f"{h}.json").is_file():
            errors.append(f"node {n['loop']}/{n['label']} has no replay "
                          f"evidence — re-run `tcg prove {n['loop']}` "
                          "(evidence is written on Accept)")

    roots = {h for h, n in nodes.items() if n.get("root")}

    # P0-A program binding is enforced inside check_graph (above), so freeze and
    # `tcg graph check` agree. Here we add the P0-B vacuity gate, per ROOT: every
    # root must carry a non-vacuous probe record. Non-root nodes carry no vacuity
    # requirement — vacuity is a root property (a vacuous lemma is useless, not
    # unsound). See docs/bundle-spec.md §8-9 and docs/findings/0002.
    vac_dir = root / WORKSPACE_DIR / "vacuity"
    for h in sorted(roots):
        n = nodes[h]
        vac_rec = vac_dir / f"{h}.json"
        if not vac_rec.is_file():
            errors.append(f"root {n['loop']}/{n['label']} has no vacuity probe — "
                          f"run `tcg vacuity {n['loop']}` (a root must pass the "
                          "antecedent-reachability probe before it can be frozen)")
        elif read_json(vac_rec).get("vacuous"):
            errors.append(f"root {n['loop']}/{n['label']} was flagged VACUOUS by "
                          "the vacuity probe (its antecedent is infeasible — the "
                          "proof is empty); fix the claim and re-prove")

    # Oracle record must cover exactly the current roots (no drift since H).
    record_path = root / "assumptions" / "oracle-record.json"
    if not record_path.is_file():
        errors.append("no oracle record; run `tcg approve --reviewer <name>`")
    else:
        approved = set(read_json(record_path).get("roots", {}))
        if approved != roots:
            errors.append("oracle record does not match current roots; "
                          "re-run `tcg approve --reviewer <name>`")

    if not (root / "subject" / "runtime.bin").is_file():
        errors.append("missing subject/runtime.bin; run "
                      "`tcg subject set --runtime <path>`")
    if not (root / "subject" / "environment.json").is_file():
        errors.append("missing subject/environment.json; run "
                      "`tcg subject set --runtime <path> --environment <path>` "
                      "(--runtime alone writes a default if none exists)")

    if errors:
        for msg in errors:
            print(f"freeze: {msg}", file=sys.stderr)
        print(f"freeze: REFUSED ({len(errors)} violation(s)); "
              "`tcg status` shows what's next per loop", file=sys.stderr)
        return int(Exit.REFUSED)

    bundle = root / "bundle"
    if bundle.exists():
        print("freeze: bundle/ already exists; `rm -rf bundle/` and re-run, "
              "or inspect it with `tcg roots bundle`", file=sys.stderr)
        return int(Exit.USAGE)

    def put(rel: str, src: Path) -> None:
        dst = bundle / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)

    put("subject/runtime.bin", root / "subject" / "runtime.bin")
    put("subject/environment.json", root / "subject" / "environment.json")
    for h, n in nodes.items():
        put(f"spec/claims/{h}.k", root / "spec" / "claims" / f"{h}.k")
        # An abstract-summary node has no replay evidence (it is bridge- or
        # stub-discharged, never directly proved); its claim text still travels
        # so verify can re-derive its discharge and inject S into its caller's
        # replay.
        if not is_bridge_node(n) and not is_assume_node(n):
            put(f"evidence/replay/{h}.json",
                root / "evidence" / "replay" / f"{h}.json")
    # Vacuity records travel with the roots (in the hash tree): they record the
    # probe that was run, and verify re-derives the probe itself — it does not
    # trust the record — but the record makes the check auditable and pins the
    # verdict the freeze gate saw. (Roots only; non-roots are not subject-bound
    # and carry no vacuity requirement.)
    for h in sorted(roots):
        put(f"evidence/vacuity/{h}.json", vac_dir / f"{h}.json")
    put("spec/interfaces.json", root / "spec" / "interfaces.json")
    put("spec/graph.json", root / "spec" / "graph.json")
    put("theory/toolchain.lock", root / WORKSPACE_DIR / "toolchain.lock")
    theory = root / "theory"
    if theory.is_dir():
        for src in sorted(p for p in theory.rglob("*") if p.is_file()):
            put(f"theory/{src.relative_to(theory)}", src)
    put("assumptions/oracle-record.json", record_path)
    annotations = root / "assumptions" / "annotations.json"
    if annotations.is_file():
        put("assumptions/annotations.json", annotations)
    else:
        write_json(bundle / "assumptions" / "annotations.json", {})

    # Vendor each cross-bundle (REUSE) dep sub-bundle into deps/<callee_root>/.
    # COPIED, not referenced by a remote path — `tcg verify <caller>` must need
    # nothing but the caller bundle. copytree brings the dep's own deps/ subtree
    # along (a content-addressed DAG). Each vendored MANIFEST is re-asserted to
    # hash to its declared <callee_root> (check_graph already gated this; this is
    # the belt-and-braces integrity assertion at copy time). Every copied file
    # lands in the hash tree below like any other bundle file, so the caller
    # MANIFEST hash-links the whole dep (integrity step 1 covers it).
    for callee_root in sorted(xbundle_deps(nodes)):
        src = root / "deps" / callee_root
        dst = bundle / "deps" / callee_root
        shutil.copytree(src, dst)
        got = sha256_file(dst / "MANIFEST.json")
        if got != callee_root:
            print(f"freeze: vendored dep {callee_root} MANIFEST hashes to {got}, "
                  "not its declared callee_root — refusing", file=sys.stderr)
            shutil.rmtree(bundle)
            return int(Exit.REFUSED)

    # Trust manifest: named assumptions with statuses. Facts not discharged in
    # this workspace are listed as assumed — never silently. The vendored,
    # pinned prover patches (theory/patches/*.diff, travelling in the hash tree
    # above) each add a named trusted input, enumerated here so no simplification
    # lemma or ghost cell enters the trusted base unlisted (bundle-spec §7).
    patch_files = sorted(
        f"theory/patches/{p.name}"
        for p in (root / "theory" / "patches").glob("*.diff")
    ) if (root / "theory" / "patches").is_dir() else []
    manifest_data = {
        "semantics": "vendored" if (bundle / "theory" / "semantics").is_dir()
                     else "assumed: semantics not vendored in this bundle",
        "subject_identity": "machine-checkable: compare keccak(subject/runtime.bin) "
                            "with the on-chain code hash",
        "reading_discipline": [
            "a prover Accept is read as a derivation in the prover's proof system",
            "a checker Accept on an implication is read as validity of that implication",
        ],
        "roots_semantics": "verifier-action-required: read the root claims; the "
                           "bundle does not transfer that they express the "
                           "property you care about",
        # Ghost instrumentation (theory/patches/ghost.diff). Additive [total]
        # cells/helpers that never appear on a stock rule's LHS; the transparency
        # obligation (does not alter non-ghost behavior) is listed, not silent.
        "A_instrumentation": {
            "status": "assumed: instrumentation transparency — the ghost-cell "
                      "patch adds only additive [total] cells/helpers and does "
                      "not alter non-ghost behavior; residual verification "
                      "obligation, pending",
            "patch": "theory/patches/ghost.diff",
        },
        # Simplification lemmas (theory/patches/lemmas.diff). The four vendored
        # submodules are baked into the definition's main module so symbolic
        # byte/word algebra reduces; each rule carries [simplification], so none
        # is a semantic rewrite step. See docs/findings/0004.
        "A_simp_lemmas": {
            "status": "proven-upstream (KEVM's own byte/int/bitwise "
                      "simplification lemmas, [simplification]-only; the "
                      "#addrFromPrivateKey concrete rule is deliberately "
                      "EXCLUDED) + assumed-consistent (bounded by "
                      "scripts/lemma-consistency.sh: no false identity proves; "
                      "the set is a large reusable core, NOT provably closed)",
            "modules": [
                "BITWISE-SIMPLIFICATION (lemmas/bitwise-simplification.k)",
                "BYTES-SIMPLIFICATION (lemmas/bytes-simplification.k)",
                "EVM-INT-SIMPLIFICATION (lemmas/evm-int-simplification.k)",
                "INT-SIMPLIFICATION (lemmas/int-simplification.k)",
            ],
            "patch": "theory/patches/lemmas.diff",
            "not_closed": "keccak stays an injectivity axiom (A_keccak); "
                          "nonlinear arithmetic stays a wall — these lemmas do "
                          "not discharge them",
            "upstream_intent": "fold the four submodules into a KEVM-provided "
                               "verification module and pin by KEVM version "
                               "instead of vendoring this driver",
        },
        "vendored_patches": patch_files,
    }

    # Bridge S<==D (docs/findings/0005). Listed ONLY when an abstract-summary
    # node is present, so non-bridge bundles' manifests are unchanged. Explicit
    # about what the bridge DISCHARGES (performed here) vs what stays ASSUMED.
    if any(is_bridge_node(n) for n in nodes.values()):
        manifest_data["bridge_S_from_D"] = {
            "status": "machine-checkable (structural + keccak, PERFORMED) + "
                      "verifier-action-required (on-chain code hash)",
            "what": "an abstract callee-summary node S (free <program>, cannot "
                    "itself Accept — a symbolic program stalls) is DISCHARGED by "
                    "the bridge S<==D: (1) a concrete callee proof D over code P, "
                    "(2) code-identity, and (3) a bridge-at-P proof B re-proving "
                    "S over P by execution.",
            "discharged": [
                "D and B both Accept over byte-identical <program> == "
                "external_code[callee] (replayed like any node)",
                "the anti-proxy binding S<=>B: B agrees with S cell-for-cell on "
                "every entry/effect the summary pins, carries S's exact storage "
                "delta, and is at least as general as S at entry — so a false or "
                "swapped summary cannot ride through (its B fails over P)",
                "code-identity: keccak256(external_code[callee]) == the declared "
                "code_hash, COMPUTED by the verifier (tcg/keccak.py), not assumed",
            ],
            "assumed": [
                "declared code_hash == the on-chain EXTCODEHASH at the callee "
                "address — a chain read, exactly the residual subject_identity "
                "leaves for the primary subject (verifier action)",
            ],
        }
    # Cross-bundle linker (REUSE). Present ONLY when a cross-bundle summary node
    # is present, so non-linker bundles' manifests are unchanged. The dep is
    # vendored (self-contained) and re-verified by the verifier's post-order
    # recursion; the only new residual assumption over the in-graph bridge is
    # NONE — code-identity is still COMPUTED, binding still PERFORMED.
    xdeps = xbundle_deps(nodes)
    if xdeps:
        links = []
        for h, n in nodes.items():
            if is_xbridge_node(n):
                cp = n["bridge"]["concrete_proof"]
                links.append({"summary": f"{n['loop']}/{n['label']}",
                              "dep": cp["dep"], "root": cp["root"]})
        manifest_data["link_S_from_dep"] = {
            "status": "machine-checkable (structural + keccak + dep re-verified, "
                      "PERFORMED) + verifier-action-required (on-chain code hash)",
            "what": "an abstract callee-summary node S (free <program>) is "
                    "DISCHARGED by REUSE of a vendored, independently-verified "
                    "callee bundle under deps/<callee_root>/ — the linker — "
                    "instead of a caller-side re-proof over the callee code P. "
                    "The dep's declared root plays the role of both D and B.",
            "discharged": [
                "the vendored dep is re-verified with the FULL verifier protocol "
                "(post-order recursion) before it is trusted — an unverifiable "
                "dep refuses the caller",
                "concrete_proof.root is one of the dep's declared roots and its "
                "<program> is the dep's own runtime P (a real execution proof "
                "over P, dep-verified)",
                "code-identity: keccak256(dep runtime) == the declared code_hash "
                "AND environment.external_code[callee] == the dep runtime "
                "byte-for-byte, COMPUTED by the verifier (tcg/keccak.py)",
                "the anti-proxy binding S<=>D: the dep root agrees with S "
                "cell-for-cell on every entry/effect S pins, carries S's exact "
                "storage delta, and is at least as general as S at entry — "
                "IDENTICAL strictness to the in-graph bridge (tcg.bridge)",
            ],
            "assumed": [
                "declared code_hash == the on-chain EXTCODEHASH at the callee "
                "address — a chain read, the same residual subject_identity "
                "leaves for the primary subject (verifier action). No caller-side "
                "re-execution over P is assumed away: the dep proved it, and the "
                "caller re-verified the dep.",
            ],
            "links": links,
        }
    # Typed-stub assumptions (STUB, Mechanism B). One A_callee_<addr> entry per
    # assume-node, present ONLY when an assume-node exists so existing bundles'
    # manifests are byte-unchanged. `status` marks it author-chosen and load-
    # bearing (distinct from the baseline A_keccak/A_simp_lemmas assumptions);
    # `load_bearing_for` names the roots whose proof injects this S. verify
    # re-checks that every assume-node's ledger_id is present here and that no
    # A_callee_* entry is orphaned (consistency) — a stub is never a silent pass.
    edges = graph.get("edges", [])
    for h, n in nodes.items():
        if is_assume_node(n):
            manifest_data[n["assume"]["ledger_id"]] = ledger_entry(
                n, roots_injecting(h, nodes, edges))
    write_json(bundle / "assumptions" / "trust-manifest.json", manifest_data)

    (bundle / "nav").mkdir()
    (bundle / "nav" / "report.md").write_text(
        "# Bundle report\n\nNon-certified narrative. Nothing under nav/ is part "
        "of the certificate; delete this directory and `tcg verify` is unchanged.\n",
        encoding="utf-8",
    )

    # Hash tree over everything except nav/ and the manifest itself.
    files = {
        str(p.relative_to(bundle)): sha256_file(p)
        for p in sorted(bundle.rglob("*"))
        if p.is_file() and "nav" not in p.relative_to(bundle).parts
    }
    manifest = bundle / "MANIFEST.json"
    write_json(manifest, {
        "cert_version": "1",
        "roots": {h: {"loop": nodes[h]["loop"], "label": nodes[h]["label"]}
                  for h in sorted(roots)},
        "files": files,
    })

    print(f"bundle frozen: {len(files)} file(s), {len(roots)} root(s)")
    print(f"certificate identity: sha256(MANIFEST.json) = {sha256_file(manifest)}")
    return int(Exit.OK)
