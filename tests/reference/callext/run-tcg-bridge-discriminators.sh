#!/usr/bin/env bash
#
# run-tcg-bridge-discriminators.sh -- the anti-proxy controls for the bridge
# S<==D. Each MUST be refused; a green here would be a false green. All verdicts
# come from the solver (bridge legs) or the bundle-only structural checks.
#
#   1. broken-summary (+6)   bridge-s-at-p over P REFUTES -> S undischarged
#   2. wrong-code-identity    external_code tampered -> keccak mismatch
#   3. proxy-swap (+0 no-op)  a plausible-but-false summary; its B REFUTES over P
#   4. undischarged           S with the bridge stripped -> no false green
#   5. compat-broken          the interference obligation REFUTES
#
# Usage:  tests/reference/callext/run-tcg-bridge-discriminators.sh [WORKROOT]
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../../.." && pwd)}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
PY="${TCG_PYTHON:-python3}"
ROOT="${1:-$(mktemp -d -t callext-discr)}"
rm -rf "$ROOT"; mkdir -p "$ROOT"

PASS=0; FAIL=0
expect() { # want_rc  got_rc  name
  if [ "$2" = "$1" ]; then echo "  [PASS] $3 (exit $2 as required)"; PASS=$((PASS+1));
  else echo "  [FAIL] $3 (exit $2, wanted $1)"; FAIL=$((FAIL+1)); fi
}

wsbuild() { # WS -- init + subject + all callext loops helper are defined per-case
  :;
}
tcg() { local ws="$1"; shift; ( cd "$ws" && PYTHONPATH="$REPO" "$PY" -m tcg "$@" ); }
mkloop() { # WS loopname "bodyfile ..." ifacefile
  local ws="$1"; tcg "$ws" loop new "$2"
  for f in $3; do cp "$HERE/tcg/src/$f" "$ws/.tcg/loops/$2/$f"; done
  tcg "$ws" iface set "$2" --file "$HERE/tcg/iface/$4"; tcg "$ws" compile-claims "$2"
}
subject() { local ws="$1"; cp "$HERE/tcg/subject/runtime.hex" "$ws/runtime.hex"
  tcg "$ws" subject set --runtime "$ws/runtime.hex" --environment "$HERE/tcg/subject/environment.json"; }

# ============================================================================
# GOOD bundle (built once) -- discriminators 2 and 4 tamper a copy of it.
# ============================================================================
GB="$ROOT/good"; mkdir -p "$GB"
echo "== building the GOOD bundle (for the bundle-only tampers) =="
tcg "$GB" init --definition "$DEF" -I "$INC1" -I "$INC2" >/dev/null
subject "$GB" >/dev/null
mkloop "$GB" callee    "d.k"            iface-callee.json           >/dev/null
mkloop "$GB" bridge    "sbridge.k"      iface-bridge.json           >/dev/null
mkloop "$GB" summary   "s.k"            iface-summary-bridged.json  >/dev/null
mkloop "$GB" caller_2a "r2a.k guar2a.k" iface-caller_2a-bridged.json >/dev/null
tcg "$GB" prove callee   >/dev/null 2>&1
tcg "$GB" prove bridge   >/dev/null 2>&1
tcg "$GB" prove caller_2a >/dev/null 2>&1
tcg "$GB" vacuity caller_2a >/dev/null 2>&1
tcg "$GB" approve --reviewer discr >/dev/null 2>&1
tcg "$GB" graph check >/dev/null 2>&1
tcg "$GB" freeze >/dev/null 2>&1
echo "  good bundle: $GB/bundle (baseline verify:)"
tcg "$GB" verify "$GB/bundle" >/dev/null 2>&1; echo "  baseline verify exit $? (expect 0 -- the honest composition holds)"

