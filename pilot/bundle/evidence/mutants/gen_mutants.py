#!/usr/bin/env python3
"""Generate the mutant-witness directories for claims 01-03 (task 04 section 3).

Deterministic and stdlib-only. Run from the bundle root:
    python3 evidence/mutants/gen_mutants.py [--claims-dir provenance/rebuild/controls-osaka]

For each witness it writes evidence/mutants/<name>/:
  mutant.bin           hard/artifact.bin with the listed byte edits (asserted old bytes)
  mutation.json        the edits, the source claim file + its sha256, the concrete state
  replay.sh            one command, `sh replay.sh` (rules: pilot/tools/mutant_witness.py)
  concrete-trace witnesses (<name> = claim-0N[-tag]):
    witness-original.k   the shipped claim made fully concrete (state sigma), program =
                         hard/artifact.bin, ensures unchanged     -> control, must Accept
    witness-mutant.k     same concrete state, program = mutant.bin, ensures
                         ?OUT ==K #buf(32, X) andBool ?OUT =/=K <claim RHS on sigma>
                         -> Accept (#Top) = the mutant's concrete run returns X, and X
                         differs from what the claim requires on that state
    witness-negative.k   same concrete state, program = mutant.bin, ensures unchanged
                         (the claim itself instantiated at sigma) -> must NOT Accept.
                         Guards against a vacuous concrete harness: if sigma's requires
                         were somehow false, every concrete claim would Accept.
  symbolic witnesses (<name> = claim-0N[-tag]-symbolic):
    claim.k              the shipped claim verbatim except <program>/<jumpDests> = mutant.bin

Semantics for every run: KEVM (evm-semantics d4bf484a + ghost + lemmas2) under kprove
in the pinned checker image (pilot/checker/STATUS.md). Concrete runs are kprove on a
claim whose pre-state is fully concrete, i.e. a single concrete execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re

IMAGE = "sha256:7d4a35bc05dfdad97b244da3c75bb3c3e710be73713cac3ca1c5bb6226cdc465"
ART_SHA256 = "c5f9e8e8da82f5ee5b74608bf05c818537174be13ea0bc00ce15d5fe55e2bd27"
MASK160 = (1 << 160) - 1

# Concrete state sigma_pin: GemJoin storage at block 26298481 (provenance/rpc_probe.json,
# 4 RPCs agree), id = GemJoin, caller = an arbitrary EOA (getters do not read caller).
GEMJOIN = 0x2F0b23f53734252Bda2277357e97e1517d6B042A
CALLER = 0x00000000000000000000000000000000C0FFEE01
PIN = {0: 0, 1: 0x35d1b3f3d7966a1dfe207aa4514c12a259a0492b,
       2: 0x4554482d41000000000000000000000000000000000000000000000000000000,
       3: 0xc02aaa39b223fe8d0a0e5c4f27ead9083c756cc2, 4: 18, 5: 1}
# sigma_hi: synthetic, slot 1 holds a word with bits above 160 set. NOT a state any real
# GemJoin reaches (slot 1 is `VatLike public vat`, only ever written with an address).
HI = {**PIN, 1: (0xA5 << 248) | PIN[1]}

READ = {"vat": 1, "ilk": 2, "gem": 3}
MASKED = {"vat": True, "ilk": False, "gem": True}

WITNESSES = [
    # name, claim id, getter, edits [(offset, old, new)], state, X (mutant output), why
    ("claim-01", "claim-01", "vat", [(0x324, 0x01, 0x02)], "pin",
     "vat() body PUSH1 0x01 -> PUSH1 0x02 at 0x324: SLOAD reads slot 2 (ilk) instead of slot 1 (vat)"),
    ("claim-01-mask", "claim-01", "vat", [(0x345, 0x16, 0x50), (0xd1, 0x16, 0x50), (0xe7, 0x16, 0x50)], "hi",
     "vat() 160-bit masks dropped: AND -> POP at 0x345 (getter body) and 0xd1, 0xe7 (vat's ABI formatter)"),
    ("claim-02", "claim-02", "ilk", [(0xa5c, 0x02, 0x03)], "pin",
     "ilk() body PUSH1 0x02 -> PUSH1 0x03 at 0xa5c: SLOAD reads slot 3 (gem) instead of slot 2 (ilk)"),
    ("claim-03", "claim-03", "gem", [(0x8e4, 0x03, 0x01)], "pin",
     "gem() body PUSH1 0x03 -> PUSH1 0x01 at 0x8e4: SLOAD reads slot 1 (vat) instead of slot 3 (gem)"),
]


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def mutate(art: bytes, edits) -> bytes:
    b = bytearray(art)
    for off, old, new in edits:
        assert b[off] == old, f"byte at {off:#x} is {b[off]:#04x}, expected {old:#04x}"
        b[off] = new
    return bytes(b)


def mutant_output(getter: str, edits, state: dict) -> int:
    """What the mutant returns on `state`, derived from the edit (checked by kprove)."""
    if getter == "vat" and edits[0][0] == 0x324:
        return state[2] & MASK160          # still masked, wrong slot
    if getter == "vat":
        return state[1]                    # masks dropped
    if getter == "ilk":
        return state[3]                    # unmasked getter, wrong slot
    if getter == "gem":
        return state[1] & MASK160
    raise AssertionError(getter)


def claim_rhs(getter: str, state: dict) -> int:
    v = state[READ[getter]]
    return v & MASK160 if MASKED[getter] else v


def swap_program(text: str, art_hex: str, new_hex: str) -> str:
    progs = re.findall(r'#parseByteStack\("0x([0-9a-f]+)"\)', text)
    assert progs == [art_hex, art_hex], "claim's <program>/<jumpDests> are not hard/artifact.bin"
    return text.replace(f'"0x{art_hex}"', f'"0x{new_hex}"')


def rename_module(text: str, new: str) -> str:
    mods = re.findall(r"^module (\S+)$", text, re.M)
    assert len(mods) == 1, mods
    return re.sub(r"^module \S+$", f"module {new}", text, flags=re.M)


def concretize(text: str, state: dict) -> str:
    m = "( " + " ".join(f"{k} |-> {v}" for k, v in sorted(state.items())) + " )"
    for var, val in (("ACCTID", str(GEMJOIN)), ("MSGSENDER", str(CALLER)), ("STORAGE", m)):
        n = len(re.findall(rf"\b{var}\b", text))
        assert n >= 2, (var, n)
        text = re.sub(rf"\b{var}:(?:Int|Map)\b", val, text)
        text = re.sub(rf"\b{var}\b", val, text)
    return text


def relabel(text: str, suffix: str) -> str:
    assert len(re.findall(r"\[label\(([\w-]+)\)", text)) == 1
    return re.sub(r"\[label\(([\w-]+)\)", rf"[label(\1-{suffix})", text)


def violation_ensures(text: str, x: int) -> str:
    lines = [i for i, l in enumerate(text.splitlines()) if "?OUT ==K" in l]
    assert len(lines) == 1, "expected exactly one ?OUT ==K conjunct in the claim"
    ls = text.splitlines()
    l = ls[lines[0]]
    rhs = l.split("?OUT ==K", 1)[1].strip()
    indent = l[: len(l) - len(l.lstrip())]
    ls[lines[0]] = (f"{indent}andBool ?OUT ==K #buf(32, {x})\n"
                    f"{indent}andBool ?OUT =/=K {rhs}")
    return "\n".join(ls) + "\n"


SH_HEAD = """#!/bin/sh
# {name}: {kind_doc}
# Generated by evidence/mutants/gen_mutants.py; see mutation.json and STATUS.md.
# Semantics: KEVM in the pinned checker image {image}
# (kprove argv = pilot/checker/run-claim.sh's, inlined because this runs from a bundle copy).
# On the shared VM, hold a prover slot around the caller (do not lock in here).
set -u
IMG={image}
T=$(mktemp -d)
trap 'rm -rf "$T"' EXIT
kp() {{  # kp <claim file in this dir> <module>: kprove stdout -> $T/<module>.out, stderr -> .err
  docker run --rm --platform linux/amd64 --network none --memory=6g --cpus=2 \\
    --user "$(id -u):$(id -g)" -e HOME=/tmp -v "$PWD:/claim:ro" -w /tmp "$IMG" \\
    kprove "/claim/$1" --definition /opt/kevm/haskell \\
      -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin --spec-module "$2" \\
    >"$T/$2.out" 2>"$T/$2.err"
}}
"""

BIND = """python3 -I - "$@" <<'PY' || {{ echo "BINDING-CHECK-FAILED"; exit 3; }}
import re, sys
def hexof(p): return open(p, "rb").read().hex()
def progs(p): return re.findall(r'#parseByteStack\\("0x([0-9a-f]+)"\\)', open(p, encoding="utf-8").read())
art, mut = hexof("../../../hard/artifact.bin"), hexof("mutant.bin")
assert art != mut, "mutant.bin equals the artefact"
{checks}
PY
"""


def concrete_replay(name, claim_id, getter, why, x, y, mod_o, mod_m, mod_n) -> str:
    checks = ('assert progs("witness-original.k") == [art, art], "control claim not bound to hard/artifact.bin"\n'
              'assert progs("witness-mutant.k") == [mut, mut], "witness claim not bound to mutant.bin"\n'
              'assert progs("witness-negative.k") == [mut, mut], "negative control not bound to mutant.bin"')
    return (SH_HEAD.format(name=name, image=IMAGE,
                           kind_doc="concrete-trace witness (kind concrete_trace_violation)")
            + BIND.format(checks=checks) + f"""
