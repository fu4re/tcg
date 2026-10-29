#!/usr/bin/env python3
"""Coverage of requirements by claims, both ways (task 04), with the verifier's own rule.

Usage: coverage.py <bundle-dir> [--out <file>]      (default --out <bundle>/evidence/coverage.json)
Reads hard/spec/phi.json and hard/spec/requirements.md (requirement ids = R<n> at
the start of a line, optionally after "- " and/or "**"). Writes the coverage
object: requirement_to_claims, claim_to_requirements, and requirement_state, with
one of three states per requirement, never merged:
  covered  claimed, no blind-spot entry;
  partial  claimed AND listed in declared_blind_spots (normally "partial": true
           plus a reason saying what is not proved);
  blind    no claim (declared in declared_blind_spots or not: uncovered_undeclared).
Plus the covered / partial / blind lists, declared_blind_spots {R: {reason, partial}},
unreferenced_clauses, unknown_requirement_refs, phi_file_hash_mismatch, and the
inconsistencies (blind spots unknown, non-partial but claimed, partial without a
claim, without a reason). total is true only when every requirement is covered:
any partial or blind requirement keeps it false.
Exit 0 whenever the inputs are well formed, gaps or not (gaps are data);
1 = malformed input (nothing written); 2 = usage.
The verifier recomputes this itself; the stored file is only compared.
"""
from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verifier"))

from tcgverify import canon, evidence, levels  # noqa: E402


def main(argv: list[str]) -> int:
    if not argv or argv[0].startswith("-") or len(argv) not in (1, 3) or (len(argv) == 3 and argv[1] != "--out"):
        print(__doc__, file=sys.stderr)
        return 2
    root = argv[0]
    out = argv[2] if len(argv) == 3 else os.path.join(root, levels.COVERAGE)
    try:
        with open(os.path.join(root, levels.PHI), encoding="utf-8") as f:
            phi = json.load(f)
        with open(os.path.join(root, levels.REQS), encoding="utf-8") as f:
            reqs = f.read()
        files = {}
        for c in phi.get("claims", []) if isinstance(phi, dict) else []:
            p = os.path.join(root, c.get("file", "")) if isinstance(c, dict) and isinstance(c.get("file"), str) else ""
            if p and os.path.isfile(p):
                files[c["file"]] = (canon.sha256_file(p), None)
        res = evidence.coverage(phi, reqs, files)
    except (OSError, ValueError, AttributeError) as e:
        print(f"coverage: malformed input: {e}", file=sys.stderr)
        return 1
    res.pop("manifest_claims_missing_from_phi")
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2, ensure_ascii=False)
        f.write("\n")
    gaps = {k: res[k] for k in ("partial", "blind", "uncovered_undeclared", "unreferenced_clauses",
                                "unknown_requirement_refs", "phi_file_hash_mismatch",
                                "blind_spots_not_in_requirements", "blind_spots_actually_covered",
                                "partial_without_claim", "blind_spots_without_reason") if res[k]}
    print(f"coverage: {len(res['requirement_to_claims'])} requirement(s): {len(res['covered'])} covered, "
          f"{len(res['partial'])} partial, {len(res['blind'])} blind; {len(res['claim_to_requirements'])} "
          f"claim(s); total={res['total']}")
    for k, v in gaps.items():
        print(f"  {k}: {v}")
    print(f"written to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
