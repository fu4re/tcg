#!/usr/bin/env bash
#
# run-tcg.sh -- drive the callext toy through tcg's REAL pipeline (prove.py
# trusted-child injection, verdict.classify judge), from the committed tcg/src
# + tcg/iface. Shows that tcg's own `prove` step already applies the abstract
# callee summary at the symbolic-code CALL (caller_2a -> Accept), that the +6
# broken summary refutes (caller_2a_broken -> exit 3), and -- via `graph check`
# -- the ONE residual gap: closure requires the abstract summary node to be
# Accepted, which it cannot be (its program is symbolic). That gap is the P1
# native work (~1-2d). See docs/findings/0005.
#
# Usage:  tests/reference/callext/run-tcg.sh [WORKDIR]
# Env:    KEVM (default ~/toolchains/kevm-1.0.678), TCG_PYTHON, REPO
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../../.." && pwd)}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
PY="${TCG_PYTHON:-python3}"
WS="${1:-$(mktemp -d -t callext-ws)}"
rm -rf "$WS"; mkdir -p "$WS"
tcg() { ( cd "$WS" && PYTHONPATH="$REPO" "$PY" -m tcg "$@" ); }

tcg init --definition "$DEF" -I "$INC1" -I "$INC2"
cp "$HERE/tcg/subject/runtime.hex" "$WS/runtime.hex"
tcg subject set --runtime "$WS/runtime.hex" --environment "$HERE/tcg/subject/environment.json"

mkloop() { # loopname  bodyfile  ifacefile
  tcg loop new "$1"
  cp "$HERE/tcg/src/$2" "$WS/.tcg/loops/$1/$2"
  tcg iface set "$1" --file "$HERE/tcg/iface/$3"
  tcg compile-claims "$1"
}
mkloop callee           d.k       iface-callee.json
mkloop summary          s.k       iface-summary.json
mkloop summary_broken   s6.k      iface-summary_broken.json
mkloop caller_inline    rinline.k iface-caller_inline.json
mkloop caller_2a        r2a.k     iface-caller_2a.json
mkloop caller_2a_broken r2a.k     iface-caller_2a_broken.json

echo "== PROVE (tcg pipeline) =="
tcg prove callee;           echo "[callee           exit $?  expect 0/Accept]"
tcg prove caller_inline;    echo "[caller_inline    exit $?  expect 0/Accept  (inlined)]"
tcg prove caller_2a;        echo "[caller_2a        exit $?  expect 0/Accept  (SUMMARY fired)]"
tcg prove caller_2a_broken; echo "[caller_2a_broken exit $?  expect 3/Refute  (+6)]"

echo "== graph check: the residual gap =="
tcg graph check 2>&1 | grep -i 'summary' || true
echo "(closure requires the abstract summary node to be Accepted -- it cannot be;"
echo " discharging it via the bridge S<==D is the P1 native work.)"