kp witness-original.k {mod_o}; rc_o=$?
kp witness-mutant.k {mod_m}; rc_m=$?
kp witness-negative.k {mod_n}; rc_n=$?
acc() {{ [ "$1" -eq 0 ] && grep -q '#Top' "$T/$2.out"; }}
echo "claim: {claim_id} ({getter}())"
echo "mutation: {why}"
echo "state: concrete, see mutation.json"
if acc $rc_o {mod_o}; then echo "control: original artefact on this state satisfies the claim (kprove #Top)"; \\
  else echo "control: NOT accepted (exit $rc_o)"; fi
if acc $rc_m {mod_m}; then echo "witness: mutant on this state returns {x:#066x} (kprove #Top)"; \\
  else echo "witness: NOT accepted (exit $rc_m)"; fi
if acc $rc_n {mod_n}; then echo "negative control: the claim at this state on the mutant WAS accepted (harness not discriminating)"; \\
  else echo "negative control: the claim at this state on the mutant is not accepted"; fi
if acc $rc_o {mod_o} && acc $rc_m {mod_m} && ! acc $rc_n {mod_n}; then
  echo "TCG-VIOLATION: {claim_id} {getter}() mutant returns {x:#066x} where the claim requires {y:#066x} on the same concrete state"
  exit 0
