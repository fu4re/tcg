#!/bin/sh
# smoke.sh — end-to-end acceptance check for the installed `tcg` command.
#
# Exercises the full happy-then-honest-refusal path: init a workspace, wire up
# a loop with a trivial claim pair, compile, and walk graph check / approve /
# prove / freeze / verify / roots — asserting the *exact* exit code, and for
# refusal steps the *exact reason*, at each one. tcg's exit codes are
# load-bearing (tcg/outcome.py: OK=0, USAGE=1, UNKNOWN=2, REFUSED=3), so
# "exited 3" alone is not proof of the *right* refusal — an unrelated
# violation, or (for `prove`/`verify`/`roots`, which all exit 1 on both a
# documented usage refusal and an uncaught crash or "not implemented yet")
# any crash or packaging omission at all, would keep this script green
# without a stderr check. Neither is success here — only the documented code
# AND reason are.
#
# Runs from a temp directory OUTSIDE any repo or existing tcg workspace,
# against whatever `tcg` resolves on $PATH (override with $TCG to point at a
# specific binary). This is deliberately NOT a `python -m tcg` / PYTHONPATH
# test: the point is to prove the *installed* command works for any
# agent/tool that shells out to `tcg`.
#
# Usage:
#   scripts/smoke.sh
#   TCG=/path/to/tcg scripts/smoke.sh
#
# Exits 0 iff every step below hit its expected exit code (and reason, where
# checked); non-zero otherwise. On any non-green outcome (including being
# interrupted mid-run) the temp tree is retained as a witness instead of
# deleted — see cleanup() below — and its path is printed.

set -u

# tcg/outcome.py's exit-code table, named here so the step calls below read
# as assertions about outcomes, not bare integers.
EXIT_OK=0
EXIT_USAGE=1
EXIT_REFUSED=3

fail_count=0
run_complete=0   # flips to 1 only after every step below has run

# step NAME EXPECTED_CODE EXPECTED_STDERR_SUBSTRING -- cmd args...
# EXPECTED_STDERR_SUBSTRING may be "" to skip the content check (fixed-string
# match via `grep -F`, so paths like "subject/runtime.bin" aren't treated as
# a regex). Captures go to $scratch, a sibling of the tcg workspace under
# test, never into it.
step() {
    name="$1"
    expected="$2"
    substr="$3"
    shift 3
    actual=0
    "$@" >"$scratch/step.out" 2>"$scratch/step.err" || actual=$?
    ok=1
    [ "$actual" -eq "$expected" ] || ok=0
    if [ -n "$substr" ] && ! grep -qF "$substr" "$scratch/step.err"; then
        ok=0
    fi
    if [ "$ok" -eq 1 ]; then
        printf 'PASS  %-20s exit=%s\n' "$name" "$actual"
    else
        if [ -n "$substr" ]; then
            printf 'FAIL  %-20s expected exit=%s and stderr containing %s, got exit=%s\n' \
                "$name" "$expected" "\"$substr\"" "$actual"
        else
            printf 'FAIL  %-20s expected exit=%s got exit=%s\n' "$name" "$expected" "$actual"
        fi
        echo "  --- stdout ---"
        sed 's/^/  /' "$scratch/step.out"
        echo "  --- stderr ---"
        sed 's/^/  /' "$scratch/step.err"
        fail_count=$((fail_count + 1))
    fi
}

