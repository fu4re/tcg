#!/usr/bin/env bash
#
# build-getters-full.sh -- reproduce the Track P0.5b getters-full workspace +
# bundle end-to-end from the committed authored sources under
# tests/reference/getters-full/.
#
# Upgrades Finding 0003a's side-effect-free half (proved without lemmas) to
# the FULL k-dss behaviour for GemJoin's vat()/ilk()/gem(): "returns exactly
# the stored slot AND changes no state." Proves, on the LEMMA-EQUIPPED
# kompiled KEVM Haskell backend (Finding 0004, gate G4->G5):
#   vat/vat (root) vat() succeeds, storage/callstack unchanged, and
#     <output> == #buf(32, #lookup(STORAGE,1) &Int maxUInt160)      -> Accept
#   ilk/ilk (root) ilk() succeeds, storage/callstack unchanged, and
#     <output> == #buf(32, #lookup(STORAGE,2))                      -> Accept
#   gem/gem (root) gem() succeeds, storage/callstack unchanged, and
#     <output> == #buf(32, #lookup(STORAGE,3) &Int maxUInt160)      -> Accept
# Each root also carries an identical-restatement guar claim (vat_g/ilk_g/gem_g).
#
# Subject: the same real GemJoin ETH-A runtime bytecode Finding 0003/0003a
# used (tests/reference/getters/subject/runtime.hex, 3462 bytes, on-chain
# EXTCODEHASH 0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa)
# -- reused as-is, not duplicated, since the bytecode is unchanged.
#
# Then: subject set, approve, graph check, vacuity (all three roots), freeze
# -> a bundle whose identity is sha256(MANIFEST.json); then self-verify.
#
# Usage:  scripts/build-getters-full.sh [WORKDIR]
#   WORKDIR   where to build the workspace (default: a fresh mktemp).
# Env overrides:
#   TCG_PYTHON  python interpreter (default: pinned pyenv 3.12.2)
#   KEVM        toolchain root (default: ~/toolchains/kevm-1.0.678-lemmas --
#               the LEMMA-EQUIPPED definition; Finding 0003a's half used the
#               plain, lemma-less ~/toolchains/kevm-1.0.678)
#
# Exit 0 iff: 6 Accepts (3 roots + 3 guars), 3 non-vacuous vacuity probes,
# bundle frozen + self-verifies to Accept (6/6 replay + 3/3 vacuity).
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
REF="$REPO/tests/reference/getters-full"
SUBJECT="$REPO/tests/reference/getters/subject"

TCG_PYTHON="${TCG_PYTHON:-/Users/akkedeline/.pyenv/versions/3.12.2/bin/python3}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678-lemmas}"
DEF="$KEVM/haskell"
INC1="$KEVM/evm-semantics-source"
INC2="$KEVM/plugin"

WORKDIR="${1:-$(mktemp -d -t tcg-getters-full)}"
mkdir -p "$WORKDIR"
WORKDIR="$(cd "$WORKDIR" && pwd)"

tcg() { ( cd "$1" && shift && PYTHONPATH="$REPO" "$TCG_PYTHON" -m tcg "$@" ); }

echo "== getters-full build (Track P0.5b) =="
echo "REPO      $REPO"
echo "python    $TCG_PYTHON"
echo "kevm def  $DEF (lemma-equipped)"
echo "workdir   $WORKDIR"
echo

tcg "$WORKDIR" init --definition "$DEF" -I "$INC1" -I "$INC2"

for name in vat ilk gem; do
  tcg "$WORKDIR" loop new "$name"
  cp "$REF/src/$name/$name.k"   "$WORKDIR/.tcg/loops/$name/$name.k"
  cp "$REF/src/$name/${name}_g.k" "$WORKDIR/.tcg/loops/$name/${name}_g.k"
  tcg "$WORKDIR" iface set "$name" --file "$REF/iface/$name.json"
  tcg "$WORKDIR" compile-claims "$name"
  echo "-- proving $name (root + guar) --"
  tcg "$WORKDIR" prove "$name"
  echo "-- vacuity probe $name (root) --"
  tcg "$WORKDIR" vacuity "$name"
done

# ---- subject + approve + graph + freeze -----------------------------------
tcg "$WORKDIR" subject set --runtime "$SUBJECT/runtime.hex" \
                           --environment "$SUBJECT/environment.json"
tcg "$WORKDIR" approve --reviewer track-p05b
tcg "$WORKDIR" graph check
tcg "$WORKDIR" freeze

BUNDLE="$WORKDIR/bundle"
echo
echo "== self-verify the frozen bundle =="
tcg "$WORKDIR" verify "$BUNDLE"

echo
echo "== getters-full build OK =="
echo "bundle:      $BUNDLE"
echo "manifest:    $BUNDLE/MANIFEST.json"
