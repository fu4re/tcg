#!/usr/bin/env bash
#
# run-tcg-bridge.sh -- build the callext caller_2a composition through tcg's
# REAL pipeline WITH the bridge S<==D discharged, freeze it, and self-verify the
# bundle bundle-only. This is the P1 native work of docs/findings/0005: the
# abstract callee-summary node S (free <program>, which can never Accept) is
# discharged by the bridge S<==D --
#   D  (callee/d)      the +5 delta over the concrete callee bytecode P (Accept),
#   B  (bridge/sbridge)  S re-proved by EXECUTION over P            (Accept),
#   code-identity      keccak256(external_code[200]) == declared hash (verifier),
#   binding S<=>B      B carries S's exact entry/effect + delta      (structural),
# so `tcg graph check` OK, `tcg freeze` OK, `tcg verify` replays D + B + the
# caller root (with S injected) and re-derives the bridge -> certificate holds.
#
# Contrast run-tcg.sh (the Finding-0005 "before" picture: graph check refuses
# because the abstract summary node cannot be Accepted). This script is "after".
#
# Usage:  tests/reference/callext/run-tcg-bridge.sh [WORKDIR]
# Env:    KEVM (default ~/toolchains/kevm-1.0.678), TCG_PYTHON, REPO
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../../.." && pwd)}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
PY="${TCG_PYTHON:-python3}"
WS="${1:-$(mktemp -d -t callext-bridge-ws)}"
rm -rf "$WS"; mkdir -p "$WS"
tcg() { ( cd "$WS" && PYTHONPATH="$REPO" "$PY" -m tcg "$@" ); }

tcg init --definition "$DEF" -I "$INC1" -I "$INC2"
cp "$HERE/tcg/subject/runtime.hex" "$WS/runtime.hex"
tcg subject set --runtime "$WS/runtime.hex" --environment "$HERE/tcg/subject/environment.json"

mkloop() { # loopname  "bodyfile ..."  ifacefile
  tcg loop new "$1"
  for f in $2; do cp "$HERE/tcg/src/$f" "$WS/.tcg/loops/$1/$f"; done
  tcg iface set "$1" --file "$HERE/tcg/iface/$3"
  tcg compile-claims "$1"
}
mkloop callee    "d.k"            iface-callee.json
mkloop bridge    "sbridge.k"      iface-bridge.json
mkloop summary   "s.k"            iface-summary-bridged.json
mkloop caller_2a "r2a.k guar2a.k" iface-caller_2a-bridged.json

echo "== PROVE (bridge legs; summary is NOT proved -- it is bridge-discharged) =="
tcg prove callee;    echo "[callee    exit $?  expect 0/Accept  (D: +5 over concrete P)]"
tcg prove bridge;    echo "[bridge    exit $?  expect 0/Accept  (B: S re-proved over P)]"
tcg prove caller_2a; echo "[caller_2a exit $?  expect 0/Accept  (root+guar, S injected)]"
tcg vacuity caller_2a

echo "== APPROVE + GRAPH CHECK + FREEZE =="
tcg approve --reviewer p1-bridge
tcg graph check;   echo "[graph check exit $?  expect 0/OK]"
tcg freeze;        echo "[freeze      exit $?  expect 0]"

echo "== VERIFY (bundle-only; replays D + B + caller, re-derives the bridge) =="
tcg verify "$WS/bundle"; echo "[verify exit $?  expect 0/holds]"

echo
echo "workspace: $WS"
echo "bundle:    $WS/bundle"
