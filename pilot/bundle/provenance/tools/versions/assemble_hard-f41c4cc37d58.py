#!/usr/bin/env python3
"""assemble_hard.py -- WS-H tooling for the bundle pilot hard layer + T-hat.

Owned by WS-H (tasks 02 + 03). Stdlib only, python 3.12. Every subcommand is
meant to be run through pilot/tools/ledger.py so that the bundle's provenance
records it.

Subcommands
  chain      read b and the external code from mainnet at a pinned block via
             several RPCs (cast), keccak each blob with `cast keccak` AND the
             repo's pure-Python keccak, record which RPCs agree, write
             hard/artifact.bin. Exit 3 (STOP) if GemJoin's keccak is not the
             development constant or the bytes differ from the dev copy.
  closure    annotation-closure check: every lemma / assumption name the
             proofs depend on (grepped from the K sources) must be listed in
             hard/annotations.json, and every listed K-sourced entry must
             exist in the sources. Exit 1 on any gap.
  rehash     recompute every hash in hard/spec/phi.json and trusted_base.json
             from the referenced objects; exit 1 on any mismatch.

Nothing here decides a verification verdict. Verdicts are kprove's.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import re
import subprocess
import sys

REPO = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
from tcg.keccak import keccak256_hex  # noqa: E402  (pure-Python, vector-tested)

GEMJOIN = "0x2F0b23f53734252Bda2277357e97e1517d6B042A"
WETH = "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2"
VAT = "0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B"
DEV_KECCAK = "0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa"
DEV_RUNTIME_HEX = REPO / "tests/reference/getters/subject/runtime.hex"


def sha256_file(p: pathlib.Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def cast(*args: str, timeout: int = 60) -> str:
    r = subprocess.run(["cast", *args], capture_output=True, text=True, timeout=timeout)
    if r.returncode != 0:
        raise RuntimeError(f"cast {' '.join(args)}: exit {r.returncode}: {r.stderr.strip()[:300]}")
    return r.stdout.strip()


# --------------------------------------------------------------------------- chain
def cmd_chain(a: argparse.Namespace) -> int:
    block = int(a.block)
    targets = {"GemJoin_ETH_A": GEMJOIN, "WETH9": WETH, "MCD_Vat": VAT}
    per_rpc: list[dict] = []
    for url in a.rpc:
        rec: dict = {"rpc": url, "ok": True, "errors": []}
        try:
            rec["chain_id"] = int(cast("chain-id", "--rpc-url", url))
            blk = json.loads(cast("block", str(block), "--json", "--rpc-url", url))
            blk = blk.get("data", blk)
            rec["block"] = {k: blk.get(k) for k in ("number", "hash", "parentHash", "stateRoot", "timestamp")}
            rec["code"] = {}
            for name, addr in targets.items():
                hexcode = cast("code", addr, "--block", str(block), "--rpc-url", url)
                rec["code"][name] = hexcode
        except Exception as e:  # recorded, never hidden
            rec["ok"] = False
            rec["errors"].append(str(e))
        try:
            rec["eth_config"] = json.loads(cast("rpc", "--rpc-url", url, "eth_config"))
        except Exception as e:
            rec["eth_config"] = None
            rec["errors"].append(f"eth_config: {e}")
        per_rpc.append(rec)

    good = [r for r in per_rpc if r["ok"]]
    if len(good) < 2:
        print(f"chain: only {len(good)} RPC(s) answered; need >= 2 that agree", file=sys.stderr)
        return 2
    ref = good[0]

    def view(r: dict) -> tuple:
        return (r["chain_id"], r["block"]["hash"], r["block"]["number"],
                tuple(sorted(r["code"].items())))

    agree = [r["rpc"] for r in good if view(r) == view(ref)]
    disagree = [r["rpc"] for r in good if view(r) != view(ref)]
    if disagree:
        print(f"chain: RPCs disagree: {disagree} vs {agree}", file=sys.stderr)
        # keep going only to write the record; exit nonzero at the end

    out: dict = {
        "format": "tcg-pilot-chain-fetch/0.1",
        "block_number": block,
        "block_hash": ref["block"]["hash"],
        "block_timestamp": ref["block"]["timestamp"],
        "state_root": ref["block"]["stateRoot"],
        "chain_id": ref["chain_id"],
        "rpcs_agreeing": agree,
        "rpcs_disagreeing": disagree,
        "rpcs_failed": [{"rpc": r["rpc"], "errors": r["errors"]} for r in per_rpc if not r["ok"]],
        "eth_config": {r["rpc"]: r["eth_config"] for r in per_rpc if r.get("eth_config")},
        "contracts": {},
    }
    stop = False
    for name, addr in targets.items():
        hexcode = ref["code"][name]
        raw = bytes.fromhex(hexcode[2:])
        k_cast = cast("keccak", hexcode)
        k_py = "0x" + keccak256_hex(raw).removeprefix("0x")
        out["contracts"][name] = {
            "address": addr,
            "size_bytes": len(raw),
            "keccak256_cast": k_cast,
            "keccak256_pure_python": k_py,
            "keccak_tools_agree": k_cast == k_py,
            "sha256": hashlib.sha256(raw).hexdigest(),
        }
        if len(raw) == 0 or k_cast != k_py:
            stop = True
        if name == "GemJoin_ETH_A":
            dev = bytes.fromhex(DEV_RUNTIME_HEX.read_text().strip().removeprefix("0x"))
            out["contracts"][name]["equals_dev_constant"] = (k_cast == DEV_KECCAK)
            out["contracts"][name]["equals_dev_runtime_hex"] = (raw == dev)
            out["contracts"][name]["dev_runtime_hex"] = str(DEV_RUNTIME_HEX.relative_to(REPO))
            if k_cast != DEV_KECCAK or raw != dev:
                stop = True
            else:
                pathlib.Path(a.artifact).write_bytes(raw)
    pathlib.Path(a.record).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    if stop:
        print("chain: STOP -- GemJoin bytes/keccak do not match the development constant, "
              "or a keccak tool disagreement / empty code", file=sys.stderr)
        return 3
    if disagree:
        return 2
    print(json.dumps({k: {kk: v[kk] for kk in ("size_bytes", "keccak256_cast")}
                      for k, v in out["contracts"].items()}, indent=1))
    print(f"chain: block {block} {out['block_hash']}; agreeing RPCs: {len(agree)}")
    return 0


# --------------------------------------------------------------------------- probe
def cmd_probe(a: argparse.Namespace) -> int:
    """Archive capability + GemJoin storage at the pinned block (for the Pre witness).

    Archive capability = the RPC serves eth_getCode at an OLD block (default:
    Finding 0003's fetch block 25782890), which a pruned node refuses. The
    consumer runs L0 days after the pin, so only archive-capable RPCs count.
    """
    out: dict = {"format": "tcg-pilot-rpc-probe/0.1", "pinned_block": int(a.block),
                 "old_block": int(a.old_block), "rpcs": {}, "storage_at_pinned_block": {}}
    for url in a.rpc:
        r: dict = {}
        try:
            code = cast("code", GEMJOIN, "--block", a.old_block, "--rpc-url", url)
            r["gemjoin_keccak_at_old_block"] = cast("keccak", code)
            r["archive_capable"] = r["gemjoin_keccak_at_old_block"] == DEV_KECCAK
        except Exception as e:
            r["archive_capable"] = False
            r["error"] = str(e)[:300]
        try:
            r["storage"] = {str(s): cast("storage", GEMJOIN, str(s), "--block", a.block, "--rpc-url", url)
                            for s in range(0, 6)}
        except Exception as e:
            r["storage_error"] = str(e)[:300]
        out["rpcs"][url] = r
    views = [json.dumps(r["storage"], sort_keys=True) for r in out["rpcs"].values() if "storage" in r]
    if len(views) < 2 or len(set(views)) != 1:
        print("probe: storage reads missing or disagree across RPCs", file=sys.stderr)
        rc = 2
    else:
        out["storage_at_pinned_block"] = json.loads(views[0])
        rc = 0
    out["archive_capable_rpcs"] = [u for u, r in out["rpcs"].items() if r.get("archive_capable")]
    pathlib.Path(a.record).write_text(json.dumps(out, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"archive_capable_rpcs": out["archive_capable_rpcs"],
                      "storage": out["storage_at_pinned_block"]}, indent=1))
    return rc


# --------------------------------------------------------------------------- spec
def cmd_spec(a: argparse.Namespace) -> int:
    """Assemble a runnable kprove module from one claim body, with tcg's own
    functions (tcg/claims.py), in one of three modes:
      prove          the claim as-is            module <LOOP>-<LABEL>-PROVE
      vacuity        ensures -> false (tcg falsify_body; antecedent kept)
                                                module <LOOP>-<LABEL>-VACUITY
      discriminator  the opposite outcome: every `?SC ==K EVMC_X` in ensures
                     swapped REVERT<->SUCCESS   module <LOOP>-<LABEL>-DISCRIMINATOR
    Pure text transform; the prover is the judge of the result."""
    from tcg.claims import assemble_prove_module, canonicalize, falsify_body
    body = canonicalize(pathlib.Path(a.claim).read_text())
    if a.schedule:
        if body.count("<schedule> SHANGHAI </schedule>") != 1:
            print(f"spec: expected exactly one <schedule> SHANGHAI </schedule> in {a.claim}", file=sys.stderr)
            return 2
        body = body.replace("<schedule> SHANGHAI </schedule>", f"<schedule> {a.schedule} </schedule>")
    if a.mode == "vacuity":
        body = falsify_body(body)
    elif a.mode == "discriminator":
        n_rev, n_suc = body.count("?SC ==K EVMC_REVERT"), body.count("?SC ==K EVMC_SUCCESS")
        if n_rev + n_suc != 1:
            print(f"spec: expected exactly one ?SC ==K EVMC_* in {a.claim}", file=sys.stderr)
            return 2
        if n_rev:
            body = body.replace("?SC ==K EVMC_REVERT", "?SC ==K EVMC_SUCCESS")
        else:
            body = body.replace("?SC ==K EVMC_SUCCESS", "?SC ==K EVMC_REVERT")
    mod = f"{a.loop}-{a.label}-{a.mode}".upper().replace("_", "-")
    text = assemble_prove_module(mod, ["edsl.md"], ["EDSL"], [], [body])
    pathlib.Path(a.out).write_text(text)
    print(mod)
    return 0


# --------------------------------------------------------------------------- variant
def _module_body(text: str) -> str:
    """The single claim body of an assembled prove module (inverse of
    tcg.claims.assemble_prove_module for one goal, no trusted children)."""
    from tcg.claims import canonicalize
    lines = text.split("\n")
    i = next(k for k, l in enumerate(lines) if l.lstrip().startswith("claim"))
    j = max(k for k, l in enumerate(lines) if l.strip() == "endmodule")
    body = [l[2:] if l.startswith("  ") else l for l in lines[i:j]]
    return canonicalize("\n".join(body))


def cmd_variant(a: argparse.Namespace) -> int:
    """Derive a new claim from an assembled <n>-<n>-PROVE module by explicit,
    recorded text edits, and emit its prove / vacuity / discriminator modules
    (same transforms as `spec`). Edits:
      --storage-symbolic   <storage> .Map </storage> -> <storage> STORAGE:Map </storage>
      --calldata K         replace the <callData> cell content by the K term K
      --requires C         append `andBool C` to the requires clause (repeatable)
      --schedule S         SHANGHAI -> S
    The new label is --label; module names <LABEL>-<LABEL>-{PROVE,...}. Pure
    text; the prover judges the result."""
    from tcg.claims import assemble_prove_module, falsify_body
    body = _module_body(pathlib.Path(a.src).read_text())
    m = re.search(r"\[label\(([a-z0-9_]+)\), all-path\]", body)
    if not m:
        print("variant: no [label(..), all-path] in source", file=sys.stderr)
        return 2
    body = body.replace(m.group(0), f"[label({a.label}), all-path]")
    if a.storage_symbolic:
        if body.count("<storage> .Map </storage>") != 1:
            print("variant: expected exactly one <storage> .Map </storage>", file=sys.stderr)
            return 2
        body = body.replace("<storage> .Map </storage>", "<storage> STORAGE:Map </storage>")
    if a.calldata:
        body, n = re.subn(r"<callData> .*? </callData>", lambda _m: f"<callData> {a.calldata} </callData>", body)
        if n != 1:
            print("variant: expected exactly one <callData> cell", file=sys.stderr)
            return 2
    for c in a.requires or []:
        e = re.search(r"\n(\s*)ensures\b", body)
        body = body[: e.start()] + f"\n   andBool {c}" + body[e.start():]
    if a.schedule:
        if body.count("<schedule> SHANGHAI </schedule>") != 1:
            print("variant: expected exactly one <schedule> SHANGHAI </schedule>", file=sys.stderr)
            return 2
        body = body.replace("<schedule> SHANGHAI </schedule>", f"<schedule> {a.schedule} </schedule>")
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    n_rev, n_suc = body.count("?SC ==K EVMC_REVERT"), body.count("?SC ==K EVMC_SUCCESS")
    if n_rev + n_suc != 1:
        print("variant: expected exactly one ?SC ==K EVMC_*", file=sys.stderr)
        return 2
    disc = (body.replace("?SC ==K EVMC_REVERT", "?SC ==K EVMC_SUCCESS") if n_rev
            else body.replace("?SC ==K EVMC_SUCCESS", "?SC ==K EVMC_REVERT"))
    L = a.label.upper().replace("_", "-")
    for mode, b in (("prove", body), ("vacuity", falsify_body(body)), ("discriminator", disc)):
        mod = f"{L}-{L}-{mode.upper()}"
        f = out / f"{a.label}-{a.label}-{mode}.k"
        f.write_text(assemble_prove_module(mod, ["edsl.md"], ["EDSL"], [], [b]))
        print(f"{f}:{mod}")
    return 0


# --------------------------------------------------------------------------- opscan
# Opcodes introduced after Shanghai (EIP numbers), i.e. those whose semantics
# differ between KEVM <schedule> SHANGHAI and mainnet osaka execution rules.
POST_SHANGHAI_OPS = {
    0x49: ("BLOBHASH", "EIP-4844, Cancun"), 0x4A: ("BLOBBASEFEE", "EIP-7516, Cancun"),
    0x5C: ("TLOAD", "EIP-1153, Cancun"), 0x5D: ("TSTORE", "EIP-1153, Cancun"),
    0x5E: ("MCOPY", "EIP-5656, Cancun"), 0x1E: ("CLZ", "EIP-7939, Osaka"),
}
# Opcodes whose behaviour changed after Shanghai without a new byte value.
CHANGED_OPS = {0xFF: ("SELFDESTRUCT", "EIP-6780, Cancun"), 0x40: ("BLOCKHASH", "EIP-2935 serves it from state, Prague; opcode semantics unchanged for the last 256 blocks")}
PRECOMPILE_CHANGES = "EIP-2537 BLS12-381 (0x0b-0x11, Prague), EIP-7951 P256VERIFY (0x100, Osaka), EIP-7823/7883 MODEXP (0x05, Osaka)"


def _disasm(code: bytes, end: int) -> list[tuple[int, int]]:
    out, pc = [], 0
    while pc < end:
        op = code[pc]
        out.append((pc, op))
        pc += 1 + (op - 0x5F if 0x60 <= op <= 0x7F else 0)
    return out


def cmd_opscan(a: argparse.Namespace) -> int:
    """Linear disassembly of b: which opcodes occur, and does any opcode whose
    semantics differ between SHANGHAI and osaka occur in the code section?
    The solc CBOR metadata trailer (last 2 bytes = its length) is data, not
    code, and is excluded. A linear sweep over-approximates the executed
    opcodes (PUSH data skipped; dead bytes after INVALID/0xfe still decoded),
    so 'absent' here is sound for 'never executed'. Exit 1 if a post-Shanghai
    opcode is present."""
    code = pathlib.Path(a.artifact).read_bytes()
    meta_len = int.from_bytes(code[-2:], "big") + 2
    end = len(code) - meta_len
    ops = _disasm(code, end)
    counts: dict[str, int] = {}
    hits = []
    for pc, op in ops:
        counts[f"0x{op:02x}"] = counts.get(f"0x{op:02x}", 0) + 1
        if op in POST_SHANGHAI_OPS:
            hits.append({"pc": pc, "op": f"0x{op:02x}", "name": POST_SHANGHAI_OPS[op][0]})
    rec = {
        "artifact": a.artifact, "sha256": sha256_file(pathlib.Path(a.artifact)),
        "keccak256": "0x" + keccak256_hex(code).removeprefix("0x"), "bytes": len(code),
        "metadata_trailer": {"bytes": meta_len, "starts_at": end, "first_bytes": code[end:end + 6].hex()},
        "code_section_bytes": end, "instructions": len(ops),
        "opcode_counts": dict(sorted(counts.items())),
        "post_shanghai_opcodes_checked": {f"0x{k:02x}": v[0] + " (" + v[1] + ")" for k, v in sorted(POST_SHANGHAI_OPS.items())},
        "post_shanghai_opcodes_present": hits,
        "changed_semantics_opcodes_present": [{"op": f"0x{k:02x}", "name": v[0], "why": v[1], "count": counts.get(f"0x{k:02x}", 0)}
                                              for k, v in sorted(CHANGED_OPS.items()) if counts.get(f"0x{k:02x}")],
        "external_calls": {"CALL": counts.get("0xf1", 0), "STATICCALL": counts.get("0xfa", 0),
                           "DELEGATECALL": counts.get("0xf4", 0), "CALLCODE": counts.get("0xf2", 0)},
        "precompile_note": f"post-Shanghai precompile changes: {PRECOMPILE_CHANGES}. GemJoin's CALL targets are read from storage slots 1 (vat) and 3 (gem); no PUSH of a precompile address feeds a CALL on any proved path (no proved path reaches a CALL).",
        "method": "linear sweep, PUSH1-PUSH32 immediates skipped, CBOR trailer excluded; over-approximates executed opcodes",
    }
    pathlib.Path(a.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(f"opscan: {len(ops)} instructions, post-Shanghai opcodes present: {len(hits)} {hits}")
    return 1 if hits else 0


# --------------------------------------------------------------------------- osaka-evidence
def cmd_osaka_evidence(a: argparse.Namespace) -> int:
    """What KEVM evm-semantics (the tarball pinned in T-hat) says about its own
    OSAKA support: the OSAKA block of schedule.md and the Osaka-fork entries of
    its declared-failing conformance list tests/execution-spec-tests/failing.llvm
    (fixtures version in VERSION). Reads the tarball; measures nothing."""
    import tarfile
    tb = pathlib.Path(a.tarball)
    rec: dict = {"tarball": str(tb.name), "tarball_sha256": sha256_file(tb)}
    with tarfile.open(tb) as tf:
        names = tf.getnames()
        root = names[0].split("/")[0]

        def rd(rel: str) -> str:
            return tf.extractfile(f"{root}/{rel}").read().decode()
        sem = "kevm-pyk/src/kevm_pyk/kproj/evm-semantics"
        sched = rd(f"{sem}/schedule.md")
        m = re.search(r"### Osaka Schedule.*?```k(.*?)```", sched, flags=re.S)
        rec["schedule_md_osaka_block"] = " ".join(m.group(1).split()) if m else None
        evm = rd(f"{sem}/evm.md")
        rec["precompiled_accounts_osaka"] = re.findall(r"rule #precompiledAccountsUB\(OSAKA\)\s*=>\s*([^\n]+)", evm)
        rec["fixtures_version"] = rd("tests/execution-spec-tests/VERSION").strip()
        failing = [l for l in rd("tests/execution-spec-tests/failing.llvm").splitlines() if l.strip()]
        osaka = [l for l in failing if "osaka" in l.lower()]
        by_dir: dict[str, int] = {}
        for l in osaka:
            parts = l.split(",")[0].split("/")
            k = "/".join(parts[1:3]) if len(parts) > 2 else parts[0]
            by_dir[k] = by_dir.get(k, 0) + 1
        rec["failing_llvm_lines"] = len(failing)
        rec["failing_llvm_osaka_lines"] = len(osaka)
        rec["failing_llvm_osaka_by_test_dir"] = dict(sorted(by_dir.items(), key=lambda kv: -kv[1]))
        rec["tests_in_tarball"] = sum(1 for n in names if "/tests/execution-spec-tests/fixtures/" in n)
    rec["reading"] = ("KEVM's OSAKA schedule = PRAGUE constants and flags + Ghasclz (EIP-7939 CLZ) only; its precompile set is PRAGUE's. "
                      "Mainnet Osaka execution-layer EIPs NOT modelled by that schedule: EIP-7823 + EIP-7883 (MODEXP bounds/repricing), "
                      "EIP-7951 (P256VERIFY precompile at 0x100), EIP-7825 (tx gas cap), EIP-7918 (blob base fee floor), EIP-7934 (block RLP size). "
                      "KEVM's own declared-failing list names Osaka fixtures in exactly these directories. "
                      "No pass/total was computed: the fixtures are not in the tarball (fetched by get_execution_spec_tests.sh) and were not run in this pilot.")
    pathlib.Path(a.out).write_text(json.dumps(rec, indent=2) + "\n")
    print(json.dumps({k: rec[k] for k in ("fixtures_version", "failing_llvm_lines", "failing_llvm_osaka_lines")}))
    return 0


# --------------------------------------------------------------------------- hardspec
CLAIM_FORMS = {  # tcg label -> (requirements referenced, Aasm annotations, source of the claim body)
    "vat": (["R1"], ["Aasm-rangeUInt-storage", "Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call"],
            "tests/reference/getters-full/src/vat/vat.k (Finding 0003b), assembled as provenance/rebuild/controls*/vat-vat-prove.k"),
    "ilk": (["R2"], ["Aasm-rangeUInt-storage", "Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call"],
            "tests/reference/getters-full/src/ilk/ilk.k (Finding 0003b), assembled as provenance/rebuild/controls*/ilk-ilk-prove.k"),
    "gem": (["R3"], ["Aasm-rangeUInt-storage", "Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call"],
            "tests/reference/getters-full/src/gem/gem.k (Finding 0003b), assembled as provenance/rebuild/controls*/gem-gem-prove.k"),
    "cagews": (["R4"], ["Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call", "Aasm-keccak-wards-slot"],
               "NEW CONTENT 2026-10-29: `assemble_hard.py variant --label cagews --storage-symbolic --requires '#lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0'` of the rebuilt Finding-0003 cage claim (provenance/rebuild/src/cage/cage.k); see provenance/decision-stub.md"),
    "cage": (["R4"], ["Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call"],
             "provenance/rebuild/src/cage/cage.k (REBUILT 2026-10-29 from Finding 0003 row 1; see provenance/decision-stub.md)"),
    "joinsym": (["R5"], ["Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call", "Aasm-rangeUInt-args"],
                "NEW CONTENT 2026-10-29: `assemble_hard.py variant --label joinsym --calldata 'b\"\\x3b\\x4d\\xa6\\x9f\" +Bytes #buf(32, USR:Int) +Bytes #buf(32, WAD:Int)' --requires '#rangeUInt(256, USR)' --requires '#rangeUInt(256, WAD)'` of provenance/rebuild/src/join/join.k (Finding 0003 row 4 rebuilt, generalised to symbolic storage with live == 0); see provenance/decision-stub.md"),
    "join": (["R5"], ["Aasm-address-range", "Aasm-gas-abstraction", "Aasm-toplevel-call"],
             "provenance/rebuild/src/join/join.k (REBUILT 2026-10-29 from Finding 0003 row 4, generalised to symbolic storage with live == 0; see provenance/decision-stub.md)"),
}
K_COMMIT = "4a46d1231473b599c699160132fd6e76a5c46406"
EVM_SEM_COMMIT = "d4bf484a5dfe1e38d729a30434cd6f41e3590fb2"

MASK160 = "storage[{s}] & (2^160 - 1)"
_COMMON_SET = ("program = hard/artifact.bin; executing account ACCTID any value in [0, 2^160); caller MSGSENDER any value in [0, 2^160); "
               "callvalue 0; top-level frame (<callStack> .List), non-static; gas not modelled (<useGas> false); schedule {sched}")
READABLE = {
    "vat": dict(function="vat()", calldata="exactly 0x36569e77 (4 bytes)", storage="any Map with storage[1] in [0, 2^256) (Aasm-rangeUInt-storage)",
                post=dict(status="EVMC_SUCCESS", output="32-byte big-endian word of " + MASK160.format(s=1),
                          storage="unchanged (same Map)", log="unchanged", call_stack="unchanged (top level)")),
    "ilk": dict(function="ilk()", calldata="exactly 0xc5ce281e (4 bytes)", storage="any Map with storage[2] in [0, 2^256) (Aasm-rangeUInt-storage)",
                post=dict(status="EVMC_SUCCESS", output="32-byte big-endian word of storage[2]",
                          storage="unchanged (same Map)", log="unchanged", call_stack="unchanged (top level)")),
    "gem": dict(function="gem()", calldata="exactly 0x7bd2bea7 (4 bytes)", storage="any Map with storage[3] in [0, 2^256) (Aasm-rangeUInt-storage)",
                post=dict(status="EVMC_SUCCESS", output="32-byte big-endian word of " + MASK160.format(s=3),
                          storage="unchanged (same Map)", log="unchanged", call_stack="unchanged (top level)")),
    "cagews": dict(function="cage()", calldata="exactly 0x69245009 (4 bytes)",
                   storage="any Map with storage[keccak256(pad32(caller) ++ pad32(0))] == 0, i.e. wards[caller] == 0 (caller is not a ward); every other slot arbitrary. keccak is KEVM's keccak(Bytes) left opaque by the prover (symbolic argument)",
                   post=dict(status="EVMC_REVERT", output="unconstrained (revert payload)",
                             storage="unchanged (same Map)", log="unchanged", call_stack="unchanged (top level)")),
    "cage": dict(function="cage()", calldata="exactly 0x69245009 (4 bytes)",
                 storage="EMPTY (.Map: every slot 0, so wards[caller] == 0 for every caller; also vat = ilk = gem = live = 0)",
                 post=dict(status="EVMC_REVERT", output="unconstrained (revert payload)",
                           storage="unchanged (still empty)", log="unchanged", call_stack="unchanged (top level)")),
    "joinsym": dict(function="join(address,uint256)",
                    calldata="0x3b4da69f ++ word(USR) ++ word(WAD), exactly 68 bytes, for EVERY 256-bit USR and WAD (USR's upper 96 bits may be dirty; the code masks them)",
                    storage="any Map with storage[5] (live) == 0; every other slot arbitrary",
                    post=dict(status="EVMC_REVERT", output="unconstrained (revert payload)",
                              storage="unchanged (same Map)", log="unchanged", call_stack="unchanged (top level)")),
    "join": dict(function="join(address,uint256)",
                 calldata="0x3b4da69f ++ uint256(0xdead) ++ uint256(10^18)  (CONCRETE usr = 0xdead, wad = 1e18)",
                 storage="any Map with storage[5] (live) == 0",
                 post=dict(status="EVMC_REVERT", output="unconstrained (revert payload)",
                           storage="unchanged (same Map)", log="unchanged", call_stack="unchanged (top level)")),
}
REACH = {
    "vat": "reachable, shown on chain: the deployed storage at the pinned block satisfies Pre for every caller (slot values in provenance/rpc_probe.json; concrete instance replayed for ilk() in pre_witness claim-02)",
    "ilk": "reachable, shown on chain: pre_witness claim-02 is the deployed storage at the pinned block (eth_getStorageAt, 4 RPCs agree) with a concrete caller; its instance Accepts and its vacuity probe does not",
    "gem": "reachable, shown on chain: the deployed storage at the pinned block satisfies Pre for every caller (same slot record as claim-02)",
    "cagews": "reachable, shown on chain: pre_witness claim-04 is the deployed storage at the pinned block with caller 0x000000000000000000000000000000000000dEaD, whose wards slot reads 0 at the pinned block (eth_getStorageAt, recorded in claim-04-config.json chain_slot_checks); its instance Accepts and its vacuity probe does not",
    "cage": "NOT reachable: no constructed GemJoin has empty storage (the constructor sets wards[deployer], vat, ilk, gem, dec, live). K-feasible only (vacuity probe). A reachable-state trap, not coverage",
    "joinsym": "reachable by judgement, not shown on chain: pre_witness claim-05 is the deployed storage at the pinned block with slot 5 (live) set to 0, i.e. the state right after a ward calls cage(); live is 1 at the pinned block",
    "join": "reachable by judgement (post-cage state), for one concrete (usr, wad)",
}
CAVEATS = {
    "vat": ["'No external call' is a bytecode-inspection fact (straight-line getter body), not a separate K postcondition (Finding 0003b caveat 2)."],
    "ilk": ["'No external call' is a bytecode-inspection fact (straight-line getter body), not a separate K postcondition (Finding 0003b caveat 2)."],
    "gem": ["'No external call' is a bytecode-inspection fact (straight-line getter body), not a separate K postcondition (Finding 0003b caveat 2)."],
    "cagews": ["Pre says wards[caller] == 0, not wards[caller] != 1. Every write to wards in the bytecode (constructor, rely, deny) stores 0 or 1, so every reachable non-ward has 0; that invariant is a bytecode-inspection argument, not proved.",
               "The meaning 'wards[caller]' rests on KEVM's keccak(Bytes) being Keccak-256 and on solc 0.5.12's mapping layout (slot = keccak256(pad32(key) ++ pad32(0))): Aasm-keccak-wards-slot / A_keccak in trusted_base.json. The proof itself treats keccak as an opaque function and needs no injectivity.",
               "Not proved: rely(usr)/deny(usr) by a non-ward (the rest of R4); cage() by a ward (success path)."],
    "cage": ["Pre is EMPTY storage (Finding 0003's shape). No constructed GemJoin is ever in that state. The claim is K-feasible (vacuity probe) but covers no configuration reachable by the deployed contract.",
             "The general R4 case needs the keccak(caller . 0) mapping-slot reasoning and is not proved in this form."],
    "joinsym": ["Calldata is exactly 68 bytes; longer calldata (extra trailing bytes, which the ABI decoder accepts) is outside this claim.",
                "'Before any external call' is a bytecode-inspection fact (the revert at pc 0x03bf precedes both CALL sites at pc 0x04e9 and 0x05de), not a separate K postcondition; the K postcondition says every other account and GemJoin's storage and log are unchanged at the halt.",
                "Covers the reachable post-cage() state (live == 0 with the rest of storage arbitrary)."],
    "join": ["Arguments are CONCRETE (usr = 0xdead, wad = 1e18), as in Finding 0003's idiom; R5 is for every usr, wad.",
             "'Before any external call' is a bytecode-inspection fact, not a separate K postcondition."],
}
PRE_SCOPE = {"cagews": ["#lookup(STORAGE, keccak(#buf(32, MSGSENDER) +Bytes #buf(32, 0))) ==Int 0"],
             "joinsym": ["#lookup(STORAGE, 5) ==Int 0"], "join": ["#lookup(STORAGE, 5) ==Int 0"]}


def _results(paths: list[str]) -> dict:
    out = {}
    for path in paths:
        for line in pathlib.Path(path).read_text().splitlines()[1:]:
            f = line.split("\t")
            out[f[1]] = dict(verdict=f[4], unknown_class=f[5], exit=int(f[3]), wall_s=float(f[6]), log_sha256=f[7],
                             image=f[8], spec=f[0], results_file=path)
    return out


def cmd_hardspec(a: argparse.Namespace) -> int:
    bundle = pathlib.Path(a.bundle)
    ctl = pathlib.Path(a.controls)
    results = _results(a.results)
    ledger = [json.loads(l) for l in (bundle / "provenance/ledger.jsonl").read_text().splitlines()]
    image = pathlib.Path(REPO / "pilot/checker/IMAGE_ID").read_text().split()[0]
    deff = json.loads(pathlib.Path(a.pins).read_text())["in_image_provenance"]["definition_kore_sha256"]
    art = (bundle / "hard/artifact.bin").read_bytes()
    spec_dir, cert_dir = bundle / "hard/spec", bundle / "hard/certs"
    spec_dir.mkdir(parents=True, exist_ok=True)
    cert_dir.mkdir(parents=True, exist_ok=True)
    forms = ["vat", "ilk", "gem", a.claim04, a.claim05]
    phi_claims, missing = [], []

    def seq_for(mod: str, spec_rel: str, h: str):
        return next((e["seq"] for e in reversed(ledger) if e.get("kind") == "run" and e.get("argv") and mod in e["argv"]
                     and any(i.get("path") == spec_rel and i.get("sha256") == h for i in e.get("inputs", []))), None)

    for k, n in enumerate(forms, start=1):
        cid = f"claim-0{k}"
        reqs, aasm, src = CLAIM_FORMS[n]
        mod = f"{n}-{n}-PROVE".upper()
        srcf = ctl / f"{n}-{n}-prove.k"
        r = results.get(mod)
        if not r or r["verdict"] != "Accept":
            missing.append(f"{cid} ({mod}): no Accept in {a.results}")
            continue
        text = srcf.read_text()
        if f"<schedule> {a.schedule} </schedule>" not in text:
            missing.append(f"{cid}: claim schedule is not {a.schedule}")
        ctl_rows = {}
        names = {"vacuity": f"{n}-{n}-VACUITY".upper(), "discriminator": f"{n}-{n}-DISCRIMINATOR".upper()}
        if n in ("vat", "ilk", "gem"):
            names["wrong_slot"] = f"WRONG-SLOT-{n.upper()}-SPEC"
        for kind, cm in names.items():
            rr = results.get(cm)
            if not rr or rr["verdict"] == "Accept":
                missing.append(f"{cid}: {kind} control {cm} missing or Accepted ({rr})")
                continue
            if rr["verdict"] == "Unknown" and rr["exit"] != 1:
                missing.append(f"{cid}: {kind} control {cm} ended exit {rr['exit']} (not a clean prover NotAccept; infra?)")
            what = {"vacuity": "same Pre, ensures false: must NOT Accept (Accept would mean Pre is unsatisfiable, a vacuous proof)",
                    "discriminator": "same claim, opposite exit status (SUCCESS<->REVERT): must NOT Accept",
                    "wrong_slot": "same getter claim, return value bound to a DIFFERENT storage slot: must NOT Accept"}[kind]
            ctl_rows[kind] = dict(module=cm, what=what, expected="not Accept", **rr)
        dst = spec_dir / f"{cid}.k"
        dst.write_text(text)
        h = sha256_file(dst)
        spec_rel = str(srcf.relative_to(bundle)) if srcf.is_absolute() else str(srcf)
        seq = seq_for(mod, spec_rel, h)
        if seq is None:
            missing.append(f"{cid}: no ledger event proving exactly this file (sha256 {h} at {spec_rel})")
        rd = READABLE[n]
        phi_claims.append({
            "id": cid, "claim": cid, "file": f"hard/spec/{cid}.k", "sha256": h, "spec_module": mod, "k_label": n,
            "source": src + (f"; <schedule> SHANGHAI </schedule> replaced by <schedule> {a.schedule} </schedule>"
                             if a.schedule != "SHANGHAI" else ""),
            "kind": "KEVM all-path reachability claim: every execution from a Pre state reaches a halting state satisfying Post",
            "program": {"binds": "hard/artifact.bin", "keccak256": "0x" + keccak256_hex(art).removeprefix("0x"),
                        "how": "<program> and <jumpDests> cells are #parseByteStack of the exact 3462 bytes"},
            "quantifies_over": {
                "configuration_set": _COMMON_SET.format(sched=a.schedule) + f"; calldata {rd['calldata']}; storage: {rd['storage']}",
                "reachability": REACH[n],
            },
            "pre": {"function": rd["function"], "calldata": rd["calldata"], "callvalue": 0,
                    "caller": "any 160-bit address (symbolic MSGSENDER)", "executing_account": "any 160-bit address (symbolic ACCTID)",
                    "storage": rd["storage"], "schedule": a.schedule, "gas": "not modelled (<useGas> false)",
                    "frame": "top-level call (<callStack> .List), non-static"},
            "post": rd["post"],
            "exit": [f"#halt with status {rd['post']['status']}"],
            "pre_scope_k": PRE_SCOPE.get(n, []),
            "aasm": aasm,
            "requirements": reqs,
            "coverage_of_requirements": {reqs[0]: "full, under the listed Aasm facts" if n in ("vat", "ilk", "gem")
                                         else "partial: see caveats and declared_blind_spots"},
            "caveats": CAVEATS[n],
            "controls": ctl_rows,
            "observed": dict(r, ledger_seq=seq),
        })
        argv = ["docker", "run", "--rm", "--platform", "linux/amd64", "--network", "none", "--memory=6g", "--cpus=2",
                "--user", "<uid>:<gid>", "-e", "HOME=/tmp", "-v", "<claimdir>:/claim:ro", "-v", "<scratch>:/work", "-w", "/work",
                image, "kprove", f"/claim/{cid}.k", "--definition", "/opt/kevm/haskell", "-I", "/opt/kevm/evm-semantics-source",
                "-I", "/opt/kevm/plugin", "--spec-module", mod]
        cert = {
            "claim": cid, "checker": "kevm-prove", "claim_file": f"hard/spec/{cid}.k", "spec_module": mod,
            "kprove_args": [],
            "kevm_version": f"evm-semantics {EVM_SEM_COMMIT} (tag v1.0.921; self-reports 1.0.678) + ghost.diff + lemmas2.diff, main module LEMMAS-DRIVER",
            "k_version": f"K v7.1.337 (commit {K_COMMIT}), kore-exec 0.1.155, z3 4.12.1",
            "semantics_hash": deff, "timeout_s": 3600, "expected": "accept",
            "argv": argv, "image_id": image, "k_commit": K_COMMIT, "evm_semantics_commit": EVM_SEM_COMMIT,
            "claim_file_sha256": h,
            "note": (f"Not a proof object (variant A). image_id={image} claim_file_sha256={h} "
                     f"definition_kore_sha256={deff}. argv is the shape of pilot/checker/run-claim.sh (never executed from here). "
                     f"Accept iff exit 0 and stdout contains #Top (tcg/verdict.py). The producer's run is ledger seq {seq}; "
                     f"the spec it proved was {spec_rel} (same sha256)."),
        }
        if seq is not None:
            cert["ledger_seq"] = seq
        (cert_dir / f"{cid}.rediscuss.json").write_text(json.dumps(cert, indent=2) + "\n")
    blind = [
        {"requirement": "R4", "partial": True, "reason":
            ("claim-04 proves cage() reverts for every non-ward caller (wards[caller] == 0) over every other storage. Not proved: rely/deny by a non-ward; "
             "a caller with wards[caller] not in {0, 1} (unreachable by bytecode inspection, not proved); cage/rely/deny success for a ward.")
            if a.claim04 == "cagews" else
            "claim-04 proves only cage() with EMPTY storage, a configuration no constructed GemJoin reaches (declared limit, not coverage). Not proved: a non-ward caller of cage/rely/deny while other wards exist; rely/deny at all."},
        {"requirement": "R5", "partial": True, "reason":
            ("claim-05 proves join reverts with live == 0 for every caller, every storage and every 256-bit (usr, wad). Not proved: calldata longer than 68 bytes; callvalue > 0 (R9); "
             "a call from a non-top-level frame (Aasm-toplevel-call). 'Before any external call' is by bytecode inspection.")
            if a.claim05 == "joinsym" else
            "claim-05 proves join with live == 0 for every caller and every storage, but for ONE concrete (usr, wad) = (0xdead, 1e18). Not proved: every usr, wad."},
        {"requirement": "R6", "reason": "Not proved. join's value movement needs the external calls Vat.slip and WETH.transferFrom composed (assume-guarantee over unaudited callees); Stage C is open (Finding 0006 + correction). The overflow guard (wad >= 2^255 reverts, Finding 0003 row 6) is outside this claim set."},
        {"requirement": "R7", "reason": "Not proved. exit's value movement needs Vat.slip and WETH.transfer composed; open (Finding 0006). The overflow guard (Finding 0003 row 5) is outside this claim set."},
        {"requirement": "R8", "reason": "Not proved as stated. Claims 01-05 show storage is unchanged on the three getter paths and the two revert paths only; no success path of join/exit/cage/rely/deny is covered."},
        {"requirement": "R9", "reason": "Not proved. Every claim fixes callvalue = 0; the non-payable guard (Finding 0003 row 7, cage only) is outside this claim set."},
    ]
    phi = {
        "format": "tcg-pilot-phi/0.1",
        "status": "DRAFT for the author's review; NOT signed (DECISIONS D4: the oracle signs sha256(phi.json) || sha256(requirements.md))",
        "artifact": {"file": "hard/artifact.bin", "keccak256": "0x" + keccak256_hex(art).removeprefix("0x"),
                     "address": GEMJOIN, "chain_id": 1, "block": 26298481},
        "requirements_file": "hard/spec/requirements.md",
        "requirements_sha256": sha256_file(spec_dir / "requirements.md"),
        "semantics": f"KEVM evm-semantics {EVM_SEM_COMMIT} + lemmas2, schedule {a.schedule}; see trusted_base.json",
        "claims": phi_claims,
        "declared_blind_spots": blind,
        "declared_limits": [
            "Every claim fixes callvalue 0, a top-level non-static frame, and gas not modelled: a claim holds for executions that do not run out of gas (Aasm-gas-abstraction). It does not guarantee termination within any gas limit.",
            f"Every claim is proved under KEVM <schedule> {a.schedule} </schedule>, which models mainnet osaka only partly (trusted_base.json semantics[0].adequacy_evidence, A1).",
        ] + (["claim-04 (EMPTY-storage cage form) quantifies over no reachable configuration: a reachable-state trap that the vacuity probe does not detect. It is listed here, not as coverage of R4."]
             if a.claim04 == "cage" else []),
        "reading_guide": "pre/post/exit are a non-K paraphrase of each claim; the K file (by sha256) is the statement that was proved. quantifies_over states the configuration set each claim ranges over and whether it is reachable. A requirement listed in a claim's `requirements` with coverage 'partial' is ALSO listed in declared_blind_spots with the uncovered part.",
    }
    if missing:
        for m in missing:
            print("hardspec: REFUSE " + m, file=sys.stderr)
        return 1
    (spec_dir / "phi.json").write_text(json.dumps(phi, indent=2) + "\n")
    print(f"hardspec: wrote {len(phi_claims)} claims, phi.json, {len(phi_claims)} certs (schedule {a.schedule}; forms {forms})")
    return 0


# --------------------------------------------------------------------------- tbase
def cmd_tbase(a: argparse.Namespace) -> int:
    """Write trusted_base.json (task 03). Hashes come from objects (files,
    the chain fetch record, the checker pins); `rehash` re-derives each."""
    bundle = pathlib.Path(a.bundle)
    pins = json.loads(pathlib.Path(a.pins).read_text())
    prov = pins["in_image_provenance"]
    chain = json.loads((bundle / "provenance/chain_fetch.json").read_text())
    probe = json.loads((bundle / "provenance/rpc_probe.json").read_text())
    osk = json.loads((bundle / "provenance/kevm_osaka_adequacy.json").read_text())
    ops = json.loads((bundle / "provenance/opscan.json").read_text())
    anns = json.loads((bundle / "hard/annotations.json").read_text())["annotations"]
    phi = json.loads((bundle / "hard/spec/phi.json").read_text())
    claim_ids = [c["id"] for c in phi["claims"]]
    forms = {c["id"]: c["k_label"] for c in phi["claims"]}
    sched = a.schedule
    fork = sched.lower()
    image = pins["image_id"]
    cfg = next(iter(chain["eth_config"].values()))["current"]
    sys.path.insert(0, str(REPO / "pilot/verifier"))
    from tcgverify.ladder import verifier_hash
    fam_ids = [x["id"] for x in anns if x.get("kind") == "simplification_lemma_family"]

    def ann(i):
        return next(x for x in anns if x["id"] == i)

    wit_dir = pathlib.Path(a.witness_dir)
    wit_files = {str(p.relative_to(bundle)): sha256_file(p) for p in sorted(wit_dir.glob("*")) if p.is_file()}
    wit_claims = sorted(p.name.removesuffix("-config.json") for p in wit_dir.glob("claim-*-config.json"))
    osaka_gap = ("KEVM d4bf484a's OSAKA schedule is PRAGUE + EIP-7939 (CLZ) only, with PRAGUE's precompile set "
                 f"(schedule.md: {osk['schedule_md_osaka_block'][:160]}...). Mainnet osaka execution-layer EIPs it does NOT model: "
                 "EIP-7823/7883 (MODEXP bounds and repricing), EIP-7951 (P256VERIFY at 0x100), EIP-7825 (tx gas cap), "
                 "EIP-7918 (blob base fee floor), EIP-7934 (block RLP size). KEVM's own declared-failing conformance list "
                 f"(tests/execution-spec-tests/failing.llvm, fixtures {osk['fixtures_version']}) has {osk['failing_llvm_osaka_lines']} "
                 f"of {osk['failing_llvm_lines']} entries on the Osaka fork, by test dir: "
                 + ", ".join(f"{k} {v}" for k, v in list(osk["failing_llvm_osaka_by_test_dir"].items())[:12])
                 + ". No pass/total was computed in this pilot (fixtures not in the tarball, not run). Record: provenance/kevm_osaka_adequacy.json.")
    gemjoin_ops = (f"GemJoin uses no opcode introduced after Shanghai (linear sweep of the {ops['code_section_bytes']}-byte code section, "
                   f"CBOR trailer excluded: none of {', '.join(v.split(' ')[0] for v in ops['post_shanghai_opcodes_checked'].values())}; "
                   "no SELFDESTRUCT, no BLOCKHASH), so the KEVM SHANGHAI/OSAKA differences reachable from its code are gas constants only, "
                   "which no claim models. Record: provenance/opscan.json.")
    claim04_reach = next(c["quantifies_over"]["reachability"] for c in phi["claims"] if c["id"] == "claim-04")
    tb = {
        "format": "tcg-pilot-trusted-base/0.1",
        "description": "T-hat for the GemJoin ETH-A pilot bundle, variant A (pinned KEVM re-discharge). Every hash here is recomputed by `python3 pilot/tools/assemble_hard.py rehash --rpc <archive RPC>`.",
        "semantics": [{
            "name": "KEVM", "role": "primary",
            "version": f"runtimeverification/evm-semantics {EVM_SEM_COMMIT} (tag v1.0.921; its kevm_pyk VERSION constant still says 1.0.678, which is what tcg's TOOLCHAIN pin and the task files call it)",
            "commit": EVM_SEM_COMMIT,
            "hash": prov["evm_semantics_tgz_sha256"],
            "hash_of": "sha256 of the GitHub source tarball of that commit, as stored at /opt/kevm/inputs/evm-semantics.tar.gz in the checker image",
            "plugin": {"name": "blockchain-k-plugin", "commit": prov["blockchain_k_plugin_rev"], "tarball_sha256": prov["blockchain_k_plugin_tgz_sha256"]},
            "patches": [{"name": "ghost.diff", "sha256": prov["patches_applied"][0]["sha256"], "repo_path": "pilot/checker/patches/ghost.diff"},
                        {"name": "lemmas2.diff", "sha256": prov["patches_applied"][1]["sha256"], "repo_path": "pilot/checker/patches/lemmas2.diff",
                         "origin": "git show p1-b-vat-slip:theory/patches/lemmas.diff (NOT main's theory/patches/lemmas.diff 8e0e5b57..., which lacks BOOL2WORD- and MAP-REASONING-SIMPLIFICATION)"}],
            "kompiled_definition": {"main_module": prov["main_module"], "definition_kore_sha256": prov["definition_kore_sha256"],
                                    "note": "kompile is not byte-deterministic (embeds paths/ordering): the consumer uses the definition inside the pinned image, never a rebuild"},
            "schedule_used_by_claims": sched,
            "adequacy_evidence": osaka_gap if sched == "OSAKA" else (
                "Claims use KEVM SHANGHAI; mainnet at the pinned block runs osaka. " + osaka_gap),
            "adequacy_evidence_for_this_artifact": gemjoin_ops,
            "adequacy_records": {"provenance/kevm_osaka_adequacy.json": sha256_file(bundle / "provenance/kevm_osaka_adequacy.json"),
                                 "provenance/opscan.json": sha256_file(bundle / "provenance/opscan.json")},
        }],
        "checker": [
            {"name": "kevm-prove", "hash": image, "image": image, "platform": pins["platform"],
             "size_bytes": pins["size_bytes"], "docker_save_sha256": pins["docker_save_sha256"],
             "in_image_manifest_sha256": pins["in_image_manifest_sha256"],
             "contents": f"kprove/kore-exec of K v7.1.337 (commit {K_COMMIT}, RV Ubuntu jammy build, base image runtimeverificationinc/kframework-k:ubuntu-jammy-7.1.337@sha256:a63698c015f2b349bb9807d486bf2a48a764237a018fd207c23ac7571519b12b), kore-exec 0.1.155, {prov['z3_version']}, plus the kompiled definition above",
             "solver": {"name": "z3", "version": prov["z3_version"],
                        "note": "the image carries RV's bundled z3 4.12.1; the repo's CLAUDE.md pins z3 4.16.0 for the laptop SMTChecker toolchain. Every verdict in this bundle came from 4.12.1 (A3)"},
             "entry": "pilot/checker/run-claim.sh <claim.k> --spec-module <MODULE> (docker run --network none --memory=6g --cpus=2); Accept iff exit 0 and stdout contains #Top",
             "size_loc": None, "self_contained": False,
             "note": "external prover, re-discharge only; emits no proof object. Distributed out of band as tcg-kevm-checker.tar (docker load), identified by image Id."},
            {"name": "tcg-verifier", "hash": verifier_hash(),
             "note": "tcgverify.ladder.verifier_hash() at the time this file was written; MUST be refreshed when the verifier freezes (rehash fails until then)"},
        ],
        "identity": {
            "function": "keccak256(runtime_bytecode)",
            "value": chain["contracts"]["GemJoin_ETH_A"]["keccak256_cast"],
            "address": GEMJOIN, "block": chain["block_number"],
            "constructor_and_immutables": "none; runtime code only (solc 0.5.12 GemJoin has no immutables; vat/ilk/gem/dec are storage slots 1-4)",
            "artifact": "hard/artifact.bin",
        },
        "environment": {
            "chain_id": chain["chain_id"],
            "fork": fork,
            "fork_basis": f"the claims are proved under KEVM <schedule> {sched} </schedule>; mainnet at the pinned block runs osaka execution rules (eth_config current.forkId {cfg['forkId']}, activationTime {cfg['activationTime']} = BPO2 blob schedule {cfg.get('blobSchedule')}, from 3 RPCs). "
                          + ("Declared fork = the schedule proved under, so L0-environment compares it with the block's fork honestly." if fork != "osaka" else
                             "KEVM OSAKA is a partial model of mainnet osaka (semantics[0].adequacy_evidence, A_osaka_model) and does not model the BPO blob parameters (A_blob_params)."),
            "block_hash": chain["block_hash"], "block_timestamp": int(chain["block_timestamp"], 16),
            "fee_schedule": f"not modelled: every claim runs with <useGas> false (Aasm-gas-abstraction); the KEVM {sched} gas constants are present in the semantics but unused",
            "external_code": [
                {"name": "WETH9", "address": WETH, "code_hash": chain["contracts"]["WETH9"]["keccak256_cast"], "role": "gem (slot 3 at the pinned block)", "reached_by_any_claim": False},
                {"name": "MCD_Vat", "address": VAT, "code_hash": chain["contracts"]["MCD_Vat"]["keccak256_cast"], "role": "vat (slot 1 at the pinned block)", "reached_by_any_claim": False},
            ],
            "external_code_note": "No proved path reaches a CALL (by bytecode inspection: the 4 CALLs sit in join/exit after the live check and the overflow guard), so WETH and Vat code are part of E for the deployed contract but no claim depends on their behaviour. A different gem/vat at the same slots would not change any claim.",
            "caller_assumptions": "msg.sender arbitrary (any 160-bit address; claim-04 additionally: not a ward); GemJoin's code runs as the top-level frame under its own account; no DELEGATECALL into GemJoin; non-static; callvalue 0 (Aasm-toplevel-call)",
            "precompiles": f"KEVM {sched}'s precompile set ({osk['precompiled_accounts_osaka'][0] if sched == 'OSAKA' else 'SHANGHAI'}: no P256VERIFY at 0x100, MODEXP without EIP-7823/7883) differs from mainnet osaka; no proved path calls a precompile and GemJoin's CALL targets come from storage",
            "resource_limits": "gas not modelled (<useGas> false): every claim holds for executions that do not run out of gas (Aasm-03). No claim guarantees termination within any gas limit; an out-of-gas halt is outside every claim. Within the gas-free semantics each all-path claim states that every path from Pre reaches #halt.",
            "storage_at_pinned_block": probe["storage_at_pinned_block"],
        },
        "assumptions": [
            {"id": "A1", "name": "semantics adequacy", "status": "assumption", "covers": ["A_kevm_edsl_simp"],
             "evidence": "KEVM is the reference K semantics of the EVM; see semantics[0].adequacy_evidence (its own declared-failing list; no pass/total measured here)",
             "risk_if_false": f"a KEVM rule (including the {sched} schedule rules and the stock EDSL [simplification] rules) that differs from mainnet osaka execution would make a proved claim false of the deployed contract, undetectably from inside the bundle"},
            {"id": "A_osaka_model", "name": f"KEVM {sched} agrees with mainnet osaka on every opcode GemJoin's proved paths execute", "status": "assumption",
             "evidence": gemjoin_ops + " The unmodelled osaka EIPs (7823, 7883, 7951, 7825, 7918, 7934) touch precompiles, tx- and block-level rules, none of which a proved path executes.",
             "risk_if_false": "if an opcode on a proved path (CALLDATALOAD, SLOAD, KECCAK256, MSTORE, JUMPI, REVERT, RETURN, AND, EQ, ...) behaved differently on mainnet osaka than in KEVM, a claim could be false of the deployed contract"},
            {"id": "A_blob_params", "name": "BPO1/BPO2 blob parameters not modelled and not relied on", "status": "assumption",
             "evidence": f"mainnet at the pin is past BPO2 (eth_config blobSchedule {cfg.get('blobSchedule')}); KEVM's schedule carries PRAGUE blob constants (Gmaxblobgas 1179648, Gtargetblobgas 786432) and no BPO forks. GemJoin has no BLOBHASH (0x49) or BLOBBASEFEE (0x4a) (provenance/opscan.json), and no claim models gas or block-level blob accounting",
             "risk_if_false": "none for these claims as long as GemJoin's code has no blob opcode (checked by opscan); a claim about a contract reading BLOBBASEFEE would be about the wrong parameter set"},
            {"id": "A2", "name": "environment adequacy", "status": "checked_at_L0",
             "note": "chain_id, fork (derived from the block) and external code hashes are compared with the chain at the pinned block; fee_schedule, caller_assumptions, precompiles and resource_limits are declared, not checked",
             "risk_if_false": "the proof transfers to a machine other than the deployed one"},
            {"id": "A3", "name": "checker soundness", "status": "assumption", "hashes": [image],
             "note": f"kprove + Haskell backend kore-exec 0.1.155 + {prov['z3_version']} inside the image (CLAUDE.md pins z3 4.16.0 for the laptop toolchain; the image carries RV's bundled z3 4.12.1, which produced every verdict here)",
             "risk_if_false": "an unsound prover step or solver answer could Accept a false claim; no proof object exists to re-check independently (variant A)"},
            {"id": "A4", "name": "artefact identity", "status": "checked_at_L0",
             "risk_if_false": "the bundle would describe different bytecode; L0 reports a different artefact"},
            {"id": "A5", "name": "annotation discipline", "status": "partially_checked",
             "note": "every lemma family / Aasm fact the claims depend on is listed in hard/annotations.json and closed mechanically (assemble_hard.py closure); their justifications are not checked",
             "risk_if_false": "an unlisted assumption would be trusted silently"},
            {"id": "A6", "name": "spec well-formedness", "status": "partially_checked",
             "note": (f"pre_witness replays concrete states satisfying the Pre of {', '.join(wit_claims)}; every claim's antecedent is K-feasible (vacuity probes) and its opposite exit status is not provable (discriminators). "
                      f"Reachability (phi.json claims[].quantifies_over.reachability): claims 01-03 and 04 are reached by the deployed storage at the pinned block; claim-05's Pre (live == 0) is the post-cage() state, reachable by judgement only. "
                      f"claim-04: {claim04_reach}"),
             "risk_if_false": "a claim over an unreachable Pre is true but says nothing about the deployed contract (a reachable-state trap: vacuity PASS does not detect it)"},
            {"id": "A_simp_lemmas", "name": "simplification lemmas sound", "status": "assumption", "covers": fam_ids,
             "evidence": "320 rules in 6 families (all [simplification], checked by closure); the 4 Finding-0004 families probed with 4 known-false identities (none proved, laptop lemma definition, scripts/lemma-consistency.sh); BOOL2WORD/MAP-REASONING extracted verbatim from upstream lemmas.k; none machine-checked against the semantics",
             "risk_if_false": "a false [simplification] rule lets kprove Accept a false postcondition; vacuity probes and program binding do not detect it (Finding 0004)"},
            ({"id": "A_keccak", "name": "KEVM keccak(Bytes) is Keccak-256; solc 0.5.12 mapping layout", "status": "assumption",
              "covers": ["Aasm-keccak-wards-slot"],
              "note": "relied on by claim-04 for the MEANING of its Pre: storage[keccak(pad32(caller) ++ pad32(0))] is wards[caller]. The symbolic proof keeps keccak uninterpreted and needs no injectivity (nothing is written before the revert, so no two keys are compared). The claim-04 pre_witness evaluates keccak concretely (plugin) for caller 0x...dEaD and its wards slot was read from the chain at the slot cast computes (claim-04-config.json chain_slot_checks)",
              "risk_if_false": "if KEVM's keccak or the assumed layout differed from mainnet, claim-04's Pre would constrain a slot other than wards[caller], and the claim would not say that non-wards cannot cage()"}
             if forms.get("claim-04") == "cagews" else
             {"id": "A_keccak", "name": "keccak256 (KEVM's uninterpreted keccak)", "status": "not_relied_on",
              "note": "claim-04 reads wards[caller] from EMPTY storage, which is 0 whatever the key; no other claim hashes",
              "risk_if_false": "none for these claims"}),
            {"id": "Aasm-01", "name": "storage words are 256-bit", "status": "assumption", "covers": ["Aasm-rangeUInt-storage"],
             "justification": ann("Aasm-rangeUInt-storage")["justification"],
             "risk_if_false": "none on a real EVM (SSTORE cannot write more than 256 bits); if KEVM storage could hold a larger Int, the getter claims would cover only states satisfying the bound"},
            {"id": "Aasm-02", "name": "addresses are 160-bit", "status": "assumption", "covers": ["Aasm-address-range"],
             "justification": ann("Aasm-address-range")["justification"],
             "risk_if_false": "none on a real EVM; the claims say nothing about a configuration with a wider id/caller"},
            {"id": "Aasm-03", "name": "gas not modelled: claims hold for executions that do not run out of gas", "status": "assumption", "covers": ["Aasm-gas-abstraction"],
             "justification": ann("Aasm-gas-abstraction")["justification"],
             "risk_if_false": "a call with too little gas halts EVMC_OUT_OF_GAS, outside every claim (claims 01-03 say SUCCESS, 04-05 say REVERT); termination within a gas limit is not claimed"},
            {"id": "Aasm-04", "name": "top-level, non-static, zero-value call", "status": "assumption", "covers": ["Aasm-toplevel-call"],
             "justification": ann("Aasm-toplevel-call")["justification"],
             "risk_if_false": "a call with value, a STATICCALL, or a DELEGATECALL into GemJoin's code is outside every claim"},
        ] + ([{"id": "Aasm-05", "name": "ABI argument words are 256-bit", "status": "assumption", "covers": ["Aasm-rangeUInt-args"],
               "justification": ann("Aasm-rangeUInt-args")["justification"],
               "risk_if_false": "none on a real EVM: a 32-byte calldata word cannot hold a larger value"}]
             if any(x["id"] == "Aasm-rangeUInt-args" for x in anns) else []) + [
            {"id": "A_checker_build", "name": "image build purity", "status": "assumption",
             "note": "the image kompiles the same K source tree as the laptop's kevm-1.0.678-lemmas2 (diff -rq identical, pilot/checker/STATUS.md) but with RV's Ubuntu K build instead of the nix build; patch was installed from an unpinned apt mirror if missing (pilot/checker/STATUS.md open problem 3)",
             "risk_if_false": "the image's prover could differ in behaviour from the laptop toolchain that produced Findings 0003/0003b; mitigated only empirically (WS-C smoke reproduces the getter Accepts)"},
        ],
        "pre_witness": {
            "claims": wit_claims,
            "config": {c: json.loads((wit_dir / f"{c}-config.json").read_text()) for c in wit_claims},
            "replay": f"cd {wit_dir.relative_to(bundle)} && sh replay.sh  (run from its own directory; needs docker + the pinned image, takes prover slots on the VM; prints one normalised verdict line per module; exit 0 iff each *-instance Accepts and each *-vacuity does not; stdout sha256 in expected.json)",
            "semantics": "the pinned KEVM image (same as every claim)",
            "files": wit_files,
            "reachability": {c: next((x["quantifies_over"]["reachability"] for x in phi["claims"] if x["id"] == c), None) for c in wit_claims},
            "location_note": "evidence/pre_witness/ is a byte-identical copy (ledger seq 69) of provenance/rebuild/pre_witness/, where the witnesses were generated (seq 27-29) and first replayed (seq 63); the original is kept so those ledger events stay replayable",
        },
        "claims_without_certificate": [
            {"claim": c, "reason": "K prover emits no proof object; re-discharged by pinned prover"} for c in claim_ids],
        "hashed_objects": [{"path": p, "sha256": sha256_file(bundle / p)} for p in
                           ["hard/artifact.bin", "hard/annotations.json", "hard/spec/phi.json", "hard/spec/requirements.md",
                            "provenance/opscan.json", "provenance/kevm_osaka_adequacy.json", "provenance/chain_fetch.json", "provenance/rpc_probe.json"]],
    }
    (bundle / "trusted_base.json").write_text(json.dumps(tb, indent=2) + "\n")
    print(f"tbase: wrote trusted_base.json (fork {fork}, {len(tb['assumptions'])} assumptions, {len(claim_ids)} claims without certificate, witnesses {wit_claims})")
    return 0


# --------------------------------------------------------------------------- rehash
def _docker(image: str, *cmd: str) -> str:
    # not a prover run (sha256sum only), but bounded like one (VM rule)
    r = subprocess.run(["docker", "run", "--rm", "--network", "none", "--memory=1g", "--cpus=1", image, *cmd],
                       capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"docker run {' '.join(cmd)}: {r.stderr.strip()[:300]}")
    return r.stdout


def cmd_rehash(a: argparse.Namespace) -> int:
    """Recompute every hash that trusted_base.json, hard/spec/phi.json and
    hard/certs/*.rediscuss.json state, from the referenced object, and compare.
    Sources: bundle files (sha256 / keccak), the chain at the pinned block via
    --rpc (eth_getCode -> keccak), the checker image (docker image inspect Id,
    sha256sum inside the image). Exit 1 on any mismatch or anything that could
    not be recomputed (an unrecomputable hash is a failure, not a pass)."""
    bundle = pathlib.Path(a.bundle)
    tb = json.loads((bundle / "trusted_base.json").read_text())
    ok_rows: list[str] = []
    bad: list[str] = []

    def check(label: str, stated: str, got: str | None) -> None:
        if got is None:
            bad.append(f"{label}: could not recompute (stated {stated})")
        elif stated.lower() != got.lower():
            bad.append(f"{label}: stated {stated} != recomputed {got}")
        else:
            ok_rows.append(f"{label}: {got}")

    # identity
    ident = tb["identity"]
    art = (bundle / "hard/artifact.bin").read_bytes()
    check("identity.value vs keccak(hard/artifact.bin)", ident["value"], "0x" + keccak256_hex(art).removeprefix("0x"))
    for url in a.rpc:
        try:
            code = cast("code", ident["address"], "--block", str(ident["block"]), "--rpc-url", url)
            check(f"identity.value vs chain [{url}]", ident["value"], cast("keccak", code))
            blk = json.loads(cast("block", str(ident["block"]), "--json", "--rpc-url", url))
            blk = blk.get("data", blk)
            check(f"environment.block_hash vs chain [{url}]", tb["environment"]["block_hash"], blk.get("hash"))
            for e in tb["environment"]["external_code"]:
                code = cast("code", e["address"], "--block", str(ident["block"]), "--rpc-url", url)
                check(f"external_code {e['name']} vs chain [{url}]", e["code_hash"], cast("keccak", code))
        except Exception as ex:
            bad.append(f"chain [{url}]: {ex}")

    # checker image + semantics inside it
    kp = next(c for c in tb["checker"] if c["name"] == "kevm-prove")
    image = kp["hash"]
    try:
        got_id = subprocess.run(["docker", "image", "inspect", "--format", "{{.Id}}", image],
                                capture_output=True, text=True, timeout=60).stdout.strip() or None
        check("checker kevm-prove image Id", image, got_id)
        inside = {}
        for line in _docker(image, "sh", "-c",
                            "sha256sum /opt/kevm/inputs/* /opt/kevm/haskell/definition.kore "
                            "/opt/kevm/MANIFEST.sha256").splitlines():
            h, p = line.split(None, 1)
            inside[p.strip()] = h
        sem = next(s for s in tb["semantics"] if s["name"] == "KEVM")
        check("semantics KEVM hash (evm-semantics tarball in image)", sem["hash"],
              inside.get("/opt/kevm/inputs/evm-semantics.tar.gz"))
        check("semantics KEVM plugin tarball", sem["plugin"]["tarball_sha256"],
              inside.get("/opt/kevm/inputs/blockchain-k-plugin.tar.gz"))
        for p in sem["patches"]:
            check(f"semantics patch {p['name']} (in image)", p["sha256"], inside.get(f"/opt/kevm/inputs/{p['name']}"))
            if p.get("repo_path"):
                check(f"semantics patch {p['name']} (repo copy)", p["sha256"], sha256_file(REPO / p["repo_path"]))
        check("semantics KEVM definition.kore", sem["kompiled_definition"]["definition_kore_sha256"],
              inside.get("/opt/kevm/haskell/definition.kore"))
        check("checker in-image MANIFEST.sha256", kp["in_image_manifest_sha256"], inside.get("/opt/kevm/MANIFEST.sha256"))
    except Exception as ex:
        bad.append(f"checker image: {ex}")

    # verifier hash (WS-A's own definition of it)
    ver = next((c for c in tb["checker"] if c["name"] == "tcg-verifier"), None)
    if ver:
        try:
            sys.path.insert(0, str(REPO / "pilot/verifier"))
            from tcgverify.ladder import verifier_hash
            check("checker tcg-verifier (tcgverify.ladder.verifier_hash)", ver["hash"], verifier_hash())
        except Exception as ex:
            bad.append(f"tcg-verifier hash: {ex}")

    # phi.json -> claim files; certs -> claim files; pre_witness files
    phi = json.loads((bundle / "hard/spec/phi.json").read_text())
    for c in phi["claims"]:
        check(f"phi.json {c['id']} -> {c['file']}", c["sha256"], sha256_file(bundle / c["file"]))
    for cert in sorted((bundle / "hard/certs").glob("*.rediscuss.json")):
        d = json.loads(cert.read_text())
        m = re.search(r"claim_file_sha256=([0-9a-f]{64})", d.get("note", ""))
        check(f"{cert.name} claim_file_sha256", m.group(1) if m else "<absent>", sha256_file(bundle / d["claim_file"]))
        check(f"{cert.name} semantics_hash = definition.kore", d.get("semantics_hash", "<absent>"),
              next(s for s in tb["semantics"] if s["name"] == "KEVM")["kompiled_definition"]["definition_kore_sha256"])
    pw = tb.get("pre_witness", {})
    for rel, h in (pw.get("files") or {}).items():
        check(f"pre_witness file {rel}", h, sha256_file(bundle / rel) if (bundle / rel).is_file() else None)
    for e in tb.get("hashed_objects", []):
        check(f"hashed_objects {e['path']}", e["sha256"], sha256_file(bundle / e["path"]) if (bundle / e["path"]).is_file() else None)

    for r in ok_rows:
        print("rehash: ok   " + r)
    for r in bad:
        print("rehash: FAIL " + r)
    print(f"rehash: {'OK' if not bad else 'FAILED'} ({len(ok_rows)} recomputed, {len(bad)} failures)")
    return 0 if not bad else 1


# --------------------------------------------------------------------------- witness
def cmd_witness(a: argparse.Namespace) -> int:
    """Concrete Pre witness: substitute concrete values for a claim's free
    variables (STORAGE, ACCTID, MSGSENDER) and emit two modules:
      <name>-instance.k  the claim at that concrete state  (expected: Accept)
      <name>-vacuity.k   the same with `ensures false`     (expected: NOT Accept;
                         if it proved, the concrete state would violate Pre)
    Storage comes from the RPC probe record (eth_getStorageAt at the pinned
    block), optionally overridden slot by slot (--set SLOT=VALUE)."""
    from tcg.claims import assemble_prove_module, canonicalize, falsify_body
    probe = json.loads(pathlib.Path(a.probe).read_text())
    storage = {int(k): int(v, 16) for k, v in probe["storage_at_pinned_block"].items()}
    for kv in a.set or []:
        k, v = kv.split("=", 1)
        storage[int(k, 0)] = int(v, 0)
    nonzero = {k: v for k, v in sorted(storage.items()) if v != 0}
    kmap = " ".join(f"( {k} |-> {v} )" for k, v in nonzero.items()) or ".Map"
    raw = pathlib.Path(a.claim).read_text()
    body = _module_body(raw) if re.search(r"^module ", raw, flags=re.M) else canonicalize(raw)
    if a.schedule:
        body = body.replace("<schedule> SHANGHAI </schedule>", f"<schedule> {a.schedule} </schedule>")
    acct, caller = int(a.acct, 16), int(a.caller, 16)
    subs = [("STORAGE:Map", f"( {kmap} )"), ("ACCTID:Int", str(acct)), ("MSGSENDER:Int", str(caller))]
    for old, new in subs:
        if old not in body:
            print(f"witness: {old} not in {a.claim}", file=sys.stderr)
            return 2
        body = body.replace(old, new)
    body = re.sub(r"\bSTORAGE\b", f"( {kmap} )", body)
    body = re.sub(r"\bACCTID\b", str(acct), body)
    body = re.sub(r"\bMSGSENDER\b", str(caller), body)
    for kv in a.subst or []:  # further free variables of the claim (e.g. USR, WAD)
        k, v = kv.split("=", 1)
        if not re.search(rf"\b{k}\b", body):
            print(f"witness: --subst {k} not in {a.claim}", file=sys.stderr)
            return 2
        body = re.sub(rf"\b{k}:Int\b", str(int(v, 0)), body)
        body = re.sub(rf"\b{k}\b", str(int(v, 0)), body)
    # chain check of extra slots the execution reads (e.g. wards[caller]):
    # the concrete map must agree with eth_getStorageAt at the pinned block.
    slot_checks = []
    for s in a.verify_slot or []:
        want = storage.get(int(s, 0), 0)
        got = {}
        for url in a.rpc or []:
            try:
                got[url] = int(cast("storage", GEMJOIN, s, "--block", str(probe["pinned_block"]), "--rpc-url", url), 16)
            except Exception as ex:
                got[url] = f"error: {str(ex)[:120]}"
        ok = [u for u, v in got.items() if v == want]
        slot_checks.append({"slot": s, "map_value": hex(want), "chain": {u: (hex(v) if isinstance(v, int) else v) for u, v in got.items()},
                            "agree": len(ok)})
        if not ok or any(isinstance(v, int) and v != want for v in got.values()):
            print(f"witness: slot {s} map value {want} disagrees with chain {got}", file=sys.stderr)
            return 3
    if re.search(r"\b[A-Z][A-Z0-9_]*:Int\b", body):
        print("witness: free Int variables remain: " + ", ".join(sorted(set(re.findall(r"\b([A-Z][A-Z0-9_]*):Int\b", body)))),
              file=sys.stderr)
        return 2
    out = pathlib.Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = a.name.upper().replace("_", "-")
    (out / f"{a.name}-instance.k").write_text(
        assemble_prove_module(f"{stem}-INSTANCE", ["edsl.md"], ["EDSL"], [], [body]))
    (out / f"{a.name}-vacuity.k").write_text(
        assemble_prove_module(f"{stem}-VACUITY", ["edsl.md"], ["EDSL"], [], [falsify_body(body)]))
    cfg = {"claim_source": a.claim, "schedule": a.schedule or "as in claim source", "acct_id": a.acct, "caller": a.caller,
           "storage_nonzero": {str(k): hex(v) for k, v in nonzero.items()},
           "storage_source": f"{a.probe} (eth_getStorageAt, block {probe['pinned_block']})",
           "overrides": a.set or [], "subst": a.subst or [], "chain_slot_checks": slot_checks,
           "unlisted_slots": "every slot not in storage_nonzero is 0 in this map; on chain other slots (e.g. other wards entries) may be non-zero. Only slots the execution reads matter for the instance: 0-5 (probe) and any listed in chain_slot_checks"}
    (out / f"{a.name}-config.json").write_text(json.dumps(cfg, indent=2) + "\n")
    print(json.dumps(cfg, indent=1))
    return 0


# --------------------------------------------------------------------------- closure
_K_BLOCK_START = re.compile(r'^\s*(rule|syntax|module|endmodule|imports|claim|context|configuration)\b|^\s*(requires)\s+"')


def _strip_k_comments(t: str) -> str:
    t = re.sub(r"/\*.*?\*/", "", t, flags=re.S)
    return re.sub(r"//[^\n]*", "", t)


def _rule_blocks(t: str) -> list[str]:
    blocks, cur = [], None
    for line in _strip_k_comments(t).splitlines():
        m = _K_BLOCK_START.match(line)
        if m:
            if cur is not None:
                blocks.append(cur)
            cur = line if m.group(1) == "rule" else None  # group(2): file-level requires "..."
        elif cur is not None:
            cur += "\n" + line
    if cur is not None:
        blocks.append(cur)
    return blocks


def _requires_conjuncts(claim_text: str) -> list[str]:
    m = re.search(r"\brequires\b(.*?)(?=\bensures\b|\[label)", claim_text.split("claim", 1)[-1], flags=re.S)
    if not m:
        return []
    return [" ".join(c.split()) for c in re.split(r"\bandBool\b", m.group(1)) if c.strip()]


def cmd_closure(a: argparse.Namespace) -> int:
    """Annotation closure (task 02 'a'). Fails (exit 1) on any of:
      - a module imported by lemmas-driver.k (other than EDSL) with no
        simplification_lemma_family annotation, or an annotation for a module
        the driver does not import;
      - a lemma/source file whose sha256 differs from the annotation;
      - a rule in a listed lemma family without the [simplification]
        attribute (that would be a semantic rewrite, not a lemma);
      - a `requires` conjunct of a claim matched by no annotation pattern and
        not declared as Pre scope for that claim in phi.json;
      - a configuration abstraction present in a claim with no annotation;
      - an annotation whose patterns match a claim set different from used_by;
      - a claim module carrying `trusted`, a rule, or more than one claim;
      - a .lean file under hard/certs (none expected under variant A) whose
        axiom / sorry names are not annotated.
    Prints every problem; judges no verification verdict."""
    bundle = pathlib.Path(a.bundle)
    ksrc = pathlib.Path(a.k_src)
    ann_doc = json.loads((bundle / "hard/annotations.json").read_text())
    anns = ann_doc["annotations"]
    phi = json.loads((bundle / "hard/spec/phi.json").read_text()) if (bundle / "hard/spec/phi.json").is_file() else None
    probs: list[str] = []
    info: list[str] = []

    # 1. driver imports <-> lemma-family annotations
    drv = ksrc / "lemmas-driver.k"
    want = ann_doc["definition_driver"]["sha256"]
    if sha256_file(drv) != want:
        probs.append(f"lemmas-driver.k sha256 {sha256_file(drv)} != annotations {want}")
    imported = set(re.findall(r"^\s*imports\s+([A-Z0-9-]+)", _strip_k_comments(drv.read_text()), flags=re.M)) - {"EDSL"}
    fams = {x["k_source"]["module"]: x for x in anns if x.get("kind") == "simplification_lemma_family"}
    for mod in sorted(imported - set(fams)):
        probs.append(f"driver imports {mod} but no annotation lists it")
    for mod in sorted(set(fams) - imported):
        probs.append(f"annotation {fams[mod]['id']} lists {mod}, which the driver does not import")

    # 2. source hashes + every rule is [simplification]
    for x in anns:
        srcs = x.get("k_source")
        for s in (srcs if isinstance(srcs, list) else [srcs] if srcs else []):
            f = ksrc / s["file"].removeprefix("/opt/kevm/evm-semantics-source/")
            if not f.is_file():
                probs.append(f"{x['id']}: source {s['file']} missing")
                continue
            if sha256_file(f) != s["sha256"]:
                probs.append(f"{x['id']}: {s['file']} sha256 {sha256_file(f)} != {s['sha256']}")
            if not re.search(rf"^\s*module\s+{re.escape(s['module'])}\b", f.read_text(), flags=re.M):
                probs.append(f"{x['id']}: module {s['module']} not defined in {s['file']}")
            if x.get("kind") == "simplification_lemma_family":
                blocks = _rule_blocks(f.read_text())
                bad = [b.splitlines()[0].strip()[:90] for b in blocks
                       if not re.search(r"\[[^\[\]]*\bsimplification\b[^\[\]]*\]\s*$", b.strip(), flags=re.S)]
                info.append(f"{x['id']}: {len(blocks)} rules in {s['file']}, non-[simplification]: {len(bad)}")
                probs += [f"{x['id']}: rule without [simplification]: {b}" for b in bad]

    # 3. claims: requires conjuncts + configuration abstractions
    claims = sorted((bundle / "hard/spec").glob("claim-*.k"))
    if not claims:
        probs.append("no hard/spec/claim-*.k files")
    scope = {}
    if phi:
        for c in phi.get("claims", []):
            scope[c["id"]] = [" ".join(s.split()) for s in c.get("pre_scope_k", [])]
    matched: dict[str, set] = {x["id"]: set() for x in anns if x.get("k_patterns")}
    for cf in claims:
        cid = cf.stem
        t = cf.read_text()
        if len(re.findall(r"^\s*claim\b", t, flags=re.M)) != 1:
            probs.append(f"{cid}: expected exactly one claim")
        if re.search(r"\btrusted\b", t) or re.search(r"^\s*rule\b", t, flags=re.M):
            probs.append(f"{cid}: spec module carries a trusted claim or a rule")
        if set(re.findall(r"^\s*imports\s+([A-Z0-9-]+)", t, flags=re.M)) != {"EDSL"}:
            probs.append(f"{cid}: imports other than EDSL")
        for conj in _requires_conjuncts(t):
            hit = [x["id"] for x in anns
                   if any(re.fullmatch(p, conj) for p in x.get("k_patterns", {}).get("requires", []))]
            for h in hit:
                matched[h].add(cid)
            if not hit and conj not in scope.get(cid, []):
                probs.append(f"{cid}: requires conjunct `{conj}` is neither an annotation nor declared Pre scope")
            elif not hit and "keccak(" in conj:
                # Pre scope is not enough here: what a keccak-keyed slot MEANS
                # (Keccak-256 + the compiler's storage layout) is an assumption.
                probs.append(f"{cid}: requires conjunct `{conj}` uses keccak but no annotation covers it")
        for x in anns:
            for p in x.get("k_patterns", {}).get("config", []):
                if re.search(p, t):
                    matched[x["id"]].add(cid)
        for cfg, label in ((r"<useGas> false </useGas>", "gas off"), (r"<callStack> \.List </callStack>", "top-level frame")):
            if re.search(cfg, t) and not any(cid in matched[k] for k in matched
                                             if any(q == cfg for q in next(x for x in anns if x["id"] == k)["k_patterns"].get("config", []))):
                probs.append(f"{cid}: configuration abstraction ({label}) not annotated")
    for x in anns:
        if x.get("k_patterns") and claims:
            if matched[x["id"]] != set(x["used_by"]):
                probs.append(f"{x['id']}: patterns match {sorted(matched[x['id']])} but used_by says {sorted(x['used_by'])}")

    # 4. Lean (variant A: none expected)
    ann_ids = {x["id"] for x in anns}
    for lf in sorted((bundle / "hard/certs").rglob("*.lean")):
        for kind, name in re.findall(r"^\s*(axiom|sorry)\s*([A-Za-z0-9_.']*)", lf.read_text(), flags=re.M):
            if name not in ann_ids:
                probs.append(f"{lf}: {kind} {name} not annotated")

    for line in info:
        print("closure: " + line)
    for p in probs:
        print("closure: FAIL " + p)
    print(f"closure: {'OK' if not probs else 'FAILED'} ({len(anns)} annotations, {len(claims)} claims, {len(probs)} problems)")
    return 0 if not probs else 1


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("chain")
    c.add_argument("--block", required=True)
    c.add_argument("--rpc", action="append", required=True)
    c.add_argument("--artifact", required=True, help="where to write b (raw runtime bytes)")
    c.add_argument("--record", required=True, help="where to write the fetch record (JSON)")
    c.set_defaults(fn=cmd_chain)
    c = sub.add_parser("probe")
    c.add_argument("--block", required=True)
    c.add_argument("--old-block", default="25782890")
    c.add_argument("--rpc", action="append", required=True)
    c.add_argument("--record", required=True)
    c.set_defaults(fn=cmd_probe)
    c = sub.add_parser("spec")
    c.add_argument("--claim", required=True)
    c.add_argument("--loop", required=True)
    c.add_argument("--label", required=True)
    c.add_argument("--mode", choices=["prove", "vacuity", "discriminator"], default="prove")
    c.add_argument("--schedule", default=None,
                   help="replace the claim's <schedule> SHANGHAI </schedule> by this KEVM schedule")
    c.add_argument("--out", required=True)
    c.set_defaults(fn=cmd_spec)
    c = sub.add_parser("variant")
    c.add_argument("--src", required=True, help="assembled <n>-<n>-prove.k module to derive from")
    c.add_argument("--label", required=True)
    c.add_argument("--storage-symbolic", action="store_true")
    c.add_argument("--calldata", default=None)
    c.add_argument("--requires", action="append")
    c.add_argument("--schedule", default=None)
    c.add_argument("--out-dir", required=True)
    c.set_defaults(fn=cmd_variant)
    c = sub.add_parser("opscan")
    c.add_argument("--artifact", required=True)
    c.add_argument("--out", required=True)
    c.set_defaults(fn=cmd_opscan)
    c = sub.add_parser("osaka-evidence")
    c.add_argument("--tarball", required=True, help="evm-semantics.tar.gz copied out of the pinned image (/opt/kevm/inputs)")
    c.add_argument("--out", required=True)
    c.set_defaults(fn=cmd_osaka_evidence)
    c = sub.add_parser("hardspec")
    c.add_argument("--bundle", default=str(REPO / "pilot/bundle"))
    c.add_argument("--controls", required=True, help="dir with <n>-<n>-prove.k assembled modules")
    c.add_argument("--results", required=True, nargs="+", help="results TSV(s) from run-controls.sh")
    c.add_argument("--schedule", required=True)
    c.add_argument("--claim04", choices=["cagews", "cage"], required=True, help="which cage form ships as claim-04")
    c.add_argument("--claim05", choices=["joinsym", "join"], required=True, help="which join form ships as claim-05")
    c.add_argument("--pins", default=str(pathlib.Path.home() / "pilot-checker/pins.json"))
    c.set_defaults(fn=cmd_hardspec)
    c = sub.add_parser("tbase")
    c.add_argument("--bundle", default=str(REPO / "pilot/bundle"))
    c.add_argument("--schedule", required=True)
    c.add_argument("--witness-dir", required=True)
    c.add_argument("--pins", default=str(pathlib.Path.home() / "pilot-checker/pins.json"))
    c.set_defaults(fn=cmd_tbase)
    c = sub.add_parser("rehash")
    c.add_argument("--bundle", default=str(REPO / "pilot/bundle"))
    c.add_argument("--rpc", action="append", default=[], help="archive-capable RPC(s) for the chain checks")
    c.set_defaults(fn=cmd_rehash)
    c = sub.add_parser("witness")
    c.add_argument("--claim", required=True)
    c.add_argument("--probe", required=True)
    c.add_argument("--acct", default=GEMJOIN)
    c.add_argument("--caller", required=True)
    c.add_argument("--set", action="append", help="storage override SLOT=VALUE")
    c.add_argument("--subst", action="append", help="concrete value for a further free variable NAME=VALUE")
    c.add_argument("--verify-slot", action="append", help="slot (hex) whose chain value must equal the map value")
    c.add_argument("--rpc", action="append", help="archive RPC(s) for --verify-slot")
    c.add_argument("--schedule", default=None)
    c.add_argument("--name", required=True)
    c.add_argument("--out-dir", required=True)
    c.set_defaults(fn=cmd_witness)
    c = sub.add_parser("closure")
    c.add_argument("--bundle", default=str(REPO / "pilot/bundle"))
    c.add_argument("--k-src", required=True,
                   help="extracted /opt/kevm/evm-semantics-source of the pinned image (see HARD_STATUS.md)")
    c.set_defaults(fn=cmd_closure)
    a = p.parse_args()
    return a.fn(a)


if __name__ == "__main__":
    sys.exit(main())
