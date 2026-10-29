"""The five ladder levels (task 06; TCG v3 sections 5, 6, 10).

Each level function returns that level's own dict. There is deliberately no
function that combines levels into one value (v3 section 6, "Reporting").
"""
from __future__ import annotations

import json
import os
import posixpath
import shutil
import subprocess
import tempfile

from . import canon, checkers, ed25519, evidence, manifest as M
from .chain import ChainError, blob_param_fork_for, fork_for
from .jsonschema_min import validate
from .keccak import keccak256

PHI, REQS = "hard/spec/phi.json", "hard/spec/requirements.md"
APPROVAL_JSON, APPROVAL_SIG = "evidence/approval.json", "evidence/approval.sig"
COVERAGE, BACKTRANSLATION = "evidence/coverage.json", "evidence/backtranslation.json"
MUTANTS, PRE_WITNESS = "evidence/mutants/", "evidence/pre_witness/"
LEDGER = "provenance/ledger.jsonl"


def _status(ok: bool) -> str:
    return "pass" if ok else "fail"


def trusted_base(view):
    """(T_hat object or None, problems)."""
    tb_children = view.children("T_hat")
    if len(tb_children) != 1:
        return None, [f"expected exactly one T_hat child, found {len(tb_children)}"]
    tb, err = view.json(tb_children[0]["path"])
    if err:
        return None, [err]
    probs = validate(tb, M.load_schema("trusted_base.schema.json"))
    return (tb if not probs else None), probs


def checker_entry(tb: dict, name: str) -> dict | None:
    for e in tb.get("checker") or []:
        if isinstance(e, dict) and e.get("name") == name:
            return e
    return None


# --- L0 ----------------------------------------------------------------------
def level0(view, chain, producer_pub: bytes, outside: list[str]) -> dict:
    checks: dict = {}
    man = view.manifest
    if man is None:
        return {"status": "fail", "checks": {"manifest": view.load_error}}
    checks["manifest_schema"] = {"ok": not (p := M.schema_problems(man)), "problems": p}
    checks["forbidden_keys"] = {"ok": not (p := M.forbidden_problems(man)), "problems": p}
    checks["structure"] = {"ok": not (p := M.structure_problems(man)), "problems": p}
    declared = man.get("root_hash")
    try:
        recomputed = canon.root_hash(man)
    except (ValueError, TypeError):
        recomputed = None
    checks["root_hash"] = {"ok": recomputed is not None and declared == recomputed,
                           "declared": declared, "recomputed": recomputed}
    checks["children"] = {"ok": not view.child_problems, "problems": view.child_problems,
                          "unlisted_files_ignored": M.unlisted_files(man, view.bundle_dir)}
    sig = man.get("producer_sig") if isinstance(man.get("producer_sig"), dict) else {}
    try:
        sig_bytes = bytes.fromhex(sig.get("sig", ""))
    except (ValueError, TypeError):
        sig_bytes = b""
    sig_ok = recomputed is not None and ed25519.verify(producer_pub, recomputed.encode("ascii"), sig_bytes)
    checks["producer_sig"] = {"ok": sig_ok and sig.get("pubkey") == producer_pub.hex(),
                              "signature_valid_under_supplied_key": sig_ok,
                              "manifest_pubkey_is_supplied_key": sig.get("pubkey") == producer_pub.hex()}
    tb, tb_probs = trusted_base(view)
    checks["trusted_base"] = {"ok": tb is not None, "problems": tb_probs}
    checks["identity"] = _identity(view, tb, chain, outside)
    checks["environment"] = _environment(tb, chain)
    return {"status": _status(all(c.get("ok") for c in checks.values())), "checks": checks}


