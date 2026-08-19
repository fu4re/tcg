#!/usr/bin/env bash
#
# run.sh -- reproduce the Gap-#1 call-site-summary probe from the committed
# standalone kprove specs under raw/. Each spec is self-contained (one module,
# trusted summary + goal where relevant); no tcg needed. On the real kompiled
# KEVM Haskell backend (kevm-1.0.678), asserts the exact verdict of each spec.
#
# The decisive result: raw kprove applies a separately-proved callee summary as
# a circularity at an UNRESOLVED (symbolic-code) external CALL (variant 2a),
# and the non-vacuity discriminators (broken +6, no-summary, ensures-false)
# all fail to Accept. See README.md and docs/findings/0005.
#
# Usage:  tests/reference/callext/run.sh
# Env:    KEVM (default ~/toolchains/kevm-1.0.678)
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
OUT="$(mktemp -d)"; RC=0

# spec-file  spec-module  expected(ACCEPT|REFUTE|NOTACCEPT)
run() {
  local f="$1" mod="$2" want="$3"
  kprove "$HERE/raw/$f.k" --definition "$DEF" --spec-module "$mod" \
         -I "$INC1" -I "$INC2" > "$OUT/$f.log" 2>&1
  local ec=$?
  local got
  if [ $ec -eq 0 ] && head -1 "$OUT/$f.log" | grep -q '#Top'; then got=ACCEPT
  elif grep -q "doesn't unify with the destination" "$OUT/$f.log"; then got=REFUTE
  else got=NOTACCEPT; fi
  local ok="FAIL"
  if [ "$want" = "$got" ]; then ok="ok"
  elif [ "$want" = "NOTACCEPT" ] && [ "$got" != "ACCEPT" ]; then ok="ok"; got="$got(not-Accept)"; fi
  printf '%-24s want=%-10s got=%-20s [%s]\n' "$f" "$want" "$got" "$ok"
  [ "$ok" = "ok" ] || RC=1
}

echo "== Gap-#1 call-site summary probe (raw kprove) =="
run callee-d             CALLEE-D-SPEC          ACCEPT     # callee +5 over concrete bytecode (D)
run bridge-s-at-p        BRIDGE-S-AT-P-SPEC     ACCEPT     # S<==D bridge: S at concrete program proves
run caller-inline        CALLER-INLINE-SPEC     ACCEPT     # INLINE baseline (callee inlined; NOT Gap-#1)
run caller-2a            CALLER-2A-SPEC         ACCEPT     # 2a DECISIVE: summary fires at symbolic CALL
run caller-2a-broken     CALLER-2A-BROKEN-SPEC  REFUTE     # +6 summary -> structural refute (non-vacuous)
run caller-2a-nosummary  CALLER-2A-NOSUMMARY-SPEC REFUTE   # no summary -> stuck at symbolic frame
run caller-2a-vacuity    CALLER-2A-VACUITY-SPEC NOTACCEPT  # ensures false -> not Accept (non-vacuous)
run caller-drain         CALLER-DRAIN-SPEC      REFUTE     # leading STOP -> callee never runs
run compat-ok            COMPAT-OK-SPEC         ACCEPT     # Guar frames A1 => Rely
run compat-broken        COMPAT-BROKEN-SPEC     REFUTE     # broken Rely -> structural refute

echo
[ $RC -eq 0 ] && echo "== all verdicts as expected ==" || echo "== MISMATCH (see $OUT) ==" >&2
exit $RC
