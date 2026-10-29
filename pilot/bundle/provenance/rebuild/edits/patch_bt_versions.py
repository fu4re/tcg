import pathlib
p = pathlib.Path("provenance/rebuild/edits/bundle_tools.py"); t = p.read_text()
old = """if B.exists():
    shutil.rmtree(B)
(B / "tcg").mkdir(parents=True)
bundled = {}
for rec, (src, name) in COPY.items():
    shutil.copy2(src, B / name)
    bundled[rec] = str(B / name)
"""
new = """# Every version ever bundled is kept under provenance/tools/versions/<name>-<sha12><ext>,
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
"""
assert old in t and "versions" not in t
t = t.replace(old, new)
old2 = """            target = bundled.get(tok) or ALIASES.get(tok) or (tok_in if pathlib.Path(tok_in).is_file() and not tok_in.startswith("..") else None)
            recorded = ins.get(tok_in) or ins.get(tok)
            if recorded is None and e.get("tool_hash") and not str(e["tool_hash"]).startswith("sha256:"):
                recorded = e["tool_hash"]
            cur = sha(target) if target else None"""
new2 = """            target = bundled.get(tok) or ALIASES.get(tok) or (tok_in if pathlib.Path(tok_in).is_file() and not tok_in.startswith("..") else None)
            recorded = ins.get(tok_in) or ins.get(tok)
            if recorded is None and e.get("tool_hash") and not str(e["tool_hash"]).startswith("sha256:"):
                recorded = e["tool_hash"]
            cur = sha(target) if target else None
            if recorded and cur != recorded:  # an earlier bundled version with exactly that hash?
                old_v = next((q for q in V.glob("*") if sha(q) == recorded), None)
                if old_v:
                    target, cur = str(old_v), recorded"""
assert old2 in t
t = t.replace(old2, new2)
p.write_text(t)
print("patched")
