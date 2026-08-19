#!/bin/sh
# repo-checks.sh — repo-side sanity checks, run from a checkout (not an
# installed `tcg`; contrast with scripts/smoke.sh, which only ever talks to
# the installed CLI).
#
# Checks:
#
# 1. patch-parity: every tcg/_data/*.diff (the package-data copies shipped
#    inside the tcg package, read by `tcg init` via importlib.resources — see
#    tcg/commands/init.py) must be byte-identical to its theory/patches/ twin
#    (the canonical, human-edited source): ghost.diff and lemmas.diff. If they
#    drift, a non-editable `pip install` ships a stale patch while the repo's
#    own theory/patches/ tree — and anything proved against it — has already
#    moved on, silently.
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

vendored_patches="ghost.diff lemmas.diff"
bundle_only_files="tcg/commands/verify.py tcg/commands/roots.py tcg/verdict.py"

fail_count=0

check_patch_parity() {
    for name in $vendored_patches; do
        canonical="$repo_root/theory/patches/$name"
        packaged="$repo_root/tcg/_data/$name"
        if [ ! -f "$canonical" ]; then
            echo "FAIL  patch-parity        missing: $canonical" >&2
            fail_count=$((fail_count + 1))
            continue
        fi
        if [ ! -f "$packaged" ]; then
            echo "FAIL  patch-parity        missing: $packaged" >&2
            fail_count=$((fail_count + 1))
            continue
        fi
        if cmp -s "$canonical" "$packaged"; then
            printf 'PASS  %-20s %s == %s\n' "patch-parity" \
                "tcg/_data/$name" "theory/patches/$name"
        else
            echo "FAIL  patch-parity        tcg/_data/$name has drifted from" \
                "theory/patches/$name (the canonical source) — copy" \
                "$canonical over $packaged and commit both" >&2
            fail_count=$((fail_count + 1))
        fi
    done
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

check_patch_parity
check_bundle_only_imports

if [ "$fail_count" -eq 0 ]; then
    echo "repo-checks: ALL PASS"
    exit 0
else
    echo "repo-checks: $fail_count check(s) FAILED"
    exit 1
fi
