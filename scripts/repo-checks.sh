#!/bin/sh
# repo-checks.sh — repo-side sanity checks, run from a checkout (not an
# installed `tcg`; contrast with scripts/smoke.sh, which only ever talks to
# the installed CLI).
#
# Checks:
#
# 1. ghost-diff-parity: tcg/_data/ghost.diff (the package-data copy shipped
#    inside the tcg package, read by `tcg init` via importlib.resources — see
#    tcg/commands/init.py) must be byte-identical to theory/patches/ghost.diff
#    (the canonical, human-edited source). If they drift, a non-editable
#    `pip install` ships a stale patch while the repo's own theory/patches/
#    tree — and anything proved against it — has already moved on, silently.
#
# 2. bundle-only-imports: tcg/commands/verify.py, tcg/commands/roots.py, and
#    tcg/verdict.py (the prover-verdict judge shared with `prove`) must not
#    import tcg.workspace or tcg.commands.* — the bundle-only contract:
#    a verifier that can reach workspace state is no longer verifying just
#    the bundle a stranger handed it. Mechanical (grep), not "someone will
#    remember" — the contract erodes silently otherwise, one convenient
#    import at a time.
#
# Usage:
#   scripts/repo-checks.sh
#
# Exits 0 iff every check passes; non-zero on the first failure, with a
# message naming the mismatch and how to fix it.

set -u

# Resolve the repo root from this script's own location, not $PWD: the
# script is meant to be runnable from anywhere in the checkout.
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P)
repo_root=$(CDPATH= cd -- "$script_dir/.." && pwd -P)

canonical="$repo_root/theory/patches/ghost.diff"
packaged="$repo_root/tcg/_data/ghost.diff"
bundle_only_files="tcg/commands/verify.py tcg/commands/roots.py tcg/verdict.py"

fail_count=0

check_ghost_diff_parity() {
    if [ ! -f "$canonical" ]; then
        echo "FAIL  ghost-diff-parity   missing: $canonical" >&2
        fail_count=$((fail_count + 1))
        return
    fi
    if [ ! -f "$packaged" ]; then
        echo "FAIL  ghost-diff-parity   missing: $packaged" >&2
        fail_count=$((fail_count + 1))
        return
    fi
    if cmp -s "$canonical" "$packaged"; then
        printf 'PASS  %-20s %s == %s\n' "ghost-diff-parity" \
            "tcg/_data/ghost.diff" "theory/patches/ghost.diff"
    else
        echo "FAIL  ghost-diff-parity   tcg/_data/ghost.diff has drifted from" \
            "theory/patches/ghost.diff (the canonical source) — copy" \
            "$canonical over $packaged and commit both" >&2
        fail_count=$((fail_count + 1))
    fi
}

check_bundle_only_imports() {
    for f in $bundle_only_files; do
        path="$repo_root/$f"
        if [ ! -f "$path" ]; then
            echo "FAIL  bundle-only-imports   missing: $path" >&2
            fail_count=$((fail_count + 1))
            continue
        fi
        hit=$(grep -nE '^[[:space:]]*(import|from)[[:space:]]+tcg\.(workspace|commands)([.[:space:]]|$)' "$path")
        if [ -n "$hit" ]; then
            echo "FAIL  bundle-only-imports   $f imports tcg.workspace or tcg.commands.* --" \
                "verify/roots/verdict must stay bundle-only (no workspace state); found:" >&2
            echo "$hit" | sed 's/^/         /' >&2
            fail_count=$((fail_count + 1))
        else
            printf 'PASS  %-20s %s has no tcg.workspace/tcg.commands.* import\n' \
                "bundle-only-imports" "$f"
        fi
    done
}

check_ghost_diff_parity
check_bundle_only_imports

if [ "$fail_count" -eq 0 ]; then
    echo "repo-checks: ALL PASS"
    exit 0
else
    echo "repo-checks: $fail_count check(s) FAILED"
    exit 1
fi
