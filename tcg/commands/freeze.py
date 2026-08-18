"""`tcg freeze` — assemble the bundle: hash tree + MANIFEST.

Freeze refuses unless the workspace is fully coherent:

- `tcg graph check` passes;
- every graph node belongs to an Accepted workspace and has Accept evidence;
- the oracle record exists and covers exactly the current roots (drift check);
- subject/runtime.bin and subject/environment.json exist.

The bundle carries only certificate material plus `nav/` outside the hash
tree. The certificate identity is the SHA-256 of MANIFEST.json.
"""
from __future__ import annotations

import shutil
import sys
from pathlib import Path

from tcg.commands.graph import check_graph
from tcg.outcome import Exit
from tcg.workspace import (
    WORKSPACE_DIR, WorkspaceError, find_root, load_graph, load_loop, read_json,
    sha256_file, write_json,
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

    # Every node — not only the root-reachable ones — must be Accepted with
    # evidence: the bundle carries Accept material only.
    for h, n in nodes.items():
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

    # Oracle record must cover exactly the current roots (no drift since H).
    roots = {h for h, n in nodes.items() if n.get("root")}
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
    for h in nodes:
        put(f"spec/claims/{h}.k", root / "spec" / "claims" / f"{h}.k")
        put(f"evidence/replay/{h}.json", root / "evidence" / "replay" / f"{h}.json")
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

    # Trust manifest: named assumptions with statuses. Facts not discharged in
    # this workspace are listed as assumed — never silently.
    write_json(bundle / "assumptions" / "trust-manifest.json", {
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
    })

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
