"""Manifest rules (task 01) shared by the verifier (L0) and tools/lint_manifest.py.

Every function returns a list of problems; [] means the rule holds. Nothing
here returns a bundle-level verdict.
"""
from __future__ import annotations

import json
import os
import re

from . import canon
from .jsonschema_min import validate

HERE = os.path.dirname(os.path.abspath(__file__))
FORBIDDEN_KEY_PARTS = ("verdict", "level", "proved", "pass", "score")
_LEVEL_KEY = re.compile(r"^l[0-4]$")
_PROVED_WORD = re.compile(r"\bproved\b", re.IGNORECASE)
# A KEVM re-discharge invocation (variant A) is role c but is NOT a proof object.
REDISCUSS_MEDIA = "application/vnd.tcg.rediscuss+json"


def load_schema(name: str) -> dict:
    with open(os.path.join(HERE, name), encoding="utf-8") as f:
        return json.load(f)


def schema_problems(manifest) -> list[str]:
    return validate(manifest, load_schema("manifest.schema.json"))


def forbidden_problems(obj, where: str = "$") -> list[str]:
    """Rule 4: no key that names a verdict/level/score, at any depth, and no
    string value containing the word 'proved'. Over-rejects on purpose."""
    out: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            low = k.lower()
            if any(p in low for p in FORBIDDEN_KEY_PARTS) or _LEVEL_KEY.match(low):
                out.append(f"{where}.{k}: forbidden key (rule 4)")
            out += forbidden_problems(v, f"{where}.{k}")
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out += forbidden_problems(v, f"{where}[{i}]")
    elif isinstance(obj, str) and _PROVED_WORD.search(obj):
        out.append(f"{where}: value contains the word 'proved' (rule 4)")
    return out


def structure_problems(manifest: dict) -> list[str]:
    out = []
    paths = [c.get("path") for c in manifest.get("children", []) if isinstance(c, dict)]
    dups = sorted({p for p in paths if paths.count(p) > 1})
    if dups:
        out.append(f"duplicate child paths: {dups}")
    if "manifest.json" in paths:
        out.append("the manifest cannot list itself as a child")
    return out


def root_problems(manifest: dict) -> list[str]:
    try:
        got = canon.root_hash(manifest)
    except (ValueError, TypeError) as e:
        return [f"root_hash not computable: {e}"]
    if manifest.get("root_hash") != got:
        return [f"root_hash mismatch: manifest says {manifest.get('root_hash')}, recomputed {got}"]
    return []


def child_file_problems(manifest: dict, bundle_dir: str) -> tuple[list[str], set[str]]:
    """Check each child's bytes on disk. Returns (problems, set of good paths)."""
    out, good = [], set()
    real_root = os.path.realpath(bundle_dir)
    for c in manifest.get("children", []):
        p = c.get("path", "")
        full = os.path.join(bundle_dir, p)
        if os.path.islink(full) or not os.path.realpath(full).startswith(real_root + os.sep):
            out.append(f"{p}: symlink or path escaping the bundle")
        elif not os.path.isfile(full):
            out.append(f"{p}: missing")
        elif canon.sha256_file(full) != c.get("hash"):
            out.append(f"{p}: sha256 differs from manifest")
        else:
            good.add(p)
    return out, good


def unlisted_files(manifest: dict, bundle_dir: str, manifest_name: str = "manifest.json") -> list[str]:
    listed = {c.get("path") for c in manifest.get("children", [])} | {manifest_name}
    found = []
    for dirpath, _, files in os.walk(bundle_dir):
        for f in files:
            rel = os.path.relpath(os.path.join(dirpath, f), bundle_dir).replace(os.sep, "/")
            if rel not in listed:
                found.append(rel)
    return sorted(found)


def claim_ids(manifest: dict) -> list[str]:
    return sorted({c["claim"] for c in manifest.get("children", [])
                   if c.get("role") == "phi" and c.get("claim")})


def certificate_problems(manifest: dict, trusted_base: dict | None) -> list[str]:
    """Rule 2: every claim has a proof object (a role-c child with a 'theorem'),
    or is listed in trusted_base.claims_without_certificate with a reason. A KEVM
    re-discharge invocation is not a proof object."""
    claims = set(claim_ids(manifest))
    if not claims:
        return ["no phi child carries a 'claim' id: the claim set is empty"]
    cs = [c for c in manifest.get("children", []) if c.get("role") == "c"]
    out = [f"certificate for unknown claim {c!r}"
           for c in sorted({c["claim"] for c in cs if "claim" in c} - claims)]
    certs = {c.get("claim") for c in cs if c.get("theorem")}  # only proof objects count
    cwc = {}
    if trusted_base is not None:
        for e in trusted_base.get("claims_without_certificate", []) or []:
            if isinstance(e, dict) and e.get("claim"):
                cwc[e["claim"]] = e.get("reason")
    for c in sorted(claims):
        if c in cwc and not (isinstance(cwc[c], str) and cwc[c].strip()):
            out.append(f"{c}: listed in claims_without_certificate without a reason")
        if c not in certs and c not in cwc:
            out.append(f"{c}: no certificate and not in claims_without_certificate (rule 2)")
    return out
