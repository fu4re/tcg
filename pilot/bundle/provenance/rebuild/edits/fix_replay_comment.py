import pathlib
p = pathlib.Path("evidence/pre_witness/replay.sh"); t = p.read_text()
old = "(on the producer VM:\n# ~/pilot-locks/with-slot.sh prover -- sh replay.sh)"
assert old in t, "comment not found"
p.write_text(t.replace(old, "(on the producer VM, a prover-slot\n# wrapper around sh replay.sh)"))
print("ok")
