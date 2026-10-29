#!/usr/bin/env bash
# Negative controls for `assemble_hard.py closure`: dropping any annotation a
# claim needs must make closure FAIL; the unmodified copy must pass.
cd ~/sheaf/tcg
for drop in Aasm-keccak-wards-slot Aasm-rangeUInt-args Aasm-rangeUInt-storage Aasm-gas-abstraction NONE; do
  T=$(mktemp -d); cp -r pilot/bundle/hard "$T/"
  python3 - "$T" "$drop" <<'EOF'
import json, sys
p = sys.argv[1] + "/hard/annotations.json"
d = json.load(open(p))
d["annotations"] = [a for a in d["annotations"] if a["id"] != sys.argv[2]]
json.dump(d, open(p, "w"))
EOF
  echo "drop=$drop:"
  python3 pilot/tools/assemble_hard.py closure --bundle "$T" --k-src ~/pilot-hard/kevm-src/evm-semantics-source | grep -E "FAIL|closure: (OK|FAILED)"
  rm -rf "$T"
done
