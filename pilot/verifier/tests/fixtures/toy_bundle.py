"""Synthetic toy bundle for the verifier tests (task 06 monotonicity suite).

Same layout and formats the real GemJoin bundle will use, with toy contents:
toy artefact bytes, two toy KEVM claims re-discharged by the fake docker in
fakebin/, one toy Lean lemma checked by the fake toolchain in fakelean/, real
ed25519 signatures from throwaway openssl keys generated at test time, and a
real ledger written by pilot/tools/ledger.py. Nothing here is GemJoin.
"""
from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys

FIX = os.path.dirname(os.path.abspath(__file__))
VERIFIER = os.path.dirname(os.path.dirname(FIX))
TOOLS = os.path.join(os.path.dirname(VERIFIER), "tools")
sys.path.insert(0, VERIFIER)

from tcgverify import canon, ladder  # noqa: E402
from tcgverify.keccak import keccak256  # noqa: E402

sys.path.insert(0, TOOLS)
import assemble  # noqa: E402
import coverage as coverage_tool  # noqa: E402
import mutant_witness  # noqa: E402

OPENSSL = shutil.which("openssl")
FAKEBIN = os.path.join(FIX, "fakebin")
FAKELEAN = os.path.join(FIX, "fakelean")
FAKE_IMAGE_ID = "sha256:" + "c0" * 32
SUBJECT = "0x00000000000000000000000000000000000a0001"
WETH = "0x00000000000000000000000000000000000a0002"
VAT = "0x00000000000000000000000000000000000a0003"
ARTIFACT = bytes.fromhex("60016000556001600155600060005260206000f3")
WETH_CODE = bytes.fromhex("6002600055600060005260206000f3")   # toy stand-in for WETH9
VAT_CODE = bytes.fromhex("6003600055600060005260206000f3")
BLOCK = {"number": 20000000, "hash": "0x" + "ab" * 32, "timestamp": 1720000000}  # cancun

REQUIREMENTS = """# Toy requirements (n)

- **R1.** Running the toy artefact stores 1 in slot 0.
- **R2.** Running the toy artefact stores 1 in slot 1.
- **R3.** The toy lemma 2 + 2 = 4 holds.
"""
CLAIMS = {
    "claim-01": "// toy K claim: slot 0 == 1 after run\nTOY-PROVABLE\n",
    "claim-02": "// toy K claim: slot 1 == 1 after run\nTOY-PROVABLE\n",
}
LEMMA_SRC = "namespace Toy\ntheorem lemma01 : 2 + 2 = 4 := rfl\nend Toy\n"
MUTANT_REPLAY = """#!/bin/sh
# toy mutant: slot 0 receives 2 instead of 1; claim-01 must refute it
od -An -tx1 mutant.bin | tr -d ' \\n'; echo
echo "Final configuration cannot be rewritten further: slot 0 = 2, claim requires 1"
exit 1
"""
PRE_REPLAY = """#!/bin/sh
# toy pre-witness: the concrete initial state is the empty storage + the artefact
od -An -tx1 ../../hard/artifact.bin | tr -d ' \\n'; echo
echo "sigma0: storage empty, callvalue 0"
"""


def sh(*argv, **kw):
    return subprocess.run(argv, check=True, capture_output=True, **kw)


def make_keys(keydir: str) -> dict:
    os.makedirs(keydir, exist_ok=True)
    out = {}
    for name in ("producer", "oracle"):
        k, p = os.path.join(keydir, f"{name}.pem"), os.path.join(keydir, f"{name}.pub.pem")
        sh(OPENSSL, "genpkey", "-algorithm", "ed25519", "-out", k)
        sh(OPENSSL, "pkey", "-in", k, "-pubout", "-out", p)
        out[name], out[name + "_pub"] = k, p
    return out


def sign(key: str, msg: bytes, tmp: str | None = None) -> bytes:
    return assemble.sign(key, msg)


def write(root: str, rel: str, data) -> None:
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as f:
        f.write(data if isinstance(data, bytes) else data.encode("utf-8"))


def write_json(root: str, rel: str, obj) -> None:
    write(root, rel, json.dumps(obj, indent=2, ensure_ascii=False) + "\n")


def sha(root: str, rel: str) -> str:
    return canon.sha256_file(os.path.join(root, rel))


def write_manifest(root: str, producer_key: str) -> dict:
    """Assemble with the real producer tool (tools/assemble.py); it must not refuse."""
    man, probs, warns = assemble.plan(root)
    if probs or warns:
        raise AssertionError(f"toy bundle does not assemble cleanly: {probs + warns}")
    man = assemble.sign_manifest(man, producer_key)
    assemble.write_manifest(root, man)
    return man


