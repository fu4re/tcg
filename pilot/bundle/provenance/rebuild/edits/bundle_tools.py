#!/usr/bin/env python3
"""Copy every producer script that a deterministic ledger event executes (and
the in-repo modules those scripts import) into provenance/tools/, and write
provenance/tools/MAP.json: for each event and each script it ran, the path as
recorded, the hash recorded at that event (if any), the bundled copy and its
hash, and whether they are equal (then the bundled copy IS the script that
ran). Past ledger events are not rewritten. Run from the bundle root."""
import hashlib, json, pathlib, shutil

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

REPO = pathlib.Path("../..").resolve()
B = pathlib.Path("provenance/tools")
COPY = {  # recorded path (as in argv, relative to the bundle root or absolute) -> source -> bundled name
    "../tools/assemble_hard.py": ("../tools/assemble_hard.py", "assemble_hard.py"),
    "../tools/coverage.py": ("../tools/coverage.py", "coverage.py"),
    "../checker/run-claim.sh": ("../checker/run-claim.sh", "run-claim.sh"),
    "/home/vladimir/sheaf/tcg/pilot/tools/mutant_witness.py": ("../tools/mutant_witness.py", "mutant_witness.py"),
}
IMPORTS = {  # imported by the scripts above / by provenance/rebuild/run-controls.sh (the wrapper that issues the kevm-prove events)
    "tcg/__init__.py": "package marker of tcg, imported with tcg.keccak / tcg.claims",
    "tcg/keccak.py": "assemble_hard.py (keccak256_hex)",
    "tcg/claims.py": "assemble_hard.py spec/variant/witness (assemble_prove_module, canonicalize, falsify_body)",
    "tcg/verdict.py": "provenance/rebuild/run-controls.sh (classify)",
}
NOT_COPIED = {
    "pilot/verifier/tcgverify/": "imported by coverage.py and by assemble_hard.py tbase/rehash (verifier_hash); it is the `tcg-verifier` checker named in trusted_base.json, frozen and hashed by WS-A, not a producer tool",
    "KEVM inputs (~/pilot-checker/pins.json, evm-semantics tarball, extracted K source)": "stay outside the bundle by decision; L4 reports them as outside_bundle",
}
# Every version ever bundled is kept under provenance/tools/versions/<name>-<sha12><ext>,
# because the verifier stands a recorded input in by HASH from any bundle child:
# replacing a copy would orphan the events recorded with the earlier version.
V = B / "versions"
V.mkdir(parents=True, exist_ok=True)
for old_file in [p for p in B.rglob("*") if p.is_file() and V not in p.parents and p.name != "MAP.json"]:
    h = sha(old_file)[:12]
    keep = V / f"{old_file.stem}-{h}{old_file.suffix}"
    if not keep.exists():
        shutil.copy2(old_file, keep)
for d in [p for p in B.iterdir() if p != V]:
    shutil.rmtree(d) if d.is_dir() else d.unlink()
(B / "tcg").mkdir(parents=True)
bundled = {}
for rec, (src, name) in COPY.items():
    shutil.copy2(src, B / name)
    bundled[rec] = str(B / name)
for rel in IMPORTS:
    shutil.copy2(REPO / rel, B / rel)
shutil.copy2("provenance/rebuild/run-controls.sh", B / "run-controls.sh")
ALIASES = {"/home/vladimir/pilot-hard/edit_annotations.py": "provenance/rebuild/edits/edit_annotations.py"}

events = []
for line in open("provenance/ledger.jsonl"):
    e = json.loads(line)
    if e.get("kind") != "run" or not e.get("deterministic"):
        continue
    ins = {i["path"]: i["sha256"] for i in e.get("inputs") or []}
    for a in e.get("argv") or []:
        for tok in a.split():
            if not tok.endswith((".py", ".sh")):
                continue
            if tok == "replay.sh":
                tok_in = "provenance/rebuild/pre_witness/replay.sh"
            else:
                tok_in = tok
            target = bundled.get(tok) or ALIASES.get(tok) or (tok_in if pathlib.Path(tok_in).is_file() and not tok_in.startswith("..") else None)
            recorded = ins.get(tok_in) or ins.get(tok)
            if recorded is None and e.get("tool_hash") and not str(e["tool_hash"]).startswith("sha256:"):
                recorded = e["tool_hash"]
            cur = sha(target) if target else None
            if recorded and cur != recorded:  # an earlier bundled version with exactly that hash?
                old_v = next((q for q in V.glob("*") if sha(q) == recorded), None)
                if old_v:
                    target, cur = str(old_v), recorded
            events.append({"seq": e["seq"], "tool": e["tool"], "recorded_path": tok, "recorded_sha256": recorded,
                           "bundled": target, "bundled_sha256": cur,
                           "status": ("same_bytes" if recorded and cur == recorded else
                                      "hash_not_recorded" if not recorded else
                                      "version_not_retained" if target else "not_bundled")})
summary = {}
for ev in events:
    summary.setdefault(ev["recorded_path"], {}).setdefault(ev["status"], []).append(ev["seq"])
doc = {
    "format": "tcg-pilot-tool-map/0.1", "class": "U",
    "files": {str(p): sha(p) for p in sorted(B.rglob("*")) if p.is_file()},
    "repo_sources": {str(B / n): s for _, (s, n) in COPY.items()} | {str(B / r): r for r in IMPORTS} | {str(B / "run-controls.sh"): "provenance/rebuild/run-controls.sh"},
    "imports": IMPORTS, "not_copied": NOT_COPIED,
    "status_meaning": {
        "same_bytes": "the bundled copy has exactly the hash the event recorded: replay with it",
        "hash_not_recorded": "the event did not hash the script (e.g. run-claim.sh, whose events record the image Id as tool_hash); the bundled copy is the current version, identity with the version that ran is not proven",
        "version_not_retained": "the event ran an earlier version of the script (assemble_hard.py was extended during assembly); that version was not kept, so the event cannot be replayed byte-for-byte",
        "not_bundled": "no copy available",
    },
    "summary": summary,
    "events": events,
}
(B / "MAP.json").write_text(json.dumps(doc, indent=2) + "\n")
print(json.dumps(summary))