def _identity(view, tb, chain, outside) -> dict:
    if tb is None:
        return {"ok": False, "detail": "no valid trusted base"}
    ident = tb["identity"]
    declared = ident["value"].lower()
    arts = view.children("b")
    art = view.read(arts[0]["path"]) if len(arts) == 1 else None
    art_k = "0x" + keccak256(art).hex() if art is not None else None
    out = {"declared": declared, "artifact_keccak": art_k, "address": ident["address"],
           "block": ident["block"], "chain_keccak": None}
    if chain is None:
        return dict(out, ok=False, detail="no chain source supplied (--rpc or --state-snapshot)")
    try:
        code = chain.code(ident["address"], ident["block"])
        outside.append(chain.describe(ident["block"]))
    except ChainError as e:
        return dict(out, ok=False, detail=f"chain read failed: {e}")
    out["chain_keccak"] = "0x" + keccak256(code).hex()
    out["chain_code_size"] = len(code)
    out["ok"] = bool(code) and art_k is not None and out["chain_keccak"] == declared == art_k
    return out


def _environment(tb, chain) -> dict:
    if tb is None or chain is None:
        return {"ok": False, "detail": "no valid trusted base" if tb is None else "no chain source"}
    env, block = tb["environment"], tb["identity"]["block"]
    out: dict = {"declared_not_checked": {k: env.get(k) for k in
                                          ("fee_schedule", "caller_assumptions", "precompiles", "resource_limits")}}
    try:
        cid = chain.chain_id()
        b = chain.block(block)
    except ChainError as e:
        return dict(out, ok=False, detail=f"chain read failed: {e}")
    out["block_hash"] = b.get("hash")
    out["chain_id"] = {"declared": env["chain_id"], "chain": cid, "ok": cid == env["chain_id"]}
    derived, snap = fork_for(cid, b["number"], b["timestamp"]), chain.declared_fork()
    fork_ok = derived is not None and str(env["fork"]).lower() == derived and \
        (snap is None or str(snap).lower() == derived)
    out["fork"] = {"declared": env["fork"], "derived_from_block": derived, "snapshot_says": snap,
                   "blob_param_fork": blob_param_fork_for(cid, b["timestamp"]), "ok": fork_ok}
    ext = []
    for e in env["external_code"]:
        try:
            code = chain.code(e["address"], block)
            got = "0x" + keccak256(code).hex()
        except ChainError as err:
            got, code = f"error: {err}", b""
        ext.append({"name": e.get("name"), "address": e["address"], "declared": e["code_hash"].lower(),
                    "chain": got, "ok": bool(code) and got == e["code_hash"].lower()})
    out["external_code"] = ext
    out["ok"] = out["chain_id"]["ok"] and fork_ok and all(x["ok"] for x in ext)
    return out


# --- L1 ----------------------------------------------------------------------
def _annotations(view):
    a = [c for c in view.children("a") if c["path"].endswith(".json")]
    if not a:
        return None, "no role-a JSON child (hard/annotations.json)"
    doc, err = view.json(a[0]["path"])
    if err:
        return None, err
    items = doc.get("annotations") if isinstance(doc, dict) else doc
    if not isinstance(items, list) or not all(isinstance(x, dict) and isinstance(x.get("id"), str) for x in items):
        return None, "annotations must be a list of objects with string ids"
    return items, None


def ledger_problems(tb: dict, annotations: list[dict]) -> list[str]:
    """The honest-reporting rule: assumptions non-empty and closed over annotations."""
    asm = [a for a in tb.get("assumptions") or [] if isinstance(a, dict)]
    if not asm:
        return ["assumptions list is empty"]
    covered = {}
    for a in asm:
        for i in [a.get("id")] + list(a.get("covers") or []):
            covered[i] = a
    probs = []
    for ann in annotations:
        a = covered.get(ann["id"])
        if a is None:
            probs.append(f"annotation {ann['id']} not in trusted_base.assumptions")
        elif not (isinstance(a.get("risk_if_false"), str) and a["risk_if_false"].strip()):
            probs.append(f"assumption {a.get('id')} covering {ann['id']} has no risk_if_false")
    return probs