fi
echo "NO-VIOLATION-SHOWN"
exit 1
""")


def symbolic_replay(name, mod) -> str:
    checks = 'assert progs("claim.k") == [mut, mut], "claim.k not bound to mutant.bin"'
    return (SH_HEAD.format(name=name, image=IMAGE,
                           kind_doc="the shipped claim, <program> = mutant.bin, judged by the KEVM verdict judge")
            + BIND.format(checks=checks) + f"""
kp claim.k {mod}; rc=$?
# stderr first (it carries kore-exec's stuck/refute message the judge reads), then
# stdout; kore-exec's per-run counter "[NNN]" is normalised so stdout is byte-stable.
sed -E 's/^kore-exec: \\[[0-9]+\\]/kore-exec: [N]/' "$T/{mod}.err"
cat "$T/{mod}.out"
exit $rc
""")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--claims-dir", default="provenance/rebuild/controls-osaka")
    a = ap.parse_args()
    art = open("hard/artifact.bin", "rb").read()
    assert sha(art) == ART_SHA256, "hard/artifact.bin is not the pinned artefact"
    for name, claim_id, getter, edits, state_name, why in WITNESSES:
        state = PIN if state_name == "pin" else HI
        src = os.path.join(a.claims_dir, f"{getter}-{getter}-prove.k")
        text = open(src, encoding="utf-8").read()
        mut = mutate(art, edits)
        x, y = mutant_output(getter, edits, state), claim_rhs(getter, state)
        assert x != y, f"{name}: mutant output equals the claim RHS on this state"
        base = name.upper().replace("-", "")
        mod_o, mod_m, mod_s = f"{base}-CONCRETE-ORIGINAL", f"{base}-CONCRETE-MUTANT", f"{base}-SYMBOLIC"
        mod_n = f"{base}-CONCRETE-NEGATIVE"
        meta = {"claim": claim_id, "getter": getter, "mutation": why,
                "edits": [{"offset": hex(o), "old": hex(p), "new": hex(n)} for o, p, n in edits],
                "artifact_sha256": ART_SHA256, "mutant_sha256": sha(mut),
                "source_claim": src, "source_claim_sha256": sha(text.encode()),
                "semantics": f"KEVM (evm-semantics d4bf484a + ghost.diff + lemmas2.diff) via kprove in {IMAGE}"}
        # concrete-trace witness
        d = os.path.join("evidence/mutants", name)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "mutant.bin"), "wb").write(mut)
        conc = concretize(text, state)
        open(os.path.join(d, "witness-original.k"), "w").write(
            relabel(rename_module(conc, mod_o), "concrete-original"))
        open(os.path.join(d, "witness-mutant.k"), "w").write(
            violation_ensures(relabel(rename_module(swap_program(conc, art.hex(), mut.hex()), mod_m),
                                      "concrete-mutant"), x))
        open(os.path.join(d, "witness-negative.k"), "w").write(
            relabel(rename_module(swap_program(conc, art.hex(), mut.hex()), mod_n), "concrete-negative"))
        st = {"id": hex(GEMJOIN), "caller": hex(CALLER),
              "storage": {str(k): f"{v:#066x}" for k, v in sorted(state.items())},
              "storage_source": ("GemJoin storage at block 26298481, provenance/rpc_probe.json"
                                 if state_name == "pin" else
                                 "SYNTHETIC: pinned storage with slot 1 = 0xa5 << 248 | Vat address; "
                                 "no real GemJoin reaches it (slot 1 is an address)")}
        json.dump(dict(meta, kind="concrete_trace_violation", state=st,
                       mutant_returns=f"{x:#066x}", claim_requires=f"{y:#066x}"),
                  open(os.path.join(d, "mutation.json"), "w"), indent=2)
        open(os.path.join(d, "replay.sh"), "w").write(
            concrete_replay(name, claim_id, getter, why, x, y, mod_o, mod_m, mod_n))
        # symbolic witness: the shipped claim, program swapped, module renamed
        ds = d + "-symbolic"
        os.makedirs(ds, exist_ok=True)
        open(os.path.join(ds, "mutant.bin"), "wb").write(mut)
        open(os.path.join(ds, "claim.k"), "w").write(rename_module(swap_program(text, art.hex(), mut.hex()), mod_s))
        json.dump(dict(meta, kind="decided by the judge at record time"),
                  open(os.path.join(ds, "mutation.json"), "w"), indent=2)
        open(os.path.join(ds, "replay.sh"), "w").write(symbolic_replay(ds.split("/")[-1], mod_s))
        print(f"{name}: x={x:#x} y={y:#x} mutant sha256 {sha(mut)}")




# ---------------------------------------------------------------------------
# Claims 04-05 (revert claims, shipped in hard/spec/). Added after 01-03 were
# recorded; `--only` regenerates just these so 01-03's recorded inputs stay
# byte-identical. These symbolic witnesses also bind claim.k to the SHIPPED
# hard/spec/claim-0N.k at replay time (program swapped + module renamed only).
VAT, WETH = PIN[1], PIN[3]
USR, WAD = 0x00000000000000000000000000000000000BEEF1, 10 ** 18
STOP_CODE = "0x00"                       # Vat stub: any call succeeds, no return data
TRUE_CODE = "0x600160005260206000f3"     # WETH stub: returns abi true (32 bytes, 1)

REVERT_WITNESSES = [
    # name, claim id, file, function, edits, storage, extra vars, extra accounts, why
    ("claim-04", "claim-04", "hard/spec/claim-04.k", "cage", [(0x833, 0x14, 0x17)], PIN, {}, [],
     "cage() auth check neutralised: EQ -> OR at 0x833, so wards[msg.sender] == 1 becomes "
     "1 | wards[msg.sender] (always non-zero) and the JUMPI past the revert is always taken"),
    ("claim-05", "claim-05", "hard/spec/claim-05.k", "join", [(0x34e, 0x14, 0x17)], {**PIN, 5: 0},
     {"USR": USR, "WAD": WAD}, [(VAT, STOP_CODE), (WETH, TRUE_CODE)],
     "join() live check neutralised: EQ -> OR at 0x34e, so live == 1 becomes 1 | live "
     "(always non-zero) and the JUMPI past the revert is always taken"),
]


def swap_program_rev(text: str, art_hex: str, new_hex: str, n_stubs: int) -> str:
    """Like swap_program; the first two #parseByteStack are <program>/<jumpDests>,
    any further ones are the harness stub accounts' code (short, distinct)."""
    progs = re.findall(r'#parseByteStack\("0x([0-9a-f]+)"\)', text)
    assert progs[:2] == [art_hex, art_hex] and len(progs) == 2 + n_stubs, "unexpected programs in claim"
    assert art_hex not in progs[2:]
    return text.replace(f'"0x{art_hex}"', f'"0x{new_hex}"')


