#!/usr/bin/env python3
"""Assemble manifest.json for a bundle directory and sign it (DECISIONS D1-D3, D10, D11).

Usage:
  assemble.py <bundle-dir> --key <producer.pem>   write <bundle-dir>/manifest.json
  assemble.py <bundle-dir> --check                plan only: print problems, write nothing

Role / class rules, by path (first match wins; D10: b, phi, a, c, T_hat, checker = T;
evidence = T*; provenance = U):
  hard/artifact.bin            b        hard/spec/**          phi
  hard/annotations.json, hard/lemmas/**  a
  hard/certs/**                c        trusted_base.json     T_hat
  checker/**, semantics/**     checker  evidence/**           V
  provenance/**, DECISIONS.md  P
Claim ids: a phi file gets the id of the hard/spec/phi.json claim whose "file" it
is; hard/certs/**/<x>.rediscuss.json gets its own "claim" field; a Lean source
listed in a hard/certs/**/theorems.json sidecar ([{"claim", "theorem", "source"}])
gets that claim and "theorem". Other files carry no claim id.

Refuses (exit 1, nothing written, every problem printed) when: a file is not
matched by a rule, or is a symlink; DECISIONS.md (root or provenance/) lacks a
row for any of D1-D11; a required role is missing; phi.json, a rediscuss file,
a theorems.json entry or trusted_base.json is malformed or points at a missing
file; the ledger chain is broken; or the manifest fails lint (schema, rule 4,
rule 2). Warnings (printed, not fatal): annotation ids not closed over
trusted_base.assumptions (the verifier's L1 would refuse).
The assembly itself is not a ledger event: the ledger is a child, hashed into
root_hash, so it cannot record the manifest. root_hash + signature are the record.
Exit 2 = usage / unreadable key.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "verifier"))

from tcgverify import canon, levels, manifest as M  # noqa: E402
from tcgverify.jsonschema_min import validate  # noqa: E402
from tcgverify.ledger_walk import walk  # noqa: E402

RULES = (("hard/artifact.bin", "b"), ("hard/spec/", "phi"), ("hard/annotations.json", "a"),
         ("hard/lemmas/", "a"), ("hard/certs/", "c"), ("trusted_base.json", "T_hat"),
         ("checker/", "checker"), ("semantics/", "checker"), ("evidence/", "V"),
         ("provenance/", "P"), ("DECISIONS.md", "P"))
CLASS = {"b": "T", "phi": "T", "a": "T", "c": "T", "T_hat": "T", "checker": "T", "V": "T*", "P": "U"}
MEDIA = {".bin": "application/octet-stream", ".json": "application/json", ".md": "text/markdown",
         ".k": "text/x-k", ".lean": "text/x-lean", ".sh": "text/x-shellscript",
         ".jsonl": "application/x-ndjson", ".sig": "application/octet-stream",
         ".tsv": "text/tab-separated-values", ".log": "text/plain", ".diff": "text/x-diff",
         ".txt": "text/plain"}
D_ROWS = [f"D{i}" for i in range(1, 12)]
OPENSSL = shutil.which("openssl") or "openssl"


def role_for(rel: str) -> str | None:
    for pattern, role in RULES:
        if rel == pattern or (pattern.endswith("/") and rel.startswith(pattern)):
            return role
    return None


def media_for(rel: str) -> str:
    if rel.endswith(".rediscuss.json"):
        return M.REDISCUSS_MEDIA
    return MEDIA.get(os.path.splitext(rel)[1], "application/octet-stream")


def _json(root, rel, probs):
    try:
        with open(os.path.join(root, rel), encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError) as e:
        probs.append(f"{rel}: unreadable or not JSON ({e})")
        return None


def plan(root: str) -> tuple[dict | None, list[str], list[str]]:
    """(unsigned manifest or None, problems, warnings)."""
    probs, warns, files = [], [], []
    path_schema = M.load_schema("manifest.schema.json")["$defs"]["child"]["properties"]["path"]
    for dp, dns, fns in os.walk(root):
        dns.sort()
        for n in dns + fns:
            if os.path.islink(os.path.join(dp, n)):
                probs.append(f"{os.path.relpath(os.path.join(dp, n), root)}: symlink")
        for n in sorted(fns):
            rel = os.path.relpath(os.path.join(dp, n), root).replace(os.sep, "/")
            if rel == "manifest.json" or os.path.islink(os.path.join(dp, n)):
                continue
            if role_for(rel) is None:
                probs.append(f"{rel}: not claimed by any role rule")
            elif validate(rel, path_schema):
                probs.append(f"{rel}: path not allowed by the manifest schema")
            else:
                files.append(rel)
    files.sort()
    roles = {role_for(f) for f in files}
    probs += [f"required role {r} has no file (expected {where})" for r, where in
              (("b", "hard/artifact.bin"), ("phi", "hard/spec/**"), ("a", "hard/annotations.json"),
               ("T_hat", "trusted_base.json"), ("checker", "checker/** or semantics/**")) if r not in roles]
    decisions = [f for f in ("DECISIONS.md", "provenance/DECISIONS.md") if f in files]
    if not decisions:
        probs.append("DECISIONS.md missing (bundle root or provenance/)")
    else:
        with open(os.path.join(root, decisions[0]), encoding="utf-8") as f:
            rows = set(re.findall(r"^\|\s*(D\d+)\s*\|", f.read(), re.MULTILINE))
        probs += [f"{decisions[0]}: no row for {d}" for d in D_ROWS if d not in rows]

    claim_of, theorem_of = {}, {}
    phi = _json(root, levels.PHI, probs) if levels.PHI in files else None
    if levels.PHI not in files:
        probs.append(f"{levels.PHI} missing")
    elif isinstance(phi, dict) and isinstance(phi.get("claims"), list):
        for c in phi["claims"]:
            if not (isinstance(c, dict) and isinstance(c.get("id"), str) and c.get("file") in files):
                probs.append(f"phi.json claim {c!r:.80}: needs an id and an existing 'file'")
            elif not c["file"].startswith("hard/spec/") or c["file"] in claim_of:
                probs.append(f"phi.json claim {c['id']}: file {c['file']} not under hard/spec/ or reused")
            else:
                claim_of[c["file"]] = c["id"]
                if c.get("sha256") != canon.sha256_file(os.path.join(root, c["file"])):
                    probs.append(f"phi.json claim {c['id']}: sha256 differs from {c['file']}")
    elif phi is not None:
        probs.append("phi.json: must be an object with a 'claims' list")
    claims = set(claim_of.values())
    rschema = M.load_schema("rediscuss.schema.json")
    for rel in files:
        if rel.startswith("hard/certs/") and rel.endswith(".rediscuss.json"):
            inv = _json(root, rel, probs)
            ps = validate(inv, rschema) if inv is not None else ["unreadable"]
            if not ps and inv["claim"] not in claims:
                ps = [f"claim {inv['claim']!r} is not a phi.json claim"]
            if not ps and claim_of.get(inv["claim_file"]) != inv["claim"]:
                ps = [f"claim_file {inv['claim_file']} is not the phi file of {inv['claim']}"]
            if not ps and inv.get("claim_file_sha256") not in \
                    (None, canon.sha256_file(os.path.join(root, inv["claim_file"]))):
                ps = ["claim_file_sha256 differs from the claim file"]
            probs += [f"{rel}: {p}" for p in ps]
            if not ps:
                claim_of[rel] = inv["claim"]
        elif rel.startswith("hard/certs/") and os.path.basename(rel) == "theorems.json":
            entries = _json(root, rel, probs)
            for t in entries if isinstance(entries, list) else [None]:
                ok = isinstance(t, dict) and t.get("claim") in claims and isinstance(t.get("theorem"), str) \
                    and t.get("source") in files and t["source"].startswith("hard/certs/") \
                    and t["source"].endswith(".lean") and t["source"] not in theorem_of
                if not ok:
                    probs.append(f"{rel}: entry {t!r:.100} needs a known claim, a theorem and an "
                                 f"existing, not yet listed hard/certs/**.lean source")
                    continue
                claim_of[t["source"]], theorem_of[t["source"]] = t["claim"], t["theorem"]

    tb = _json(root, "trusted_base.json", probs) if "trusted_base.json" in files else None
    if tb is not None:
        probs += [f"trusted_base.json: {p}" for p in validate(tb, M.load_schema("trusted_base.schema.json"))]
    if "provenance/ledger.jsonl" in files:
        with open(os.path.join(root, "provenance/ledger.jsonl"), "rb") as f:
            _, errs = walk(f.read())
        probs += [f"provenance/ledger.jsonl: {e}" for e in errs]
    else:
        warns.append("no provenance/ledger.jsonl: L4 will fail")

    children = []
    for rel in files:
        role = role_for(rel)
        c = {"path": rel, "hash": canon.sha256_file(os.path.join(root, rel)), "class": CLASS[role],
             "media": media_for(rel), "role": role}
        if rel in claim_of:
            c["claim"] = claim_of[rel]
        if rel in theorem_of:
            c["theorem"] = theorem_of[rel]
        children.append(c)
    no_cert = sorted(claims - {claim_of[p] for p in theorem_of})
    man = {"format": "tcg-bundle/0.1", "domain": "evm-bytecode", "children": children,
           "not_claimed": M.load_schema("manifest.schema.json")["properties"]["not_claimed"]["const"],
           "self_contained": not no_cert}
    if no_cert:
        man["self_contained_reason"] = (f"{len(no_cert)} claim(s) without a proof object in the bundle, "
                                        f"re-discharged by an external pinned checker: {', '.join(no_cert)}")
    man["root_hash"] = canon.root_hash(man)
    probs += [f"manifest: {p}" for p in M.schema_problems(dict(man, producer_sig={
        "alg": "ed25519", "pubkey": "0" * 64, "sig": "0" * 128}))]
    probs += [f"manifest: {p}" for p in M.forbidden_problems(man) + M.structure_problems(man)]
    probs += M.certificate_problems(man, tb if isinstance(tb, dict) else None)
    anns = _json(root, "hard/annotations.json", []) if "hard/annotations.json" in files else None
    items = anns.get("annotations") if isinstance(anns, dict) else anns
    if isinstance(tb, dict) and isinstance(items, list):
        warns += levels.ledger_problems(tb, [a for a in items if isinstance(a, dict) and isinstance(a.get("id"), str)])
    return (None if probs else man), probs, warns


def sign(key: str, msg: bytes) -> bytes:
    with tempfile.TemporaryDirectory() as t:
        m, s = os.path.join(t, "m"), os.path.join(t, "s")
        with open(m, "wb") as f:
            f.write(msg)
        subprocess.run([OPENSSL, "pkeyutl", "-sign", "-rawin", "-inkey", key, "-in", m, "-out", s],
                       check=True, capture_output=True)
        with open(s, "rb") as f:
            return f.read()


def raw_pubkey(key: str) -> bytes:
    der = subprocess.run([OPENSSL, "pkey", "-in", key, "-pubout", "-outform", "DER"],
                         check=True, capture_output=True).stdout
    if len(der) != 44 or not der.startswith(bytes.fromhex("302a300506032b6570032100")):
        raise ValueError("key is not an ed25519 private key")
    return der[-32:]


def sign_manifest(man: dict, key: str) -> dict:
    man = {k: v for k, v in man.items() if k != "producer_sig"}
    man["root_hash"] = canon.root_hash(man)
    man["producer_sig"] = {"alg": "ed25519", "pubkey": raw_pubkey(key).hex(),
                           "sig": sign(key, man["root_hash"].encode("ascii")).hex()}
    return man


def write_manifest(root: str, man: dict) -> None:
    tmp = os.path.join(root, ".manifest.json.tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(man, f, indent=2, ensure_ascii=False)
        f.write("\n")
    os.replace(tmp, os.path.join(root, "manifest.json"))


def main(argv: list[str]) -> int:
    if len(argv) == 2 and argv[1] == "--check":
        root, key = argv[0], None
    elif len(argv) == 3 and argv[1] == "--key":
        root, key = argv[0], argv[2]
    else:
        print(__doc__, file=sys.stderr)
        return 2
    if not os.path.isdir(root):
        print(f"assemble: no such directory {root}", file=sys.stderr)
        return 2
    man, probs, warns = plan(root)
    for w in warns:
        print(f"WARN: {w}")
    for p in probs:
        print(f"REFUSE: {p}")
    if probs:
        print(f"assemble: {len(probs)} problem(s); nothing written")
        return 1
    if key is None:
        print(f"assemble --check: OK, {len(man['children'])} children, root_hash {man['root_hash']}")
        return 0
    try:
        man = sign_manifest(man, key)
    except (OSError, ValueError, subprocess.CalledProcessError) as e:
        print(f"assemble: cannot sign with {key}: {e}", file=sys.stderr)
        return 2
    write_manifest(root, man)
    print(f"assemble: wrote {os.path.join(root, 'manifest.json')}: {len(man['children'])} children, "
          f"root_hash {man['root_hash']}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
