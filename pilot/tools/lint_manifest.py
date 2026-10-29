#!/usr/bin/env python3
"""Lint a tcg-bundle/0.1 manifest (task 01). Stdlib only.

Checks:
  1. JSON Schema (pilot/schema/manifest.schema.json, validated by the
     verifier's fail-closed minimal 2020-12 validator; if the `jsonschema`
     package happens to be installed it is run as well, never instead);
  2. rule 4: no verdict/level/proved/pass/score key at any depth, no value
     containing the word "proved";
  3. unique child paths;
  4. root_hash recomputed per DECISIONS D2;
  unless --schema-only, also (bundle dir = the manifest's directory):
  5. every child file exists inside the bundle and has the listed sha256;
  6. no unlisted file in the bundle dir;
  7. rule 2: every claim has a certificate or is in
     trusted_base.json claims_without_certificate with a reason.

Usage: lint_manifest.py <manifest.json> [--schema-only]
Exit 0 = no problem found; 1 = problems (all printed); 2 = usage / unreadable.
The linter checks form only. It never says anything about whether a claim holds.
"""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "verifier"))

from tcgverify import manifest as M  # noqa: E402


def lint(path: str, schema_only: bool) -> list[str]:
    with open(path, encoding="utf-8") as f:
        man = json.load(f)
    if not isinstance(man, dict):
        return ["manifest is not a JSON object"]
    probs = [f"schema: {p}" for p in M.schema_problems(man)]
    try:
        import jsonschema  # optional cross-check only
        for e in jsonschema.Draft202012Validator(M.load_schema("manifest.schema.json")).iter_errors(man):
            probs.append(f"schema (jsonschema): {e.message}")
    except ImportError:
        pass
    probs += M.forbidden_problems(man)
    probs += M.structure_problems(man)
    probs += M.root_problems(man)
    if not schema_only:
        bundle = os.path.dirname(os.path.abspath(path))
        file_probs, good = M.child_file_problems(man, bundle)
        probs += file_probs
        probs += [f"{p}: file in bundle dir but not listed in the manifest"
                  for p in M.unlisted_files(man, bundle, os.path.basename(path))]
        tb = None
        tb_paths = [c["path"] for c in man.get("children", []) if c.get("role") == "T_hat"]
        if len(tb_paths) == 1 and tb_paths[0] in good:
            try:
                with open(os.path.join(bundle, tb_paths[0]), encoding="utf-8") as f:
                    tb = json.load(f)
            except ValueError as e:
                probs.append(f"{tb_paths[0]}: not JSON ({e})")
        else:
            probs.append("trusted base (role T_hat) missing or unreadable; rule 2 not checkable")
        probs += M.certificate_problems(man, tb if isinstance(tb, dict) else None)
    return probs


def main(argv: list[str]) -> int:
    args = [a for a in argv if a != "--schema-only"]
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        probs = lint(args[0], "--schema-only" in argv)
    except (OSError, ValueError) as e:
        print(f"lint_manifest: cannot read {args[0]}: {e}", file=sys.stderr)
        return 2
    for p in probs:
        print(f"FAIL: {p}")
    print(f"{args[0]}: {len(probs)} problem(s)")
    return 1 if probs else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
