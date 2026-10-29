#!/usr/bin/env bash
set -euo pipefail
cd ~/sheaf/tcg/pilot/bundle
TXT="approval by H (the author, D5) with the oracle key (D4): evidence/approval.sig sha256 $(sha256sum evidence/approval.sig | cut -c1-64) \
over phi_sha256 $(sha256sum hard/spec/phi.json | cut -c1-64) || requirements_sha256 $(sha256sum hard/spec/requirements.md | cut -c1-64) \
(both equal the current files); evidence/approval.json sha256 $(sha256sum evidence/approval.json | cut -c1-64), derived from approval.msg only (seq 98). \
Signature checked by the producer with openssl pkeyutl -verify and tcgverify.ed25519 (both valid; a 1-char tampered message fails); the binding check belongs to L3. \
Oracle public key (sha256 $(sha256sum ~/pilot-keys/oracle.pub.pem | cut -c1-64)) and approval.msg moved out of the bundle to ~/pilot-keys/: the trust anchor ships out of band."
python3 ../tools/ledger.py note --ledger provenance/ledger.jsonl --root . --tool manual --deterministic \
  --in evidence/approval.sig evidence/approval.json hard/spec/phi.json hard/spec/requirements.md --text "$TXT"
python3 provenance/rebuild/edits/patch_phiv.py
E=provenance/rebuild/edits/make_phi_versions.py
python3 ../tools/ledger.py run --ledger provenance/ledger.jsonl --root . --tool make_phi_versions --tool-file $E \
  --in $E hard/spec/phi.json provenance/ledger.jsonl evidence/approval.json --out evidence/phi_versions.json -- python3 $E
python3 ../tools/verify_ledger.py provenance/ledger.jsonl
