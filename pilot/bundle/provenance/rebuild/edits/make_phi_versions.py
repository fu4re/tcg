#!/usr/bin/env python3
"""Write evidence/phi_versions.json (task 04 section 5) from the bundle itself.

Run from the bundle root. Every hash below is recomputed from a file present
in the bundle; every ledger seq is looked up in provenance/ledger.jsonl (the
Accept run whose argv names the module and whose inputs carry that file hash).
Judges nothing."""
import hashlib, json, pathlib

def sha(p): return hashlib.sha256(pathlib.Path(p).read_bytes()).hexdigest()

led = [json.loads(l) for l in open("provenance/ledger.jsonl")]

def proved(spec, mod):
    h = sha(spec)
    for e in led:
        if e.get("kind") == "run" and mod in (e.get("argv") or []) and \
           any(i.get("path") == spec and i.get("sha256") == h for i in e.get("inputs", [])):
            return {"ledger_seq": e["seq"], "exit": e["exit"]}
    return None

def form(spec, mod, note):
    return {"file": spec, "sha256": sha(spec), "spec_module": mod, "run": proved(spec, mod), "note": note}


def _dedup(ws):  # one version per distinct hash; later identical writes are listed, not counted as versions
    out = {}
    for w in ws:
        if w["sha256"] in out:
            out[w["sha256"]].setdefault("rewritten_identically_at_seq", []).append(w["ledger_seq"])
        else:
            out[w["sha256"]] = dict(w)
    return list(out.values())


def _approval(h):  # from evidence/approval.json (derived from approval.msg); this script verifies no signature
    ap = pathlib.Path("evidence/approval.json")
    if not ap.is_file():
        return {"seen_by_H": False, "approved_by_H": False}
    a = json.loads(ap.read_text())
    ok = a.get("phi_sha256") == h
    return {"seen_by_H": ok, "approved_by_H": ok,
            "approval": ({"file": "evidence/approval.json", "sig": "evidence/approval.sig",
                          "signed_at_utc": a.get("signed_at_utc"), "requirements_sha256": a.get("requirements_sha256"),
                          "check": "signature validity is checked at L3 (oracle key out of band)"} if ok else None)}

phi_writes = [{"ledger_seq": e["seq"], "sha256": o["sha256"]} for e in led for o in (e.get("outputs") or [])
              if o["path"] == "hard/spec/phi.json"]
C, O = "provenance/rebuild/controls", "provenance/rebuild/controls-osaka"
doc = {
    "format": "tcg-pilot-phi-versions/0.1",
    "phi_json_versions": [
        dict(w, version=i + 1, **_approval(w["sha256"]),
             note=("first and only phi.json written so far (hardspec seq 59, schedule OSAKA, forms vat/ilk/gem/cagews/joinsym; "
                   "re-written byte-identically by later re-runs)") if i == 0 else "")
        for i, w in enumerate(_dedup(phi_writes))],
    "current": {"file": "hard/spec/phi.json", "sha256": sha("hard/spec/phi.json")},
    "pre_phi_json_history": {
        "why": ("Before phi.json existed, the claim statements it now references changed twice; those changes are "
                "recorded here by claim-file hash, because no phi.json was ever written for the earlier forms."),
        "changes": [
            {"change": "claim-04 cage(): EMPTY storage -> reachable Pre (symbolic storage, wards[caller] == 0)",
             "from": form(f"{C}/cage-cage-prove.k", "CAGE-CAGE-PROVE", "Finding-0003 shape rebuilt; unreachable Pre (kept as control)"),
             "to": form(f"{C}/cagews-cagews-prove.k", "CAGEWS-CAGEWS-PROVE", "assemble_hard.py variant, ledger seq 8")},
            {"change": "claim-05 join(): one concrete (usr, wad) -> every 256-bit usr, wad",
             "from": form(f"{C}/join-join-prove.k", "JOIN-JOIN-PROVE", "symbolic storage + live == 0, usr = 0xdead, wad = 1e18"),
             "to": form(f"{C}/joinsym-joinsym-prove.k", "JOINSYM-JOINSYM-PROVE", "assemble_hard.py variant, ledger seq 9")},
            {"change": "all five claims: <schedule> SHANGHAI </schedule> -> <schedule> OSAKA </schedule> (mainnet runs osaka at the pin)",
             "pairs": [{"from": form(f"{C}/{n}-{n}-prove.k", f"{n.upper()}-{n.upper()}-PROVE", "SHANGHAI"),
                        "to": form(f"{O}/{n}-{n}-prove.k", f"{n.upper()}-{n.upper()}-PROVE", "OSAKA; byte-identical to hard/spec/" + cid + ".k")}
                       for cid, n in [("claim-01", "vat"), ("claim-02", "ilk"), ("claim-03", "gem"),
                                      ("claim-04", "cagews"), ("claim-05", "joinsym")]]},
        ],
    },
    "rule": "H signs sha256(phi.json) || sha256(requirements.md) (D4). Any later change appends a version here and makes an earlier signature stale (L3 fails), by design.",
}
for p in doc["pre_phi_json_history"]["changes"][2]["pairs"]:
    cid = p["to"]["note"].split("hard/spec/")[1].removesuffix(".k")
    assert p["to"]["sha256"] == sha(f"hard/spec/{cid}.k"), cid
pathlib.Path("evidence/phi_versions.json").write_text(json.dumps(doc, indent=2) + "\n")
print(json.dumps(doc["phi_json_versions"]))
