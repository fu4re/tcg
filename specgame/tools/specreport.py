"""Lint, Check, κ and vacuity (a) for every spec; the WP3 acceptance gate (`make specs`).

    python tools/specreport.py [--artifact subjects/capped_token/CappedToken.sol]
                               [--timeout-ms N] [--wall-timeout-s S] [--out build/specs]

Specs: specs/*.sol and specs/controls/*.sol (not specs/havoc/). Writes
<out>/<name>.json per spec and <out>/summary.json, prints one table row per
spec, and exits 1 if any spec misses its expectation below (Unknown is never
an Accept, so a solver budget problem shows up as a failed expectation).
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402
import check as check_cli  # noqa: E402
import kappa as kappa_mod  # noqa: E402
import vacuity as vacuity_mod  # noqa: E402

LADDER = ("phi_owner", "phi_cap", "phi_both", "phi_transfer", "phi_full")
# name -> (expected Check verdict, expected κ: 0 | ">0" | None, expected vacuity (a): "ok" | "flag")
EXPECT = {
    "phi_top": ("Accept", 0, "ok"),
    **{n: ("Accept", ">0", "ok") for n in LADDER},
    "phi_false": ("Refute", ">0", "ok"),
    "phi_dead": ("Accept", None, "flag"),
}


def spec_files(subject=None) -> list[Path]:
    root = core.load_subject(subject).specs_dir
    return sorted(root.glob("*.sol")) + sorted((root / "controls").glob("*.sol"))


def report(spec: Path, artifact: Path, timeout_ms: int, wall_s: float, subject=None) -> dict:
    doc: dict = {"spec": str(spec.relative_to(core.ROOT)), "spec_source_sha256": core.sha256_file(spec),
                 "artifact": str(artifact), "artifact_source_sha256": core.sha256_file(artifact),
                 "timeout_ms": timeout_ms, "wall_timeout_s": wall_s}
    doc["lint"] = check_cli.lint(spec, artifact, subject=subject)
    if doc["lint"]:
        return doc
    r = core.smtcheck_isolated(spec, artifact, timeout_ms, wall_s, cache_dir=core.CACHE_DIR, subject=subject)
    doc["check"] = asdict(r)
    doc["kappa"] = kappa_mod.kappa(spec, artifact, timeout_ms, wall_s, subject=subject)
    doc["vacuity_a"] = vacuity_mod.vacuity(spec, artifact, timeout_ms, wall_s, subject=subject)
    return doc


def summarize(name: str, doc: dict) -> tuple[dict, list[str]]:
    row = {"spec": name}
    problems = []
    if doc["lint"]:
        row.update(verdict="lint_rejected")
        return row, [f"{name}: lint {doc['lint']}"]
    c, k, v = doc["check"], doc["kappa"], doc["vacuity_a"]
    vac = "flag" if v["flagged"] else ("unknown" if v["unknown"] else "ok")
    row.update(verdict=c["verdict"], reason=c["reason"], check_s=c["duration_s"],
               kappa=k["kappa"], asserts=k["asserts"], kappa_s=k["check_over_H"]["duration_s"],
               vacuity_a=vac, vacuity_s=v["duration_s"])
    exp = EXPECT.get(name)
    if exp is None:
        return row, [f"{name}: no expectation recorded in specreport.EXPECT"]
    want_v, want_k, want_vac = exp
    if c["verdict"] != want_v:
        problems.append(f"{name}: Check {c['verdict']} ({c['reason']}), want {want_v}")
    if want_v == "Refute" and not all(t["counterexample"] for x in c["checks"] for t in x["result"]["targets"]
                                      if t["status"] == "violated"):
        problems.append(f"{name}: Refute without a parsed counterexample")
    if want_k == 0 and k["kappa"] != 0:
        problems.append(f"{name}: kappa {k['kappa']}, want 0")
    if want_k == ">0" and not (k["kappa"] or 0) > 0:
        problems.append(f"{name}: kappa {k['kappa']}, want > 0")
    if vac != want_vac:
        problems.append(f"{name}: vacuity (a) {vac}, want {want_vac}")
    return row, problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--artifact", type=Path, help="default: the subject's b")
    ap.add_argument("--timeout-ms", type=int, default=check_cli.DEFAULT_TIMEOUT_MS)
    ap.add_argument("--wall-timeout-s", type=float, default=check_cli.DEFAULT_WALL_TIMEOUT_S)
    ap.add_argument("--out", type=Path, default=core.ROOT / "build" / "specs")
    ap.add_argument("--only", nargs="*", help="spec names to run (default: all)")
    a = ap.parse_args(argv)
    a.out.mkdir(parents=True, exist_ok=True)
    rows, problems = [], []
    a.artifact = a.artifact or core.load_subject(a.subject).source_path
    for spec in spec_files(a.subject):
        if a.only and spec.stem not in a.only:
            continue
        doc = report(spec, a.artifact, a.timeout_ms, a.wall_timeout_s, a.subject)
        (a.out / f"{spec.stem}.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        row, p = summarize(spec.stem, doc)
        rows.append(row)
        problems += p
        print(f"{row['spec']:14s} {row.get('verdict', '?'):8s} kappa={row.get('kappa')!s:>2}/{row.get('asserts')!s:<2} "
              f"vacuity(a)={row.get('vacuity_a', '-'):8s} check {row.get('check_s')} s, "
              f"kappa {row.get('kappa_s')} s, vacuity {row.get('vacuity_s')} s", flush=True)
    (a.out / "summary.json").write_text(json.dumps({"timeout_ms": a.timeout_ms, "wall_timeout_s": a.wall_timeout_s,
                                                    "rows": rows, "problems": problems}, indent=1) + "\n")
    for p in problems:
        print(f"FAIL {p}")
    print(f"specs: {len(rows) - len({p.split(':')[0] for p in problems})}/{len(rows)} as expected")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
