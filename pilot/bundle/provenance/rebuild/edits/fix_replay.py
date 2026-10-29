#!/usr/bin/env python3
"""Remove every host path from evidence/pre_witness/replay.sh (dry-run finding:
the script reached for /home/vladimir/pilot-locks/with-slot.sh, which keeps its
locks under $HOME and fails under the verifier's scratch HOME). The caller now
holds the prover slot around the whole replay. stdout format is unchanged.
Run from the bundle root. The original under provenance/rebuild/pre_witness/
is left as is (history of ledger seq 27-29, 63)."""
import pathlib, re, sys
p = pathlib.Path("evidence/pre_witness/replay.sh")
t = p.read_text()
old_comment = """# On the producer VM each container takes a prover slot if the slot wrapper
# exists ($PILOT_SLOT or /home/vladimir/pilot-locks/with-slot.sh); this does
# not change the output.
"""
new_comment = """# No host paths: the CALLER holds any resource lock (on the producer VM:
# ~/pilot-locks/with-slot.sh prover -- sh replay.sh). Containers run one at a
# time, each bounded by --memory=6g --cpus=2.
"""
old_slot = """SLOT=""
for s in "${PILOT_SLOT:-}" /home/vladimir/pilot-locks/with-slot.sh; do
  if [ -n "$s" ] && [ -x "$s" ]; then SLOT="$s prover --"; break; fi
done
"""
for o in (old_comment, old_slot):
    if o not in t:
        print("fix_replay: expected block not found", file=sys.stderr)
        sys.exit(1)
t = t.replace(old_comment, new_comment).replace(old_slot, "")
t = t.replace("out=$($SLOT docker run", "out=$(docker run")
if "/home/" in t or "SLOT" in t:
    print("fix_replay: host path or SLOT still present", file=sys.stderr)
    sys.exit(1)
p.write_text(t)
print("ok")