def level1(view, variant: str, verifier_hash: str, outside: list[str], limits: tuple = ()) -> dict:
    tb, _ = trusted_base(view)
    anns, err = _annotations(view)
    if tb is None or anns is None:
        reason = [err or "trusted base invalid"]
    else:
        reason = ledger_problems(tb, anns)
    if reason:
        return {"status": "refused", "claims": [], "checks": {},
                "refused_reason": "empty or incomplete assumption ledger", "refused_detail": reason}
    checks: dict = {}
    v = checker_entry(tb, "tcg-verifier")
    checks["verifier_hash"] = {"running": verifier_hash, "trusted_base": v and v.get("hash"),
                               "ok": bool(v) and verifier_hash in checkers._hashes(v)}
    allowed = checkers.STANDARD_LEAN_AXIOMS
    if isinstance(tb.get("lean_axioms"), list):  # T_hat may only narrow the standard set
        allowed = allowed & frozenset(tb["lean_axioms"])
    checks["lean_axiom_whitelist"] = sorted(allowed)
    if variant == "B":
        checks["semantics"] = _semantics(view, tb)
    claims = M.claim_ids(view.manifest)
    results: list[dict] = []
    image = None
    lean_groups: dict[str, list] = {}
    for claim in claims:
        certs = [c for c in view.children("c") if c.get("claim") == claim]
        checked = False
        for c in certs:
            if c["media"] == M.REDISCUSS_MEDIA and variant == "A":
                checked = True
                if image is None:
                    kentry = checker_entry(tb, "kevm-prove") or {}
                    image = checkers.docker_image_identity(kentry, outside) + (kentry,)
                    if image[1] == "ok":
                        outside.append(f"KEVM checker docker image {image[0]} (T_hat checker kevm-prove)")
                results.append(_kevm(view, claim, c, image, limits))
            elif c["media"] == "text/x-lean" and c.get("theorem"):
                checked = True
                proj = _lean_project_dir(view, c["path"])
                lean_groups.setdefault(proj or "", []).append((claim, c["theorem"], c["path"]))
        if not checked:
            results.append({"claim": claim, "checker": None, "result": "not_checked",
                            "detail": f"no certificate checkable under variant {variant}"})
    for proj, items in lean_groups.items():
        if not proj:
            results += [{"claim": c, "checker": "lean", "theorem": t, "result": "malformed",
                         "detail": "no lean-toolchain above the source"} for c, t, _ in items]
            continue
        entry = checker_entry(tb, "lean") or {}
        results += checkers.lean_project(view.path(proj + "/lean-toolchain")[:-len("/lean-toolchain")],
                                         [(c, t, view.path(p)) for c, t, p in items], entry, allowed, outside)
    claims_ok = bool(results) and all(r["result"] == "accept" for r in results) and \
        {r["claim"] for r in results} == set(claims)
    checks_ok = checks["verifier_hash"]["ok"] and checks.get("semantics", {"ok": True})["ok"]
    return {"status": _status(claims_ok and checks_ok), "claims": results, "checks": checks,
            "refused_reason": None}


def _kevm(view, claim, child, image, limits=()) -> dict:
    image_id, status, detail = image[:3]
    base = {"claim": claim, "checker": "kevm-prove", "invocation": child["path"], "self_contained": False}
    if status != "ok":
        return dict(base, result=status, detail=detail)
    inv, err = view.json(child["path"])
    probs = [err] if err else validate(inv, M.load_schema("rediscuss.schema.json"))
    if not probs and inv["claim"] != claim:
        probs = [f"invocation names claim {inv['claim']}"]
    phi = [c for c in view.children("phi") if c["path"] == (inv or {}).get("claim_file") and c.get("claim") == claim]
    if not probs and not (phi and view.path(phi[0]["path"])):
        probs = ["claim_file is not a verified phi child of this claim"]
    if not probs and inv.get("claim_file_sha256") not in (None, phi[0]["hash"]):
        probs = ["claim_file_sha256 differs from the claim file in the manifest"]
    if not probs and inv.get("image_id") not in (None, image_id) and \
            inv["image_id"] not in checkers._hashes(image[3]):
        probs = [f"image_id {inv['image_id']} is not the image T_hat names"]
    if probs:
        return dict(base, result="malformed", detail=probs)
    return checkers.kevm_claim(claim, child["path"], view.path(phi[0]["path"]), image_id, inv, limits)