def resign(root: str, producer_key: str) -> dict:
    """An adversarial producer re-signs: re-hashes the children it already listed
    (keeping their role/claim metadata), drops the vanished ones, signs again.
    Deliberately NOT assemble.py, which would refuse most of these bundles."""
    with open(os.path.join(root, "manifest.json"), encoding="utf-8") as f:
        man = json.load(f)
    man["children"] = [dict(c, hash=sha(root, c["path"])) for c in man["children"]
                       if os.path.isfile(os.path.join(root, c["path"]))]
    man = assemble.sign_manifest(man, producer_key)
    assemble.write_manifest(root, man)
    return man


def approve(root: str, oracle_key: str) -> None:
    phi, req = sha(root, "hard/spec/phi.json"), sha(root, "hard/spec/requirements.md")
    write_json(root, "evidence/approval.json", {"phi_sha256": phi, "requirements_sha256": req,
                                               "signer": "oracle (toy key)"})
    write(root, "evidence/approval.sig", sign(oracle_key, (phi + req).encode("ascii"), root))


def write_phi(root: str) -> None:
    claims = [{"id": "claim-01", "file": "hard/spec/claim-01.k", "requirements": ["R1"],
               "pre": "toy: empty storage", "post": "slot0 == 1", "exit": "success"},
              {"id": "claim-02", "file": "hard/spec/claim-02.k", "requirements": ["R2"],
               "pre": "toy: empty storage", "post": "slot1 == 1", "exit": "success"},
              {"id": "lemma-01", "file": "hard/spec/lemma-01.statement.lean", "requirements": ["R3"],
               "pre": "-", "post": "2 + 2 = 4", "exit": "-"}]
    for c in claims:
        c["sha256"] = sha(root, c["file"])
    write_json(root, "hard/spec/phi.json", {"claims": claims, "declared_blind_spots": []})
    if coverage_tool.main([root]) != 0:
        raise AssertionError("tools/coverage.py rejected the toy phi.json")


def write_claim(root: str, cid: str, text: str) -> None:
    """A toy KEVM claim file plus its re-discharge invocation (claim_file_sha256 kept in step)."""
    write(root, f"hard/spec/{cid}.k", text)
    write_json(root, f"hard/certs/{cid}.rediscuss.json", {
        "claim": cid, "checker": "kevm-prove", "claim_file": f"hard/spec/{cid}.k",
        "spec_module": "TOY-SPEC", "kprove_args": [], "kevm_version": "toy", "k_version": "toy",
        "timeout_s": 60, "expected": "accept", "image_id": FAKE_IMAGE_ID,
        "claim_file_sha256": sha(root, f"hard/spec/{cid}.k"), "argv": ["kprove", "toy"]})


