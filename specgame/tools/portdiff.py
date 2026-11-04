"""Mechanical equivalence check of a ported subject (protocol v3, subjects).

    python tools/portdiff.py --subject vat --original <sheaf Vat.sol> [--modified subjects/vat/Vat.sol]
        [--seed 0] [--n 5000] [--max-txs 6] [--log subjects/vat/portdiff_log.json]

Both sources are compiled as the subject's contract with the pinned settings;
the same seeded σ_0 .. σ_{n-1} (tools/seqgen.py on the subject's profile, no
probe) are run on both with the core executor (deploy, the profile's setup,
the transactions, the profile's observation); the observations must be equal
on every σ. The log records both source and runtime sha256, the parameters,
the number of successful calls per function (so it shows the σ reach real
behaviour, not only reverts) and the first divergence, if any.

Exit 0 = equal on every σ, 1 = a divergence (named in the log), 2 = usage /
compile error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import seqgen  # noqa: E402
import specgame_core as core  # noqa: E402


def first_difference(o1: core.Observation, o2: core.Observation) -> str:
    a, b = o1.data, o2.data
    for k in ("deploy", "setup", "txs", "probe"):
        if a.get(k) != b.get(k):
            if isinstance(a.get(k), list):
                for i, (x, y) in enumerate(zip(a[k], b[k])):
                    if x != y:
                        return f"{k}[{i}]: {x} != {y}"
            return f"{k}: {a.get(k)} != {b.get(k)}"
    for key in sorted(set(a["state"] or {}) | set(b["state"] or {})):
        if (a["state"] or {}).get(key) != (b["state"] or {}).get(key):
            return f"state {key}: {(a['state'] or {}).get(key)} != {(b['state'] or {}).get(key)}"
    return "observations differ"


def portdiff(original: Path, modified: Path, subject: core.Subject, seed: int, n: int, max_txs: int) -> dict:
    eo = core.compile_artifact(original, subject=subject)
    em = core.compile_artifact(modified, subject=subject)
    fns = seqgen.tx_functions(em, subject)
    successes: dict[str, int] = {f: 0 for f in fns}
    calls: dict[str, int] = {f: 0 for f in fns}
    divergence = None
    for i in range(n):
        sigma = seqgen.gen_sigma(seed, i, fns, max_txs, subject=subject)
        oo, om = core.run_sequence(eo, sigma), core.run_sequence(em, sigma)
        if not core.observation_equal(oo, om):
            divergence = {"sigma_index": i, "sigma": sigma, "first_difference": first_difference(oo, om),
                          "obs_original_sha256": oo.sha256(), "obs_modified_sha256": om.sha256()}
            break
        for tx, step in zip(sigma["txs"], om.data["txs"]):
            calls[tx["fn"]] += 1
            successes[tx["fn"]] += step["outcome"] == core.Outcome.SUCCESS.value
    return {
        "version": 1, "subject": subject.name,
        "original": {"path": str(original), "source_sha256": eo["source_sha256"], "runtime_sha256": eo["runtime_sha256"]},
        "modified": {"path": str(modified), "source_sha256": em["source_sha256"], "runtime_sha256": em["runtime_sha256"]},
        "same_runtime_bytecode": eo["runtime_sha256"] == em["runtime_sha256"],
        "params": {"seed": seed, "n": n, "max_txs": max_txs,
                   "distribution": seqgen.distribution_id(fns, max_txs, subject)},
        "sigmas_run": (divergence["sigma_index"] + 1) if divergence else n,
        "equal": divergence is None,
        "calls_per_function": calls, "successes_per_function": successes,
        "divergence": divergence,
        "toolchain": core.toolchain_fingerprint(),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", required=True)
    ap.add_argument("--original", type=Path, required=True)
    ap.add_argument("--modified", type=Path, help="default: the subject's b")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=5000)
    ap.add_argument("--max-txs", type=int, default=seqgen.DEFAULT_MAX_TXS)
    ap.add_argument("--log", type=Path)
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    subj = core.load_subject(a.subject)
    try:
        doc = portdiff(a.original, a.modified or subj.source_path, subj, a.seed, a.n, a.max_txs)
    except (core.CompileError, core.ProfileError, ValueError) as e:
        print(f"portdiff: ERROR: {e}", file=sys.stderr)
        return 2
    if a.log:
        a.log.parent.mkdir(parents=True, exist_ok=True)
        a.log.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(f"portdiff {subj.name}: original runtime {doc['original']['runtime_sha256'][:16]}…, "
          f"modified {doc['modified']['runtime_sha256'][:16]}… (same bytecode: {doc['same_runtime_bytecode']})")
    print(f"  {doc['sigmas_run']} σ (seed {a.seed}, max_txs {a.max_txs}): "
          + ("observations equal on every σ" if doc["equal"] else f"DIVERGENCE at σ {doc['divergence']['sigma_index']}: "
             f"{doc['divergence']['first_difference']}"))
    print("  successful calls / calls: " + ", ".join(
        f"{f.split('(')[0]}{'' if f.count(',') < 2 or not f.startswith('file') else '3'} "
        f"{doc['successes_per_function'][f]}/{doc['calls_per_function'][f]}" for f in sorted(doc["calls_per_function"])))
    return 0 if doc["equal"] else 1


if __name__ == "__main__":
    sys.exit(main())