def _lean_project_dir(view, rel: str) -> str | None:
    parts = rel.split("/")[:-1]
    while parts:
        if view.path("/".join(parts + ["lean-toolchain"])):
            return "/".join(parts)
        parts.pop()
    return None


def _semantics(view, tb) -> dict:
    out = []
    for s in tb.get("semantics") or []:
        if isinstance(s, dict) and s.get("path"):
            p = os.path.join(view.dir, s["path"])
            got = canon.tree_hash(p) if os.path.isdir(p) else None
            out.append({"name": s.get("name"), "path": s["path"], "declared": s.get("hash"),
                        "tree_hash": got, "ok": got is not None and got == s.get("hash")})
    return {"ok": bool(out) and all(x["ok"] for x in out), "entries": out}


# --- L2 ----------------------------------------------------------------------
def level2(view, execute: bool, outside: list[str]) -> dict:
    out = {"coverage_total": False, "coverage": _coverage(view)}
    out["coverage_total"] = out["coverage"].get("total", False)
    bt, err = view.json(BACKTRANSLATION)
    key = next((k for k in ("claims", "entries") if isinstance(bt, dict) and isinstance(bt.get(k), list)), None)
    entries = bt[key] if key else bt  # "claims" (pilot bundle), "entries" (earlier draft), or a bare list
    out["backtranslation"] = entries if isinstance(entries, list) else None
    out["backtranslation_meta"] = ({k: v for k, v in bt.items() if k != key}
                                   if isinstance(bt, dict) else {"error": err})
    out["mutants"], out["no_witness"] = _mutants(view, execute, outside)
    out["pre_witness_replays"], out["pre_witness"] = _pre_witness(view, execute, outside)
    return out


def _coverage(view) -> dict:
    phi, err = view.json(PHI)
    reqs = view.read(REQS)
    if err or reqs is None:
        return {"total": False, "error": err or "requirements.md absent or not hash-verified"}
    files = {c["path"]: (c.get("hash"), c.get("claim")) for c in view.children("phi")}
    try:
        res = evidence.coverage(phi, reqs.decode("utf-8", errors="replace"), files,
                                M.claim_ids(view.manifest))
    except ValueError as e:
        return {"total": False, "error": str(e)}
    stored, _ = view.json(COVERAGE)
    res["stored_coverage_matches"] = isinstance(stored, dict) and \
        stored.get("requirement_to_claims") == res["requirement_to_claims"] and \
        stored.get("claim_to_requirements") == res["claim_to_requirements"] and \
        stored.get("requirement_state") == res["requirement_state"]
    return res


