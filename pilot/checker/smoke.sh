#!/usr/bin/env bash
# pilot/checker/smoke.sh -- re-prove the getters-full claims (Finding 0003b)
# and the wrong-slot discriminator inside the pinned image, via run-claim.sh.
#
# Expected: vat/ilk/gem roots + their _g guars -> Accept (exit 0 + #Top);
#           WRONG-SLOT-{VAT,ILK,GEM}-SPEC -> NOT Accept.
# Verdicts are classified by tcg/verdict.py (the same judge `tcg prove` and
# `tcg verify` use), copied next to the results with its sha256.
#
# Specs: smoke/specs/*-prove.k are the files `tcg prove` assembles from
# tests/reference/getters-full/ (generated with tcg's own pipeline; kprove
# argv recorded in STATUS.md); wrong-slot.k is tests/control/getters-full/
# wrong-slot.k verbatim.
#
# Usage:  pilot/checker/smoke.sh [OUT_DIR]   (default ~/pilot-checker/smoke)
# Exit 0 iff every expectation holds.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/../.." && pwd)"
OUT="${1:-$HOME/pilot-checker/smoke}"
TIMEOUT="${SMOKE_TIMEOUT:-3600}"   # tcg's default replay.timeout_seconds
mkdir -p "$OUT/specs" "$OUT/logs"
cp "$SCRIPT_DIR"/smoke/specs/*.k "$OUT/specs/"
cp "$REPO/tcg/verdict.py" "$OUT/verdict.py"
( cd "$OUT" && sha256sum specs/*.k verdict.py ) > "$OUT/inputs.sha256"

IMAGE_ID="${TCG_CHECKER_IMAGE_ID:-$(head -1 "$SCRIPT_DIR/IMAGE_ID")}"
export TCG_CHECKER_IMAGE_ID="$IMAGE_ID"

SLOT="${TCG_SLOT_WRAPPER:-$HOME/pilot-locks/with-slot.sh}"   # VM-wide prover slots (3)
[[ -x "$SLOT" ]] || { echo "smoke: slot wrapper $SLOT missing" >&2; exit 2; }
RESULTS="$OUT/results.tsv"
printf 'spec\tmodule\texpected\texit\tverdict\tunknown_class\twall_s\n' > "$RESULTS"
fail=0

run() {  # run SPEC MODULE EXPECTED(Accept|NotAccept)
  local spec="$1" mod="$2" expect="$3" log="$OUT/logs/$2.log" rc timed_out=0 t0 t1
  echo "[smoke] $mod ($spec), expect $expect" >&2
  echo "# $SLOT prover -- $SCRIPT_DIR/run-claim.sh $OUT/specs/$spec --spec-module $mod   (image $IMAGE_ID)" > "$log.cmd"
  t0=$(date +%s.%N)
  "$SLOT" prover -- timeout "$TIMEOUT" "$SCRIPT_DIR/run-claim.sh" "$OUT/specs/$spec" --spec-module "$mod" > "$log" 2>&1
  rc=$?
  t1=$(date +%s.%N)
  [[ $rc -eq 124 ]] && timed_out=1
  local cls
  cls="$(python3 -I -c '
import sys
sys.path.insert(0, sys.argv[1])
from verdict import classify
v, u, h = classify(int(sys.argv[2]), open(sys.argv[3], encoding="utf-8", errors="replace").read(), sys.argv[4] == "1")
print(v + "\t" + (u or "-"))' "$OUT" "$rc" "$log" "$timed_out")"
  local verdict="${cls%%$'\t'*}" wall
  wall=$(python3 -c "print(round($t1-$t0,1))")
  printf '%s\t%s\t%s\t%s\t%s\t%s\n' "$spec" "$mod" "$expect" "$rc" "$cls" "$wall" >> "$RESULTS"
  if [[ "$expect" == Accept && "$verdict" != Accept ]] || [[ "$expect" == NotAccept && "$verdict" == Accept ]]; then
    echo "[smoke] EXPECTATION FAILED: $mod -> $verdict" >&2; fail=1
  fi
}

run vat-vat-prove.k   VAT-VAT-PROVE   Accept
run vat-vat_g-prove.k VAT-VAT-G-PROVE Accept
run ilk-ilk-prove.k   ILK-ILK-PROVE   Accept
run ilk-ilk_g-prove.k ILK-ILK-G-PROVE Accept
run gem-gem-prove.k   GEM-GEM-PROVE   Accept
run gem-gem_g-prove.k GEM-GEM-G-PROVE Accept
run wrong-slot.k WRONG-SLOT-VAT-SPEC NotAccept
run wrong-slot.k WRONG-SLOT-ILK-SPEC NotAccept
run wrong-slot.k WRONG-SLOT-GEM-SPEC NotAccept

cat "$RESULTS"
exit $fail
