#!/usr/bin/env python3
"""Regenerate the variant-B delta under pilot/variant_b/staging/ (never touches pilot/bundle/).

  python3 pilot/variant_b/tools/build_staging.py

Writes, with paths relative to the bundle root the delta is meant to overlay:
  staging/hard/certs/ilk/                 Lean certificate project for claim-02 (sources only;
                                          its semantics/evmyullean is derived by apply_patches.sh)
  staging/hard/spec/phi.claim-02.lean.json   proposed new phi entry (Lean formulation of claim-02)
  staging/hard/spec/phi_delta.md          K-to-Lean translation table and narrowings
  staging/trusted_base.delta.json         T_hat additions/changes for variant B
  staging/manifest_children.json          role-c children the assembler should add
staging/semantics/evmyullean/ (pristine upstream + patches) is maintained by hand.
Hashes use the verifier's own canon.tree_hash / sha256_file."""
import json, os, shutil, subprocess, sys

VB = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PILOT = os.path.dirname(VB)
sys.path.insert(0, os.path.join(PILOT, "verifier"))
from tcgverify import canon  # noqa: E402

ST = os.path.join(VB, "staging")
SEM = os.path.join(ST, "semantics", "evmyullean")
CERT_REL = "hard/certs/ilk"
CERT = os.path.join(ST, CERT_REL)
TOOLCHAIN = "leanprover/lean4:v4.22.0"
THEOREM = "GemJoin.Ilk.ilk_correct"
# sha256 of bin/lean of the official v4.22.0 release, per platform; linux is re-hashed below.
LEAN_DARWIN_ARM64 = "c89073b8a577a5914ead7b740d2ad996af1ad5ad5b4bfc2825e0bce2f01b6aa4"

LAKEFILE = """import Lake
open Lake DSL

-- Lean certificate for claim-02 (GemJoin ETH-A ilk()) over EVMYulLean.
-- ./semantics/evmyullean is the bundle's semantics/evmyullean/upstream with
-- semantics/evmyullean/patches/0001..0005 applied (semantics/evmyullean/apply_patches.sh);
-- T_hat binds both trees by hash.
package «variantB» where
  moreLeanArgs := #["-DautoImplicit=false"]
  moreServerOptions := #[⟨`autoImplicit, false⟩]

require evmyul from "semantics/evmyullean"

@[default_target]
lean_lib «GemJoin»
"""


def sha(p):
    return canon.sha256_file(p)


def build_cert():
    if os.path.exists(CERT):
        shutil.rmtree(CERT)
    os.makedirs(CERT)
    for f in ("lean-toolchain", "lake-manifest.json", "GemJoin.lean"):
        shutil.copy2(os.path.join(VB, f), os.path.join(CERT, f))
    with open(os.path.join(CERT, "lakefile.lean"), "w", encoding="utf-8") as f:
        f.write(LAKEFILE)
    for sub in ("GemJoin", "controls"):
        for dp, _, fs in os.walk(os.path.join(VB, sub)):
            for name in sorted(fs):
                if name.endswith(".lean"):
                    src = os.path.join(dp, name)
                    dst = os.path.join(CERT, os.path.relpath(src, VB))
                    os.makedirs(os.path.dirname(dst), exist_ok=True)
                    shutil.copy2(src, dst)
    os.makedirs(os.path.join(CERT, "semantics"))
    subprocess.run(["sh", os.path.join(SEM, "apply_patches.sh"),
                    os.path.join(CERT, "semantics", "evmyullean")], check=True)
    with open(os.path.join(CERT, "lean-toolchain"), encoding="utf-8") as f:
        assert f.read().strip() == TOOLCHAIN


def cert_files():
    """Every file of the certificate project outside its semantics/ copy."""
    out = []
    for dp, dns, fs in os.walk(CERT):
        dns[:] = sorted(d for d in dns if os.path.relpath(os.path.join(dp, d), CERT) != "semantics")
        for name in sorted(fs):
            p = os.path.join(dp, name)
            out.append((CERT_REL + "/" + os.path.relpath(p, CERT), sha(p)))
    return sorted(out)