def concretize_rev(text: str, state: dict, extra: dict, accounts) -> str:
    text = concretize(text, state)
    for var, val in extra.items():
        assert len(re.findall(rf"\b{var}\b", text)) >= 2, var
        text = re.sub(rf"\b{var}:Int\b", str(val), text)
        text = re.sub(rf"\b{var}\b", str(val), text)
    # Pin <callDepth> 0 (Pre leaves it free in the <callState> frame; a symbolic
    # depth makes CALL branch on depth >= 1024 and fail on that branch).
    sf = "<static> false </static>"
    assert text.count(sf) == 1
    i = text.index(sf)
    ind = text[text.rindex("\n", 0, i) + 1: i]
    text = text.replace(sf, sf + "\n" + ind + "<callDepth> 0 </callDepth>")
    # GemJoin's own balance/nonce made concrete (Pre leaves them free), so a
    # value-0 CALL cannot branch on a symbolic balance.
    st = "<storage> ( "
    assert text.count(st) == 1
    i = text.index(st)
    ind = text[text.rindex("\n", 0, i) + 1: i]
    text = text[:i] + "<balance> 0 </balance>\n" + ind + "<nonce> 1 </nonce>\n" + ind + text[i:]
    if accounts:
        close = "            </account>\n"
        assert text.count(close) == 1
        acc = "".join(
            "            <account>\n"
            f"              <acctID> {a} </acctID>\n"
            "              <balance> 0 </balance>\n"
            f"              <code> #parseByteStack(\"{c}\") </code>\n"
            "              <storage> .Map </storage>\n"
            "              <origStorage> .Map </origStorage>\n"
            "              <transientStorage> .Map </transientStorage>\n"
            "              <nonce> 1 </nonce>\n"
            "            </account>\n" for a, c in accounts)
        text = text.replace(close, close + acc)
    return text