def build(root: str, keys: dict) -> dict:
    os.makedirs(root, exist_ok=True)
    write(root, "hard/artifact.bin", ARTIFACT)
    write(root, "hard/spec/requirements.md", REQUIREMENTS)
    for cid, text in CLAIMS.items():
        write_claim(root, cid, text)
    write(root, "hard/spec/lemma-01.statement.lean", "theorem Toy.lemma01 : 2 + 2 = 4\n")
    write(root, "hard/certs/lean/lean-toolchain", "toy\n")
    write(root, "hard/certs/lean/lakefile.lean", "-- toy lake project\n")
    write(root, "hard/certs/lean/Toy/Lemma01.lean", LEMMA_SRC)
    write_json(root, "hard/certs/lean/theorems.json",
               [{"claim": "lemma-01", "theorem": "Toy.lemma01", "source": "hard/certs/lean/Toy/Lemma01.lean"}])
    write_json(root, "hard/annotations.json", {"annotations": [
        {"id": "Aasm-01", "statement": "toy: no reentrancy", "used_by": ["claim-01", "claim-02"],
         "justification": "toy", "class": "T"},
        {"id": "simp-01", "statement": "toy simplification lemma", "used_by": ["claim-01"],
         "justification": "toy", "class": "T"}]})
    write_phi(root)
    write_json(root, "checker/kevm-prove.image.json", {"image_id": FAKE_IMAGE_ID, "note": "toy"})
    write_json(root, "trusted_base.json", {
        "semantics": [{"name": "toy-semantics", "hash": "0" * 64, "role": "primary"}],
        "checker": [
            {"name": "kevm-prove", "hash": FAKE_IMAGE_ID, "image": "tcg/kevm-checker:toy", "self_contained": False},
            {"name": "lean", "version": "toy",
             "hash": canon.sha256_file(os.path.join(FAKELEAN, "toy", "bin", "lean")), "self_contained": True},
            {"name": "tcg-verifier", "hash": ladder.verifier_hash()}],
        "identity": {"function": "keccak256(runtime_bytecode)", "value": "0x" + keccak256(ARTIFACT).hex(),
                     "address": SUBJECT, "block": BLOCK["number"], "constructor_and_immutables": "none"},
        "environment": {"chain_id": 1, "fork": "cancun", "fee_schedule": "cancun",
                        "external_code": [{"name": "WETH", "address": WETH, "code_hash": "0x" + keccak256(WETH_CODE).hex()},
                                          {"name": "Vat", "address": VAT, "code_hash": "0x" + keccak256(VAT_CODE).hex()}],
                        "caller_assumptions": "toy", "precompiles": "standard", "resource_limits": "toy"},
        "assumptions": [
            {"id": "A1", "name": "semantics adequacy", "status": "assumption", "risk_if_false": "toy"},
            {"id": "A3", "name": "checker soundness", "status": "assumption", "risk_if_false": "toy"},
            {"id": "Aasm-01", "name": "toy no reentrancy", "status": "assumption", "risk_if_false": "toy"},
            {"id": "A_simp_lemmas", "name": "simplification lemmas", "status": "assumption",
             "covers": ["simp-01"], "risk_if_false": "toy"}],
        "claims_without_certificate": [
            {"claim": "claim-01", "reason": "K prover emits no proof object; re-discharged by pinned prover"},
            {"claim": "claim-02", "reason": "K prover emits no proof object; re-discharged by pinned prover"}]})
    write_json(root, "evidence/backtranslation.json", {"model": "none (toy)", "requirements_withheld": True,
               "entries": [{"claim": "claim-01", "translation": "slot 0 ends as 1", "referenced_requirement": "R1",
                            "agreement": "agree", "note": ""}]})
    mdir = "evidence/mutants/claim-01/"
    write(root, mdir + "mutant.bin", bytes.fromhex("60026000556001600155600060005260206000f3"))
    write(root, mdir + "replay.sh", MUTANT_REPLAY)
    write(root, "evidence/pre_witness/replay.sh", PRE_REPLAY)
    if mutant_witness.record(root, "claim-01", "claim-01", "refute", 2) != 0:
        raise AssertionError("tools/mutant_witness.py refused the toy mutant")
    out = subprocess.run(["sh", "replay.sh"], cwd=os.path.join(root, "evidence/pre_witness"),
                         capture_output=True).stdout
    write_json(root, "evidence/pre_witness/expected.json", {"output_sha256": hashlib.sha256(out).hexdigest()})
    approve(root, keys["oracle"])
    write(root, "DECISIONS.md", "# Toy decisions\n\n| # | Topic | Choice |\n|---|---|---|\n" +
          "".join(f"| D{i} | toy | toy |\n" for i in range(1, 12)))
    led = os.path.join(root, "provenance/ledger.jsonl")
    os.makedirs(os.path.dirname(led), exist_ok=True)
    for out_rel, cmd in (("provenance/artifact.sha256", ["sha256sum", "hard/artifact.bin"]),
                         ("provenance/artifact.hex", ["od", "-An", "-tx1", "hard/artifact.bin"])):
        sh(sys.executable, os.path.join(TOOLS, "ledger.py"), "run", "--ledger", led, "--root", root,
           "--in", "hard/artifact.bin", "--stdout", out_rel, "--", *cmd, cwd=root)
    sh(sys.executable, os.path.join(TOOLS, "ledger.py"), "note", "--ledger", led, "--root", root,
       "--tool", "toy-model", "--model", "toy-0", "--text", "toy generator call", cwd=root)
    return write_manifest(root, keys["producer"])


def snapshot(directory: str, code: dict | None = None, **over) -> str:
    os.makedirs(directory, exist_ok=True)
    codes = {SUBJECT: ARTIFACT, WETH: WETH_CODE, VAT: VAT_CODE}
    codes.update(code or {})
    snap = {"chain_id": 1, "block": dict(BLOCK), "code": {a: "0x" + c.hex() for a, c in codes.items()}}
    snap.update(over)
    write_json(directory, "snapshot.json", snap)
    return directory
