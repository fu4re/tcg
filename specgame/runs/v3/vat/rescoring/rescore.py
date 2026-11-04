"""Union-pool rescoring of the Vat specs (protocol.md 16.11, WP8).

    python runs/v3/vat/rescoring/rescore.py [--workers 4]   (from specgame/)

Pool U = the union of the six v3 trajectories' W* (`runs/v3/vat/<cond>/seed_<s>/W_star.json`,
each = the Vat ladder pool + that trajectory's own witnesses) and the Vat ladder pool
(`evidence.W` of `bundles/vat/phi_*/manifest.json`), as {mutant, sigma} pairs deduplicated
by canonical JSON (events.pool_from). Specs scored: every round's selected spec of every
trajectory (a round whose selected candidate has no runnable spec, lint_rejected or
compile_error, is recorded as "no spec", K = []), and the 11 hand ladder specs
(`bundles/vat/<phi>/phi/Spec.sol`). Each spec's K_U = mutants m with some pair (m, σ) in U
such that σ violates the spec over m (events.Scorer.kill_set, core v2 executor; no solver).

Supplementary column: U plus the one hand σ of `runs/v3/vat/f0/seed_0/probes/m08_sin_setup/`
(U+probe), reported separately; it is not part of any pool.

Writes rescoring.json next to this file. Nothing else is modified.
"""
from __future__ import annotations

import argparse
import json
import multiprocessing as mp
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]  # specgame/
sys.path.insert(0, str(ROOT / "tools"))
import events  # noqa: E402
import specgame_core as core  # noqa: E402

TRAJ = [("fM", 0), ("f0", 0), ("f0", 1), ("fMplus", 0), ("fMplus", 1), ("fM", 1)]
LADDER = ["phi_top", "phi_auth", "phi_consent", "phi_frob", "phi_frob_guards", "phi_frob_both", "phi_fold",
          "phi_move_flux", "phi_grab_heal_suck", "phi_books", "phi_full"]
VAT = core.load_subject("vat")
MUTANTS = events.load_mutants(VAT.mutants_dir / "mutants.json")
NAMES = {m["id"]: m["name"] for m in MUTANTS}


def rel(p: Path) -> str:
    return str(Path(p).resolve().relative_to(ROOT))


def pools() -> tuple[dict, list[dict], list[dict], dict]:
    per = {}
    for c, s in TRAJ:
        f = ROOT / "runs/v3/vat" / c / f"seed_{s}" / "W_star.json"
        per[f"{c}/seed_{s}"] = {"path": rel(f), "pairs": events.load_witnesses(f)}
    ladder_pairs = []
    for p in LADDER:
        m = json.loads((ROOT / "bundles/vat" / p / "manifest.json").read_text())
        ladder_pairs += [{"mutant": w["mutant"], "sigma": w["sigma"]} for w in m["evidence"]["W"]]
    union = events.pool_from([v["pairs"] for v in per.values()] + [ladder_pairs])
    probe = json.loads((ROOT / "runs/v3/vat/f0/seed_0/probes/m08_sin_setup/result.json").read_text())
    m08 = next(m["id"] for m in MUTANTS if m["name"] == "m08_grab_no_vice")
    probe_pair = {"mutant": m08, "sigma": probe["sigma"]}
    return per, ladder_pairs, union, probe_pair


def spec_list() -> list[dict]:
    out = []
    for c, s in TRAJ:
        d = ROOT / "runs/v3/vat" / c / f"seed_{s}"
        ev = json.loads((d / "events.json").read_text())
        own = {r["t"]: r for r in ev["rounds"]}
        final = json.loads((d / "trajectory.json").read_text())["result"]["final"]
        t = 1
        while (d / f"round_{t}").is_dir():
            j = json.loads((d / f"round_{t}" / "selected.json").read_text())["selected"]
            cd = d / f"round_{t}" / f"cand_{j}"
            sc = json.loads((cd / "score.json").read_text())
            runnable = sc["acc"] != "lint_rejected" and sc.get("check_reason") != "compile_error"
            out.append({"key": f"{c}/seed_{s}/round_{t}", "trajectory": f"{c}/seed_{s}", "round": t, "cand": j,
                        "final": (t, j) == (final["round"], final["cand"]), "acc": sc["acc"],
                        "check_reason": sc.get("check_reason"), "runnable": runnable,
                        "spec": rel(cd / "Spec.sol") if runnable else None,
                        "own_pool": f"runs/v3/vat/{c}/seed_{s}/W_star.json",
                        "K_own_pool": sorted(own[t]["kill_set"]) if t in own else None})
            t += 1
    for p in LADDER:
        m = json.loads((ROOT / "bundles/vat" / p / "manifest.json").read_text())
        out.append({"key": f"ladder/{p}", "trajectory": None, "round": None, "cand": None, "final": None,
                    "acc": m["hard"]["c"]["verdict"], "check_reason": m["hard"]["c"]["reason"], "runnable": True,
                    "spec": f"bundles/vat/{p}/phi/Spec.sol", "own_pool": f"bundles/vat/{p}/manifest.json evidence.W",
                    "K_own_pool": sorted(m["claimed"]["kill_set"])})
    return out


