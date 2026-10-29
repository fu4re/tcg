#!/usr/bin/env python3
"""Record or check mutant witnesses (task 04), with the verifier's own rules.

Convention, one directory per witness: <bundle>/evidence/mutants/<name>/ (name
usually claim-0N, or claim-0N-<tag> for several per claim) holding
  mutant.bin   the mutated runtime bytecode (must differ from hard/artifact.bin), or
  harness/     a concrete-execution harness for the mutant;
  replay.sh    run as `sh replay.sh` with cwd = that directory, inside a scratch
               copy of the bundle, env = PATH + a scratch HOME only. Its stdout
               must be byte-stable across runs (no temp paths, timings, dates);
  refutation.json  {"claim", "kind", "output_sha256", "runs"}, written by `record`.
Kinds, never merged (rules in pilot/verifier/tcgverify/evidence.py):
  refute                    stdout judged "refute" by the KEVM verdict judge: a
                            symbolic stuck state, NOT a concrete counterexample
  concrete_trace_violation  exit 0 and a stdout line "TCG-VIOLATION: <what>"
  not_accept                stdout not judged "accept"; reported, never a witness

Usage:
  mutant_witness.py record <bundle> <name> --claim <id> --kind <kind> [--runs N]
      runs replay.sh N times (default 2); refuses (exit 1, nothing written) unless
      every run gives the same stdout and the kind's rule holds; then writes
      refutation.json. Real provers must run in a slot on the shared VM:
      ~/pilot-locks/with-slot.sh prover -- python3 pilot/tools/mutant_witness.py record ...
  mutant_witness.py check <bundle>
      replays every witness the way the verifier's L2 does; prints one line each.
      Exit 0 unless a witness is malformed or not reproduced.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "verifier"))

from tcgverify import canon, evidence, levels  # noqa: E402


def _subject_problem(root: str, d: str) -> str | None:
    base = os.path.join(root, levels.MUTANTS, d)
    mb, harness = os.path.join(base, "mutant.bin"), os.path.join(base, "harness")
    if not os.path.isfile(os.path.join(base, "replay.sh")):
        return "replay.sh missing"
    if not (os.path.isfile(mb) or os.path.isdir(harness)):
        return "neither mutant.bin nor harness/"
    art = os.path.join(root, "hard/artifact.bin")
    if os.path.isfile(mb) and os.path.isfile(art) and canon.sha256_file(mb) == canon.sha256_file(art):
        return "mutant.bin is byte-identical to the artefact"
    return None


def record(root, name, claim, kind, runs) -> int:
    bad = _subject_problem(root, name) or (kind not in evidence.KINDS and f"kind must be one of {evidence.KINDS}")
    if bad:
        print(f"REFUSE: {name}: {bad}")
        return 1
    script = f"{levels.MUTANTS}{name}/replay.sh"
    results = [evidence.run_replay(root, script) for _ in range(runs)]
    hashes = {canon.sha256_bytes(r[1].encode()) for r in results}
    if len(hashes) != 1:
        print(f"REFUSE: {name}: replay stdout differs across {runs} runs (not byte-stable): {sorted(hashes)}")
        return 1
    rc, out, _, timed_out, _ = results[0]
    j = evidence.judge_witness(kind, rc, out, timed_out, None)
    if not j["kind_rule_holds"]:
        print(f"REFUSE: {name}: the '{kind}' rule does not hold (exit {rc}, judge says "
              f"{j['checker_classification']}, violation line: {'yes' if 'violation' in j else 'no'})")
        return 1
    ref = {"claim": claim, "kind": kind, "output_sha256": j["output_sha256"], "runs": runs}
    with open(os.path.join(root, levels.MUTANTS, name, "refutation.json"), "w", encoding="utf-8") as f:
        json.dump(ref, f, indent=2)
        f.write("\n")
    print(f"recorded {name}: {kind} for {claim}, stdout sha256 {j['output_sha256']}")
    return 0


def check(root) -> int:
    mdir = os.path.join(root, levels.MUTANTS)
    names = sorted(d for d in os.listdir(mdir) if os.path.isdir(os.path.join(mdir, d))) if os.path.isdir(mdir) else []
    failed = 0
    for d in names:
        try:
            with open(os.path.join(mdir, d, "refutation.json"), encoding="utf-8") as f:
                ref = json.load(f)
            bad = _subject_problem(root, d) or (ref.get("kind") not in evidence.KINDS and "bad kind")
        except (OSError, ValueError, AttributeError) as e:
            ref, bad = {}, f"refutation.json unreadable: {e}"
        if bad:
            print(f"{d}: malformed ({bad})")
            failed += 1
            continue
        rc, out, _, timed_out, _ = evidence.run_replay(root, f"{levels.MUTANTS}{d}/replay.sh")
        j = evidence.judge_witness(ref["kind"], rc, out, timed_out, ref.get("output_sha256") or "")
        print(f"{d}: claim {ref.get('claim')} kind {ref['kind']} -> {j['outcome']}"
              f"{'' if ref['kind'] in evidence.WITNESS_KINDS else ' (not a witness)'}")
        failed += j["outcome"] != ref["kind"]
    print(f"{len(names)} witness dir(s), {failed} malformed or not reproduced")
    return 1 if failed else 0


def main(argv) -> int:
    p = argparse.ArgumentParser(prog="mutant_witness.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("record")
    r.add_argument("bundle")
    r.add_argument("name")
    r.add_argument("--claim", required=True)
    r.add_argument("--kind", required=True, choices=evidence.KINDS)
    r.add_argument("--runs", type=int, default=2)
    c = sub.add_parser("check")
    c.add_argument("bundle")
    a = p.parse_args(argv)
    if a.cmd == "record":
        return record(a.bundle, a.name, a.claim, a.kind, max(1, a.runs))
    return check(a.bundle)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
