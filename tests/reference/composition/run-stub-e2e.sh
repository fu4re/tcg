#!/usr/bin/env bash
#
# run-stub-e2e.sh -- build the STUB (Mechanism B, tcg/assume.py) composition E2E
# through tcg's REAL pipeline and self-verify it bundle-only with the REAL
# prover. The abstract callee-summary node S (<program> _PGM, <id> 200) is
# discharged NOT by the bridge S<==D but by a NAMED, TYPED ASSUMPTION: the callee
# at address 200 is OPAQUE (its code is not proved), and the caller chooses to
# assume a conservative typed frame for it. That assumption is:
#   * real / load-bearing -- S is still injected as a trusted child into the
#     caller root caller_2a/r2a, so its root proof is the SAME real kprove Accept
#     as the honest bridge case (run-tcg-bridge.sh); the caller genuinely leans
#     on the assumed frame at the CALL;
#   * never silent -- enumerated in the trust ledger under A_callee_200; default
#     `verify` surfaces a prominent (warn) section, `--strict` refuses, and a
#     missing-or-orphan ledger entry refuses (ledger consistency).
#
# The stub graph is exactly:
#   { summary/s (assume-discharged), caller_2a/r2a (ROOT), caller_2a/guar }.
# NO callee (d) or bridge (sbridge) node -- there is no bridge.
#
# compile-claims only wires a `bridge` block from the iface into the graph node,
# never an `assume` block (by design: the assume block is authored per-bundle,
# like the synthetic graphs in tests/test_assume.py). So this script compiles the
# summary as an ordinary abstract-summary claim, then INJECTS the assume block
# into the summary/s node in spec/graph.json -- exactly the block tcg.assume /
# graph check / freeze / verify consume. No product code is changed.
#
# Rows produced (docs/e2e/composition-matrix.md B0-B4; B5 is the honest bridge
# bundle from run-tcg-bridge.sh, verified separately as a regression):
#   B0  tcg verify <bundle>           -> 0 + trailing WARN author-chosen assumption section
#   B1  tcg verify --strict <bundle>  -> 3 (auditor wants a fully-discharged certificate)
#   B2  delete A_callee_200 entry, rehash MANIFEST, verify -> 3 (consistency: missing)
#   B3  add orphan A_callee_999 entry, rehash MANIFEST, verify -> 3 (consistency: orphan)
#   B4  tcg roots <bundle>            -> 0, surfaces the load-bearing assumption
#
# Usage:  tests/reference/composition/run-stub-e2e.sh [WORKDIR]
# Env:    KEVM (default ~/toolchains/kevm-1.0.678), TCG_PYTHON, REPO
set -uo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="${REPO:-$(cd "$HERE/../../.." && pwd)}"
KEVM="${KEVM:-$HOME/toolchains/kevm-1.0.678}"
DEF="$KEVM/haskell"; INC1="$KEVM/evm-semantics-source"; INC2="$KEVM/plugin"
PY="${TCG_PYTHON:-python3}"
CALLEXT="$REPO/tests/reference/callext"        # reuse the callext src + subject + ifaces
WS="${1:-$(mktemp -d -t stub-e2e-ws)}"
rm -rf "$WS"; mkdir -p "$WS"
LOGS="$WS/logs"; mkdir -p "$LOGS" "$WS/tools"
tcg() { ( cd "$WS" && PYTHONPATH="$REPO" "$PY" -m tcg "$@" ); }

# The load-bearing typed frame (verbatim intent of tests/reference/composition/
# opaque/README.md: storage-frame + reentrancy, conservative by default). Kept on
# one line and ASCII so it round-trips cleanly through the shell and JSON.
FRAME='Frame A_callee_200 - opaque callee OpaqueNotify at address 200 (0xc8). Storage-frame (load-bearing): the callee MUST NOT write any storage of the caller account; its writes are confined to its OWN account storage (a single counter slot), so the caller storage is unchanged across the external CALL. Reentrancy (load-bearing): the callee MUST NOT reenter the caller (no nested CALL/CALLCODE/DELEGATECALL/STATICCALL back into the caller, directly or transitively, before it returns). MAY (unconstrained, NOT assumed away): revert or run out of gas; consume arbitrary forwarded gas; write its own storage arbitrarily; return arbitrary output; emit logs. Status: assumed-callee (AUTHOR-CHOSEN, load-bearing) - NOT discharged over the callee code.'

