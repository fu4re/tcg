"""Check(artifact, φ): SMTChecker CHC over a spec harness (SPEC_FORMAT.md section 6).

    python tools/check.py <spec.sol> [--artifact subjects/capped_token/CappedToken.sol]
                          [--timeout-ms N] [--wall-timeout-s S] [--json out.json]
                          [--mode isolated|whole] [--workers N] [--no-cache]

Default mode is protocol v2 `isolated`: one harness per check_* (the fixed
header plus that check), run in a pool of up to `workers` solc processes; the
spec verdict combines them (Accept iff every check is Accept; Refute if any
check is Refute; else Unknown, reason `budget` / `unproved` / ...). `whole` is
the v1 single-harness Check, kept for comparison. Isolated results are read
from and written to the verdict cache build/cache/ unless --no-cache (a pure
optimization keyed by the exact solc input; verify.py never uses it).

The spec is linted first (tools/speclint.py, names taken from the compiled
artifact); a lint failure is a usage error, not a verdict. Prints the verdict,
the reason, a per-assert table and the duration; `--json` writes the full
CheckResult (exact solc input and its sha256, raw solc output) plus the lint
result.

Exit codes: 0 Accept, 3 Refute, 2 Unknown, 1 usage / lint / compile-time error.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402
import speclint  # noqa: E402

DEFAULT_ARTIFACT = core.load_subject().source_path  # the default subject's b
# Frozen protocol values (protocol.json "check").
DEFAULT_TIMEOUT_MS = core.CHECK_TIMEOUT_MS
DEFAULT_WALL_TIMEOUT_S = core.CHECK_WALL_TIMEOUT_S

EXIT = {core.Verdict.ACCEPT.value: 0, core.Verdict.REFUTE.value: 3, core.Verdict.UNKNOWN.value: 2}


def lint(spec: Path, artifact: Path, tc: core.Toolchain | None = None, subject=None) -> list[str]:
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    entry = core.compile_artifact(artifact, tc, subject=subj)
    names = speclint.names_from_entry(entry)
    return [str(v) for v in speclint.lint_spec(spec.read_text(), names, subj)]


def target_rows(result: core.CheckResult) -> list[str]:
    rows = []
    for t in result.targets:
        rows.append(f"  {t['function'] or '-':40s} line {t['line']!s:>4}  {t['status'] or 'no result'}")
        if t.get("counterexample"):
            for l in t["counterexample"]["assignments"]:
                rows.append(f"      {l}")
            for l in t["counterexample"]["trace"]:
                rows.append(f"      | {l}")
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", type=Path)
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--artifact", type=Path, help="default: the subject's b")
    ap.add_argument("--timeout-ms", type=int, default=DEFAULT_TIMEOUT_MS)
    ap.add_argument("--wall-timeout-s", type=float, default=DEFAULT_WALL_TIMEOUT_S)
    ap.add_argument("--json", type=Path, help="write the full CheckResult here")
    ap.add_argument("--mode", choices=["isolated", "whole"], default=core.CHECK_MODE)
    ap.add_argument("--workers", type=int, default=core.CHECK_WORKERS)
    ap.add_argument("--no-cache", action="store_true")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 1 if e.code else 0
    a.artifact = a.artifact or core.load_subject(a.subject).source_path
    if not a.spec.is_file() or not a.artifact.is_file():
        print(f"check: no such file: {a.spec if not a.spec.is_file() else a.artifact}", file=sys.stderr)
        return 1
    try:
        problems = lint(a.spec, a.artifact, subject=a.subject)
    except core.CompileError as e:
        print(f"check: artifact does not compile: {e}", file=sys.stderr)
        return 1
    if problems:
        for p in problems:
            print(f"{a.spec}: {p}")
        print(f"check: {a.spec} is not a spec (lint), no verdict")
        return 1

    if a.mode == "whole":
        r = core.smtcheck(a.spec, a.artifact, a.timeout_ms, a.wall_timeout_s, subject=a.subject)
        result = asdict(r)
        result["mode"] = "whole"
        print(f"spec      {a.spec}")
        print(f"artifact  {a.artifact}")
        print(f"mode      whole (protocol v1)")
        print(f"verdict   {r.verdict} ({r.reason})")
        print(f"duration  {r.duration_s} s (timeout {r.timeout_ms} ms per query, wall {r.wall_timeout_s} s)")
        print(f"input     sha256 {r.solc_input_sha256}")
        print("targets:")
        for row in target_rows(r):
            print(row)
    else:
        r = core.smtcheck_isolated(a.spec, a.artifact, a.timeout_ms, a.wall_timeout_s, workers=a.workers, subject=a.subject,
                                   cache_dir=None if a.no_cache else core.CACHE_DIR)
        result = asdict(r)
        print(f"spec      {a.spec}")
        print(f"artifact  {a.artifact}")
        print(f"mode      isolated (Check v2), subject {a.subject}, {len(r.checks)} checks, {r.workers} workers")
        print(f"verdict   {r.verdict} ({r.reason})")
        print(f"duration  {r.duration_s} s wall, {r.cpu_s} s solc total, {r.cache_hits} cache hits "
              f"(timeout {r.timeout_ms} ms per query, wall {r.wall_timeout_s} s per check)")
        for c in r.checks:
            cr = core.CheckResult(**c["result"])
            print(f"check {c['check']}: {cr.verdict} ({cr.reason}), {cr.duration_s} s"
                  f"{' (cached)' if c['cached'] else ''}, input sha256 {cr.solc_input_sha256[:16]}…")
            for row in target_rows(cr):
                print("  " + row)
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        doc = {"spec": str(a.spec), "artifact": str(a.artifact),
               "spec_source_sha256": core.sha256_file(a.spec),
               "artifact_source_sha256": core.sha256_file(a.artifact),
               "lint": [], "mode": a.mode, "check": result}
        a.json.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return EXIT[r.verdict]


if __name__ == "__main__":
    sys.exit(main())