# ============================================================================
# 2. wrong-code-identity: tamper external_code[200] to a DIFFERENT program P',
#    rehash environment.json in MANIFEST (so the hash tree stays consistent),
#    verify -> refused at step 4 (keccak(P') != declared code_hash). No prover.
# ============================================================================
echo; echo "== 2. wrong-code-identity (bundle tamper; expect verify REFUSED) =="
D2="$ROOT/d2-wrong-code"; cp -R "$GB/bundle" "$D2"
"$PY" - "$D2" <<'PY'
import json, hashlib, sys
b = sys.argv[1]
ep = b + "/subject/environment.json"; e = json.load(open(ep))
e["external_code"]["0x00000000000000000000000000000000000000c8"] = "600154600501600155"  # P'
open(ep,"w").write(json.dumps(e, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
mp = b + "/MANIFEST.json"; m = json.load(open(mp))
m["files"]["subject/environment.json"] = hashlib.sha256(open(ep,"rb").read()).hexdigest()
open(mp,"w").write(json.dumps(m, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
print("  tampered external_code[200] := 600154600501600155 and rehashed MANIFEST")
PY
tcg "$GB" verify "$D2" 2>&1 | grep -iE 'code-identity|REFUSED' | sed 's/^/    /'
tcg "$GB" verify "$D2" >/dev/null 2>&1; expect 3 $? "wrong-code-identity"

# ============================================================================
# 4. undischarged: strip the bridge block off the summary node (rehash graph),
#    verify -> the verifier no longer sees an abstract-summary node, so it
#    demands replay evidence S can never have -> refused. No false green.
# ============================================================================
echo; echo "== 4. undischarged: bridge stripped (bundle tamper; expect verify REFUSED) =="
D4="$ROOT/d4-undischarged"; cp -R "$GB/bundle" "$D4"
"$PY" - "$D4" <<'PY'
import json, hashlib, sys
b = sys.argv[1]
gp = b + "/spec/graph.json"; g = json.load(open(gp))
for h,n in g["nodes"].items(): n.pop("bridge", None)
open(gp,"w").write(json.dumps(g, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
mp = b + "/MANIFEST.json"; m = json.load(open(mp))
m["files"]["spec/graph.json"] = hashlib.sha256(open(gp,"rb").read()).hexdigest()
open(mp,"w").write(json.dumps(m, indent=2, ensure_ascii=False, sort_keys=True) + "\n")
print("  stripped the bridge block from the summary node and rehashed MANIFEST")
PY
tcg "$GB" verify "$D4" 2>&1 | grep -iE 'no replay evidence|REFUSED' | sed 's/^/    /'
tcg "$GB" verify "$D4" >/dev/null 2>&1; expect 3 $? "undischarged (bridge stripped)"
echo "  (the workspace form is run-tcg.sh: bridge-less summary -> graph check"
echo "   'trusted child s (summary) is Compiled, not Accepted' -- the same refusal.)"

# ============================================================================
# 1. broken-summary (+6): the +6 bridge B REFUTES over P; graph check then
#    refuses because S's bridge leg is not Accepted.
# ============================================================================
echo; echo "== 1. broken-summary +6 (expect bridge6 REFUTE + graph check REFUSED) =="
D1="$ROOT/d1-broken"; mkdir -p "$D1"
tcg "$D1" init --definition "$DEF" -I "$INC1" -I "$INC2" >/dev/null; subject "$D1" >/dev/null
mkloop "$D1" callee         "d.k"       iface-callee.json                >/dev/null
mkloop "$D1" bridge6        "sbridge6.k" iface-bridge6.json              >/dev/null
mkloop "$D1" summary_broken "s6.k"      iface-summary_broken-bridged.json >/dev/null
mkloop "$D1" caller_broken  "rbroken.k" iface-caller_broken.json         >/dev/null
tcg "$D1" prove callee >/dev/null 2>&1
tcg "$D1" prove bridge6 >/dev/null 2>&1; expect 3 $? "bridge6 (bridge-s-at-p +6) REFUTES over P"
tcg "$D1" prove caller_broken >/dev/null 2>&1   # Accepts: caller trusts the false +6 summary
tcg "$D1" graph check 2>&1 | grep -iE 'sbridge|REFUSED' | sed 's/^/    /'
tcg "$D1" graph check >/dev/null 2>&1; expect 3 $? "broken-summary graph check REFUSED"

# ============================================================================
# 3. proxy-swap (+0): a plausible 'this CALL is a no-op' summary the caller
#    proves with; its bridge B REFUTES over P (which delivers +5).
# ============================================================================
echo; echo "== 3. proxy-swap +0 no-op (expect bridge_proxy REFUTE + graph check REFUSED) =="
D3="$ROOT/d3-proxy"; mkdir -p "$D3"
tcg "$D3" init --definition "$DEF" -I "$INC1" -I "$INC2" >/dev/null; subject "$D3" >/dev/null
mkloop "$D3" callee        "d.k"            iface-callee.json               >/dev/null
mkloop "$D3" bridge_proxy  "sbridge_proxy.k" iface-bridge_proxy.json        >/dev/null
mkloop "$D3" summary_proxy "s_proxy.k"      iface-summary_proxy-bridged.json >/dev/null
mkloop "$D3" caller_proxy  "rproxy.k"       iface-caller_proxy.json         >/dev/null
tcg "$D3" prove callee >/dev/null 2>&1
tcg "$D3" prove bridge_proxy >/dev/null 2>&1; expect 3 $? "bridge_proxy (no-op summary) REFUTES over P"
tcg "$D3" prove caller_proxy >/dev/null 2>&1
tcg "$D3" graph check 2>&1 | grep -iE 'sbridge|REFUSED' | sed 's/^/    /'
tcg "$D3" graph check >/dev/null 2>&1; expect 3 $? "proxy-swap graph check REFUSED"

# ============================================================================
# 5. compat-broken: the interference obligation REFUTES (structural).
# ============================================================================
echo; echo "== 5. compat-broken (expect prove REFUTE) =="
D5="$ROOT/d5-compat"; mkdir -p "$D5"
tcg "$D5" init --definition "$DEF" -I "$INC1" -I "$INC2" >/dev/null; subject "$D5" >/dev/null
mkloop "$D5" compat_broken "compat_broken.k" iface-compat_broken.json >/dev/null
tcg "$D5" prove compat_broken 2>&1 | grep -iE 'Refute' | sed 's/^/    /'
tcg "$D5" prove compat_broken >/dev/null 2>&1; expect 3 $? "compat-broken REFUTES"

# ============================================================================
echo
echo "== discriminators: $PASS passed, $FAIL failed =="
echo "workroot: $ROOT"
[ "$FAIL" -eq 0 ] || exit 1
