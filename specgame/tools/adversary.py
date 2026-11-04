"""Adversary A: seeded witness search for a spec φ over the library M (WP4;
protocol.md sections 4, 7, 8, 15; note Section 7 "Moves", Theorem 8.4).

    python tools/adversary.py --spec specs/phi.sol [--mutants mutants/mutants.json]
        [--base subjects/capped_token/CappedToken.sol] [--seed 0] [--budget 2000] [--max-txs 6]
        [--per-mutant 1] [--out build/witnesses/<phi>.json] [--log build/witnesses/<phi>.log.json]

For every **included** mutant m of mutants.json (in file order):

1. Spec is compiled over m (`compile_spec_over`); its check_* names are the
   probe targets;
2. σ_0, σ_1, ... σ_{B_A-1} come from `seqgen.gen_sigma(seed, i, fns, max_txs,
   probe_checks=checks)`, unchanged: fns are the transaction functions of b
   (so the σ list does not depend on the spec or the mutant), the probe is
   drawn after the transactions, so σ_i's prefix and probe arguments are the
   same for every spec (only the drawn `probe.check` name differs);
3. σ_i is a candidate iff `evaluate_witness(Spec over m, σ_i)` is violated
   (some check_* ends in Panic(0x01), each check on its own fresh replay);
4. every candidate goes through the **replay gate** before it is kept: Spec is
   recompiled over m from source (the pair runtime sha256 must equal the
   first compile's), σ is round-tripped through its canonical JSON and
   `evaluate_witness` runs again; a candidate that is not violated there is
   discarded and logged with its outcomes, never counted;
5. the search for m stops after `per_mutant` kept witnesses (default 1: one
   witness per mutant decides the kill set, Def. 5.3) or at the budget.

`σ.probe.check` is provenance (protocol.md Sharpened definition 13): in a
kept witness it is set to the first check (sorted) that ended in violation,
the same name as `observed.check`; seqgen's drawn name is replaced.

Adversary id = sha256 of the canonical JSON of {adversary source sha256,
seqgen source sha256, parameters (seed, B_A, max_txs, per_mutant, seqgen
distribution id)}. It goes into the bundle's evidence layer.

Outputs: `--out`, a JSON list of witnesses (schemas/witness.schema.json),
deterministic; `--log`, parameters, adversary id, per-mutant σ tried, outcome
counts, discards, wall times (the only non-deterministic content).
Exit 0 = search ran (a surviving mutant is a result, not an error),
1 = input error.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqgen  # noqa: E402
import specgame_core as core  # noqa: E402

DEFAULT_SEED = 0
DEFAULT_BUDGET = 2000
DEFAULT_PER_MUTANT = 1
DEFAULT_BASE = core.ROOT / "subjects" / "capped_token" / "CappedToken.sol"
DEFAULT_MUTANTS = core.ROOT / "subjects" / "capped_token" / "mutants" / "mutants.json"


class AdversaryError(Exception):
    pass


def params(seed: int, budget: int, max_txs: int, per_mutant: int, fns: list[str], subject=None) -> dict:
    return {"seed": seed, "B_A": budget, "max_txs": max_txs, "per_mutant": per_mutant,
            "distribution": seqgen.distribution_id(fns, max_txs, subject)}


def adversary_id(p: dict) -> str:
    return core.json_sha256({"adversary_source_sha256": core.sha256_file(__file__),
                             "seqgen_source_sha256": core.sha256_file(seqgen.__file__),
                             "params": p})


def included_mutants(mutants_json: Path, root: Path = core.ROOT) -> list[dict]:
    doc = json.loads(Path(mutants_json).read_text())
    out = []
    for m in doc["mutants"]:
        if m["status"] == "included":
            out.append({"id": m["id"], "path": (root / m["path"]).resolve(), "name": Path(m["path"]).stem})
    return out


def replay_gate(spec_path: Path, mutant_path: Path, sigma: dict, pair_runtime_sha256: str | None = None,
                subject=None) -> dict:
    """Second, independent evaluation of a candidate (m, σ) against φ.
    Returns {"kept": bool, "outcomes": {...}, "reason": str, "pair_runtime_sha256": ...}."""
    entry = core.compile_spec_over(spec_path, mutant_path, subject=subject)
    if pair_runtime_sha256 is not None and entry["runtime_sha256"] != pair_runtime_sha256:
        raise AdversaryError(f"recompiled Spec over {mutant_path} has a different runtime sha256")
    sigma2 = json.loads(core.canonical_json(sigma))
    ev = core.evaluate_witness(entry, sigma2)
    if ev.violated:
        reason = "violation"
    elif not ev.deploy_ok:
        reason = "deploy of Spec over the mutant failed"
    else:
        reason = "no check ends in violation"
    return {"kept": ev.violated, "outcomes": ev.outcomes, "reason": reason,
            "pair_runtime_sha256": entry["runtime_sha256"]}


def witness(mutant_id: str, sigma: dict, spec_sha: str, pair_sha: str, check: str) -> dict:
    s = json.loads(core.canonical_json(sigma))
    s["probe"]["check"] = check
    return {"version": 1, "mutant": mutant_id, "sigma": s,
            "observed": {"spec_source_sha256": spec_sha, "pair_runtime_sha256": pair_sha,
                         "check": check, "outcome": core.Outcome.VIOLATION.value}}


def search(spec_path: Path, mutants: list[dict], base_path: Path = DEFAULT_BASE, seed: int = DEFAULT_SEED,
           budget: int = DEFAULT_BUDGET, max_txs: int = seqgen.DEFAULT_MAX_TXS,
           per_mutant: int = DEFAULT_PER_MUTANT, subject=None) -> tuple[list[dict], dict]:
    """Returns (W as a list of witnesses, log)."""
    if budget < 1 or per_mutant < 1 or max_txs < 0:
        raise AdversaryError("budget >= 1, per_mutant >= 1, max_txs >= 0 required")
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    fns = seqgen.tx_functions(core.compile_artifact(base_path, subject=subj), subj)
    p = params(seed, budget, max_txs, per_mutant, fns, subj)
    spec_sha = core.sha256_file(spec_path)
    W: list[dict] = []
    per: list[dict] = []
    discarded: list[dict] = []
    t_all = time.monotonic()
    for m in mutants:
        t0 = time.monotonic()
        entry = core.compile_spec_over(spec_path, m["path"], subject=subj)
        checks = entry["checks"]
        kept: list[int] = []
        counts: dict[str, int] = {}
        tried = 0
        for i in range(budget):
            tried = i + 1
            sigma = seqgen.gen_sigma(seed, i, fns, max_txs, probe_checks=checks, subject=subj)
            ev = core.evaluate_witness(entry, sigma)
            for o in ev.outcomes.values():
                counts[o] = counts.get(o, 0) + 1
            if not ev.violated:
                continue
            gate = replay_gate(spec_path, m["path"], sigma, entry["runtime_sha256"], subj)
            if not gate["kept"]:
                discarded.append({"mutant": m["id"], "name": m["name"], "sigma_index": i, "sigma": sigma,
                                  "first_outcomes": ev.outcomes, "replay_outcomes": gate["outcomes"],
                                  "reason": "replay gate: " + gate["reason"]})
                continue
            check = sorted(c for c, o in ev.outcomes.items() if o == core.Outcome.VIOLATION.value)[0]
            W.append(witness(m["id"], sigma, spec_sha, entry["runtime_sha256"], check))
            kept.append(i)
            if len(kept) >= per_mutant:
                break
        per.append({"mutant": m["id"], "name": m["name"], "pair_runtime_sha256": entry["runtime_sha256"],
                    "checks": checks, "sigmas_tried": tried, "witness_sigma_indices": kept,
                    "killed": bool(kept), "check_outcome_counts": dict(sorted(counts.items())),
                    "wall_s": round(time.monotonic() - t0, 3)})
    kill = sorted({w["mutant"] for w in W})
    log = {"version": 1, "spec": str(spec_path), "spec_source_sha256": spec_sha,
           "adversary_id": adversary_id(p), "params": p,
           "adversary_source_sha256": core.sha256_file(__file__),
           "kill_set": kill, "ms_cert_on_own_W": {"killed": len(kill), "total": len(mutants)},
           "mutants": per, "discarded": discarded,
           "wall_s": round(time.monotonic() - t_all, 3)}
    return W, log


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spec", type=Path, help="required unless --coverage")
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--mutants", type=Path, help="default: subjects/<subject>/mutants/mutants.json")
    ap.add_argument("--base", type=Path, help="default: the subject's b")
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--budget", type=int, default=DEFAULT_BUDGET, help="B_A: sigmas tried per (mutant, spec)")
    ap.add_argument("--max-txs", type=int, default=seqgen.DEFAULT_MAX_TXS)
    ap.add_argument("--per-mutant", type=int, default=DEFAULT_PER_MUTANT)
    ap.add_argument("--out", type=Path)
    ap.add_argument("--log", type=Path)
    ap.add_argument("--coverage", type=int, metavar="N",
                    help="only report successful/total calls per function over N σ of this seed (no search)")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 1 if e.code else 0
    if not a.coverage and a.spec is None:
        ap.error("--spec is required")
    if a.coverage:
        print(seqgen.coverage_table(seqgen.coverage(a.subject, a.coverage, a.seed, a.max_txs)))
        return 0
    name = a.spec.stem
    out = a.out or core.ROOT / "build" / "witnesses" / f"{name}.json"
    logp = a.log or out.with_name(f"{out.stem}.log.json")
    try:
        subj = core.load_subject(a.subject)
        W, log = search(a.spec, included_mutants(a.mutants or subj.mutants_dir / "mutants.json"),
                        a.base or subj.source_path, a.seed, a.budget, a.max_txs, a.per_mutant, subj)
    except (AdversaryError, core.CompileError, core.ExecutorError, core.SigmaError, core.ProfileError,
            OSError, KeyError) as e:
        print(f"adversary: ERROR: {e}", file=sys.stderr)
        return 1
    out.parent.mkdir(parents=True, exist_ok=True)
    logp.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(W, indent=1, sort_keys=True) + "\n")
    logp.write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    for r in log["mutants"]:
        print(f"  {r['name']:30s} {'KILLED' if r['killed'] else 'survives':8s} tried {r['sigmas_tried']:5d}"
              f"  {r['wall_s']:7.2f} s" + (f"  sigma_{r['witness_sigma_indices'][0]}" if r["killed"] else ""))
    k = log["ms_cert_on_own_W"]
    print(f"adversary {log['adversary_id'][:12]}: {a.spec} ms_cert(own W) = {k['killed']}/{k['total']}, "
          f"|W| = {len(W)}, discarded {len(log['discarded'])}, {log['wall_s']:.1f} s -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
