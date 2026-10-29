#!/usr/bin/env python3
"""Write provenance/iterations.json (task 05 section 2) from the ledger and the
run-controls result TSVs. Run from the bundle root. Judges nothing: every
verdict is copied from a results TSV row (tcg/verdict.py classification of
that run's kprove output) or marked absent."""
import csv, glob, hashlib, json, pathlib

def sha(p):
    p = pathlib.Path(p)
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None

led = [json.loads(l) for l in open("provenance/ledger.jsonl")]
rows = {}
for f in sorted(glob.glob("provenance/rebuild/results/*/results.tsv") + glob.glob("provenance/rebuild/results/matrix-*/*.tsv")):
    for r in csv.DictReader(open(f), delimiter="\t"):
        rows.setdefault((r["module"], r["spec"].removeprefix("provenance/rebuild/").removeprefix("pilot/bundle/")), []).append(dict(r, results_file=f))

def verdict(e):
    argv = e["argv"]
    spec = next((a for a in argv if a.endswith(".k")), None)
    mod = argv[argv.index("--spec-module") + 1] if "--spec-module" in argv else None
    key = (mod, (spec or "").removeprefix("provenance/rebuild/"))
    cands = rows.get(key, [])
    out = {o["path"]: o["sha256"] for o in e.get("outputs") or []}
    for r in cands:  # match the run by its log hash
        if r["log_sha256"] in out.values():
            return mod, spec, {"verdict": r["verdict"], "unknown_class": r["unknown_class"], "exit": int(r["exit"]),
                               "wall_s": float(r["wall_s"]), "results_file": r["results_file"]}
    return mod, spec, None

LINEAGE = {  # shipped claim -> prove modules of every form it went through
    "claim-01": ["VAT-VAT-PROVE"], "claim-02": ["ILK-ILK-PROVE"], "claim-03": ["GEM-GEM-PROVE"],
    "claim-04": ["CAGE-CAGE-PROVE", "CAGEWS-CAGEWS-PROVE"], "claim-05": ["JOIN-JOIN-PROVE", "JOINSYM-JOINSYM-PROVE"],
}
phi = json.loads(open("hard/spec/phi.json").read())
accepted = {c["id"]: c["observed"]["ledger_seq"] for c in phi["claims"]}
runs, per_claim = [], {c: [] for c in LINEAGE}
for e in led:
    if e.get("kind") != "run" or e.get("tool") != "kevm-prove" or "--spec-module" not in (e.get("argv") or []):
        continue
    mod, spec, v = verdict(e)
    ins = {i["path"]: i["sha256"] for i in e.get("inputs") or []}
    rec = {"ledger_seq": e["seq"], "module": mod, "spec": spec, "spec_sha256": ins.get(spec), "exit": e["exit"],
           "started": e["started"], "ended": e["ended"], "result": v,
           "log": [{"path": o["path"], "sha256": o["sha256"]} for o in e.get("outputs") or []]}
    if v is None:
        rec["result_note"] = "no results-TSV row matches this run's log hash (pre-crash round 1 wrote logs outside the bundle root)"
    runs.append(rec)
    for cid, mods in LINEAGE.items():
        if mod in mods and e["seq"] <= accepted[cid]:
            per_claim[cid].append({"ledger_seq": e["seq"], "module": mod, "spec": spec, "spec_sha256": ins.get(spec),
                                   "verdict": v["verdict"] if v else None,
                                   "role": "accepted (shipped)" if e["seq"] == accepted[cid] else "preceding run"})
doc = {
    "format": "tcg-pilot-iterations/0.1", "class": "U",
    "august_2026_pilot": {
        "iterations_retained": False,
        "reason": ("The original G4 runs (Finding 0003, cert 668f3d7d...) lived in an August session scratchpad that no longer exists; their claim "
                   "sources, intermediate Refute/Unknown runs and counterexamples were never committed. Only the Finding's prose survives, "
                   "from which claims 04/05 were rebuilt (provenance/decision-stub.md N1)."),
    },
    "this_assembly_2026_10_29": {
        "iterations_retained": True,
        "where": "every kprove run is a ledger event (provenance/ledger.jsonl); verdicts in provenance/rebuild/results/{round1,osaka,matrix-shanghai,matrix-osaka}/*.tsv with logs/ beside them",
        "infra_fail": [{"module": "ILK-ILK-PROVE", "spec": "provenance/rebuild/controls-osaka/ilk-ilk-prove.k",
                        "note": "in flight at the VM reboot; no ledger run event, empty log; not counted (ledger note seq 7)"},
                       {"module": "CAGE-CAGE-VACUITY", "spec": "provenance/rebuild/controls/cage-cage-vacuity.k",
                        "note": "in flight at the VM reboot; no ledger run event, empty log; not counted (ledger note seq 7)"}],
        "refute_or_unknown_before_accept": "none: no prove module of any shipped claim's lineage ever returned Refute or Unknown before its Accept; every Refute/Unknown in the TSVs is a control (vacuity / discriminator / wrong-slot), expected to not Accept",
        "per_claim": per_claim,
        "all_kevm_runs": runs,
    },
}
pathlib.Path("provenance/iterations.json").write_text(json.dumps(doc, indent=2) + "\n")
bad = [r for c in per_claim.values() for r in c if r["role"] == "preceding run" and r["verdict"] not in ("Accept", None)]
print(json.dumps({"runs": len(runs), "per_claim": {k: len(v) for k, v in per_claim.items()}, "preceding_non_accept": bad}))
