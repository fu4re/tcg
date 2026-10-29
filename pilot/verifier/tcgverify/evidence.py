"""Evidence rules shared by the verifier (L2) and the producer tools
(tools/coverage.py, tools/mutant_witness.py), so both apply the same judgement.

Coverage: totality both ways between requirements.md (R<n> ids) and
phi.json claims. Mutant witnesses: evidence/mutants/<name>/{mutant.bin |
harness/, replay.sh, refutation.json}; each kind has its own acceptance rule
and the outcomes are never merged:
  refute                    replay stdout classified "refute" by the KEVM judge
                            (a symbolic stuck state: NO concrete counterexample)
  concrete_trace_violation  replay exits 0 and prints a line "TCG-VIOLATION: ..."
                            (a concrete run of the mutant violates the claim)
  not_accept                the judge does not classify the replay as accept;
                            reported, never counted as a witness
plus not_reproduced (stdout hash differs or the kind's rule fails), malformed, not_run.
"""
from __future__ import annotations

import os
import re
import shutil
import tempfile

from . import canon, checkers

REQ_ID = re.compile(r"^\s*(?:[-*]\s*)?(?:\*\*)?(R\d+)\b", re.MULTILINE)
KINDS = ("refute", "concrete_trace_violation", "not_accept")
WITNESS_KINDS = ("refute", "concrete_trace_violation")
VIOLATION = re.compile(r"^TCG-VIOLATION: (.+)$", re.MULTILINE)


def coverage(phi, reqs_text: str, files: dict | None = None, manifest_claims=None) -> dict:
    """files: {path: (sha256, claim id or None)} for the phi claim files, or None
    to skip the file checks. Raises ValueError only on malformed input."""
    if not isinstance(phi, dict) or not isinstance(phi.get("claims"), list):
        raise ValueError("phi.json must be an object with a 'claims' list")
    req_ids = sorted(set(REQ_ID.findall(reqs_text)), key=lambda r: int(r[1:]))
    r2c = {r: [] for r in req_ids}
    c2r, unknown, file_mismatch = {}, [], []
    for c in phi["claims"]:
        if not isinstance(c, dict) or not isinstance(c.get("id"), str):
            raise ValueError("phi.json claim entry without a string id")
        if c["id"] in c2r:
            raise ValueError(f"duplicate claim id {c['id']}")
        if files is not None:
            got = files.get(c.get("file"))
            if not got or got[0] != c.get("sha256") or got[1] not in (None, c["id"]):
                file_mismatch.append(c["id"])
        refs = [r for r in c.get("requirements") or [] if isinstance(r, str)]
        c2r[c["id"]] = [r for r in refs if r in r2c]
        unknown += [f"{c['id']}->{r}" for r in refs if r not in r2c]
        for r in c2r[c["id"]]:
            r2c[r].append(c["id"])
    blind = {}
    for b in phi.get("declared_blind_spots") or []:
        if not isinstance(b, dict) or not isinstance(b.get("requirement"), str):
            raise ValueError("declared_blind_spots entries need a string 'requirement'")
        if "partial" in b and not isinstance(b["partial"], bool):
            raise ValueError(f"declared_blind_spots {b['requirement']}: 'partial' must be a boolean")
        blind[b["requirement"]] = {"reason": b.get("reason"), "partial": b.get("partial", False)}
    # Three states per requirement, never merged: covered (claimed, no blind-spot entry),
    # partial (claimed AND a blind-spot entry saying what is not proved; an entry
    # without "partial": true there is also listed in blind_spots_actually_covered),
    # blind (no claim at all, declared or not).
    state = {}
    for r, cs in r2c.items():
        if not cs:
            state[r] = "blind"
        elif r in blind:  # a declared gap on a claimed requirement is never "covered"
            state[r] = "partial"
        else:
            state[r] = "covered"
    res = {"requirement_to_claims": r2c, "claim_to_requirements": c2r,
           "requirement_state": state,
           "covered": [r for r in r2c if state[r] == "covered"],
           "partial": [r for r in r2c if state[r] == "partial"],
           "blind": [r for r in r2c if state[r] == "blind"],
           "declared_blind_spots": blind,
           "uncovered_undeclared": [r for r in r2c if state[r] == "blind" and r not in blind],
           "blind_spots_not_in_requirements": sorted(set(blind) - set(r2c)),
           "blind_spots_actually_covered": sorted(r for r in blind if r2c.get(r) and not blind[r]["partial"]),
           "partial_without_claim": sorted(r for r in blind if blind[r]["partial"] and r in r2c and not r2c[r]),
           "blind_spots_without_reason": sorted(r for r, b in blind.items()
                                                if not (isinstance(b["reason"], str) and b["reason"].strip())),
           "unreferenced_clauses": [c for c, rs in c2r.items() if not rs],
           "unknown_requirement_refs": unknown, "phi_file_hash_mismatch": file_mismatch,
           "manifest_claims_missing_from_phi":
               sorted(set(manifest_claims or ()) - set(c2r)) if manifest_claims is not None else []}
    # total only when every requirement is fully covered and nothing is inconsistent;
    # partial and blind requirements both keep it false.
    res["total"] = bool(req_ids) and len(res["covered"]) == len(req_ids) and not (
        res["unreferenced_clauses"] or unknown or file_mismatch or res["manifest_claims_missing_from_phi"]
        or res["blind_spots_not_in_requirements"])
    return res


def run_replay(bundle_dir: str, script_rel: str, outside: list[str] | None = None, timeout: int = 3600):
    """Run `sh <script>` in its directory inside a disposable copy of bundle_dir,
    with only PATH and a scratch HOME. Returns checkers.run()'s tuple."""
    with tempfile.TemporaryDirectory() as tmp:
        work = shutil.copytree(bundle_dir, os.path.join(tmp, "bundle"), symlinks=True)
        sh = shutil.which("sh")
        if outside is not None:
            outside.append(f"{sh} (sha256 {canon.sha256_file(sh)}) used to run bundle-supplied scripts")
        return checkers.run([sh, os.path.basename(script_rel)],
                            cwd=os.path.join(work, os.path.dirname(script_rel)), timeout=timeout,
                            env={"PATH": os.environ.get("PATH", ""), "HOME": tmp})


def judge_witness(kind: str, rc, out: str, timed_out: bool, recorded_sha256: str | None) -> dict:
    """Apply the kind's acceptance rule to one replay. Never raises."""
    e = {"exit": rc, "timed_out": timed_out, "output_sha256": canon.sha256_bytes(out.encode()),
         "checker_classification": checkers.classify_kprove(rc, out, timed_out)}
    e["reproduced"] = recorded_sha256 is None or e["output_sha256"] == recorded_sha256
    v = VIOLATION.findall(out)
    if v:
        e["violation"] = v[0][:500]
    if kind == "refute":
        ok = e["checker_classification"] == "refute"
    elif kind == "concrete_trace_violation":
        ok = rc == 0 and not timed_out and bool(v)
    elif kind == "not_accept":
        ok = e["checker_classification"] != "accept"
    else:
        return dict(e, outcome="malformed", detail=f"unknown kind {kind!r}")
    e["kind_rule_holds"] = ok
    e["outcome"] = kind if ok and e["reproduced"] else "not_reproduced"
    return e