def _mutants(view, execute, outside):
    dirs = sorted({c["path"][len(MUTANTS):].split("/")[0] for c in view.children("V")
                   if c["path"].startswith(MUTANTS) and c["path"].count("/") >= 3})
    art = [c["hash"] for c in view.children("b")]
    res = []
    for d in dirs:
        base = f"{MUTANTS}{d}/"
        ref, err = view.json(base + "refutation.json")
        ref = ref if isinstance(ref, dict) else {}
        e = {"dir": base, "claim": ref.get("claim"), "kind": ref.get("kind"), "replayed": False}
        subject = [c for c in view.children("V") if c["path"] == base + "mutant.bin" or
                   c["path"].startswith(base + "harness/")]
        bad = err or (not view.path(base + "replay.sh") and "replay.sh missing") or \
            (e["kind"] not in evidence.KINDS and f"kind {e['kind']!r} not in {evidence.KINDS}") or \
            (e["claim"] not in M.claim_ids(view.manifest) and f"unknown claim {e['claim']!r}") or \
            (not subject and "neither mutant.bin nor harness/") or \
            (any(c["hash"] in art for c in subject if c["path"].endswith("mutant.bin")) and
             "mutant.bin is byte-identical to the artefact")
        if bad:
            res.append(dict(e, outcome="malformed", detail=bad))
            continue
        if not execute:
            res.append(dict(e, outcome="not_run", detail="--no-exec"))
            continue
        rc, out, _, timed_out, wall = evidence.run_replay(view.dir, base + "replay.sh", outside)
        res.append(dict(e, replayed=True, wall_s=wall,
                        **evidence.judge_witness(e["kind"], rc, out, timed_out, ref.get("output_sha256") or "")))
    witnessed = {m["claim"] for m in res if m["outcome"] in evidence.WITNESS_KINDS}
    return res, sorted(set(M.claim_ids(view.manifest or {})) - witnessed)


def _pre_witness(view, execute, outside):
    script = PRE_WITNESS + "replay.sh"
    exp, err = view.json(PRE_WITNESS + "expected.json")
    if not view.path(script) or err:
        return False, {"detail": err or "no pre_witness/replay.sh"}
    if not execute:
        return False, {"detail": "--no-exec"}
    rc, out, _, timed_out, wall = evidence.run_replay(view.dir, script, outside)
    h = canon.sha256_bytes(out.encode())
    ok = rc == 0 and isinstance(exp, dict) and h == exp.get("output_sha256")
    return ok, {"exit": rc, "timed_out": timed_out, "output_sha256": h,
                "expected_sha256": exp.get("output_sha256") if isinstance(exp, dict) else None, "wall_s": wall}


# --- L3 ----------------------------------------------------------------------
def level3(view, oracle_pub: bytes, producer_pub: bytes) -> dict:
    phi, reqs = view.read(PHI), view.read(REQS)
    proven = canon.sha256_bytes(phi) if phi is not None else None
    req_h = canon.sha256_bytes(reqs) if reqs is not None else None
    out = {"status": "fail", "approved_hash": None, "proven_hash": proven,
           "requirements_hash": req_h, "approved_requirements_hash": None,
           "signer": None, "reason": None}
    sig = view.read(APPROVAL_SIG)
    if sig is None:
        return dict(out, reason="approval.sig absent or not hash-verified")
    if oracle_pub == producer_pub:
        return dict(out, reason="oracle key equals producer key (D4 requires separate keys)")
    appr, _ = view.json(APPROVAL_JSON)
    if isinstance(appr, dict) and isinstance(appr.get("phi_sha256"), str) \
            and isinstance(appr.get("requirements_sha256"), str):
        a_phi, a_req = appr["phi_sha256"], appr["requirements_sha256"]
    else:
        a_phi, a_req = proven, req_h
    if a_phi is None or a_req is None:
        return dict(out, reason="phi.json or requirements.md absent")
    msg = (a_phi + a_req).encode("ascii")
    out.update(approved_hash=a_phi, approved_requirements_hash=a_req)
    if ed25519.verify(oracle_pub, msg, sig):
        out["signer"] = "oracle"
    elif ed25519.verify(producer_pub, msg, sig):
        return dict(out, signer="producer", reason="approval signed by producer")
    else:
        return dict(out, reason="approval signature invalid under the oracle key")
    if a_phi != proven or a_req != req_h:
        return dict(out, reason="approved hash differs from proven hash (approved then changed)")
    return dict(out, status="pass")