def success_ensures(text: str) -> str:
    """Witness form: the mutant halts with EVMC_SUCCESS. The success path writes
    storage (cage: live := 0), emits LogNote and warms accounts, so the witness
    abstracts GemJoin's <storage>, <touchedAccounts>, the whole <substate> (Finding 0006 correction:
    abstract <log> when the path logs) and ghost.diff's <callCounter>/<inFunc>, which
    every CALL bumps. It asserts nothing but the status code."""
    old = "ensures ?SC ==K EVMC_REVERT"
    assert text.count(old) == 1
    text = text.replace(old, "ensures ?SC ==K EVMC_SUCCESS")
    m = re.findall(r"<storage> (\( [^)]* \)) </storage>", text)
    assert len(m) == 1
    text = text.replace(f"<storage> {m[0]} </storage>", f"<storage> {m[0]} => ?_ </storage>")
    cs = "          </callState>\n"
    assert text.count(cs) == 1
    text = text.replace(cs, cs + "          <substate> _ => ?_ </substate>\n")
    # <touchedAccounts> (in <evm>) also grows on CALL
    cst = "          <callStack> .List </callStack>\n"
    assert text.count(cst) == 1
    text = text.replace(cst, cst + "          <touchedAccounts> _ => ?_ </touchedAccounts>\n")
    # ghost.diff's instrumentation cells (top level of <kevm>) change on every CALL
    ug = "      <useGas> false </useGas>\n"
    assert text.count(ug) == 1
    return text.replace(ug, ug + "      <callCounter> _ => ?_ </callCounter>\n"
                                 "      <inFunc> _ => ?_ </inFunc>\n")


