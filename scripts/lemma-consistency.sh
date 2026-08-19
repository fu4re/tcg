#!/usr/bin/env bash
#
# lemma-consistency.sh -- MANDATORY soundness control for the vendored
# simplification lemmas (Finding 0004, task 4).
#
# Adding simplification lemmas grows the trusted base, and NEITHER the vacuity
# probe NOR program-binding catches a FALSE lemma: a wrong simplification rule
# would let the prover Accept a false postcondition, silently. This script is
# the bound on that growth. It attempts to prove a battery of KNOWN-FALSE
# identities -- one per vendored submodule -- against the lemma-equipped
# definition, and REQUIRES the prover to refuse every one of them (verdict !=
# Accept: no "#Top" AND non-zero kprove exit).
#
# If ANY false identity proves (Accept), the lemma set is UNSOUND: the script
# fails loudly with a non-zero exit and the offending probe named. Do NOT ship
# a lemma set that proves a false identity.
#
# The probe claims live in tests/control/lemmas/false-identities.k (each a bare
# functional claim <k> LHS:Int => WRONG:Int </k> whose LHS a real simplification
# rule reduces to its CORRECT value, leaving the false equality correct==wrong).
#
# Usage:  scripts/lemma-consistency.sh
# Env overrides:
#   KEVM_LEMMAS   lemma-equipped toolchain root
#                 (default: ~/toolchains/kevm-1.0.678-lemmas)
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"

KEVM_LEMMAS="${KEVM_LEMMAS:-$HOME/toolchains/kevm-1.0.678-lemmas}"
DEF="$KEVM_LEMMAS/haskell"
INC1="$KEVM_LEMMAS/evm-semantics-source"
INC2="$KEVM_LEMMAS/plugin"
SPEC="$REPO/tests/control/lemmas/false-identities.k"
LOGDIR="$REPO/tests/control/lemmas/logs"
mkdir -p "$LOGDIR"

if [ ! -f "$DEF/definition.kore" ]; then
  echo "lemma-consistency: no lemma-equipped definition at $DEF" >&2
  echo "  build it first: scripts/build-kevm.sh --lemmas" >&2
  exit 2
fi

# One probe per vendored submodule. Each MUST NOT prove.
MODULES=(
  "PROBE-ASWORD-SPEC:evm-int-simplification: #asWord(#buf(32,X)) => X, target X+1"
  "PROBE-RANGE-SPEC:bytes-simplification: decode 2nd arg (WAD), target 1st arg (USR)"
  "PROBE-INT-SPEC:int-simplification: (A+B)-B => A, target A+1"
  "PROBE-BITWISE-SPEC:bitwise-simplification: X&X => X, target X+1"
  "PROBE-B2W-SPEC:bool2word-simplification: b2w-eq-zero direction: bool2Word(bool2Word(B)==Int 0) => WRONG bool2Word(B) (correct: bool2Word(notBool B))"
)

echo "== lemma consistency probe =="
echo "definition  $DEF"
echo "spec        $SPEC"
echo

fail=0
for entry in "${MODULES[@]}"; do
  mod="${entry%%:*}"
  desc="${entry#*:}"
  log="$LOGDIR/probe-$mod.log"
  kprove "$SPEC" --definition "$DEF" --spec-module "$mod" \
    -I "$INC1" -I "$INC2" > "$log" 2>&1
  rc=$?
  # Accept iff kprove exit 0 AND the "#Top" success marker is present (the same
  # corroboration tcg.verdict.classify() requires -- exit 0 alone is not Accept).
  if [ "$rc" -eq 0 ] && grep -q '#Top' "$log"; then
    echo "  UNSOUND  $mod  (PROVED a false identity!)  exit=$rc"
    echo "           $desc"
    echo "           log: $log"
    fail=1
  else
    echo "  refused  $mod  exit=$rc  ($desc)"
  fi
done

echo
if [ "$fail" -ne 0 ]; then
  echo "lemma-consistency: FAILED -- at least one FALSE identity PROVED." >&2
  echo "The lemma set is UNSOUND and MUST NOT be shipped. STOP." >&2
  exit 1
fi
echo "lemma-consistency: OK -- all ${#MODULES[@]} false identities refused (none proved)."
