#!/usr/bin/env bash
#
# build-reference.sh -- reproduce the Track D reference workspace + bundle
# end-to-end from the committed authored sources under tests/reference/.
#
# Proves, on the real kompiled KEVM Haskell backend (gate G2):
#   ledger/base   (role frame)  STOP program halts EVMC_SUCCESS      -> Accept
#   withdraw/main (role loop, ROOT)  CEI debit: bytecode 604660005500
#     (PUSH1 0x46; PUSH1 0x00; SSTORE; STOP) drives storage slot 0
#     100 => 70, pc 0 => 5, halts EVMC_SUCCESS                        -> Accept
#   withdraw/guar (role guar)    same debit, slot 1 (42) framed        -> Accept
# withdraw declares ledger/base as a trusted lemma, so proving withdraw
# writes trusted-lemma edges main->base and guar->base (exercises closure).
#
# Then: subject set (runtime 604660005500 + a real environment.json),
# approve, graph check, freeze -> a bundle whose identity is sha256(MANIFEST).
#
# A second, throwaway workspace runs the drain refutation control:
#   drain/drain (role loop)  bytecode 006046600055 (leading STOP; the debit
#     SSTORE is dead code after halt) claims storage slot 0 => 70 while the
#     concrete post-storage stays 100 -> STRUCTURAL non-unification -> Refute.
#
# Usage:  scripts/build-reference.sh [WORKDIR]
#   WORKDIR   where to build the reference workspace (default: a fresh mktemp).
# Env overrides:
#   TCG_PYTHON  python interpreter (default: pinned pyenv 3.12.2)
#   KEVM        toolchain root (default: ~/toolchains/kevm-1.0.678)
#
# Exit 0 iff: 3 Accepts, bundle frozen + self-verifies to Accept, and the
# drain control returns exit 3 (structural Refute). Anything else aborts.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
REF="$REPO/tests/reference"

TCG_PYTHON="${TCG_PYTHON:-python3}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"
INC1="$KEVM/evm-semantics-source"
INC2="$KEVM/plugin"

WORKDIR="${1:-$(mktemp -d -t tcg-reference)}"
mkdir -p "$WORKDIR"
WORKDIR="$(cd "$WORKDIR" && pwd)"
DRAINDIR="${WORKDIR%/}-drain"

tcg() { ( cd "$1" && shift && PYTHONPATH="$REPO" "$TCG_PYTHON" -m tcg "$@" ); }

echo "== reference build =="
echo "REPO      $REPO"
echo "python    $TCG_PYTHON"
echo "kevm def  $DEF"
echo "workdir   $WORKDIR"
echo

# ---- 1. correct-form workspace: ledger + withdraw ----------------------------
tcg "$WORKDIR" init --definition "$DEF" -I "$INC1" -I "$INC2"

tcg "$WORKDIR" loop new ledger
cp "$REF/src/ledger/base.k" "$WORKDIR/.tcg/loops/ledger/base.k"
tcg "$WORKDIR" iface set ledger --file "$REF/iface/ledger.json"
tcg "$WORKDIR" compile-claims ledger

tcg "$WORKDIR" loop new withdraw
cp "$REF/src/withdraw/main.k" "$WORKDIR/.tcg/loops/withdraw/main.k"
cp "$REF/src/withdraw/guar.k" "$WORKDIR/.tcg/loops/withdraw/guar.k"
tcg "$WORKDIR" iface set withdraw --file "$REF/iface/withdraw.json"
tcg "$WORKDIR" compile-claims withdraw

echo "-- proving ledger (base) --";    tcg "$WORKDIR" prove ledger
echo "-- proving withdraw (main,guar) --"; tcg "$WORKDIR" prove withdraw

# ---- 1b. vacuity probe: the root must not be an empty (vacuous) proof --------
# Falsifies each proved claim's postcondition and re-proves; a NON-vacuous
# claim's falsified form does not prove. freeze refuses a root without a
# non-vacuous vacuity record (P0-B, Hole 1). withdraw carries the root (main).
echo "-- vacuity probe withdraw (root main + guar) --"; tcg "$WORKDIR" vacuity withdraw

# ---- 2. subject + approve + graph + freeze -----------------------------------
tcg "$WORKDIR" subject set --runtime "$REF/subject/runtime.hex" \
                           --environment "$REF/subject/environment.json"
tcg "$WORKDIR" approve --reviewer track-d
tcg "$WORKDIR" graph check
tcg "$WORKDIR" freeze

BUNDLE="$WORKDIR/bundle"
echo
echo "== self-verify the frozen bundle =="
tcg "$WORKDIR" verify "$BUNDLE"

# ---- 3. drain refutation control (separate throwaway workspace) --------------
echo
echo "== drain refutation control =="
rm -rf "$DRAINDIR"; mkdir -p "$DRAINDIR"
tcg "$DRAINDIR" init --definition "$DEF" -I "$INC1" -I "$INC2"
tcg "$DRAINDIR" loop new drain
cp "$REF/src/drain/drain.k" "$DRAINDIR/.tcg/loops/drain/drain.k"
tcg "$DRAINDIR" iface set drain --file "$REF/iface/drain.json"
tcg "$DRAINDIR" compile-claims drain
set +e
tcg "$DRAINDIR" prove drain
DRAIN_RC=$?
set -e
echo "drain prove exit: $DRAIN_RC (expected 3 = structural Refute)"
[ "$DRAIN_RC" -eq 3 ] || { echo "FAIL: drain did not structurally Refute" >&2; exit 1; }

echo
echo "== reference build OK =="
echo "bundle:      $BUNDLE"
echo "manifest:    $BUNDLE/MANIFEST.json"
echo "drain logs:  $DRAINDIR/.tcg/logs/"