# --- L4 ----------------------------------------------------------------------
def level4(view, execute: bool, outside: list[str], skip_provers: bool = False) -> dict:
    """Each deterministic run event lands in exactly one bucket: replayed and matched,
    replayed with a mismatch, skipped by the consumer (--l4-skip-provers), not
    replayable because it needs a path outside the bundle that no byte-identical
    bundle child can stand in for (never a pass, never a mismatch), or not replayed
    for another reason. A recorded outside input whose sha256 equals a verified
    bundle child is replayed from that child (a "stand-in", by hash alone)."""
    from .ledger_walk import walk
    data = view.read(LEDGER)
    out = {"status": "fail", "chain_intact": False, "events_total": 0, "deterministic_total": 0,
           "events_replayed": 0, "mismatches": [], "not_replayable_outside_bundle": [],
           "skipped_by_consumer": [], "replayed_with_stand_ins": [], "not_replayed": [],
           "inconsistent_outputs": []}
    if data is None:
        return dict(out, detail="provenance/ledger.jsonl absent or not hash-verified")
    events, errs = walk(data)
    out.update(chain_intact=not errs, chain_errors=errs, events_total=len(events))
    det = [e for e in events if e.get("kind") == "run" and e.get("deterministic") is True]
    out["deterministic_total"] = len(det)
    by_path: dict[str, list] = {}
    by_hash = {}
    for c in view.children():
        if view.path(c["path"]):
            by_hash.setdefault(c.get("hash"), c["path"])
    for ev in det:
        stand_ins, paths, why = plan_event(ev, by_hash)
        if errs:
            out["not_replayed"].append({"seq": ev["seq"], "reason": "chain broken"})
        elif skip_provers and is_prover_event(ev):
            out["skipped_by_consumer"].append({"seq": ev["seq"], "reason": "not replayed: skipped by consumer"})
        elif paths:
            kind = "input" if set(paths) - {"outputs"} else "output"
            out["not_replayable_outside_bundle"].append(
                {"seq": ev["seq"], "reason": f"not_replayable: {kind} outside bundle", "paths": paths, "why": why})
            for ps in paths.values():
                for q in ps:
                    by_path.setdefault(q, []).append(ev["seq"])
        else:
            r = _replay(view, ev, execute, outside, stand_ins)
            if isinstance(r, dict):
                out["events_replayed"] += 1
                if stand_ins:
                    out["replayed_with_stand_ins"].append({"seq": ev["seq"], "stand_ins": stand_ins})
                if r:
                    out["mismatches"].append(dict(r, seq=ev["seq"], used_stand_ins=bool(stand_ins)))
            else:
                out["not_replayed"].append({"seq": ev["seq"], "reason": r})
    for q, seqs in sorted(by_path.items()):
        outside.append(f"ledger events {sorted(set(seqs))} depend on {q}, outside the bundle (not replayed)")
    out["counts"] = {"replayed_matched": out["events_replayed"] - len(out["mismatches"]),
                     "replayed_mismatched": len(out["mismatches"]),
                     "not_replayable_outside_bundle": len(out["not_replayable_outside_bundle"]),
                     "skipped_by_consumer": len(out["skipped_by_consumer"]),
                     "not_replayed_other": len(out["not_replayed"])}
    last_written = {}
    for ev in events:
        for o in ev.get("outputs") or []:
            if isinstance(o, dict) and isinstance(o.get("path"), str):
                last_written[o["path"]] = o.get("sha256")
    out["inconsistent_outputs"] = [
        {"path": c["path"], "ledger_says": last_written[c["path"]], "bundle_has": c["hash"]}
        for c in view.children() if c["path"] in last_written and last_written[c["path"]] != c["hash"]]
    if errs or out["mismatches"] or out["inconsistent_outputs"] or not events:
        out["status"] = "fail"
    elif out["not_replayed"] or out["not_replayable_outside_bundle"] or out["skipped_by_consumer"] or not det:
        out["status"] = "partial"
    else:
        out["status"] = "pass"
    return out


