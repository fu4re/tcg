"""Bundle assembler: workspace inputs -> bundles/<name>/ (protocol.md section 14).

    python tools/bundle.py --out bundles/<name> --artifact subjects/capped_token/CappedToken.sol
        --spec specs/phi.sol --mutants mutants/mutants.json --witnesses W.json
        --adversary-id ID --adversary-source tools/adversary.py
        --adversary-seed N --adversary-budget N
        [--check-json check.json] [--timeout-ms N] [--wall-timeout-s S]
        [--feedback feedback.json] [--root DIR]

Bundle layout (every path relative to the bundle directory):

    manifest.json              the manifest (schemas/manifest.schema.json)
    b/CappedToken.sol          b, verbatim
    phi/Spec.sol               phi, verbatim
    c/<check>/solc_input.json  per check_* of phi (Check v2): the exact solc
                               standard-JSON input of its isolated harness over b,
                               canonical JSON (file sha256 = solc_input_sha256)
    c/<check>/solc_output.json solc's raw stdout for it, verbatim
    mutants/<id>.sol           every included mutant source, named by its id
    core/specgame_core.py      the core the bundle was produced with (audit copy)

What the producer re-establishes before anything goes in (the verifier repeats
all of it from the bundle alone):

- Check(b, phi), protocol v2: run here with core.smtcheck_isolated (no cache),
  or taken from `check.py --json` (mode isolated) after every per-check solc
  input is re-derived from b and phi and compared;
- M: only `included` mutants of mutants.json; every id recomputed from the
  source and compared, base compared with b, every properness sigma replayed
  (run(b, s) != run(m, s), observation hashes compared with mutants.json);
- W: every presented pair re-evaluated with core.evaluate_witness on Spec over
  its mutant; pairs that do not end in a violation (or name a mutant outside
  M) go to `evidence.discarded` with the outcomes, never into W;
- claimed: ms_cert = {killed, total} and the kill set computed from W.

Mutant paths in mutants.json are resolved against --root (default: the
specgame/ directory). Deterministic: the same inputs give a byte-identical
bundle (sorted keys, sorted W, no timestamps, no absolute paths).

Restamp (`python tools/bundle.py --restamp bundles/<name>`): rewrite only the
provenance layer, the core audit copy and the `files` table of an existing
bundle, after a change that leaves every verdict-relevant input unchanged
(e.g. protocol.md prose, the verifier's or the core's source text). Nothing is
re-run: Check, the adversary, W and the properness pairs are reused as
bundled. Refused (bundle left untouched) unless every listed file matches its
hash, the current core re-derives the same b and Spec-over-b runtime ids, the
same checks, the byte-identical solc input of c and the same mutant ids, and
the semantics version (solc, z3, python, pyrevm, evm_version, spec_id, gas,
block env, chain id) is unchanged; only core_sha256 / core_version may move.
The verifier remains the only full check.

`--migrate-executor-limits` additionally lets `executor_limits` move (core v2:
lifted code size limit for the Spec harness, deploy gas). It is accepted only
with a proof inside the bundle: every properness σ is run on b and on its
mutant, and every witness σ on Spec-over-its-mutant for every check, under the
core v1 executor (legacy_executor=True) and the current one; every observation
must be identical, else the restamp is refused.

Exit codes: 0 bundle written, 1 input error (nothing written).
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import tempfile
import time
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402
import runstore  # noqa: E402  (check.json or check.json.gz)
import verify  # noqa: E402  (schema validator; the verifier's own source is hashed into provenance)

DEFAULT_TIMEOUT_MS = core.CHECK_TIMEOUT_MS          # protocol.json "check"
DEFAULT_WALL_TIMEOUT_S = core.CHECK_WALL_TIMEOUT_S

B_DIR = "b"  # b/<subject contract file>
PHI_PATH = "phi/Spec.sol"
C_INPUT_PATH = "c/{check}/solc_input.json"
C_OUTPUT_PATH = "c/{check}/solc_output.json"
CORE_PATH = "core/specgame_core.py"
PROFILE_PATH = "subject/profile.json"  # the subject's profile, pinned by protocol.json


class BundleError(Exception):
    pass


def _log(msg: str) -> None:
    print(f"bundle: {msg}", file=sys.stderr)


def derive_check_inputs(phi_text: str, b_text: str, timeout_ms: int, subject=None) -> list[tuple[str, dict]]:
    """(check, exact solc input) per check_* of phi: the isolated harness over b."""
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    return [(n, core.solc_input({core.SPEC_UNIT: core.isolated_harness(t, subj), subj.unit: b_text},
                                core.model_checker_settings(timeout_ms)))
            for n, t in core.check_functions(phi_text, subj)]


def _check_result(a, b_text: str, phi_text: str) -> dict:
    """Hard layer c (Check v2): per check, the exact solc input, its sha256, raw
    output and verdict; plus the combined verdict."""
    if a.check_json is None:
        c = asdict(core.smtcheck_isolated(a.spec, a.artifact, a.timeout_ms, a.wall_timeout_s, cache_dir=None,
                                          subject=a.subject))
    else:
        doc = runstore.read_check_json(a.check_json)
        c = doc.get("check", doc)
        if c.get("mode") != "isolated":
            raise BundleError("Check result is not protocol v2 (mode isolated); re-run check.py")
    want = derive_check_inputs(phi_text, b_text, c["timeout_ms"], a.subject)
    if [n for n, _ in want] != [row["check"] for row in c["checks"]]:
        raise BundleError("Check result's checks are not the check_* functions of --spec")
    for (n, inp), row in zip(want, c["checks"]):
        r = row["result"]
        if core.canonical_json(inp) != core.canonical_json(r["solc_input"]) or core.json_sha256(inp) != r["solc_input_sha256"]:
            raise BundleError(f"Check result for {n}: solc input is not the one derived from --artifact and --spec")
    return c


def _load_mutants(a, b_entry: dict, val: verify.SchemaValidator) -> list[dict]:
    doc = json.loads(a.mutants.read_text())
    errs = val.validate(doc, "mutants.schema.json")
    if errs:
        raise BundleError(f"{a.mutants}: schema: {errs[:5]}")
    base = doc["base"]
    if base["source_sha256"] != b_entry["source_sha256"] or base["runtime_sha256"] != b_entry["runtime_sha256"]:
        raise BundleError(f"{a.mutants}: base is not --artifact (source or runtime sha256 differs)")
    out, seen = [], {b_entry["runtime_sha256"]}
    for mu in doc["mutants"]:
        if mu["status"] != "included":
            _log(f"mutant {mu['id'][:12]} excluded ({mu.get('exclusion_reason')}), not in M")
            continue
        path = (a.root / mu["path"]).resolve()
        text = path.read_text()
        if core.sha256_hex(text.encode()) != mu["source_sha256"]:
            raise BundleError(f"mutant {mu['id'][:12]}: source sha256 of {mu['path']} differs from mutants.json")
        ent = core.compile_artifact(path, subject=a.subject)
        if ent["runtime_sha256"] != mu["id"]:
            raise BundleError(f"mutant {mu['path']}: recomputed id {ent['runtime_sha256'][:12]} != {mu['id'][:12]}")
        if mu["id"] in seen:
            raise BundleError(f"mutant {mu['id'][:12]}: duplicate id (or equal to b)")
        seen.add(mu["id"])
        p = mu["properness"]
        ob, om = core.run_sequence(b_entry, p["sigma"]), core.run_sequence(ent, p["sigma"])
        if core.observation_equal(ob, om):
            raise BundleError(f"mutant {mu['id'][:12]}: properness sigma gives equal observations")
        if (ob.sha256(), om.sha256()) != (p["obs_base_sha256"], p["obs_mutant_sha256"]):
            raise BundleError(f"mutant {mu['id'][:12]}: properness observation hashes differ from mutants.json")
        out.append({"id": mu["id"], "text": text, "entry": ent, "path": path,
                    "operator": mu["operator"], "fault_class": mu["fault_class"],
                    "properness_sigma": [p["sigma"]]})
    if not out:
        raise BundleError("no included mutant: ms_cert would have total 0")
    return sorted(out, key=lambda m: m["id"])


def _sort_key(w: dict) -> tuple[str, bytes]:
    return w["mutant"], core.canonical_json(w)


def _witnesses(a, mutants: list[dict], val: verify.SchemaValidator) -> tuple[list, list]:
    doc = json.loads(a.witnesses.read_text())
    ws = doc["W"] if isinstance(doc, dict) else doc
    uniq: dict[bytes, dict] = {}
    for i, w in enumerate(ws):
        errs = val.validate(w, "witness.schema.json")
        if errs:
            raise BundleError(f"{a.witnesses}[{i}]: schema: {errs[:5]}")
        core.validate_sigma(w["sigma"], need_probe=True, subject=a.subject)
        uniq.setdefault(core.canonical_json(w), w)
    by_id = {m["id"]: m for m in mutants}
    spec_over: dict[str, dict] = {}
    keep, discarded = [], []
    for w in sorted(uniq.values(), key=_sort_key):
        m = by_id.get(w["mutant"])
        if m is None:
            discarded.append({"witness": w, "reason": "mutant not in M"})
            continue
        if m["id"] not in spec_over:
            spec_over[m["id"]] = core.compile_spec_over(a.spec, m["path"], subject=a.subject)
        ev = core.evaluate_witness(spec_over[m["id"]], w["sigma"])
        if ev.violated:
            keep.append(w)
        else:
            why = verify.discard_reason(ev)
            discarded.append({"witness": w, "reason": why})
            _log(f"witness for {w['mutant'][:12]} discarded: {why}")
    return keep, discarded


def assemble(a) -> dict[str, bytes]:
    """All bundle files (path -> bytes), manifest.json included."""
    val = verify.SchemaValidator(verify.SCHEMA_DIR)
    b_text, phi_text = a.artifact.read_text(), a.spec.read_text()
    subj = core.load_subject(a.subject)
    b_path = f"{B_DIR}/{subj.unit}"
    b_entry = core.compile_artifact(a.artifact, subject=subj)
    pair = core.compile_spec_over(a.spec, a.artifact, subject=subj)
    c = _check_result(a, b_text, phi_text)
    if c["verdict"] != core.Verdict.ACCEPT.value:
        _log(f"WARNING: Check(b, phi) = {c['verdict']} ({c['reason']}); the verifier will not certify this bundle")
    mutants = _load_mutants(a, b_entry, val)
    W, discarded = _witnesses(a, mutants, val)
    kill = sorted({w["mutant"] for w in W})

    adv_src = core.sha256_file(a.adversary_source)
    feedback = json.loads(a.feedback.read_text()) if a.feedback else None
    files: dict[str, bytes] = {
        b_path: b_text.encode(),
        PHI_PATH: phi_text.encode(),
        CORE_PATH: Path(core.__file__).read_bytes(),
        PROFILE_PATH: (core.ROOT / core.PROTOCOL["subjects"][subj.name]["profile"]).read_bytes(),
    }
    c_rows = []
    for row in c["checks"]:
        r, n = row["result"], row["check"]
        files[C_INPUT_PATH.format(check=n)] = core.canonical_json(r["solc_input"])
        files[C_OUTPUT_PATH.format(check=n)] = r["raw_output"].encode()
        c_rows.append({"check": n, "solc_input_path": C_INPUT_PATH.format(check=n),
                       "solc_input_sha256": r["solc_input_sha256"],
                       "solc_output_path": C_OUTPUT_PATH.format(check=n),
                       "verdict": r["verdict"], "reason": r["reason"]})
    for m in mutants:
        files[f"mutants/{m['id']}.sol"] = m["text"].encode()
    manifest = {
        "version": 1,
        "files": {p: core.sha256_hex(data) for p, data in sorted(files.items())},
        "hard": {
            "b": {"path": b_path, "source_sha256": b_entry["source_sha256"],
                  "runtime_sha256": b_entry["runtime_sha256"]},
            "phi": {"path": PHI_PATH, "source_sha256": pair["spec_source_sha256"],
                    "pair_runtime_sha256": pair["runtime_sha256"], "checks": pair["checks"]},
            "c": {"mode": "isolated", "command": ["solc", "--standard-json"],
                  "verdict": c["verdict"], "reason": c["reason"], "timeout_ms": c["timeout_ms"],
                  "wall_timeout_s": c["wall_timeout_s"], "checks": c_rows},
        },
        "evidence": {
            "M": [{"id": m["id"], "path": f"mutants/{m['id']}.sol",
                   "properness_sigma": m["properness_sigma"]} for m in mutants],
            "W": W,
            "adversary": {"id": a.adversary_id, "source_sha256": adv_src,
                          "seed": a.adversary_seed, "B_A": a.adversary_budget},
            "discarded": discarded,
        },
        "metadata": {"mutants": [{"id": m["id"], "operator": m["operator"],
                                  "fault_class": m["fault_class"]} for m in mutants]},
        "provenance": {
            "toolchain": core.toolchain_fingerprint(),
            "core_path": CORE_PATH,
            "core_sha256": core.sha256_file(core.__file__),
            "verifier_sha256": core.sha256_file(verify.__file__),
            "subject": subj.name,
            "subject_profile_path": PROFILE_PATH,
            "protocol_json_sha256": core.sha256_file(verify.PROTOCOL_JSON),
            "protocol_md_sha256": core.sha256_file(verify.PROTOCOL_MD),
            "feedback": feedback,
        },
        "claimed": {"ms_cert": {"killed": len(kill), "total": len(mutants)}, "kill_set": kill},
        "not_claimed": [verify.V_COMPLETENESS],
    }
    errs = val.validate(manifest, "manifest.schema.json")
    if errs:
        raise BundleError(f"assembled manifest violates the schema: {errs[:5]}")
    files[verify.MANIFEST] = (json.dumps(manifest, indent=1, sort_keys=True) + "\n").encode()
    return files


def write_bundle(files: dict[str, bytes], out: Path) -> None:
    """Write into a fresh temp dir next to `out`, then swap it in."""
    out = out.resolve()
    if out.exists() and not (out / verify.MANIFEST).is_file() and any(out.iterdir()):
        raise BundleError(f"{out} exists, is not empty and is not a bundle; refusing to overwrite")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = Path(tempfile.mkdtemp(prefix=f".{out.name}.", dir=out.parent))
    try:
        for p, data in sorted(files.items()):
            f = tmp / p
            f.parent.mkdir(parents=True, exist_ok=True)
            f.write_bytes(data)
        if out.exists():
            shutil.rmtree(out)
        tmp.rename(out)
    finally:
        if tmp.exists():
            shutil.rmtree(tmp)


FINGERPRINT_MAY_CHANGE = {"core_sha256", "core_version"}
EXECUTOR_MIGRATION_KEYS = {"executor_limits"}  # core v1 -> v2, only with the equal-observation proof


def executor_migration_proof(bdir: Path, m: dict, subj) -> dict:
    """Every σ of the bundle under the core v1 executor and the current one:
    identical observations, or BundleError."""
    hard = m["hard"]
    b_entry = core.compile_artifact(bdir / hard["b"]["path"], subject=subj)
    ments = {mu["id"]: core.compile_artifact(bdir / mu["path"], subject=subj) for mu in m["evidence"]["M"]}
    paths = {mu["id"]: bdir / mu["path"] for mu in m["evidence"]["M"]}
    n = 0

    def same(entry, sigma, check, what):
        nonlocal n
        o_old = core.run_sequence(entry, sigma, probe_check=check, legacy_executor=True)
        o_new = core.run_sequence(entry, sigma, probe_check=check)
        n += 1
        if not core.observation_equal(o_old, o_new):
            raise BundleError(f"executor migration: {what} observes differently under core v1 and v2")
    for mu in m["evidence"]["M"]:
        for j, sigma in enumerate(mu["properness_sigma"]):
            same(b_entry, sigma, None, f"b on properness σ {j} of {mu['id'][:12]}")
            same(ments[mu["id"]], sigma, None, f"mutant {mu['id'][:12]} on properness σ {j}")
    for i, w in enumerate(m["evidence"]["W"]):
        pair = core.compile_spec_over(bdir / hard["phi"]["path"], paths[w["mutant"]], subject=subj)
        for check in pair["checks"]:
            same(pair, w["sigma"], check, f"witness {i} ({check})")
    return {"observations_compared": n}


def restamp(bdir: Path, migrate_executor_limits: bool = False) -> dict[str, bytes]:
    """New bundle files for `bdir` with current provenance (see module doc)."""
    val = verify.SchemaValidator(verify.SCHEMA_DIR)
    m = json.loads((bdir / verify.MANIFEST).read_text())
    present = {str(p.relative_to(bdir)) for p in bdir.rglob("*") if p.is_file()} - {verify.MANIFEST}
    if present != set(m["files"]):
        raise BundleError(f"files on disk differ from the manifest: {sorted(present ^ set(m['files']))[:5]}")
    files = {p: (bdir / p).read_bytes() for p in m["files"]}
    for p, h in m["files"].items():
        if core.sha256_hex(files[p]) != h:
            raise BundleError(f"{p}: bytes do not match the manifest; restamp refuses a modified bundle")
    hard, prov = m["hard"], m["provenance"]
    subj = core.load_subject(prov.get("subject"))
    b_text, phi_text = files[hard["b"]["path"]].decode(), files[hard["phi"]["path"]].decode()
    with tempfile.TemporaryDirectory(prefix="specgame-restamp-") as tmp:
        bp, sp = Path(tmp) / "b.sol", Path(tmp) / "phi.sol"
        bp.write_text(b_text)
        sp.write_text(phi_text)
        b_entry = core.compile_artifact(bp, subject=subj)
        pair = core.compile_spec_over(sp, bp, subject=subj)
        if b_entry["runtime_sha256"] != hard["b"]["runtime_sha256"]:
            raise BundleError("b: the current core derives a different runtime id")
        if (pair["runtime_sha256"], pair["checks"]) != (hard["phi"]["pair_runtime_sha256"], hard["phi"]["checks"]):
            raise BundleError("phi: the current core derives a different Spec-over-b id or check list")
        c = hard["c"]
        want = derive_check_inputs(phi_text, b_text, c["timeout_ms"], subj)
        if [n for n, _ in want] != [row["check"] for row in c["checks"]]:
            raise BundleError("c: the current core derives a different list of checks")
        for (n, inp), row in zip(want, c["checks"]):
            if core.canonical_json(inp) != files[row["solc_input_path"]] \
                    or core.json_sha256(inp) != row["solc_input_sha256"]:
                raise BundleError(f"c[{n}]: the current core derives a different solc input; "
                                  "Check would have to be re-run")
        for mu in m["evidence"]["M"]:
            mp = Path(tmp) / f"{mu['id']}.sol"
            mp.write_bytes(files[mu["path"]])
            if core.compile_artifact(mp, subject=subj)["runtime_sha256"] != mu["id"]:
                raise BundleError(f"mutant {mu['id'][:12]}: the current core derives a different id")
    fp = core.toolchain_fingerprint()
    old = prov["toolchain"]
    may = FINGERPRINT_MAY_CHANGE | (EXECUTOR_MIGRATION_KEYS if migrate_executor_limits else set())
    moved = sorted(k for k in set(fp) | set(old) if fp.get(k) != old.get(k) and k not in may)
    if moved:
        raise BundleError(f"semantics version changed in {moved}; rebuild the bundle, do not restamp")
    if migrate_executor_limits and fp.get("executor_limits") != old.get("executor_limits"):
        proof = executor_migration_proof(bdir, m, subj)
        print(f"bundle: restamp {bdir}: executor migration proof: {proof['observations_compared']} "
              f"observations identical under core v1 and v2", file=sys.stderr)
    files[CORE_PATH] = Path(core.__file__).read_bytes()
    profile = (core.ROOT / core.PROTOCOL["subjects"][subj.name]["profile"]).read_bytes()
    if prov.get("subject_profile_path") in files and files[prov["subject_profile_path"]] != profile:
        raise BundleError("the bundled subject profile differs from the pinned one; rebuild, do not restamp")
    files[PROFILE_PATH] = profile
    new_prov = {k: v for k, v in prov.items() if k != "protocol_sha256"}
    new_prov.update(toolchain=fp, core_sha256=core.sha256_file(core.__file__), subject=subj.name,
                    subject_profile_path=PROFILE_PATH,
                    verifier_sha256=core.sha256_file(verify.__file__),
                    protocol_json_sha256=core.sha256_file(verify.PROTOCOL_JSON),
                    protocol_md_sha256=core.sha256_file(verify.PROTOCOL_MD))
    m["provenance"] = new_prov
    m["files"] = {p: core.sha256_hex(data) for p, data in sorted(files.items())}
    errs = val.validate(m, "manifest.schema.json")
    if errs:
        raise BundleError(f"restamped manifest violates the schema: {errs[:5]}")
    files[verify.MANIFEST] = (json.dumps(m, indent=1, sort_keys=True) + "\n").encode()
    return files


def restamp_main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description="restamp the provenance of existing bundles")
    ap.add_argument("--restamp", type=Path, nargs="+", required=True, metavar="BUNDLE")
    ap.add_argument("--migrate-executor-limits", action="store_true",
                    help="core v1 -> v2: allow executor_limits to move, with the equal-observation proof")
    a = ap.parse_args(argv)
    code = 0
    for bdir in a.restamp:
        t0 = time.monotonic()
        try:
            old = (bdir / verify.MANIFEST).read_bytes()
            files = restamp(bdir, a.migrate_executor_limits)
            if files[verify.MANIFEST] == old:
                print(f"bundle: restamp {bdir}: already current ({time.monotonic() - t0:.2f} s)")
                continue
            write_bundle(files, bdir)
        except (BundleError, core.CompileError, core.ProfileError, core.ExecutorError, core.SigmaError,
                OSError, ValueError, KeyError) as e:
            print(f"bundle: restamp {bdir}: REFUSED: {e}", file=sys.stderr)
            code = 1
            continue
        print(f"bundle: restamp {bdir}: provenance rewritten ({time.monotonic() - t0:.2f} s)")
    return code


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, required=True, help="bundle directory to (re)write")
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--artifact", type=Path, required=True, help="b")
    ap.add_argument("--spec", type=Path, required=True, help="phi")
    ap.add_argument("--mutants", type=Path, required=True, help="mutants.json (schemas/mutants.schema.json)")
    ap.add_argument("--root", type=Path, default=core.ROOT, help="base for mutant paths in mutants.json")
    ap.add_argument("--witnesses", type=Path, required=True, help="JSON list of witnesses (or {\"W\": [...]})")
    ap.add_argument("--adversary-id", required=True)
    ap.add_argument("--adversary-source", type=Path, required=True, help="file whose sha256 is recorded")
    ap.add_argument("--adversary-seed", type=int, required=True)
    ap.add_argument("--adversary-budget", type=int, required=True, help="B_A")
    ap.add_argument("--check-json", type=Path, help="check.py --json output, or its runs/ form check.json.gz (else Check is run here)")
    ap.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    ap.add_argument("--wall-timeout-s", type=float, default=DEFAULT_WALL_TIMEOUT_S)
    ap.add_argument("--feedback", type=Path, help="JSON: condition, round, seed, model, temperature, "
                                                  "prompts_sha256 (omit for a hand-written spec)")
    return ap


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if "--restamp" in argv:
        return restamp_main(argv)
    try:
        a = parser().parse_args(argv)
    except SystemExit as e:
        return 1 if e.code else 0
    try:
        files = assemble(a)
        write_bundle(files, a.out)
    except (BundleError, core.CompileError, core.SigmaError, core.ExecutorError,
            OSError, ValueError, KeyError) as e:
        print(f"bundle: ERROR: {e}", file=sys.stderr)
        return 1
    m = json.loads(files[verify.MANIFEST])
    ms = m["claimed"]["ms_cert"]
    print(f"bundle: wrote {a.out} ({len(files)} files): Check {m['hard']['c']['verdict']}, "
          f"|M| = {ms['total']}, |W| = {len(m['evidence']['W'])}, "
          f"discarded {len(m['evidence']['discarded'])}, ms_cert = {ms['killed']}/{ms['total']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
