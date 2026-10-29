#!/usr/bin/env bash
# Re-run every deterministic assemble_hard.py step whose ledger event used a
# version of the script that was not retained, now with the current version
# (byte-identical to provenance/tools/assemble_hard.py), each as a new ledger
# event, and check that every output is byte-identical to what is shipped.
# Run from the bundle root. Exit 1 if any output changed.
set -uo pipefail
L="python3 ../tools/ledger.py run --ledger provenance/ledger.jsonl --root ."
A=../tools/assemble_hard.py
R=provenance/rebuild; C=$R/controls; O=$R/controls-osaka; W=$R/pre_witness
OUTS=( $C/cagews-cagews-{prove,vacuity,discriminator}.k $O/cagews-cagews-{prove,vacuity,discriminator}.k
       $C/joinsym-joinsym-{prove,vacuity,discriminator}.k $O/joinsym-joinsym-{prove,vacuity,discriminator}.k
       provenance/opscan.json provenance/kevm_osaka_adequacy.json
       $W/claim-0{2,4,5}-{instance,vacuity}.k $W/claim-0{2,4,5}-config.json
       hard/spec/phi.json hard/spec/claim-0{1,2,3,4,5}.k hard/certs/claim-0{1,2,3,4,5}.rediscuss.json
       provenance/closure.out )
before=$(sha256sum "${OUTS[@]}")
KECC='#lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0'
CD='b"\x3b\x4d\xa6\x9f" +Bytes #buf(32, USR:Int) +Bytes #buf(32, WAD:Int)'
for sch in SHANGHAI OSAKA; do
  if [ $sch = SHANGHAI ]; then D=$C; S=(); else D=$O; S=(--schedule OSAKA); fi
  $L --tool assemble_hard.variant --in $C/cage-cage-prove.k $A --out $D/cagews-cagews-{prove,vacuity,discriminator}.k -- \
     python3 $A variant --src $C/cage-cage-prove.k --label cagews --storage-symbolic --requires "$KECC" "${S[@]}" --out-dir $D >/dev/null
  $L --tool assemble_hard.variant --in $C/join-join-prove.k $A --out $D/joinsym-joinsym-{prove,vacuity,discriminator}.k -- \
     python3 $A variant --src $C/join-join-prove.k --label joinsym --calldata "$CD" --requires "#rangeUInt(256, USR)" --requires "#rangeUInt(256, WAD)" "${S[@]}" --out-dir $D >/dev/null
done
$L --tool assemble_hard.opscan --in hard/artifact.bin $A --out provenance/opscan.json -- python3 $A opscan --artifact hard/artifact.bin --out provenance/opscan.json >/dev/null
$L --tool assemble_hard.osaka-evidence --in /home/vladimir/pilot-hard/kevm-inputs/evm-semantics.tar.gz $A --out provenance/kevm_osaka_adequacy.json -- \
   python3 $A osaka-evidence --tarball /home/vladimir/pilot-hard/kevm-inputs/evm-semantics.tar.gz --out provenance/kevm_osaka_adequacy.json >/dev/null
$L --tool assemble_hard.witness --in $C/ilk-ilk-prove.k provenance/rpc_probe.json $A --out $W/claim-02-{instance,vacuity}.k $W/claim-02-config.json -- \
   python3 $A witness --claim $C/ilk-ilk-prove.k --probe provenance/rpc_probe.json --caller 0x00000000000000000000000000000000000000aa --schedule OSAKA --name claim-02 --out-dir $W >/dev/null
$L --tool assemble_hard.witness --in $C/cagews-cagews-prove.k provenance/rpc_probe.json $A --out $W/claim-04-{instance,vacuity}.k $W/claim-04-config.json -- \
   python3 $A witness --claim $C/cagews-cagews-prove.k --probe provenance/rpc_probe.json --caller 0x000000000000000000000000000000000000dEaD \
   --verify-slot 0x44ad89ba62b98ff34f51403ac22759b55759460c0bb5521eb4b6ee3cff49cf83 --rpc https://eth.drpc.org --rpc https://mainnet.gateway.tenderly.co \
   --rpc https://eth-mainnet.public.blastapi.io --schedule OSAKA --name claim-04 --out-dir $W >/dev/null
$L --tool assemble_hard.witness --in $C/joinsym-joinsym-prove.k provenance/rpc_probe.json $A --out $W/claim-05-{instance,vacuity}.k $W/claim-05-config.json -- \
   python3 $A witness --claim $C/joinsym-joinsym-prove.k --probe provenance/rpc_probe.json --caller 0x00000000000000000000000000000000000000aa --set 5=0 \
   --subst USR=0xdead --subst WAD=1000000000000000000 --schedule OSAKA --name claim-05 --out-dir $W >/dev/null
M=$R/results/matrix-osaka
$L --tool assemble_hard.hardspec --in $A provenance/ledger.jsonl $M/getters.tsv $M/revert.tsv hard/spec/requirements.md /home/vladimir/pilot-checker/pins.json \
   --out hard/spec/phi.json hard/spec/claim-0{1,2,3,4,5}.k hard/certs/claim-0{1,2,3,4,5}.rediscuss.json -- \
   python3 $A hardspec --bundle . --controls $O --results $M/getters.tsv $M/revert.tsv --schedule OSAKA --claim04 cagews --claim05 joinsym >/dev/null
$L --tool assemble_hard.closure --in $A hard/annotations.json hard/spec/phi.json hard/spec/claim-0{1,2,3,4,5}.k --stdout provenance/closure.out -- \
   python3 $A closure --bundle . --k-src /home/vladimir/pilot-hard/kevm-src/evm-semantics-source
after=$(sha256sum "${OUTS[@]}")
if [ "$before" = "$after" ]; then echo "rerun_current: all ${#OUTS[@]} outputs byte-identical"; exit 0; fi
echo "rerun_current: CHANGED outputs:"; diff <(echo "$before") <(echo "$after"); exit 1