def _escapes(path, cwd: str = ".") -> bool:
    if not isinstance(path, str):
        return True
    if path.startswith(("/", "~")):
        return True
    norm = posixpath.normpath(posixpath.join(cwd, path))
    return norm == ".." or norm.startswith("../")


PROVER_WORDS = ("docker", "kprove", "run-claim.sh", "lake", "lean", "kevm")


def is_prover_event(ev: dict) -> bool:
    """A prover/container run: docker image Id as tool hash, or a prover named in tool/argv."""
    th, tool = str(ev.get("tool_hash") or ""), str(ev.get("tool") or "").lower()
    names = {posixpath.basename(a) for a in ev.get("argv") or [] if isinstance(a, str)}
    return th.startswith("sha256:") or any(w in tool for w in PROVER_WORDS) or \
        any(n in PROVER_WORDS for n in names)


def plan_event(ev: dict, by_hash: dict) -> tuple[dict, dict, dict]:
    """(stand_ins {outside rel path: bundle child}, blocking paths by field, why per path).
    Ledger paths are root-relative; argv paths are relative to cwd. An argv element
    counts as a path if it (or its --opt= value) contains '/' or is '..'. An outside
    input is replayable only when it is relative and its recorded sha256 equals a
    verified bundle child; absolute paths and outputs outside the bundle never are."""
    cwd = ev.get("cwd") if isinstance(ev.get("cwd"), str) else "."
    found, why, stand_ins = {}, {}, {}

    def block(field, path, reason):
        found.setdefault(field, []).append(str(path))
        why.setdefault(str(path), reason)  # the first (most specific) reason wins
    if _escapes(cwd):
        block("cwd", cwd, "cwd outside the bundle")
    for x in ev.get("inputs") or []:
        path = x.get("path") if isinstance(x, dict) else x
        if not _escapes(path):
            continue
        if not isinstance(path, str) or path.startswith(("/", "~")):
            block("inputs", path, "absolute path")
        elif not isinstance(x.get("sha256"), str):
            block("inputs", path, "hash not recorded")
        elif x["sha256"] not in by_hash:
            block("inputs", path, "no bundle child has the recorded sha256")
        else:
            stand_ins[posixpath.normpath(path)] = by_hash[x["sha256"]]
    outs = [x.get("path") if isinstance(x, dict) else x for x in ev.get("outputs") or []]
    for path in outs + [ev[k] for k in ("stdout", "stderr") if ev.get(k) is not None]:
        if _escapes(path):
            block("outputs", path, "output outside the bundle")
    for a in ev.get("argv") or []:
        if not isinstance(a, str) or " " in a:  # shell strings are not parsed
            continue
        v = a.split("=", 1)[1] if a.startswith("-") and "=" in a else a
        if ("/" in v or v == "..") and _escapes(v, cwd if not _escapes(cwd) else "."):
            target = posixpath.normpath(posixpath.join(cwd, v)) if not v.startswith(("/", "~")) else None
            if target not in stand_ins:
                block("argv", a, "absolute path" if target is None else "not a recorded input with a stand-in")
    return ({} if found else stand_ins), found, why


