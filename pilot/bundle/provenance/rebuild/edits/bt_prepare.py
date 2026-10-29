#!/usr/bin/env python3
"""Back-translation step 0 (task 04 section 2): build the ONLY input the blind
translator gets, and prove it carries no requirement text.

Run from the bundle root. Writes provenance/sessions/bt-input/:
  claim-0N.k        byte copies of hard/spec/claim-0N.k
  phi.json          hard/spec/phi.json with requirement-describing fields removed
and provenance/sessions/bt-input.strip_record.json (what was removed, why, and
the leakage check). Exit 1 if any 6-word shingle of requirements.md survives in
the input, or if a requirement sentence appears verbatim."""
import hashlib, json, pathlib, re, shutil, sys

def sha(b): return hashlib.sha256(b).hexdigest()

phi_src = pathlib.Path("hard/spec/phi.json")
phi = json.loads(phi_src.read_text())
TOP_STRIP = {
    "requirements_file": "path of n",
    "requirements_sha256": "hash of n",
    "declared_blind_spots": "one entry per requirement R4-R9 paraphrasing what n asks and is not proved",
    "reading_guide": "explains how claims relate to requirements",
    "status": "mentions the requirements file and signature",
}
CLAIM_STRIP = {
    "coverage_of_requirements": "producer's judgement of how far the claim covers a requirement",
    "caveats": "producer commentary; names parts of R4/R5/R9 that are not proved",
    "controls": "prover results of control runs (not part of the statement)",
    "observed": "prover verdict of the claim (not part of the statement)",
    "source": "producer provenance of the claim text (Findings, commands)",
}
removed = []
for k, why in TOP_STRIP.items():
    if k in phi:
        removed.append({"path": k, "why": why}); phi.pop(k)
for c in phi["claims"]:
    for k, why in CLAIM_STRIP.items():
        if k in c:
            removed.append({"path": f"claims[{c['id']}].{k}", "why": why}); c.pop(k)

out = pathlib.Path("provenance/sessions/bt-input")
if out.exists():
    shutil.rmtree(out)
out.mkdir(parents=True)
phi_bytes = (json.dumps(phi, indent=2) + "\n").encode()
(out / "phi.json").write_bytes(phi_bytes)
for c in phi["claims"]:
    shutil.copyfile(c["file"], out / pathlib.Path(c["file"]).name)

# leakage check against n
req = pathlib.Path("hard/spec/requirements.md").read_text()
words = lambda s: re.findall(r"[a-z0-9_]+", s.lower())
rw = words(req)
shingles = {" ".join(rw[i:i + 6]) for i in range(len(rw) - 5)}
blob = " ".join(words(" ".join(p.read_text() for p in sorted(out.iterdir()))))
hits = sorted(s for s in shingles if s in blob)
sentences = [s.strip() for s in re.findall(r"\*\*R\d+\*\*([^\n]+)", req)]
verbatim = [s for s in sentences if s and s.lower() in blob]
rec = {
    "input_dir": str(out),
    "files": {p.name: sha(p.read_bytes()) for p in sorted(out.iterdir())},
    "phi_source": {"file": str(phi_src), "sha256": sha(phi_src.read_bytes())},
    "removed_fields": removed,
    "kept_requirement_refs": "claims[].requirements (ids R1..R5 only, no text)",
    "leakage_check": {"method": "every 6-word shingle of hard/spec/requirements.md (lowercased word tokens) searched in the concatenated input files",
                      "requirements_sha256": sha(req.encode()), "shingles": len(shingles),
                      "shingle_hits": hits, "verbatim_requirement_sentences": verbatim},
}
pathlib.Path("provenance/sessions/bt-input.strip_record.json").write_text(json.dumps(rec, indent=2) + "\n")
print(json.dumps({"removed": len(removed), "shingle_hits": hits, "verbatim": verbatim, "files": list(rec["files"])}))
sys.exit(1 if hits or verbatim else 0)
