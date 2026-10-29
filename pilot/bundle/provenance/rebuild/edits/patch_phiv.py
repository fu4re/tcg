import pathlib
p = pathlib.Path("provenance/rebuild/edits/make_phi_versions.py"); t = p.read_text()
old = """        dict(w, version=i + 1, seen_by_H=False,
             note=("first and only phi.json written so far (hardspec, schedule OSAKA, forms vat/ilk/gem/cagews/joinsym); "
                   "DRAFT, not yet seen or signed by H") if i == 0 else "")
        for i, w in enumerate(phi_writes)],"""
new = """        dict(w, version=i + 1, **_approval(w["sha256"]),
             note=("first and only phi.json written so far (hardspec seq 59, schedule OSAKA, forms vat/ilk/gem/cagews/joinsym; "
                   "re-written byte-identically by later re-runs)") if i == 0 else "")
        for i, w in enumerate(_dedup(phi_writes))],"""
assert old in t
t = t.replace(old, new)
helpers = '''
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

'''
anchor = "phi_writes = ["
assert anchor in t and "def _dedup" not in t
t = t.replace(anchor, helpers + anchor, 1)
p.write_text(t)
print("patched")
