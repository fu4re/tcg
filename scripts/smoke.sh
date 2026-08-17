#!/bin/sh
# smoke.sh — end-to-end acceptance check for the installed `tcg` command.
#
# Exercises the full happy-then-honest-refusal path: init a workspace, wire up
# a loop with a trivial claim pair, compile, and walk graph check / approve /
# prove / freeze — asserting the *exact* exit code at each step. tcg's exit
# codes are load-bearing (tcg/outcome.py: OK=0, USAGE=1, UNKNOWN=2, REFUSED=3),
# so "prints something" is not success here — only the documented code is.
#
# Runs from a temp directory OUTSIDE any repo, against whatever `tcg` resolves
# on $PATH (override with $TCG to point at a specific binary). This is
# deliberately NOT a `python -m tcg` / PYTHONPATH test: the point is to prove
# the *installed* command works for any agent/tool that shells out to `tcg`.
#
# Usage:
#   scripts/smoke.sh
#   TCG=/path/to/tcg scripts/smoke.sh
#
# Exits 0 iff every step below hit its expected exit code; non-zero otherwise.

set -u

TCG="${TCG:-tcg}"

fail_count=0

# step NAME EXPECTED_CODE -- cmd args...
step() {
    name="$1"
    expected="$2"
    shift 2
    actual=0
    "$@" >step.out 2>step.err || actual=$?
    if [ "$actual" -eq "$expected" ]; then
        printf 'PASS  %-20s exit=%s\n' "$name" "$actual"
    else
        printf 'FAIL  %-20s expected exit=%s got exit=%s\n' "$name" "$expected" "$actual"
        echo "  --- stdout ---"
        sed 's/^/  /' step.out
        echo "  --- stderr ---"
        sed 's/^/  /' step.err
        fail_count=$((fail_count + 1))
    fi
}

command -v "$TCG" >/dev/null 2>&1 || {
    echo "FAIL  smoke: '$TCG' not found on PATH (set \$TCG to override)" >&2
    exit 1
}

workdir=$(mktemp -d "${TMPDIR:-/tmp}/tcg-smoke.XXXXXX") || {
    echo "FAIL  smoke: could not create temp dir" >&2
    exit 1
}
cleanup() { rm -rf "$workdir"; }
trap cleanup EXIT INT TERM

case "$workdir" in
    /Users/*/sheaf/*|"$PWD"/*)
        echo "FAIL  smoke: temp dir $workdir looks like it is inside a repo" >&2
        exit 1
        ;;
esac

echo "using tcg: $(command -v "$TCG")"
echo "workdir:   $workdir"
echo

cd "$workdir" || exit 1

step "init"             0 "$TCG" init
step "loop new"         0 "$TCG" loop new demo

cat >iface.json <<'EOF'
{"pre":"true","post":"true","exit":"normal","footprint":{"reads":[],"writes":[]},"rely":"true","guar":"true","claims":[{"label":"main","file":"main.k"},{"label":"guar","file":"guar.k","role":"guar","root":false}]}
EOF

cat >.tcg/loops/demo/main.k <<'EOF'
claim <k> #execute => #halt </k>
requires true
ensures true
[label(main), all-path]
EOF

cat >.tcg/loops/demo/guar.k <<'EOF'
claim <k> #execute => #halt </k>
requires true
ensures true
[label(guar), all-path]
EOF

step "iface set"        0 "$TCG" iface set demo --file iface.json
step "compile-claims"   0 "$TCG" compile-claims demo
step "graph check"      3 "$TCG" graph check
step "approve"          0 "$TCG" approve --reviewer smoke
step "prove"            1 "$TCG" prove demo
step "freeze"           3 "$TCG" freeze

echo
if [ "$fail_count" -eq 0 ]; then
    echo "smoke: ALL PASS"
    exit 0
else
    echo "smoke: $fail_count step(s) FAILED"
    exit 1
fi