# ---- small python tools (no product code touched) -----------------------------
cat > "$WS/tools/inject_assume.py" <<'PYEOF'
import json, sys
graph_path, addr, ledger, frame = sys.argv[1:5]
g = json.load(open(graph_path))
hit = None
for h, n in g["nodes"].items():
    if n.get("loop") == "summary" and n.get("label") == "s":
        n["assume"] = {"callee_address": addr, "frame": frame, "ledger_id": ledger}
        hit = h
assert hit, "summary/s node not found in graph.json"
json.dump(g, open(graph_path, "w"), indent=2, sort_keys=True)
print(f"injected assume block into summary/s node {hit[:12]} "
      f"(callee_address={addr}, ledger_id={ledger})")
PYEOF

# Tamper a COPIED bundle's ledger and re-hash MANIFEST so step-1 integrity still
# passes -- the ONLY refusal left is the ledger-consistency one (verify[4-graph]).
cat > "$WS/tools/tamper_ledger.py" <<'PYEOF'
import json, hashlib, sys
bundle, action = sys.argv[1], sys.argv[2]
tm_path = f"{bundle}/assumptions/trust-manifest.json"
tm = json.load(open(tm_path))
if action == "delete":            # B2: assume-node present, its ledger entry gone
    key = sys.argv[3]
    tm.pop(key, None)
elif action == "orphan":          # B3: extra A_callee_* entry no assume-node backs
    key = sys.argv[3]
    tm[key] = {"status": "assumed-callee (AUTHOR-CHOSEN, load-bearing)",
               "callee_address": "999", "frame": "orphan frame - no assume-node",
               "load_bearing_for": []}
raw = json.dumps(tm, indent=2, sort_keys=True).encode("utf-8")
open(tm_path, "wb").write(raw)
new = hashlib.sha256(raw).hexdigest()
man_path = f"{bundle}/MANIFEST.json"
m = json.load(open(man_path))
m["files"]["assumptions/trust-manifest.json"] = new       # keep step-1 integrity clean
open(man_path, "w").write(json.dumps(m, indent=2))
print(f"{action}: rewrote trust-manifest.json (sha256 {new[:12]}...) and "
      "updated its MANIFEST hash-tree entry (step-1 integrity stays clean)")
PYEOF

echo "############################################################"
echo "# BUILD -- stub composition through the real tcg pipeline"
echo "############################################################"
tcg init --definition "$DEF" -I "$INC1" -I "$INC2"
cp "$CALLEXT/tcg/subject/runtime.hex" "$WS/runtime.hex"
tcg subject set --runtime "$WS/runtime.hex" --environment "$CALLEXT/tcg/subject/environment.json"

mkloop() { # loopname  "bodyfile ..."  ifacefile
  tcg loop new "$1"
  for f in $2; do cp "$CALLEXT/tcg/src/$f" "$WS/.tcg/loops/$1/$f"; done
  tcg iface set "$1" --file "$CALLEXT/tcg/iface/$3"
  tcg compile-claims "$1"
}
# summary/s: ordinary abstract-summary claim (iface-summary.json has NO bridge
# block, so the node is discharged by neither bridge nor Accept -- we make it a
# stub by injecting the assume block below).
mkloop summary   "s.k"             iface-summary.json
# caller_2a: root r2a + guar, injecting summary/s as a trusted child (identical
# to the honest bridge caller -- same claim text, same real kprove Accept).
mkloop caller_2a "r2a.k guar2a.k"  iface-caller_2a-bridged.json

