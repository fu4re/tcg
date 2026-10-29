#!/usr/bin/env bash
# Append fresh re-runs of the deterministic assemble_hard.py steps that a
# bundle-only consumer CAN replay, now declaring every file the command reads,
# including the Python imports (dry-run finding: ModuleNotFoundError 'tcg').
# Imports are recorded at the path they are imported from (../../tcg/*.py,
# i.e. REPO = parents[2] of ../tools/assemble_hard.py); their bytes equal the
# bundle children provenance/tools/tcg/*.py, so the verifier stands them in
# by hash. Older events stay as recorded (accepted mismatches, no retraction).
# Steps that read absolute / KEVM / network inputs are not re-run here (they
# stay outside_bundle). Run from the bundle root; exit 1 if any output changed.
set -uo pipefail
L="python3 ../tools/ledger.py run --ledger provenance/ledger.jsonl --root ."
A=../tools/assemble_hard.py
IMP="../../tcg/__init__.py ../../tcg/keccak.py ../../tcg/claims.py"
R=provenance/rebuild; C=$R/controls; O=$R/controls-osaka; W=$R/pre_witness
for f in __init__.py keccak.py claims.py; do
  cmp -s ../../tcg/$f provenance/tools/tcg/$f || { echo "rerun_hermetic: ../../tcg/$f differs from provenance/tools/tcg/$f" >&2; exit 1; }
done
cmp -s $A provenance/tools/assemble_hard.py || { echo "rerun_hermetic: $A differs from provenance/tools/assemble_hard.py" >&2; exit 1; }
OUTS=( $C/cagews-cagews-{prove,vacuity,discriminator}.k $O/cagews-cagews-{prove,vacuity,discriminator}.k
       $C/joinsym-joinsym-{prove,vacuity,discriminator}.k $O/joinsym-joinsym-{prove,vacuity,discriminator}.k
       provenance/opscan.json $W/claim-0{2,5}-{instance,vacuity}.k $W/claim-0{2,5}-config.json )
before=$(sha256sum "${OUTS[@]}")
KECC='#lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0'
CD='b"\x3b\x4d\xa6\x9f" +Bytes #buf(32, USR:Int) +Bytes #buf(32, WAD:Int)'
for sch in SHANGHAI OSAKA; do
  if [ $sch = SHANGHAI ]; then D=$C; S=(); else D=$O; S=(--schedule OSAKA); fi
  $L --tool assemble_hard.variant --in $A $IMP $C/cage-cage-prove.k --out $D/cagews-cagews-{prove,vacuity,discriminator}.k -- \
     python3 $A variant --src $C/cage-cage-prove.k --label cagews --storage-symbolic --requires "$KECC" "${S[@]}" --out-dir $D >/dev/null
  $L --tool assemble_hard.variant --in $A $IMP $C/join-join-prove.k --out $D/joinsym-joinsym-{prove,vacuity,discriminator}.k -- \
     python3 $A variant --src $C/join-join-prove.k --label joinsym --calldata "$CD" --requires "#rangeUInt(256, USR)" --requires "#rangeUInt(256, WAD)" "${S[@]}" --out-dir $D >/dev/null
done
$L --tool assemble_hard.opscan --in $A $IMP hard/artifact.bin --out provenance/opscan.json -- python3 $A opscan --artifact hard/artifact.bin --out provenance/opscan.json >/dev/null
$L --tool assemble_hard.witness --in $A $IMP $C/ilk-ilk-prove.k provenance/rpc_probe.json --out $W/claim-02-{instance,vacuity}.k $W/claim-02-config.json -- \
   python3 $A witness --claim $C/ilk-ilk-prove.k --probe provenance/rpc_probe.json --caller 0x00000000000000000000000000000000000000aa --schedule OSAKA --name claim-02 --out-dir $W >/dev/null
$L --tool assemble_hard.witness --in $A $IMP $C/joinsym-joinsym-prove.k provenance/rpc_probe.json --out $W/claim-05-{instance,vacuity}.k $W/claim-05-config.json -- \
   python3 $A witness --claim $C/joinsym-joinsym-prove.k --probe provenance/rpc_probe.json --caller 0x00000000000000000000000000000000000000aa --set 5=0 \
   --subst USR=0xdead --subst WAD=1000000000000000000 --schedule OSAKA --name claim-05 --out-dir $W >/dev/null
after=$(sha256sum "${OUTS[@]}")
if [ "$before" = "$after" ]; then echo "rerun_hermetic: all ${#OUTS[@]} outputs byte-identical"; exit 0; fi
echo "rerun_hermetic: CHANGED outputs:"; diff <(echo "$before") <(echo "$after"); exit 1
