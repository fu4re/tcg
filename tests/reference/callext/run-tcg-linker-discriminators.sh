#!/usr/bin/env bash
#
# run-tcg-linker-discriminators.sh -- the anti-proxy controls for the CROSS-
# BUNDLE linker (REUSE, Mechanism A). Sibling of run-tcg-bridge-discriminators.sh
# (the in-graph bridge). Each discriminator MUST be refused by `tcg verify`; a
# green here would be a false green. The honest composition MUST verify (exit 0).
#
# The bundles are the same tiny synthetic dep + caller the fast unit tests use
# (tests/test_xbridge.py), built on disk by build_linker_cases.py, then judged
# by the REAL `tcg verify` CLI:
#
#   honest                    dep re-verified (post-order) + caller Accepts   -> 0
#   proxy-summary (+0 no-op)  S asserts a delta the dep root does not carry    -> 3 (step 4 binding)
#   code-hash-mismatch        keccak(dep runtime) != declared code_hash        -> 3 (step 4 code-identity)
#   external-code-mismatch    external_code[callee] != dep runtime             -> 3 (step 4 code-identity)
#   nonroot-ref               concrete_proof.root is not a dep root            -> 3 (step 4 membership)
#   missing-dep               deps/<callee_root>/ absent                       -> 3 (step 4 deps)
#   manifest-hash-mismatch    sha256(dep MANIFEST) != <callee_root> dir name   -> 3 (step 4 content-address)
#   dep-fails-own-verify      the dep does not itself verify (bad oracle)      -> 3 (step 4 recursion)
#   tampered-dep-byte         a vendored dep file flipped, MANIFEST stale      -> 3 (step 1 integrity)
#
# ONLY the honest case runs kprove (step 5 replay of the dep root over P and of
# the caller root with S injected, plus vacuity). Every discriminator refuses
# BEFORE step 5, so they are deterministic with or without the toolchain; if no
# kompiled definition is available the honest case is SKIPPED (not failed) and
# the discriminators still run.
#
# Usage:  tests/reference/callext/run-tcg-linker-discriminators.sh [WORKROOT]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../../.." && pwd)}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="${TCG_DEFINITION:-$KEVM/haskell}"
INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
PY="${TCG_PYTHON:-python3}"
ROOT="${1:-$(mktemp -d -t linker-discr)}"

DEFARGS=()
if [ -d "$DEF" ]; then DEFARGS=(--definition "$DEF"); fi
if [ -d "$INC1" ]; then DEFARGS+=(-I "$INC1"); fi
if [ -d "$INC2" ]; then DEFARGS+=(-I "$INC2"); fi

PASS=0; FAIL=0; SKIP=0
verify() { ( cd "$REPO" && PYTHONPATH="$REPO" "$PY" -m tcg verify "$1" "${DEFARGS[@]}" ); }

echo "== building linker discriminator bundles into $ROOT =="
CASES="$(cd "$REPO" && PYTHONPATH="$REPO" "$PY" -m tests.reference.callext.build_linker_cases "$ROOT")"
echo "$CASES" | sed 's/^/  /'

echo
while read -r name want caller; do
    [ -n "$name" ] || continue
    if [ "$name" = "honest" ] && [ ! -d "$DEF" ]; then
        echo "  [SKIP] honest (no kompiled definition at $DEF; set TCG_DEFINITION)"
        SKIP=$((SKIP + 1)); continue
    fi
    verify "$caller" >"$ROOT/$name.log" 2>&1
    got=$?
    if [ "$got" = "$want" ]; then
        echo "  [PASS] $name (exit $got as required)"; PASS=$((PASS + 1))
    else
        echo "  [FAIL] $name (exit $got, wanted $want) -- see $ROOT/$name.log"
        FAIL=$((FAIL + 1))
    fi
done <<< "$CASES"

echo
echo "== linker discriminators: $PASS passed, $FAIL failed, $SKIP skipped =="
echo "workroot: $ROOT"
[ "$FAIL" -eq 0 ] || exit 1