def score(args) -> dict:
    item, union, probe_pair = args
    t0 = time.monotonic()
    if not item["runnable"]:
        return {**item, "K_union": [], "K_union_probe": [], "note": "no spec (lint_rejected or compile_error)",
                "wall_s": 0.0}
    sc = events.Scorer(MUTANTS, VAT)
    spec = ROOT / item["spec"]
    k, results = sc.kill_set(spec, union)
    kp, rp = sc.kill_set(spec, [probe_pair])
    return {**item, "K_union": k, "K_union_probe": sorted(set(k) | set(kp)),
            "probe_outcome": rp[0]["outcomes"] if rp else None,
            "pairs_violated": sum(r["violated"] for r in results), "pairs_evaluated": len(results),
            "wall_s": round(time.monotonic() - t0, 3)}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=4)
    a = ap.parse_args()
    t0 = time.monotonic()
    per, ladder_pairs, union, probe_pair = pools()
    specs = spec_list()
    with mp.Pool(a.workers) as pool:
        rows = pool.map(score, [(s, union, probe_pair) for s in specs], chunksize=1)
    n = len(MUTANTS)
    for r in rows:
        r["ms_union"] = f"{len(r['K_union'])}/{n}"
        r["ms_own_pool"] = None if r["K_own_pool"] is None else f"{len(r['K_own_pool'])}/{n}"
        r["gained_on_union"] = sorted(NAMES[m] for m in set(r["K_union"]) - set(r["K_own_pool"] or []))
        r["lost_on_union"] = sorted(NAMES[m] for m in set(r["K_own_pool"] or []) - set(r["K_union"]))
        r["K_union_names"] = sorted(NAMES[m] for m in r["K_union"])
        r["K_union_probe_names"] = sorted(NAMES[m] for m in r["K_union_probe"])
    finals = [r for r in rows if r["final"]] + [r for r in rows if r["key"] == "ladder/phi_full"]
    order_own = [r["key"] for r in sorted(finals, key=lambda r: (-len(r["K_own_pool"]), r["key"]))]
    order_union = [r["key"] for r in sorted(finals, key=lambda r: (-len(r["K_union"]), r["key"]))]
    doc = {
        "version": 1, "script": rel(Path(__file__)), "core_version": core.CORE_VERSION,
        "toolchain": core.toolchain_fingerprint(),
        "mutants": [{"id": m["id"], "name": m["name"]} for m in MUTANTS],
        "pools": {"trajectories": {k: {"path": v["path"], "size": len(v["pairs"]),
                                       "sha256": events.pool_sha256(v["pairs"])} for k, v in per.items()},
                  "ladder": {"size": len(ladder_pairs), "distinct": len(events.pool_from([ladder_pairs])),
                             "sha256": events.pool_sha256(events.pool_from([ladder_pairs]))},
                  "union": {"size": len(union), "sha256": events.pool_sha256(union),
                            "per_mutant": {NAMES[m["id"]]: sum(p["mutant"] == m["id"] for p in union) for m in MUTANTS}},
                  "probe": {"path": "runs/v3/vat/f0/seed_0/probes/m08_sin_setup/result.json",
                            "sigma_sha256": core.json_sha256(probe_pair["sigma"])}},
        "rows": rows,
        "finals_ordering": {"by_own_pool": order_own, "by_union": order_union,
                            "counts_own": {r["key"]: len(r["K_own_pool"]) for r in finals},
                            "counts_union": {r["key"]: len(r["K_union"]) for r in finals}},
        "wall_s": round(time.monotonic() - t0, 3),
    }
    (HERE / "rescoring.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    for r in rows:
        print(f"{r['key']:28s} acc {r['acc']:8s} own {r['ms_own_pool']}  union {r['ms_union']}  "
              f"+probe {len(r['K_union_probe'])}/{n}  gained {r['gained_on_union']} lost {r['lost_on_union']}")
    print("finals by own pool:", order_own)
    print("finals by union:   ", order_union)
    print(f"union |U| = {len(union)}; wall {doc['wall_s']} s")
    return 0


if __name__ == "__main__":
    sys.exit(main())
