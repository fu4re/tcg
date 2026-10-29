#!/usr/bin/env bash
# run-controls.sh -- WS-H: re-discharge claim / vacuity / discriminator specs
# inside the pinned checker image (pilot/checker/run-claim.sh), one ledger
# event per kprove run, verdict classified by tcg/verdict.py (the same judge
# `tcg prove` / `tcg verify` use). This script judges nothing itself.
#
# Usage (from anywhere):
#   run-controls.sh <results.tsv> <spec.k>:<MODULE>:<Accept|NotAccept> ...
# spec paths are relative to the bundle root (pilot/bundle). Logs land next
# to the results file in logs/<MODULE>.log (+ .log.err). Classification uses
# stdout+stderr, as `tcg prove` does. Exit 0 iff every expectation held.
set -uo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BUNDLE="$(cd "$HERE/../.." && pwd)"
REPO="$(cd "$BUNDLE/../.." && pwd)"
RESULTS="$1"; shift
LOGDIR="$(dirname "$RESULTS")/logs"
mkdir -p "$LOGDIR"
IMAGE_ID="${TCG_CHECKER_IMAGE_ID:-$(head -1 "$REPO/pilot/checker/IMAGE_ID")}"
export TCG_CHECKER_IMAGE_ID="$IMAGE_ID"
TIMEOUT="${CONTROL_TIMEOUT:-3600}"
SLOT="${PILOT_SLOT:-$HOME/pilot-locks/with-slot.sh}"
[[ -x "$SLOT" ]] || { echo "run-controls: slot wrapper $SLOT missing" >&2; exit 2; }
[[ -f "$RESULTS" ]] || printf 'spec\tmodule\texpected\texit\tverdict\tunknown_class\twall_s\tlog_sha256\timage\n' > "$RESULTS"

fail=0
for item in "$@"; do
  IFS=: read -r spec mod expect <<<"$item"
  log="$LOGDIR/$mod.log"
  rel_log="$(python3 -c 'import os,sys;print(os.path.relpath(sys.argv[1],sys.argv[2]))' "$log" "$BUNDLE")"
  echo "[controls] $mod ($spec) expect $expect" >&2
  t0=$(date +%s.%N)
  # VM concurrency rule: every prover container holds one of the 3 VM-wide
  # prover slots (shared with WS-C); run-claim.sh adds --memory=6g --cpus=2.
  # The lock wraps the ledger call, so the recorded argv stays run-claim.sh.
  ( cd "$BUNDLE" && "$SLOT" prover -- timeout "$TIMEOUT" python3 "$REPO/pilot/tools/ledger.py" run \
      --ledger provenance/ledger.jsonl --root . \
      --tool kevm-prove --tool-hash "$IMAGE_ID" \
      --in "$spec" --stdout "$rel_log" --stderr "$rel_log.err" \
      -- ../checker/run-claim.sh "$spec" --spec-module "$mod" )
  rc=$?
  t1=$(date +%s.%N)
  timed_out=0; [[ $rc -eq 124 ]] && timed_out=1
  cls="$(python3 -I -c '
import sys
sys.path.insert(0, sys.argv[1])
from tcg.verdict import classify
rd = lambda f: open(f, encoding="utf-8", errors="replace").read()
v, u, h = classify(int(sys.argv[2]), rd(sys.argv[3]) + rd(sys.argv[3] + ".err"), sys.argv[4] == "1")  # stdout+stderr, as tcg prove
print(v + "\t" + (u or "-"))' "$REPO" "$rc" "$log" "$timed_out")"
  verdict="${cls%%$'\t'*}"
  wall=$(python3 -c "print(round($t1-$t0,1))")
  printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$spec" "$mod" "$expect" "$rc" "$cls" "$wall" \
    "$(sha256sum "$log" | cut -c1-64)" "$IMAGE_ID" >> "$RESULTS"
  if [[ "$expect" == Accept && "$verdict" != Accept ]] || [[ "$expect" == NotAccept && "$verdict" == Accept ]]; then
    echo "[controls] EXPECTATION FAILED: $mod -> $verdict" >&2; fail=1
  else
    echo "[controls] $mod -> $verdict (as expected)" >&2
  fi
done
exit $fail