def main():
    build_cert()
    up_hash = canon.tree_hash(os.path.join(SEM, "upstream"))
    built_hash = canon.tree_hash(os.path.join(CERT, "semantics", "evmyullean"))
    with open(os.path.join(SEM, "TREE_SHA256.txt"), "rb") as f:
        listing = canon.sha256_bytes(f.read())
    patches = [(n, sha(os.path.join(SEM, "patches", n)))
               for n in sorted(os.listdir(os.path.join(SEM, "patches"))) if n.endswith(".patch")]
    lean_linux = sha(os.path.expanduser("~/.elan/toolchains/leanprover--lean4---v4.22.0/bin/lean"))
    with open(os.path.join(CERT, "lake-manifest.json"), encoding="utf-8") as f:
        deps = [{"name": p["name"], "rev": p.get("rev"), "url": p.get("url")}
                for p in json.load(f)["packages"] if p.get("type") == "git"]
    files = cert_files()
    fh = dict(files)
    ilk_src = CERT_REL + "/GemJoin/Ilk.lean"

    faith = {
        "0001-dj-aux-fuel.patch": ("modification", "assumption A_sem_DJ (upstream D_J_aux is a partial def: no equations to prove against)"),
        "0002-zeroes-transparent.patch": ("modification", "assumption A_sem_zeroes (upstream zeroes is an opaque FFI constant)"),
        "0003-frombytearray-structural.patch": ("modification, proved equal", "GemJoin.ByteArray_toList_eq (hard/certs/ilk/GemJoin/Bytes.lean)"),
        "0004-tobytes-structural.patch": ("modification, proved equal", "GemJoin.toBytesFuel_eq (hard/certs/ilk/GemJoin/Bytes.lean)"),
        "0005-tobytearray-32.patch": ("modification, proved equal given 0002 and 0004", "GemJoin.toByteArray_eq (hard/certs/ilk/GemJoin/Bytes.lean)"),
    }
    assert set(faith) == {n for n, _ in patches}, patches

    tb = {
        "format": "tcg-pilot-trusted-base-delta/0.1",
        "status": "PROPOSED for bundle version 2 (variant B). Not merged into pilot/bundle/trusted_base.json; the variant-A ladder is computed without it. The phi change it goes with needs H's re-signature.",
        "applies_to": {"file": "trusted_base.json", "sha256_when_written": "8bb0b042764a4540bb0c381b3a3a28c521c8b04b51b176a560d66e921d8e38cb"},
        "generated_by": "python3 pilot/variant_b/tools/build_staging.py",
        "semantics_add": [
            {
                "name": "EVMYulLean (pristine upstream)",
                "role": "second semantics; cross-check of claim-02 only",
                "path": "semantics/evmyullean/upstream",
                "hash": up_hash,
                "hash_of": "canon.tree_hash (pilot/verifier/tcgverify/canon.py) of the directory",
                "upstream": {"repo": "https://github.com/leonardoalt/EVMYulLean", "commit": "56253eb468bb39355ed522440502e3480c0139f0",
                             "export": "git archive of that commit", "licence": "Apache-2.0 (upstream/license.txt)"},
                "listing_sha256": listing,
                "listing_of": "sha256 of semantics/evmyullean/TREE_SHA256.txt (per-file sha256sum listing that apply_patches.sh checks)",
                "provenance": "semantics/evmyullean/PROVENANCE.md",
            },
            {
                "name": "EVMYulLean as built (upstream + patches 0001-0005)",
                "role": "the semantics the claim-02 Lean certificate is kernel-checked against",
                "path": CERT_REL + "/semantics/evmyullean",
                "hash": built_hash,
                "hash_of": "canon.tree_hash of the directory",
                "derived_from": {"path": "semantics/evmyullean/upstream", "hash": up_hash},
                "derivation": "sh semantics/evmyullean/apply_patches.sh <dst>; then canon.tree_hash(<dst>) must equal this hash",
                "derivation_checked_by_verifier": False,
                "derivation_note": "the verifier (variant B) checks both tree hashes, not that one is derived from the other; re-running apply_patches.sh is the check",
                "vendored_hash_rule": "the vendored semantics is upstream tree hash + the ordered patch hashes; it is a MODIFICATION of upstream",
                "patches": [{"name": n, "sha256": h, "repo_path": "semantics/evmyullean/patches/" + n,
                             "kind": faith[n][0], "faithfulness": faith[n][1]} for n, h in patches],
            },
        ],
        "checker_add": [
            {
                "name": "lean",
                "hash": [lean_linux, LEAN_DARWIN_ARM64],
                "hash_of": "sha256 of bin/lean of the elan toolchain " + TOOLCHAIN + " (linux/amd64, darwin/arm64)",
                "toolchain": TOOLCHAIN,
                "project": CERT_REL,
                "entry": "lake build in a scratch copy with every .olean deleted, then `#print axioms " + THEOREM + "` (pilot/verifier/tcgverify/checkers.py lean_project)",
                "accept_rule": "build exit 0, no sorry/admit in the certificate source, axioms within lean_axioms",
                "proof_style": "kernel evaluation (kernel_theorem: Eq.refl added with addDecl, so only the kernel checks it) and decide +kernel; no native_decide, no Lean.ofReduceBool, no Lean.trustCompiler",
                "lake_dependencies_outside_bundle": deps,
                "cost_note": "measured on the VM (8 vCPU): GemJoin library 637 s wall, 5.9 GB peak, with Mathlib oleans present. The verifier deletes every .olean including the dependencies', so a verifier run also rebuilds the imported part of Mathlib from source: not measured",
            }
        ],
        "assumptions_add": [
            {
                "id": "A3_lean",
                "name": "Lean kernel soundness (variant B checker)",
                "status": "assumption",
                "hashes": [lean_linux, LEAN_DARWIN_ARM64],
                "note": "Lean 4 v4.22.0 kernel; replaces A3 (kprove) for claim-02 under variant B only. The certificate is re-checked from source, so the elaborator and tactics are untrusted; the kernel and the axioms propext, Classical.choice, Quot.sound are trusted",
                "risk_if_false": "a kernel bug could accept a false claim-02 statement",
            },
            {
                "id": "A1_evmyul",
                "name": "EVMYulLean adequacy for the claim-02 path",
                "status": "assumption",
                "note": "A1 gains a second semantics: the Lean statement is about EVMYulLean 56253eb4, not about mainnet. The ilk() path executes 77 instructions of 53 opcodes all present in EVMYulLean's step; no conformance pass rate was measured here",
                "risk_if_false": "an EVMYulLean rule on the path (CALLDATALOAD, SLOAD, MSTORE, MLOAD, JUMPI, RETURN, ...) that differs from mainnet would make the Lean claim false of the deployed contract; agreement with KEVM on claim-02 (cross_checked) makes a shared error less likely, not impossible",
            },
            {
                "id": "A_sem_DJ",
                "name": "patch 0001: fuel-bounded D_J_aux equals upstream partial D_J_aux",
                "status": "assumption",
                "patch": {"name": "0001-dj-aux-fuel.patch", "sha256": dict(patches)["0001-dj-aux-fuel.patch"]},
                "argument": "every recursive call needs i < c.size and advances i by at most 33 without wrapping, so fuel c.size + 1 is never exhausted while c.size + 33 < 2^256. Not provable: a partial def has no equations",
                "evidence": "empirical, not a verdict: compiled #eval of the upstream body (copied verbatim as a partial def) and of patched D_J give the same 59 entries [16, 113, 169, ..., 3354] on the GemJoin runtime, equal to the kernel-checked table (GemJoin.DJ.D_J_runtime) and to an independent Python scan, all stopping at 3470. WETH9/Vat not checked (no runtime bytecode on the VM)",
                "risk_if_false": "JUMP/JUMPI destinations accepted or rejected differently from upstream; a proof could certify a run upstream rejects, or the reverse",
            },
            {
                "id": "A_sem_zeroes",
                "name": "patch 0002: ByteArray.zeroes n = ⟨Array.replicate n 0⟩ matches upstream's C memset_zero",
                "status": "assumption",
                "patch": {"name": "0002-zeroes-transparent.patch", "sha256": dict(patches)["0002-zeroes-transparent.patch"]},
                "argument": "equal for n < 2^64; compiled upstream passes n mod 2^64 beyond that, unreachable under any gas schedule. The extern is removed, so kernel and compiled code agree on the patched tree",
                "risk_if_false": "wrong memory contents or sizes after MSTORE, padded reads or RETURN",
            },
            {
                "id": "A_lean_deps",
                "name": "Lean dependencies fetched by lake",
                "status": "assumption",
                "note": "Mathlib and its dependencies are not in the bundle; lake fetches them at the git revs in hard/certs/ilk/lake-manifest.json (verifier reports them in outside_bundle). They are rebuilt from source by the kernel, so a bad dependency can only add axioms (caught by the whitelist) or break the build",
                "risk_if_false": "a dependency rev could become unavailable and make L1 for claim-02 unreproducible (checker_unavailable / not_accept, never a false accept)",
            },
        ],
        "assumptions_unchanged_note": "A3 (kprove) stays for claims 01, 03, 04, 05 and for the variant-A discharge of claim-02",
        "lean_axioms": ["propext", "Classical.choice", "Quot.sound"],
        "claims_without_certificate_remove": ["claim-02"],
        "cross_checked": ["claim-02"],
        "cross_checked_basis": {
            "claim-02": {
                "kevm": "Accept under variant A (phi.json claim-02 observed, ledger_seq 41); to be re-confirmed by ladder_A",
                "lean": "accept: lake build OK, #print axioms " + THEOREM + " = [propext, Classical.choice, Quot.sound] (pilot/variant_b/STATUS.md); to be re-confirmed by the verifier --variant B",
                "scope": "agreement under the Lean narrowings (gas 30,000,000, empty substate at entry); see hard/spec/phi.claim-02.lean.json",
            }
        },
        "hashed_objects_add": [
            {"path": "hard/spec/phi.claim-02.lean.json", "sha256": None, "note": "filled when merged into phi.json"},
            {"path": "semantics/evmyullean/PROVENANCE.md", "sha256": sha(os.path.join(SEM, "PROVENANCE.md"))},
        ],
    }

    phi = {
        "format": "tcg-pilot-phi-entry/0.1",
        "status": "PROPOSED new formulation of claim-02 for phi version 2; NOT signed. H must re-sign phi.json after it is merged (L3 fails until then)",
        "merge": "add as claims[id=claim-02].lean (the K formulation stays; the claim gains a second formulation and a second discharge)",
        "id": "claim-02",
        "claim": "claim-02",
        "k_label": "ilk",
        "kind": "Lean theorem over EVMYulLean: the message call Ξ ends in success with the stated output and account map",
        "file": ilk_src,
        "sha256": fh[ilk_src],
        "theorem": THEOREM,
        "statement": (
            "theorem ilk_correct (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)\n"
            "    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)\n"
            "    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray) :\n"
            "    ∃ cA' g' A', Ξ (f + 79) cA gbh blocks σ σ₀ G0 default (env a s o gp h d bvh)\n"
            "      = .ok (.success (cA', σ, g', A') (UInt256.toByteArray (slot σ a ⟨2⟩)))"),
        "statement_depends_on": {
            "definitions": {
                "GemJoin.Ilk.env": "call environment: codeOwner a, sender s, source o, weiValue 0, calldata 0xc5ce281e, code GemJoin.runtime, perm true (non-static), other fields universally quantified",
                "GemJoin.Ilk.slot": "(σ.find? a).option 0 (Account.lookupStorage k): EVMYulLean's SLOAD read, 0 for an absent account or key",
                "GemJoin.Ilk.G0": "30000000 (gas at entry)",
                "GemJoin.runtime": "the 3462 bytes of hard/artifact.bin (keccak 0x8661c673…0874fa)",
                "UInt256.toByteArray": "EVMYulLean (patched by 0005); GemJoin.toByteArray_eq proves it is the 32 big-endian bytes",
            },
            "files": {p: fh[p] for p in (ilk_src, CERT_REL + "/GemJoin/Runtime.lean")},
            "semantics": CERT_REL + "/semantics/evmyullean (T_hat semantics 'EVMYulLean as built')",
        },
        "program": {"binds": "hard/artifact.bin", "keccak256": "0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa",
                    "how": "GemJoin.runtime is generated from hard/artifact.bin (byte-identical, 3462 bytes); its jump table is D_J runtime 0, kernel-checked equal to a 59-entry table (GemJoin.DJ.D_J_runtime)"},
        "quantifies_over": "every account map σ (so every storage of the callee, every word in slot 2), callee a, caller s, origin o, gas price, block header, depth, blob hashes, σ₀, created accounts, processed blocks, genesis header, and fuel f + 79 for every f",
        "pre": {"function": "ilk()", "calldata": "exactly 0xc5ce281e (4 bytes)", "callvalue": 0,
                "caller": "any address", "executing_account": "any address", "storage": "any (σ arbitrary)",
                "gas": "exactly 30,000,000 at entry (NARROWER than K: K does not model gas)",
                "substate": "empty at entry (NARROWER than K: slot 2 cold)",
                "frame": "any depth d; non-static"},
        "post": {"status": "success (Ξ returns .ok (.success ...))", "output": "UInt256.toByteArray (slot σ a 2) = 32-byte big-endian word of storage[2]",
                 "account_map": "unchanged (σ)", "not_stated": "remaining gas, substate (logs, touched accounts), created accounts: existentially quantified"},
        "narrowings_vs_k": [
            {"id": "N_gas", "what": "gas at entry fixed at 30,000,000 (the run uses 2393); K proves it for <useGas> false. Generalising needs symbolic gas comparisons through UInt256 % 2^256; not attempted"},
            {"id": "N_substate", "what": "substate at entry empty; with slot 2 warm only the SLOAD cost differs; not proved"},
            {"id": "N_log", "what": "K's Post says the log is unchanged; the Lean statement leaves the returned substate (which holds the logs) existential, so 'no log' is not stated"},
            {"id": "N_semantics", "what": "the statement is about EVMYulLean 56253eb4 + patches 0001-0005 (0001, 0002 assumed faithful: A_sem_DJ, A_sem_zeroes; 0003-0005 proved equal)"},
        ],
        "aasm": ["A1_evmyul", "A_sem_DJ", "A_sem_zeroes", "A3_lean"],
        "requirements": ["R2"],
        "coverage_of_requirements": {"R2": "partial under the narrowings N_gas, N_substate, N_log; the K formulation stays the full one"},
        "controls": {
            "negative": {
                "file": CERT_REL + "/controls/IlkMutants.lean",
                "sha256": fh[CERT_REL + "/controls/IlkMutants.lean"],
                "run": "lake env lean controls/IlkMutants.lean (in hard/certs/ilk, after lake build)",
                "expected": "mut_slot3 (output bound to slot 3), mut_gem_selector (calldata 0x7bd2bea7), mut_callvalue (call value 1) rejected by the kernel; ctl (the true statement) accepted",
                "observed": "as expected, 2026-10-29, 198 s, 5.8 GB (pilot/variant_b/STATUS.md)",
                "checked_by_verifier": False,
            },
            "vacuity": "not applicable in the K sense: the statement is an equation about a total function, not an implication; Pre is the universally quantified environment, and every instance is satisfiable (e.g. the empty account map)",
        },
        "translation_table": "hard/spec/phi_delta.md",
    }

    children = {
        "format": "tcg-pilot-manifest-children/0.1",
        "note": "role-c children for the assembler (pilot/tools/assemble_hard.py) to add in bundle version 2. Exactly one proof object (with theorem); the rest are Lean project support files (no claim). semantics/ trees are bound by T_hat semantics hashes. List every file of both trees as children too: the verifier only reports unlisted files (unlisted_files_ignored), but its Lean check copies and builds the whole project directory, so an unlisted file would still be compiled",
        "proof_objects": [{"path": ilk_src, "role": "c", "media": "text/x-lean", "claim": "claim-02", "theorem": THEOREM, "sha256": fh[ilk_src]}],
        "support_files": [{"path": p, "role": "c", "sha256": h} for p, h in files if p != ilk_src],
        "trees": [{"path": "semantics/evmyullean/upstream", "tree_hash": up_hash},
                  {"path": CERT_REL + "/semantics/evmyullean", "tree_hash": built_hash}],
    }

    os.makedirs(os.path.join(ST, "hard", "spec"), exist_ok=True)
    shutil.copy2(os.path.join(VB, "phi_delta.md"), os.path.join(ST, "hard", "spec", "phi_delta.md"))
    for name, obj in (("trusted_base.delta.json", tb), ("hard/spec/phi.claim-02.lean.json", phi),
                      ("manifest_children.json", children)):
        with open(os.path.join(ST, name), "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=1, ensure_ascii=False)
            f.write("\n")
    print("upstream tree_hash", up_hash)
    print("built    tree_hash", built_hash)
    print("lean linux sha256 ", lean_linux)
    print("cert files", len(files))


if __name__ == "__main__":
    main()