# require_step NAME EXPECTED_CODE -- cmd args...
#
# Fail-fast variant for the two preconditions everything else depends on:
# `init` and `loop new`. If either fails, every later command runs in a
# directory WITHOUT a `.tcg/` workspace — and tcg's find_root() responds to
# that by walking UP from cwd looking for one. Combined with a $TMPDIR that
# happens to sit under some real workspace, `approve`/`prove` would then
# silently mutate that real workspace's state while this script keeps
# printing FAILs for an unrelated reason. Abort loud instead of letting that
# happen.
require_step() {
    name="$1"
    expected="$2"
    shift 2
    actual=0
    "$@" >"$scratch/step.out" 2>"$scratch/step.err" || actual=$?
    if [ "$actual" -ne "$expected" ]; then
        fail_count=$((fail_count + 1))
        printf 'FAIL  %-20s expected exit=%s got exit=%s — aborting: unsafe to run later steps without a workspace\n' \
            "$name" "$expected" "$actual" >&2
        echo "  --- stdout ---" >&2
        sed 's/^/  /' "$scratch/step.out" >&2
        echo "  --- stderr ---" >&2
        sed 's/^/  /' "$scratch/step.err" >&2
        exit 1
    fi
    printf 'PASS  %-20s exit=%s\n' "$name" "$actual"
}

# resolve_abs PATH — an absolute, symlink-resolved-directory form of PATH.
# `command -v` only guarantees an absolute result for a plain PATH lookup; a
# $TCG given as a relative path containing a slash (e.g. ./dist/tcg) is
# handed back unchanged, and would 127 on every step once we cd elsewhere.
resolve_abs() {
    d=$(dirname "$1")
    f=$(basename "$1")
    (cd "$d" 2>/dev/null && printf '%s/%s\n' "$(pwd -P)" "$f")
}

TCG_RAW="${TCG:-tcg}"
tcg_which=$(command -v "$TCG_RAW") || {
    echo "FAIL  smoke: '$TCG_RAW' not found on PATH (set \$TCG to override)" >&2
    exit 1
}
TCG=$(resolve_abs "$tcg_which")
if [ -z "$TCG" ] || [ ! -x "$TCG" ]; then
    echo "FAIL  smoke: could not resolve '$TCG_RAW' (via '$tcg_which') to an absolute executable path" >&2
    exit 1
fi

command -v python3 >/dev/null 2>&1 || {
    echo "FAIL  smoke: 'python3' not found on PATH (needed to derive the iface.json fixture)" >&2
    exit 1
}

base=$(mktemp -d "${TMPDIR:-/tmp}/tcg-smoke.XXXXXX") || {
    echo "FAIL  smoke: could not create temp dir" >&2
    exit 1
}
# Absolute, symlink-resolved: a relative $TMPDIR would otherwise leave `base`
# relative, and the EXIT trap's `rm -rf` would then run it from INSIDE the
# very directory it just deleted (cwd) — silently leaking the tree — while
# the repo guard below would be comparing a relative string against absolute
# ancestors.
base=$(cd "$base" && pwd -P)

# `workdir` is the directory tcg actually runs in — it must look exactly like
# what a real user gets from a clean `tcg init`. `scratch`, a SIBLING (not a
# child) of workdir, holds everything the harness itself produces (captured
# stdout/stderr, the derived iface.json fixture) so none of that leaks into
# the workspace under test as a stray file tcg never wrote. (A plain
# `>step.out` redirect, evaluated before the command runs, would otherwise
# plant step.out in workdir before even `tcg init` gets to see an empty dir.)
workdir="$base/workspace"
scratch="$base/scratch"
mkdir -p "$workdir" "$scratch" || {
    echo "FAIL  smoke: could not create workdir/scratch under $base" >&2
    exit 1
}

cleanup() {
    cd / 2>/dev/null || true   # never rm our own cwd; portable across NFS etc.
    if [ "$run_complete" -eq 1 ] && [ "$fail_count" -eq 0 ]; then
        rm -rf "$base"
    else
        echo "witness retained: $base"
    fi
}
trap cleanup EXIT
# Signals must terminate (not fall through into a since-deleted workdir) —
# `exit` fires the EXIT trap above, so cleanup still runs exactly once, and
# because run_complete never reaches 1 on this path the witness is kept.
trap 'exit 130' INT
trap 'exit 143' TERM

# Guard: workdir must not be inside a git work tree, nor under an existing
# tcg workspace. Either would make find_root() (which walks UP from cwd)
# resolve to that ancestor instead of the fixture built below, and
# approve/prove/freeze would mutate real state instead of throwaway state.
if command -v git >/dev/null 2>&1 && git -C "$workdir" rev-parse --git-dir >/dev/null 2>&1; then
    echo "FAIL  smoke: $workdir is inside a git work tree" >&2
    exit 1