def revert_concrete_replay(name, claim_id, fn, why, mod_o, mod_m, mod_n, n_stubs) -> str:
    n = 2 + n_stubs
    checks = (f'assert progs("witness-original.k")[:2] == [art, art] and len(progs("witness-original.k")) == {n}, "control claim not bound to hard/artifact.bin"\n'
              f'assert progs("witness-mutant.k")[:2] == [mut, mut] and len(progs("witness-mutant.k")) == {n}, "witness claim not bound to mutant.bin"\n'
              f'assert progs("witness-negative.k")[:2] == [mut, mut] and len(progs("witness-negative.k")) == {n}, "negative control not bound to mutant.bin"')
    return (SH_HEAD.format(name=name, image=IMAGE,
                           kind_doc="concrete-trace witness (kind concrete_trace_violation)")
            + BIND.format(checks=checks) + f"""
kp witness-original.k {mod_o}; rc_o=$?
kp witness-mutant.k {mod_m}; rc_m=$?
kp witness-negative.k {mod_n}; rc_n=$?
acc() {{ [ "$1" -eq 0 ] && grep -q '#Top' "$T/$2.out"; }}
echo "claim: {claim_id} ({fn}() reverts)"
echo "mutation: {why}"
echo "state: concrete, see mutation.json"
if acc $rc_o {mod_o}; then echo "control: original artefact on this state reverts, as the claim says (kprove #Top)"; \\
  else echo "control: NOT accepted (exit $rc_o)"; fi
if acc $rc_m {mod_m}; then echo "witness: mutant on this state halts with EVMC_SUCCESS (kprove #Top)"; \\
  else echo "witness: NOT accepted (exit $rc_m)"; fi
if acc $rc_n {mod_n}; then echo "negative control: the claim at this state on the mutant WAS accepted (harness not discriminating)"; \\
  else echo "negative control: the claim at this state on the mutant is not accepted"; fi
if acc $rc_o {mod_o} && acc $rc_m {mod_m} && ! acc $rc_n {mod_n}; then
  echo "TCG-VIOLATION: {claim_id} {fn}() mutant halts with EVMC_SUCCESS where the claim requires EVMC_REVERT on the same concrete state"
  exit 0
fi
echo "NO-VIOLATION-SHOWN"
exit 1
""")


