"""Build the mutation class M with properness evidence (WP2; protocol.md
sections 6 and 10; note Def. 4.1-4.2, open question 10).

    python tools/properness.py [--base subjects/capped_token/CappedToken.sol] [--mutants mutants]
        [--seed 0] [--budget 2000] [--max-txs 6]
        [--out mutants/mutants.json] [--log build/properness_log.json]

For every `mutants/m*.sol` (sorted by file name):

1. labels from the header comment (`// operator:`, `// fault_class:`,
   `// fault:`, optional `// expected_unkillable:`); a file without operator
   or fault_class is an error in the library, not a mutant;
2. compile with the core (`compile_artifact`); id = runtime sha256. An id
   equal to b's or to an earlier mutant's is **rejected**: logged, not in M;
   a file that does not compile has no id and is logged only;
3. excluded (in mutants.json with `status: excluded`): artifact lint fails
   (`lint`), public ABI differs from b's (`abi_differs`), the first differing
   σ fails to deploy the mutant (`does_not_deploy`), no differing σ within
   the budget (`no_properness_pair`);
4. differential search: σ_0, σ_1, ... from `seqgen` (seed, max_txs; the same
   σ list for every mutant, no probe), `observation_equal(run(b, σ), run(m, σ))`
   via the core; the first σ with unequal observations is the candidate pair;
5. the candidate is re-checked by a second, independent replay (both
   artifacts recompiled from source, σ round-tripped through its canonical
   JSON, fresh EVMs); both replays must give the same observation hashes and
   those must differ, else the build fails (executor nondeterminism is a bug,
   not a verdict);
6. behavioural duplicates (protocol.md section 10): included m, m' are flagged
   iff `run(m, σ) = run(m', σ)` on every σ in the union of their properness
   pairs; marked in `behavioural_duplicate_of`, never merged. For a flagged
   pair the log also records the first σ of the same stream that separates
   the two (`separation`, informational: the flag is relative to the recorded
   σ set, not a claim of equivalence).

Outputs are deterministic (no timestamps, no timings): `mutants.json`
(schemas/mutants.schema.json) and the log (parameters, distribution id,
toolchain fingerprint, every rejected / excluded mutant with its reason and
every pair with its two replays' observation hashes). Exit 0 = built,
1 = build error (the message names it), 2 = usage.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqgen  # noqa: E402
import specgame_core as core  # noqa: E402
import speclint  # noqa: E402

DEFAULT_SEED = 0
DEFAULT_BUDGET = 2000
DEFAULT_BASE = core.ROOT / "subjects" / "capped_token" / "CappedToken.sol"
DEFAULT_MUTANTS = core.ROOT / "subjects" / "capped_token" / "mutants"
DEFAULT_OUT = DEFAULT_MUTANTS / "mutants.json"
DEFAULT_LOG = core.ROOT / "build" / "properness_log.json"

LABELS = ("operator", "fault_class", "fault", "expected_unkillable")
_LABEL_RE = re.compile(r"^//\s*(" + "|".join(LABELS) + r"):\s*(.+?)\s*$")


class BuildError(Exception):
    pass


def rel(p: Path) -> str:
    p = Path(p).resolve()
    try:
        return str(p.relative_to(core.ROOT))
    except ValueError:
        return str(p)


def parse_labels(text: str) -> dict:
    """T* labels from the leading `// key: value` comment lines."""
    labels = {}
    for line in text.splitlines():
        m = _LABEL_RE.match(line.strip())
        if m:
            labels[m.group(1)] = m.group(2)
    return labels


def abi_key(entry: dict) -> str:
    return core.canonical_json(sorted(entry["abi"], key=lambda x: json.dumps(x, sort_keys=True))).decode()


def first_difference(o1: core.Observation, o2: core.Observation) -> str:
    """Where two observations first differ, for logs and reports (never a verdict)."""
    def show(step: dict | None) -> str:
        if step is None:
            return "absent"
        if step["outcome"] == "success" and step["return"]:
            v = int(step["return"], 16)
            return f"success:{v if v < 2**64 else hex(v)}"
        return step["outcome"]
    a, b = o1.data, o2.data
    if a["deploy"] != b["deploy"]:
        return f"deploy: {show(a['deploy'])} vs {show(b['deploy'])}"
    for i in range(max(len(a["txs"]), len(b["txs"]))):
        x = a["txs"][i] if i < len(a["txs"]) else None
        y = b["txs"][i] if i < len(b["txs"]) else None
        if x != y:
            return f"txs[{i}]: {show(x)} vs {show(y)}"
    for k in sorted(set(a["state"] or {}) | set(b["state"] or {})):
        x, y = (a["state"] or {}).get(k), (b["state"] or {}).get(k)
        if x != y:
            return f"state {k}: {show(x)} vs {show(y)}"
    return "equal"


def replay_pair(base_path: Path, mutant_path: Path, sigma: dict, tc: core.Toolchain,
                subject=None) -> tuple[str, str]:
    """Second, independent replay: recompile both, round-trip σ, fresh EVMs."""
    sigma2 = json.loads(core.canonical_json(sigma))
    eb = core.compile_artifact(base_path, tc, subject=subject)
    em = core.compile_artifact(mutant_path, tc, subject=subject)
    return core.run_sequence(eb, sigma2).sha256(), core.run_sequence(em, sigma2).sha256()


def separate(e1: dict, e2: dict, sigma_at, budget: int) -> dict:
    """Informational only, for a flagged duplicate pair: the first σ of the same
    stream on which the two mutants differ. The flag itself follows protocol.md
    section 10 (union of the properness pairs) and is not changed by this."""
    for i in range(budget):
        s = sigma_at(i)
        o1, o2 = core.run_sequence(e1, s), core.run_sequence(e2, s)
        if not core.observation_equal(o1, o2):
            return {"separated": True, "sigma_index": i, "summary": seqgen.summarize(s),
                    "first_difference": first_difference(o1, o2),
                    "obs_a_sha256": o1.sha256(), "obs_b_sha256": o2.sha256()}
    return {"separated": False, "sigmas_tried": budget}


def build(base_path: Path, mutant_paths: list[Path], seed: int = DEFAULT_SEED,
          budget: int = DEFAULT_BUDGET, max_txs: int = seqgen.DEFAULT_MAX_TXS,
          tc: core.Toolchain | None = None, subject=None) -> tuple[dict, dict]:
    """Returns (mutants.json document, log document)."""
    tc = tc or core.Toolchain.default()
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    base_text = Path(base_path).read_text()
    base_lint = speclint.lint_artifact(base_text, subj)
    if base_lint:
        raise BuildError(f"base {rel(base_path)} fails the artifact lint: {[str(v) for v in base_lint]}")
    eb = core.compile_artifact(base_path, tc, subject=subj)
    core.check_deployable(eb)  # EIP-170: the executor's lifted limit is for the Spec harness only
    fns = seqgen.tx_functions(eb, subj)
    base_obs: dict[int, core.Observation] = {}
    sigmas: dict[int, dict] = {}

    def sigma_at(i: int) -> dict:
        if i not in sigmas:
            sigmas[i] = seqgen.gen_sigma(seed, i, fns, max_txs, subject=subj)
            core.validate_sigma(sigmas[i], subject=subj)
        return sigmas[i]

    def base_at(i: int) -> core.Observation:
        if i not in base_obs:
            base_obs[i] = core.run_sequence(eb, sigma_at(i))
        return base_obs[i]

    entries: list[dict] = []          # mutants.json items
    records: list[dict] = []          # log items, one per file
    compiled: dict[str, dict] = {}    # id -> compiled entry (included only)
    seen: dict[str, str] = {eb["runtime_sha256"]: rel(base_path)}

    for path in mutant_paths:
        text = Path(path).read_text()
        labels = parse_labels(text)
        missing = [k for k in ("operator", "fault_class") if k not in labels]
        if missing:
            raise BuildError(f"{rel(path)}: header lacks {missing}")
        rec = {"path": rel(path), "source_sha256": core.sha256_hex(text.encode()), "labels": labels}
        records.append(rec)
        try:
            em = core.compile_artifact(path, tc, subject=subj)
        except core.CompileError as e:
            rec.update(status="rejected", reason="does_not_compile", detail=str(e)[:500])
            continue
        core.check_deployable(em)  # raises: a mutant above EIP-170 fails the whole build, loudly
        mid = em["runtime_sha256"]
        rec["id"] = mid
        if mid in seen:
            rec.update(status="rejected", reason="runtime_sha256_equals", equals=seen[mid])
            continue
        seen[mid] = rel(path)
        item = {"id": mid, "path": rel(path), "source_sha256": rec["source_sha256"],
                "operator": labels["operator"], "fault_class": labels["fault_class"],
                "status": "excluded", "properness": None, "behavioural_duplicate_of": []}
        entries.append(item)

        lint = speclint.lint_artifact(text, subj)
        if lint:
            item["exclusion_reason"] = "lint"
            rec.update(status="excluded", reason="lint", detail=[str(v) for v in lint])
            continue
        if abi_key(em) != abi_key(eb):
            item["exclusion_reason"] = "abi_differs"
            rec.update(status="excluded", reason="abi_differs",
                       detail={"base": sorted(eb["hashes"]), "mutant": sorted(em["hashes"])})
            continue

        found = None
        tried = 0
        for i in range(budget):
            tried = i + 1
            om = core.run_sequence(em, sigma_at(i))
            if not core.observation_equal(base_at(i), om):
                found = (i, om)
                break
        rec["sigmas_tried"] = tried
        if found is None:
            item["exclusion_reason"] = "no_properness_pair"
            rec.update(status="excluded", reason="no_properness_pair")
            continue
        i, om = found
        sigma = sigma_at(i)
        ob = base_at(i)
        rec["pair"] = {"sigma_index": i, "sigma": sigma, "summary": seqgen.summarize(sigma),
                       "first_difference": first_difference(ob, om),
                       "replay1": {"obs_base_sha256": ob.sha256(), "obs_mutant_sha256": om.sha256()}}
        if om.data["deploy"]["outcome"] != core.Outcome.SUCCESS.value:
            item["exclusion_reason"] = "does_not_deploy"
            rec.update(status="excluded", reason="does_not_deploy")
            continue
        hb, hm = replay_pair(Path(base_path), Path(path), sigma, tc, subj)
        rec["pair"]["replay2"] = {"obs_base_sha256": hb, "obs_mutant_sha256": hm}
        if (hb, hm) != (ob.sha256(), om.sha256()) or hb == hm:
            raise BuildError(f"{rel(path)}: replay 2 disagrees with replay 1 on sigma {i}: "
                             f"{rec['pair']['replay1']} vs {rec['pair']['replay2']}")
        item["status"] = "included"
        item["properness"] = {"sigma": sigma, "obs_base_sha256": hb, "obs_mutant_sha256": hm}
        rec.update(status="included")
        compiled[mid] = em

    # Behavioural duplicates among included mutants (protocol.md section 10).
    included = [e for e in entries if e["status"] == "included"]
    dup_checks = []
    for x in range(len(included)):
        for y in range(x + 1, len(included)):
            m1, m2 = included[x], included[y]
            union = [m1["properness"]["sigma"]]
            if core.canonical_json(m2["properness"]["sigma"]) != core.canonical_json(union[0]):
                union.append(m2["properness"]["sigma"])
            equal_on = []
            for s in union:
                equal_on.append(core.observation_equal(core.run_sequence(compiled[m1["id"]], s),
                                                       core.run_sequence(compiled[m2["id"]], s)))
            dup = all(equal_on)
            check = {"a": m1["path"], "b": m2["path"], "sigmas": len(union),
                     "equal_on": equal_on, "duplicate": dup}
            if dup:
                m1["behavioural_duplicate_of"].append(m2["id"])
                m2["behavioural_duplicate_of"].append(m1["id"])
                check["separation"] = separate(compiled[m1["id"]], compiled[m2["id"]], sigma_at, budget)
            dup_checks.append(check)
    for e in entries:
        e["behavioural_duplicate_of"].sort()

    doc = {"version": 1,
           "base": {"path": rel(base_path), "source_sha256": eb["source_sha256"],
                    "runtime_sha256": eb["runtime_sha256"]},
           "mutants": entries}
    log = {"version": 1,
           "params": {"seed": seed, "budget": budget, "max_txs": max_txs,
                      "distribution": seqgen.distribution_id(fns, max_txs, subj),
                      "properness_source_sha256": core.sha256_file(__file__)},
           "toolchain": core.toolchain_fingerprint(tc),
           "base": doc["base"],
           "mutants": records,
           "rejected": [{"path": r["path"], "reason": r["reason"], **({"equals": r["equals"]} if "equals" in r else {})}
                        for r in records if r["status"] == "rejected"],
           "excluded": [{"path": r["path"], "id": r["id"], "reason": r["reason"]}
                        for r in records if r["status"] == "excluded"],
           "duplicate_checks": dup_checks,
           "summary": {"files": len(records), "included": len(included),
                       "excluded": sum(r["status"] == "excluded" for r in records),
                       "rejected": sum(r["status"] == "rejected" for r in records)}}
    return doc, log


def dump(obj: dict) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, ensure_ascii=True) + "\n"


def table(log: dict) -> str:
    rows = [f"{'mutant':34} {'status':9} {'id':10} {'tried':>5}  pair / reason"]
    dup_of = {}
    for c in log["duplicate_checks"]:
        if c["duplicate"]:
            dup_of.setdefault(c["a"], []).append(Path(c["b"]).stem)
            dup_of.setdefault(c["b"], []).append(Path(c["a"]).stem)
    for r in log["mutants"]:
        what = (f"{r['pair']['summary']}  [{r['pair']['first_difference']}]"
                if r["status"] == "included" else r["reason"])
        if r["path"] in dup_of:
            what += f"  DUPLICATE of {','.join(dup_of[r['path']])}"
        if "expected_unkillable" in r["labels"]:
            what += "  (expected_unkillable)"
        rows.append(f"{Path(r['path']).stem:34} {r['status']:9} {r.get('id', '-')[:10]:10} "
                    f"{r.get('sigmas_tried', '-'):>5}  {what}")
    s = log["summary"]
    for c in log["duplicate_checks"]:
        if c["duplicate"]:
            sep = c["separation"]
            rows.append(f"duplicate flag {Path(c['a']).stem} ~ {Path(c['b']).stem} (on {c['sigmas']} sigma): "
                        + (f"separated by sigma_{sep['sigma_index']}: {sep['summary']}  [{sep['first_difference']}]"
                           if sep["separated"] else f"not separated within {sep['sigmas_tried']} sigmas"))
    rows.append(f"included {s['included']}, excluded {s['excluded']}, rejected {s['rejected']} "
                f"(seed {log['params']['seed']}, budget {log['params']['budget']}, "
                f"max_txs {log['params']['max_txs']})")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--base", type=Path, help="default: the subject's b")
    ap.add_argument("--mutants", type=Path, help="directory of m*.sol (default: subjects/<subject>/mutants)")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="sigmas tried per mutant")
    ap.add_argument("--max-txs", type=int, default=seqgen.DEFAULT_MAX_TXS)
    ap.add_argument("--out", type=Path, help="default: <mutants>/mutants.json")
    ap.add_argument("--log", type=Path, default=DEFAULT_LOG)
    a = ap.parse_args(argv)
    subj = core.load_subject(a.subject)
    a.base = a.base or subj.source_path
    a.mutants = a.mutants or subj.mutants_dir
    a.out = a.out or a.mutants / "mutants.json"
    if a.budget < 1 or a.max_txs < 0:
        ap.error("budget >= 1 and max-txs >= 0 required")
    paths = sorted(a.mutants.glob("m*.sol"))
    if not paths:
        ap.error(f"no m*.sol in {a.mutants}")
    try:
        doc, log = build(a.base, paths, a.seed, a.budget, a.max_txs, subject=subj)
    except (BuildError, core.CompileError, core.ExecutorError, core.SigmaError) as e:
        print(f"properness: build error: {e}", file=sys.stderr)
        return 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.log.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(dump(doc))
    a.log.write_text(dump(log))
    print(table(log))
    print(f"wrote {a.out} and {a.log}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
