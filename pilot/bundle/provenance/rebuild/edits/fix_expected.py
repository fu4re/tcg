import json, pathlib
p = pathlib.Path("evidence/pre_witness/expected.json"); d = json.loads(p.read_text())
d["produced_by"] = ("ledger seq 63 (first replay, exit 0); re-confirmed by seq 132 with the host-path-free replay.sh "
                    "(caller held the prover slot; env -i, scratch HOME), same stdout; pinned image "
                    "sha256:7d4a35bc05dfdad97b244da3c75bb3c3e710be73713cac3ca1c5bb6226cdc465")
p.write_text(json.dumps(d, indent=2) + "\n"); print("ok")
