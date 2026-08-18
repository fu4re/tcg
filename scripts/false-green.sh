#!/usr/bin/env bash
#
# false-green.sh -- reproduce gate G3's two demonstrated FALSE GREENS end to
# end on the real kompiled KEVM Haskell backend, and show the tool now REFUSES
# each, naming which guard catches which hole (docs/findings/0002):
#
#   Demo A -- program binding (P0-A) catches the G3 vacuous claim.
#     The blind-agent claim `<k> #execute ~> _ </k>` PROVES Accept (#Top) --
#     the exact false green -- yet references no <program> cell, so `tcg
#     freeze` REFUSES it: a root that binds to no subject bytecode is worthless.
#
#   Demo B -- the vacuity probe (P0-B) catches an antecedent-infeasible claim.
#     A claim that DOES bind to the subject program but carries a contradictory
#     `requires` PROVES Accept (#Top) -- another false green (vacuous: the
#     initial state is unreachable) -- and program binding passes it, but `tcg
#     vacuity` FLAGS it: its falsified form (ensures false) STILL proves.
#
# Between them, both holes are closed. Every verdict below is the real prover's
# (exit code + #Top), judged by the shared tcg.verdict.classify(); no simulated
# output.
#
# Usage:  scripts/false-green.sh [WORKDIR]
# Env overrides: TCG_PYTHON (pinned pyenv 3.12.2), KEVM (~/toolchains/kevm-1.0.678).
#
# Exit 0 iff BOTH false greens are reproduced (prove Accept) AND both are then
# refused by the right guard with the right exit code.
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
REF="$REPO/tests/reference"
TCG_PYTHON="${TCG_PYTHON:-/Users/akkedeline/.pyenv/versions/3.12.2/bin/python3}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"

WORKDIR="${1:-$(mktemp -d -t tcg-false-green)}"; mkdir -p "$WORKDIR"
WORKDIR="$(cd "$WORKDIR" && pwd)"
A="$WORKDIR/demoA"; B="$WORKDIR/demoB"
FAIL=0

tcg() { ( cd "$1" && shift && PYTHONPATH="$REPO" "$TCG_PYTHON" -m tcg "$@" ); }
run() {  # run CMD..., capture rc+output; sets RC and OUT
  OUT="$("$@" 2>&1)"; RC=$?
}
check() {  # check NAME EXPECTED_RC ACTUAL_RC EXPECTED_SUBSTR OUTPUT
  local name="$1" exp="$2" act="$3" sub="$4" out="$5" ok=1
  [ "$act" = "$exp" ] || ok=0
  [ -z "$sub" ] || printf '%s' "$out" | grep -qF -- "$sub" || ok=0
  if [ "$ok" = 1 ]; then printf '  PASS  %-34s exit=%s\n' "$name" "$act"
  else printf '  FAIL  %-34s expected exit=%s substr=%q; got exit=%s\n' \
         "$name" "$exp" "$sub" "$act"; printf '%s\n' "$out" | sed 's/^/        /'
       FAIL=$((FAIL+1)); fi
}

echo "== Demo A: program binding catches the G3 no-<program> root =="
rm -rf "$A"; mkdir -p "$A"
tcg "$A" init --definition "$DEF" -I "$INC1" -I "$INC2" >/dev/null
tcg "$A" loop new debit >/dev/null
# the exact G3 claim: no <program> cell, no nontrivial postcondition
printf 'claim <k> #execute ~> _ </k>\n [label(debit), all-path]\n' \
  > "$A/.tcg/loops/debit/debit.k"
"$TCG_PYTHON" - "$A/.tcg/loops/debit/iface.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["claims"] = [{"label": "debit", "file": "debit.k", "role": "loop", "root": True}]
json.dump(d, open(p, "w"))
PY
tcg "$A" iface set debit --file "$A/.tcg/loops/debit/iface.json" >/dev/null
tcg "$A" compile-claims debit >/dev/null
# (1) the false green: the worthless claim PROVES Accept
run tcg "$A" prove debit
check "G3 claim proves (false green)" 0 "$RC" "Accept: debit" "$OUT"
# subject + approve so the ONLY thing between us and a certificate is the gate
tcg "$A" subject set --runtime "$REF/subject/runtime.hex" \
                     --environment "$REF/subject/environment.json" >/dev/null
tcg "$A" approve --reviewer false-green >/dev/null
# (2) freeze REFUSES: the root binds to no subject bytecode
run tcg "$A" freeze
check "freeze REFUSES (program binding)" 3 "$RC" \
  "no extractable <program> cell" "$OUT"

echo
echo "== Demo B: the vacuity probe catches a program-bound vacuous root =="
rm -rf "$B"; mkdir -p "$B"
tcg "$B" init --definition "$DEF" -I "$INC1" -I "$INC2" >/dev/null
tcg "$B" loop new vac >/dev/null
# reference root (binds to the subject program) + a CONTRADICTORY requires,
# so its antecedent is infeasible -> the proof is vacuous.
"$TCG_PYTHON" - "$REF/src/withdraw/main.k" "$B/.tcg/loops/vac/vac.k" <<'PY'
import sys
src = open(sys.argv[1]).read().rstrip("\n").splitlines()
# insert the contradictory antecedent just before the trailing attribute list
attr = src.pop()  # " [label(main), all-path]"
body = "\n".join(src) + "\n    requires 100 =/=Int 100\n" + \
       attr.replace("label(main)", "label(vac)")
open(sys.argv[2], "w").write(body + "\n")
PY
"$TCG_PYTHON" - "$B/.tcg/loops/vac/iface.json" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
d["claims"] = [{"label": "vac", "file": "vac.k", "role": "loop", "root": True}]
json.dump(d, open(p, "w"))
PY
tcg "$B" iface set vac --file "$B/.tcg/loops/vac/iface.json" >/dev/null
tcg "$B" compile-claims vac >/dev/null
tcg "$B" subject set --runtime "$REF/subject/runtime.hex" \
                     --environment "$REF/subject/environment.json" >/dev/null
# (1) the false green: the vacuous claim PROVES Accept (program binding passes)
run tcg "$B" prove vac
check "vacuous claim proves (false green)" 0 "$RC" "Accept: vac" "$OUT"
# (2) the vacuity probe FLAGS it -- the falsified form still proves
run tcg "$B" vacuity vac
check "vacuity REFUSES (antecedent empty)" 3 "$RC" "VACUOUS: vac/vac" "$OUT"
# (3) and freeze refuses on the recorded vacuity flag
tcg "$B" approve --reviewer false-green >/dev/null
run tcg "$B" freeze
check "freeze REFUSES (vacuous root)" 3 "$RC" "flagged VACUOUS" "$OUT"

echo
if [ "$FAIL" -eq 0 ]; then
  echo "false-green: OK -- both G3 false greens reproduced AND refused"
  echo "  Hole 1 (program binding): caught by freeze / verify step 4-graph"
  echo "  Hole 1 (vacuity):         caught by tcg vacuity / verify step 5-vacuity"
  exit 0
fi
echo "false-green: FAILED ($FAIL check(s) did not behave as required)" >&2
exit 1