def main_rev(only) -> None:
    art = open("hard/artifact.bin", "rb").read()
    assert sha(art) == ART_SHA256, "hard/artifact.bin is not the pinned artefact"
    phi = json.load(open("hard/spec/phi.json"))
    shipped = {c["id"]: c for c in phi["claims"]}
    for name, claim_id, src, fn, edits, state, extra, accounts, why in REVERT_WITNESSES:
        if only and name not in only:
            continue
        text = open(src, encoding="utf-8").read()
        assert sha(text.encode()) == shipped[claim_id]["sha256"], f"{src} differs from phi.json's sha256"
        mut = mutate(art, edits)
        base = name.upper().replace("-", "")
        mod_o, mod_m, mod_n = (f"{base}-CONCRETE-ORIGINAL", f"{base}-CONCRETE-MUTANT",
                               f"{base}-CONCRETE-NEGATIVE")
        mod_s = f"{base}-SYMBOLIC"
        meta = {"claim": claim_id, "function": f"{fn}()", "mutation": why,
                "edits": [{"offset": hex(o), "old": hex(p), "new": hex(n)} for o, p, n in edits],
                "artifact_sha256": ART_SHA256, "mutant_sha256": sha(mut),
                "source_claim": src, "source_claim_sha256": sha(text.encode()),
                "semantics": f"KEVM (evm-semantics d4bf484a + ghost.diff + lemmas2.diff) via kprove in {IMAGE}"}
        d = os.path.join("evidence/mutants", name)
        os.makedirs(d, exist_ok=True)
        open(os.path.join(d, "mutant.bin"), "wb").write(mut)
        conc = concretize_rev(text, state, extra, accounts)
        open(os.path.join(d, "witness-original.k"), "w").write(
            relabel(rename_module(conc, mod_o), "concrete-original"))
        conc_m = swap_program_rev(conc, art.hex(), mut.hex(), len(accounts))
        open(os.path.join(d, "witness-mutant.k"), "w").write(
            success_ensures(relabel(rename_module(conc_m, mod_m), "concrete-mutant")))
        open(os.path.join(d, "witness-negative.k"), "w").write(
            relabel(rename_module(conc_m, mod_n), "concrete-negative"))
        st = {"id": hex(GEMJOIN), "caller": hex(CALLER),
              "storage": {str(k): f"{v:#066x}" for k, v in sorted(state.items())},
              "gemjoin_balance": 0, "gemjoin_nonce": 1, "callDepth": 0,
              "vars": {k: hex(v) for k, v in extra.items()},
              "other_accounts": [{"address": hex(a), "code": c, "role": "harness stub"} for a, c in accounts],
              "storage_source": "GemJoin storage at block 26298481 (provenance/rpc_probe.json)"
                                + ("; slot 5 (live) set to 0 = the state after cage()" if state.get(5) == 0 else ""),
              "note": ("Vat/WETH are stubs (Vat: STOP; WETH: returns true). claim-05's Pre leaves every "
                       "other account unconstrained, so this state is inside its quantification. They "
                       "model only 'the external calls succeed', not real Vat/WETH behaviour."
                       if accounts else "caller has no wards entry, so wards[caller] == 0 as Pre requires")}
        json.dump(dict(meta, kind="concrete_trace_violation", state=st),
                  open(os.path.join(d, "mutation.json"), "w"), indent=2)
        open(os.path.join(d, "replay.sh"), "w").write(
            revert_concrete_replay(name, claim_id, fn, why, mod_o, mod_m, mod_n, len(accounts)))
        ds = d + "-symbolic"
        os.makedirs(ds, exist_ok=True)
        open(os.path.join(ds, "mutant.bin"), "wb").write(mut)
        open(os.path.join(ds, "claim.k"), "w").write(rename_module(swap_program(text, art.hex(), mut.hex()), mod_s))
        json.dump(dict(meta, kind="decided by the judge at record time"),
                  open(os.path.join(ds, "mutation.json"), "w"), indent=2)
        checks = ('assert progs("claim.k") == [mut, mut], "claim.k not bound to mutant.bin"\n'
                  f'src = open("../../../{src}", encoding="utf-8").read()\n'
                  'exp = re.sub(r"^module \\S+$", "module ' + mod_s + '", '
                  'src.replace(\'"0x\' + art + \'"\', \'"0x\' + mut + \'"\'), flags=re.M)\n'
                  f'assert open("claim.k", encoding="utf-8").read() == exp, '
                  f'"claim.k is not {src} with only <program> and the module name changed"')
        open(os.path.join(ds, "replay.sh"), "w").write(
            SH_HEAD.format(name=ds.split("/")[-1], image=IMAGE,
                           kind_doc=f"the shipped {src}, <program> = mutant.bin, judged by the KEVM verdict judge")
            + BIND.format(checks=checks) + f"""
kp claim.k {mod_s}; rc=$?
# stderr first (it carries kore-exec's stuck/refute message the judge reads), then
# stdout; kore-exec's per-run counter "[NNN]" is normalised so stdout is byte-stable.
sed -E 's/^kore-exec: \\[[0-9]+\\]/kore-exec: [N]/' "$T/{mod_s}.err"
cat "$T/{mod_s}.out"
exit $rc
""")
        print(f"{name}: mutant sha256 {sha(mut)}")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--revert":
        main_rev(sys.argv[2:])          # gen_mutants.py --revert [claim-04 claim-05]
    else:
        main()                          # claims 01-03 (already recorded: do not rerun)
