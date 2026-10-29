#!/usr/bin/env python3
"""Write evidence/approval.json from evidence/approval.msg ONLY (task 04 s5,
D4), then move the out-of-band files out of the bundle: the oracle public key
(a trust anchor; the consumer receives it out of band) and approval.msg (no
role in the bundle: the verifier rebuilds the message from approval.json) go
to ~/pilot-keys/. Run from the bundle root. Verifies nothing cryptographically
(that is L3's job); it only refuses a malformed message."""
import datetime, json, os, pathlib, re, shutil, sys

ev = pathlib.Path("evidence")
msg = (ev / "approval.msg").read_bytes()
if not re.fullmatch(rb"[0-9a-f]{128}", msg):
    print("make_approval: approval.msg is not 128 lowercase hex chars", file=sys.stderr)
    sys.exit(1)
m = msg.decode("ascii")
mtime = os.stat(ev / "approval.sig").st_mtime
doc = {
    "phi_sha256": m[:64],
    "requirements_sha256": m[64:],
    "signed_message": "sha256(phi.json) || sha256(requirements.md), ASCII hex, per D4",
    "signer": "oracle (H = the author, D5)",
    "signed_at_utc": datetime.datetime.fromtimestamp(mtime, datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
    "signed_at_basis": "mtime of evidence/approval.sig on the producer VM (not a signed timestamp)",
}
(ev / "approval.json").write_text(json.dumps(doc, indent=2) + "\n")
keys = pathlib.Path.home() / "pilot-keys"
keys.mkdir(mode=0o700, exist_ok=True)
for name in ("oracle.pub.pem", "approval.msg"):
    dst = keys / name
    if dst.exists():
        print(f"make_approval: {dst} exists, refusing to overwrite", file=sys.stderr)
        sys.exit(1)
    shutil.move(str(ev / name), str(dst))
print(json.dumps(doc))
