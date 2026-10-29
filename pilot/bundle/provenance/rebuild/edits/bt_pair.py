#!/usr/bin/env python3
"""Back-translation step 2 (task 04 section 2): a script, not a model.

Usage (bundle root): bt_pair.py <session-id>
Reads provenance/sessions/<id>.result.json (the blind translator's output) and
places each translation beside the requirement text(s) its claim references
(phi.json claims[].requirements -> hard/spec/requirements.md). Writes
evidence/backtranslation.json. Judges nothing: every `agreement` is "unclear";
deciding agree/disagree is H's job. Any translator sentence asserting that the
claims match / satisfy / capture a specification or requirement is removed
from the translation and written to provenance/sessions/<id>.quarantine.json
(class U), as task 04 requires ("V refuses to contain" such a sentence)."""
import hashlib, json, pathlib, re, sys

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

sid = sys.argv[1]
S = pathlib.Path("provenance/sessions")
res = json.loads((S / f"{sid}.result.json").read_text())
text = res["result"]
m = re.search(r"\[\s*\{.*\}\s*\]", text, flags=re.S)
if not m:
    print("bt_pair: no JSON array in the translator output", file=sys.stderr)
    sys.exit(1)
items = json.loads(m.group(0))
phi = json.loads(pathlib.Path("hard/spec/phi.json").read_text())
req_md = pathlib.Path("hard/spec/requirements.md").read_text()
reqs = {k: v.strip() for k, v in re.findall(r"^- \*\*(R\d+)\*\*\s+(.+)$", req_md, flags=re.M)}
VERDICT = re.compile(r"\b(match(es|ed)?|satisf(y|ies|ied)|correctly captur\w*|conform\w*|faithful\w*|agree\w*)\b", re.I)
quarantine, rows = [], []
by_claim = {c["id"]: c for c in phi["claims"]}
seen = set()
for it in items:
    cid, tr = it.get("claim"), it.get("translation", "")
    seen.add(cid)
    kept = []
    for s in re.split(r"(?<=[.!?])\s+", tr.strip()):
        if VERDICT.search(s) and re.search(r"\b(spec\w*|requirement\w*|intent\w*|informal)\b", s, re.I):
            quarantine.append({"claim": cid, "sentence": s, "class": "U", "why": "asserts phi matches n; not allowed in V"})
        else:
            kept.append(s)
    c = by_claim.get(cid)
    rows.append({
        "claim": cid,
        "claim_file": c["file"] if c else None, "claim_sha256": c["sha256"] if c else None,
        "translation": " ".join(kept),
        "referenced_requirement": [{"id": r, "text": reqs.get(r)} for r in (c["requirements"] if c else [])],
        "agreement": "unclear",
        "note": "not assessed by any tool or model; agree/disagree is H's judgement (task 04: disagreements are reported, not resolved)",
    })
missing = sorted(set(by_claim) - seen)
doc = {
    "format": "tcg-pilot-backtranslation/0.1",
    "class": "T*",
    "translator": {
        "model": next(iter(res.get("modelUsage", {})), None), "session_id": res.get("session_id"),
        "cli": (S / f"{sid}.env.txt").read_text().splitlines()[0].removeprefix("claude_version: "),
        "transcript": {f"provenance/sessions/{sid}.{x}": sha(S / f"{sid}.{x}")
                       for x in ("stdin.txt", "result.json", "stderr", "env.txt", "listing-before.txt", "listing-after.txt")},
        "prompt": {"provenance/sessions/backtranslation_prompt.md": sha(S / "backtranslation_prompt.md")},
    },
    "requirements_withheld": {
        "how": ("translator ran as unix user agent, which cannot read /home/vladimir (checked in listing-before); its working directory held only "
                "claim-01..05.k and a stripped phi.json; all tools disabled (--tools \"\"), no MCP; its entire input is the recorded stdin file"),
        "strip_record": {"provenance/sessions/bt-input.strip_record.json": sha(S / "bt-input.strip_record.json")},
        "requirements_sha256_withheld": sha("hard/spec/requirements.md"),
    },
    "pairing": {"by": "provenance/rebuild/edits/bt_pair.py (script)", "sha256": sha(__file__)},
    "caveats": [
        "The translator saw the producer's own English paraphrase of each claim (phi.json pre/post/quantifies_over); its sentences may echo that wording rather than reflect an independent reading of the K text. It checks that phi is readable and consistent, not that a second reader derives the same meaning from K alone.",
        "The translator is the same model family as the producing agent (claude-opus-5-5); blind to n, not independent of the producer's model.",
        "One sample, no repetition: no measure of translation variance.",
    ],
    "claims": rows,
    "claims_without_translation": missing,
    "quarantined_sentences": len(quarantine),
}
pathlib.Path("evidence/backtranslation.json").write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n")
if quarantine:
    (S / f"{sid}.quarantine.json").write_text(json.dumps(quarantine, indent=2) + "\n")
print(json.dumps({"claims": len(rows), "missing": missing, "quarantined": len(quarantine), "requirements_found": sorted(reqs)}))
sys.exit(1 if missing else 0)