def _replay(view, ev, execute, outside, stand_ins=None):
    """{} = replayed and matched; {..} = mismatch details; str = why not replayed.
    Callers have already excluded events needing paths no stand-in covers. The
    bundle copy is nested deep enough that every stand-in lands inside the sandbox."""
    argv = ev.get("argv")
    if not execute:
        return "--no-exec"
    if not (isinstance(argv, list) and argv and all(isinstance(a, str) for a in argv)):
        return "argv malformed"
    tool, th = shutil.which(argv[0]), ev.get("tool_hash")
    if not tool:
        return f"tool {argv[0]!r} not on PATH"
    tool_ok = canon.sha256_file(os.path.realpath(tool)) == th  # ledger.py's default: the program run
    if not tool_ok and isinstance(th, str) and th.startswith("sha256:"):  # a docker image Id
        rc, out, _, _, _ = checkers.run(["docker", "image", "inspect", th], timeout=120)
        try:
            tool_ok = rc == 0 and json.loads(out)[0].get("Id") == th
        except (ValueError, IndexError, AttributeError):
            tool_ok = False
        if tool_ok:
            outside.append(f"docker image {th} (tool of replayed ledger events)")
    if not tool_ok:  # a script named in argv and recorded as an input with that hash
        recorded = {posixpath.normpath(posixpath.join(ev.get("cwd") or ".", a)) for a in argv[1:]}
        tool_ok = any(isinstance(i, dict) and i.get("sha256") == th and isinstance(i.get("path"), str)
                      and posixpath.normpath(i["path"]) in recorded for i in ev.get("inputs") or [])
    if not tool_ok:
        return f"tool {argv[0]!r} not available by hash {th}"
    for i in ev.get("inputs") or []:
        if isinstance(i.get("path"), str) and posixpath.normpath(i["path"]) in (stand_ins or {}):
            continue  # byte-identical by construction (plan_event matched the recorded sha256)
        p = view.path(i.get("path", ""))
        if not p or canon.sha256_file(p) != i.get("sha256"):
            return f"input {i.get('path')} not in the bundle with the recorded hash"
    cwd = ev.get("cwd") or "."
    outside.append(f"{os.path.realpath(tool)} (sha256 {ev['tool_hash']}) used to replay ledger events")
    with tempfile.TemporaryDirectory() as tmp:
        depth = max([len(p.split("/")) for p in stand_ins or {}] + [0])
        work = view.copy_to(os.path.join(tmp, *[f"up{i}" for i in range(depth)], "bundle"))
        for rel, child in (stand_ins or {}).items():
            dst = os.path.normpath(os.path.join(work, rel))
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(view.path(child), dst)
        for o in ev.get("outputs") or []:  # outputs must be produced by the replay itself
            p = os.path.join(work, o.get("path", ""))
            if os.path.isfile(p):
                os.remove(p)
        streams, err_path = {}, os.path.join(tmp, "replay.stderr")
        for k in ("stdout", "stderr"):
            if isinstance(ev.get(k), str):
                os.makedirs(os.path.dirname(os.path.join(work, ev[k])) or work, exist_ok=True)
                streams[k] = open(os.path.join(work, ev[k]), "wb")
        if "stderr" not in streams:  # kept for the mismatch report only
            streams["stderr"] = open(err_path, "wb")
            err_file = err_path
        else:
            err_file = os.path.join(work, ev["stderr"])
        try:
            p = subprocess.run(argv, cwd=os.path.join(work, cwd), timeout=3600,
                               env={"PATH": os.environ.get("PATH", ""), "HOME": tmp},
                               stdout=streams.get("stdout", subprocess.DEVNULL),
                               stderr=streams.get("stderr", subprocess.DEVNULL))
            rc, timed_out = p.returncode, False
        except subprocess.TimeoutExpired:
            rc, timed_out = None, True
        except OSError:
            rc, timed_out = 127, False
        finally:
            for fh in streams.values():
                fh.close()
        diff = {}
        if rc != ev.get("exit"):
            diff["exit"] = {"recorded": ev.get("exit"), "replayed": rc, "timed_out": timed_out}
        for o in ev.get("outputs") or []:
            p = os.path.join(work, o.get("path", ""))
            got = canon.sha256_file(p) if os.path.isfile(p) else None
            if got != o.get("sha256"):
                diff.setdefault("outputs", []).append({"path": o.get("path"), "recorded": o.get("sha256"),
                                                       "replayed": got})
        if diff and os.path.isfile(err_file):
            with open(err_file, "rb") as f:
                diff["replay_stderr_tail"] = f.read()[-600:].decode(errors="replace")
    return diff
