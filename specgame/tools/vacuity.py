"""Vacuity check (a): Pre satisfiability per check (protocol.md section 12).

    python tools/vacuity.py <spec.sol> [--artifact subjects/capped_token/CappedToken.sol]
                            [--timeout-ms N] [--wall-timeout-s S] [--json out.json]

For every check_* of the spec, `assert(false)` is inserted right after its
leading requires (speclint.pre_probe_source) of that check's isolated
harness (Check v2: one harness per check, run in the worker pool). Per check:

  probe violated  -> satisfiable
  probe safe      -> unsatisfiable (FLAG: every assert of the check is vacuous)
  otherwise       -> unknown

This tests Pre satisfiability only, deliberately not reachability of the assert
points on b: a must-revert check has an unreachable assert point on b by
design (SPEC_FORMAT.md sections 4 and 7).

Exit codes: 0 all satisfiable, 3 some check flagged unsatisfiable, 2 no flag
but some unknown, 1 usage / lint error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402
import speclint  # noqa: E402
import check as check_cli  # noqa: E402

DEFAULT_ARTIFACT = core.load_subject().source_path
MARKER = "SPECGAME-PRE-PROBE"


def check_names(spec_text: str, subject=None) -> list[str]:
    return [n for n, _ in core.check_functions(spec_text, subject)]


def vacuity(spec: Path, artifact: Path, timeout_ms: int, wall_timeout_s: float,
            tc: core.Toolchain | None = None, workers: int | None = None,
            cache_dir: Path | None = core.CACHE_DIR, subject=None) -> dict:
    """Check v2 isolation: per check, its isolated harness with the probe after
    Pre, one solc run each, in the worker pool."""
    text = spec.read_text()
    t0 = time.monotonic()
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    harnesses = [(n, speclint.pre_probe_source(core.isolated_harness(t, subj), n))
                 for n, t in core.check_functions(text, subj)]
    results = core.smtcheck_harnesses(harnesses, artifact.read_text(), timeout_ms, wall_timeout_s, tc,
                                      workers, cache_dir, subj)
    rows = []
    for (name, probed), rc in zip(harnesses, results):
        r = rc["result"]
        probe_lines = {i + 1 for i, l in enumerate(probed.splitlines()) if MARKER in l}
        st = next((t["status"] for t in r["targets"] if t["line"] in probe_lines), None)
        if r["reason"] in check_cli_undetermined():
            pre = "unknown"
        elif st == "violated":
            pre = "satisfiable"
        elif st == "safe":
            pre = "unsatisfiable"
        else:
            pre = "unknown"
        rows.append({"check": name, "probe_status": st or "no result", "pre": pre, "reason": r["reason"],
                     "duration_s": r["duration_s"], "cached": rc["cached"],
                     "solc_input_sha256": r["solc_input_sha256"]})
    return {
        "spec": str(spec),
        "artifact": str(artifact),
        "mode": "isolated",
        "duration_s": round(time.monotonic() - t0, 3),
        "cpu_s": round(sum(x["duration_s"] for x in rows), 3),
        "rows": rows,
        "flagged": [x["check"] for x in rows if x["pre"] == "unsatisfiable"],
        "unknown": [x["check"] for x in rows if x["pre"] == "unknown"],
    }


def check_cli_undetermined() -> set[str]:
    # Check runs whose per-target statuses cannot be trusted at all.
    return {"compile_error", "solver_unavailable", "unparsed", "wall_timeout", "no_targets"}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--artifact", type=Path, help="default: the subject's b")
    ap.add_argument("--timeout-ms", type=int, default=check_cli.DEFAULT_TIMEOUT_MS)
    ap.add_argument("--wall-timeout-s", type=float, default=check_cli.DEFAULT_WALL_TIMEOUT_S)
    ap.add_argument("--json", type=Path)
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 1 if e.code else 0
    if not a.spec.is_file():
        print(f"vacuity: no such file {a.spec}", file=sys.stderr)
        return 1
    a.artifact = a.artifact or core.load_subject(a.subject).source_path
    problems = check_cli.lint(a.spec, a.artifact, subject=a.subject)
    if problems:
        for p in problems:
            print(f"{a.spec}: {p}")
        return 1
    res = vacuity(a.spec, a.artifact, a.timeout_ms, a.wall_timeout_s, subject=a.subject)
    print(f"spec {a.spec}: vacuity (a), Pre satisfiability per check ({res['duration_s']} s)")
    for x in res["rows"]:
        flag = "  FLAG" if x["pre"] == "unsatisfiable" else ""
        print(f"  {x['check']:40s} probe {x['probe_status']:10s} Pre {x['pre']}{flag}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    if res["flagged"]:
        return 3
    return 2 if res["unknown"] else 0


if __name__ == "__main__":
    sys.exit(main())
