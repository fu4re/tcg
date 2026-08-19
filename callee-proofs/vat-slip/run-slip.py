#!/usr/bin/env python3
"""run-slip.py NAME — run one Vat.slip spec (specs/NAME.k) against the bool2Word
lemma-equipped def and classify with the SAME judge tcg prove uses
(tcg.verdict.classify: exit 0 + "#Top" => Accept). Reproduces the STATUS §6 rows.

The spec is a bare `claim` body; this wraps it as `requires "edsl.md"` /
`imports EDSL` (the substrate the getters/reference proofs use) and points kprove
at the def. NO b2w.k: the bool2Word [simplification] rules now live in the def
(BOOL2WORD-SIMPLIFICATION), so importing b2w.k too would duplicate the
[b2w-eq-zero]/[b2w-eq-one] rule labels.

Env: KEVM_LEMMAS2 (default ~/toolchains/kevm-1.0.678-lemmas2), built by
     `LEMMAS_DIR=$KEVM_LEMMAS2 scripts/build-kevm.sh --lemmas`.

Usage:  python3 callee-proofs/vat-slip/run-slip.py <slip_d|slip_dpos|slip_de|slip_wrong|slip_vac>
"""
import os, sys, subprocess, tempfile, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]                       # <repo>/callee-proofs/vat-slip -> <repo>
sys.path.insert(0, str(REPO))
from tcg.claims import emit_module, module_name
from tcg.verdict import classify, to_text

name = sys.argv[1] if len(sys.argv) > 1 else sys.exit(__doc__)
L2 = Path(os.environ.get("KEVM_LEMMAS2", os.path.expanduser("~/toolchains/kevm-1.0.678-lemmas2")))
DEF, INC1, INC2 = L2 / "haskell", L2 / "evm-semantics-source", L2 / "plugin"
if not (DEF / "definition.kore").is_file():
    sys.exit(f"no def at {DEF} (build: LEMMAS_DIR={L2} scripts/build-kevm.sh --lemmas)")

body = (HERE / "specs" / f"{name}.k").read_text(encoding="utf-8")
mod = module_name("slip", name)
build = Path(tempfile.mkdtemp(prefix="tcg-slip-"))
spec = build / f"{name}-verify.k"
spec.write_text(emit_module("slip", name, ["edsl.md"], ["EDSL"], body), encoding="utf-8")

argv = ["kprove", str(spec), "--definition", str(DEF), "--spec-module", mod,
        "-I", str(INC1), "-I", str(INC2)]
print("MODULE :", mod)
print("CMD    :", " ".join(argv), flush=True)
started, timed_out = time.monotonic(), False
try:
    p = subprocess.run(argv, capture_output=True, text=True, timeout=3600, cwd=build)
    rc, log = p.returncode, p.stdout + p.stderr
except subprocess.TimeoutExpired as e:
    rc, log, timed_out = -1, to_text(e.stdout) + to_text(e.stderr), True

log_path = HERE / "logs" / f"{name}-lemmas2.log"
log_path.write_text(log, encoding="utf-8")
verdict, ucls, hint = classify(rc, log, timed_out)
print(f"EXIT   : {rc}   duration {round(time.monotonic()-started,1)}s")
print(f"#Top?  : {'yes' if '#Top' in log else 'no'}")
print(f"VERDICT: {verdict}{f'({ucls})' if ucls else ''}" + (f"   hint={hint}" if hint else ""))
print(f"LOG    : {log_path}")