fi
p="$workdir"
while [ "$p" != "/" ]; do
    if [ -d "$p/.tcg" ]; then
        echo "FAIL  smoke: $p (ancestor of workdir) already has a .tcg workspace" >&2
        exit 1
    fi
    p=$(dirname "$p")
done

echo "using tcg: $TCG"
echo "workdir:   $workdir"
echo "scratch:   $scratch"
echo

cd "$workdir" || exit 1

require_step "init"      "$EXIT_OK" "$TCG" init
require_step "loop new"  "$EXIT_OK" "$TCG" loop new demo

# Derive the interface fixture from what `tcg loop new` actually generated
# (.tcg/loops/demo/iface.json = IFACE_TEMPLATE, which carries "requires":
# ["evm.md"] and "imports": ["EVM"]) instead of hand-rolling a parallel JSON
# blob. A handwritten fixture that omits those keys still "works" — but only
# because compile-claims' fallback defaults happen to match — and so it
# silently stops exercising the template path every real user starts from.
python3 - "$workdir/.tcg/loops/demo/iface.json" "$scratch/iface.json" <<'PY' || { printf 'FAIL  %-20s could not derive iface.json from the generated template\n' fixture >&2; exit 1; }
import json
import sys

src, dst = sys.argv[1], sys.argv[2]
with open(src) as f:
    iface = json.load(f)

iface["claims"] = [
    {"label": "main", "file": "main.k"},
    {"label": "guar", "file": "guar.k", "role": "guar", "root": False},
]

with open(dst, "w") as f:
    json.dump(iface, f)
PY

# Both claim bodies are byte-identical but for the label token — one template,
# written twice. These belong INSIDE the workspace (a real user authors them
# there too), unlike the harness-only iface.json fixture above.
for lbl in main guar; do
    printf 'claim <k> #execute => #halt </k>\nrequires true\nensures true\n[label(%s), all-path]\n' \
        "$lbl" >".tcg/loops/demo/$lbl.k" \
        || { printf 'FAIL  %-20s could not write .tcg/loops/demo/%s.k\n' fixture "$lbl" >&2; exit 1; }
done

step "iface set"        "$EXIT_OK"      ""                            "$TCG" iface set demo --file "$scratch/iface.json"
step "compile-claims"   "$EXIT_OK"      ""                            "$TCG" compile-claims demo
step "graph check"      "$EXIT_REFUSED" "is Compiled, not Accepted"   "$TCG" graph check
step "approve"          "$EXIT_OK"      ""                            "$TCG" approve --reviewer smoke
# Expected reason is "no kompiled definition": a fresh `tcg init` writes no
# "definition" into toolchain.lock, and nothing above passes --definition. If
# a definition-discovery feature (env var / global config file) lands later,
# this step must explicitly neutralize it (isolate $HOME, unset the var, ...)
# so exit 1 here still means THIS reason and not something else entirely.
step "prove"            "$EXIT_USAGE"   "no kompiled definition"      "$TCG" prove demo
step "freeze"           "$EXIT_REFUSED" "missing subject/runtime.bin" "$TCG" freeze

# Exercise the bundle-only commands too, so a packaging omission (module not
# shipped / not importable — dispatched as "tcg: '<cmd>' is not implemented
# yet", also exit 1) can't hide behind steps that never touch them.
step "verify (missing)" "$EXIT_USAGE"   "no MANIFEST.json in"         "$TCG" verify does-not-exist-bundle
step "roots (missing)"  "$EXIT_USAGE"   "no MANIFEST.json in"         "$TCG" roots does-not-exist-bundle

echo
run_complete=1
if [ "$fail_count" -eq 0 ]; then
    echo "smoke: ALL PASS"
    exit 0
else
    echo "smoke: $fail_count step(s) FAILED"
    exit 1
fi
