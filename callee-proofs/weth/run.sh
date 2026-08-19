#!/usr/bin/env bash
# run.sh -- reproduce the WETH9 callee-summary results on the real kompiled KEVM
# Haskell backend (lemma-equipped def kevm-1.0.678-lemmas). Each spec is a
# self-contained module over the EXACT on-chain WETH9 runtime (bytecode/runtime.hex,
# EXTCODEHASH 0xd0a06b...25e23). Verdicts classified by the SHARED judge
# tcg.verdict.classify(); this script asserts the expected verdict of each.
#
#   D proofs Accept ONLY with lemmas_min.k (the minimal subset of upstream lemmas.k
#   OMITTED by the frozen driver: bool2Word l.71-72 + Map-reasoning l.125-130).
#   Frozen-def transferFrom_d Refutes at the bool2Word wall (pc 1755); b2w-only
#   stalls at the #lookup-over-update wall -> both families are necessary.
#
# Usage:  callee-proofs/weth/run.sh
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678-lemmas}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
TCG="/Users/akkedeline/sheaf/tcg"
OUT="$(mktemp -d)"; RC=0

run() {  # spec-basename  spec-module  expected(ACCEPT|NOTACCEPT|REFUTE)
  local f="$1" mod="$2" want="$3"
  kprove "$HERE/specs/$f.k" --definition "$DEF" --spec-module "$mod" -I "$INC1" -I "$INC2" \
      > "$OUT/$f.log" 2>&1
  local ec=$?
  local got
  got=$(cd /tmp && python3 - "$ec" "$OUT/$f.log" <<PY
import sys; sys.path.insert(0,"$TCG")
from tcg.verdict import classify
v,_,_=classify(int(sys.argv[1]), open(sys.argv[2],errors="replace").read(), False)
print(v)
PY
)
  local ok="FAIL"
  if [ "$want" = "$got" ]; then ok="ok"
  elif [ "$want" = "NOTACCEPT" ] && [ "$got" != "Accept" ]; then ok="ok"; got="$got(not-Accept)"; fi
  printf '%-24s want=%-10s got=%-22s [%s]\n' "$f" "$want" "$got" "$ok"
  [ "$ok" = "ok" ] || RC=1
}

echo "== WETH9 callee summaries (real bytecode, lemma-equipped def + omitted-lemma subset) =="
run transferFrom_d_lem     WETH-TRANSFERFROM-D-LEM-SPEC      Accept      # join-leg summary D
run transferFrom_wrong_lem WETH-TRANSFERFROM-WRONG-LEM-SPEC  NOTACCEPT   # wrong delta +WAD+1 refused
run transferFrom_vac_lem   WETH-TRANSFERFROM-VAC-LEM-SPEC    NOTACCEPT   # ensures false (RHS bottom) -> non-vacuous
run transfer_d_lem         WETH-TRANSFER-D-LEM-SPEC          Accept      # exit-leg summary D
run transfer_wrong_lem     WETH-TRANSFER-WRONG-LEM-SPEC      NOTACCEPT   # wrong delta +WAD+1 refused
run transfer_vac_lem       WETH-TRANSFER-VAC-LEM-SPEC        NOTACCEPT   # ensures false (RHS bottom) -> non-vacuous
echo "-- walls (frozen driver, no lemmas.k) --"
run transferFrom_d         WETH-TRANSFERFROM-D-SPEC          REFUTE      # bool2Word wall, pc 1755
run transferFrom_d_b2w     WETH-TRANSFERFROM-D-B2W-SPEC      NOTACCEPT   # b2w-only: #lookup-over-update wall

echo
[ $RC -eq 0 ] && echo "== all verdicts as expected ==" || echo "== MISMATCH (see $OUT) ==" >&2
exit $RC