echo "== PROVE (only caller_2a; summary/s is NOT proved -- it is stub/assume-discharged) =="
tcg prove caller_2a 2>&1 | tee "$LOGS/prove-caller_2a.log"; echo "[caller_2a prove exit ${PIPESTATUS[0]}  expect 0/Accept (root+guar, S injected)]"
tcg vacuity caller_2a 2>&1 | tee "$LOGS/vacuity-caller_2a.log"; echo "[vacuity exit ${PIPESTATUS[0]}  expect 0/non-vacuous]"

echo "== INJECT the typed-stub assume block into summary/s (callee_address 200, ledger A_callee_200) =="
"$PY" "$WS/tools/inject_assume.py" "$WS/spec/graph.json" "200" "A_callee_200" "$FRAME"

echo "== APPROVE + GRAPH CHECK + FREEZE =="
tcg approve --reviewer stub-e2e
tcg graph check 2>&1 | tee "$LOGS/graph-check.log"; echo "[graph check exit ${PIPESTATUS[0]}  expect 0/OK]"
tcg freeze 2>&1 | tee "$LOGS/freeze.log"; echo "[freeze exit ${PIPESTATUS[0]}  expect 0]"

BUNDLE="$WS/bundle"
echo
echo "############################################################"
echo "# DISCRIMINATORS B0-B4 (real tcg verify / roots; logs kept)"
echo "############################################################"

echo "== B0: tcg verify <bundle>  (expect 0 + WARN author-chosen assumption section) =="
tcg verify "$BUNDLE" > "$LOGS/B0-verify.log" 2>&1; B0=$?
cat "$LOGS/B0-verify.log"; echo "[B0 verify exit $B0  expect 0]"

echo "== B1: tcg verify --strict <bundle>  (expect 3) =="
tcg verify --strict "$BUNDLE" > "$LOGS/B1-verify-strict.log" 2>&1; B1=$?
cat "$LOGS/B1-verify-strict.log"; echo "[B1 verify --strict exit $B1  expect 3]"

echo "== B2: delete A_callee_200 ledger entry, rehash MANIFEST, verify  (expect 3: consistency missing) =="
cp -R "$BUNDLE" "$WS/bundle-B2"
"$PY" "$WS/tools/tamper_ledger.py" "$WS/bundle-B2" delete A_callee_200
tcg verify "$WS/bundle-B2" > "$LOGS/B2-verify.log" 2>&1; B2=$?
cat "$LOGS/B2-verify.log"; echo "[B2 verify exit $B2  expect 3]"

echo "== B3: add orphan A_callee_999 ledger entry, rehash MANIFEST, verify  (expect 3: consistency orphan) =="
cp -R "$BUNDLE" "$WS/bundle-B3"
"$PY" "$WS/tools/tamper_ledger.py" "$WS/bundle-B3" orphan A_callee_999
tcg verify "$WS/bundle-B3" > "$LOGS/B3-verify.log" 2>&1; B3=$?
cat "$LOGS/B3-verify.log"; echo "[B3 verify exit $B3  expect 3]"

echo "== B4: tcg roots <bundle>  (expect 0, surfaces the load-bearing assumption) =="
tcg roots "$BUNDLE" > "$LOGS/B4-roots.log" 2>&1; B4=$?
cat "$LOGS/B4-roots.log"; echo "[B4 roots exit $B4  expect 0]"

echo
echo "############################################################"
echo "# SUMMARY"
echo "############################################################"
printf 'B0 verify (default)      exit %s  (expect 0)\n' "$B0"
printf 'B1 verify --strict       exit %s  (expect 3)\n' "$B1"
printf 'B2 deleted ledger entry  exit %s  (expect 3)\n' "$B2"
printf 'B3 orphan ledger entry   exit %s  (expect 3)\n' "$B3"
printf 'B4 roots                 exit %s  (expect 0)\n' "$B4"
echo
echo "workspace: $WS"
echo "bundle:    $BUNDLE"
echo "logs:      $LOGS"
