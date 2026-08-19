"""Bridge S<==D — discharge of an abstract callee-summary node.

Finding 0005 established that raw kprove applies a separately-proved callee
summary at an UNRESOLVED (symbolic-code) external CALL: the caller root closes
only by consuming an injected abstract summary `S` whose `<program>` cell is a
free variable (so it unifies with the stalled symbolic callee frame). Such an
`S` can NEVER be Accepted on its own (a symbolic program stalls) and, taken as
a bare axiom, would apply to ANY code at the callee address — unsound in
isolation. This module carries the obligation that makes it sound: the bridge
`S <== D`, three checks that TOGETHER discharge `S`, bound by CONTENT, not name:

  1. **D** — a concrete callee proof of the delta over the real callee bytecode
     `P`, Accepted in its own loop (its `<program>` == P).
  2. **code-identity** — `external_code[callee] == P` AND `keccak256(P)` equals
     the declared on-chain code hash. PURE text + keccak, PERFORMED by the
     verifier (this module), not assumed. Ties `S` to the code actually at the
     callee address.
  3. **bridge-s-at-p (B)** — `S` instantiated with `<program> := P` proves by
     EXECUTION over the real bytecode (Accepted, `<program>` == P). This is what
     forecloses a proxy: whatever `S` asserts must actually HOLD over `P`.

The anti-proxy binding across the abstraction boundary is re-established here in
full: the summary the caller injects (== `S` by hash) must agree cell-for-cell
with the claim re-proved over `P` (== `B`) on every entry/effect cell it pins
(`binding_errors`), `B`'s `<program>` and `D`'s `<program>` must byte-equal the
declared `external_code[callee]`, and `keccak256` of that code must equal the
declared hash. A summary with a DIFFERENT delta than `P` produces (broken +6,
proxy no-op) fails at `B` over `P`; a summary bound to code other than what is
installed fails code-identity; a summary with no bridge at all is never
discharged. The one node not replayed directly (`S`, which cannot Accept) is
pinned tighter than a normal trusted lemma, not looser.

Pure functions over claim text + graph/environment dicts. NO tcg.workspace or
tcg.commands import (shared by `graph check`, `freeze`, and the bundle-only
`verify`; see scripts/repo-checks.sh's mechanical guard). Same discipline on
every side.
"""
from __future__ import annotations

import re

from tcg.claims import extract_program_bytes
from tcg.keccak import keccak256_hex

REQUIRED_BRIDGE_KEYS = ("callee_address", "code_hash", "concrete_proof",
                        "at_program_proof")

# A single K variable (or the anonymous `_`): what an abstracted/framed cell
# looks like. `_PGM`, `CODE`, `_Gas`, `_` all match; `#parseByteStack("…")`,
# `100000`, `EVMC_SUCCESS` do not.
_KVAR = re.compile(r"_?[A-Z][A-Za-z0-9']*|_")
_ACCOUNT = re.compile(r"<account\b.*?</account>", re.DOTALL)
_TOP_CELL = re.compile(r"<([A-Za-z][A-Za-z0-9]*)>(.*?)</\1>", re.DOTALL)
_PROGRAM = re.compile(r"<program>(.*?)</program>", re.DOTALL)

# Cells excluded from the cell-by-cell binding: <program> is the ONE cell the
# summary abstracts (checked separately: S abstract, B == P), and <k> is the
# abstract-machine continuation whose `…` cell-frame ellipsis differs between a
# summary (which SKIPS execution: `#execute => #halt …`) and its at-P proof
# (which EXECUTES). <k> is instead checked lightly: both must start at #execute.
_BINDING_EXCLUDE = frozenset({"program", "k"})


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", s).strip()


def _is_kvar(token: str) -> bool:
    return bool(_KVAR.fullmatch(token.strip()))


def _split_rw(content: str) -> tuple[str, str]:
    """(lhs, rhs) of a cell; rhs == lhs when the cell does not rewrite."""
    if "=>" in content:
        lhs, rhs = content.split("=>", 1)
        return _norm(lhs), _norm(rhs)
    n = _norm(content)
    return n, n


def _top_cells(claim_text: str) -> dict[str, str]:
    """name -> raw content for TOP-LEVEL cells (account blocks stripped so their
    nested cells do not leak in). First occurrence wins."""
    stripped = _ACCOUNT.sub("", claim_text)
    out: dict[str, str] = {}
    for m in _TOP_CELL.finditer(stripped):
        out.setdefault(m.group(1), m.group(2))
    return out


def _int_token(tok: str) -> int | None:
    t = tok.strip()
    try:
        return int(t, 16) if t.lower().startswith("0x") else int(t)
    except ValueError:
        return None


def _account_storage(claim_text: str, addr_int: int) -> str | None:
    """The <storage> cell content of the account whose <acctID> == addr_int."""
    for m in _ACCOUNT.finditer(claim_text):
        block = m.group(0)
        aid = re.search(r"<acctID>\s*(\S+)\s*</acctID>", block)
        if aid and _int_token(aid.group(1)) == addr_int:
            st = re.search(r"<storage>(.*?)</storage>", block, re.DOTALL)
            return st.group(1) if st else None
    return None


def _hex_to_bytes(hexstr) -> bytes | None:
    h = str(hexstr).strip()
    if h.lower().startswith("0x"):
        h = h[2:]
    if not h or len(h) % 2 != 0 or not re.fullmatch(r"[0-9a-fA-F]+", h):
        return None
    return bytes.fromhex(h)


def _norm_hex(hexstr) -> str:
    h = str(hexstr).strip().lower()
    return h[2:] if h.startswith("0x") else h


def is_bridge_node(node: dict) -> bool:
    """A node is an abstract-summary node iff it carries a bridge block."""
    return isinstance(node.get("bridge"), dict)


def resolve_ref(nodes: dict, ref) -> str | None:
    """Hash of the node whose (loop, label) match `ref`, else None. Refs are
    stored by name and resolved to a content hash here — the same {loop,label}
    indirection `prove` uses for trusted children."""
    if not isinstance(ref, dict):
        return None
    loop, label = ref.get("loop"), ref.get("label")
    for h, n in nodes.items():
        if n.get("loop") == loop and n.get("label") == label:
            return h
    return None


def program_is_abstract_var(claim_text: str) -> bool:
    """True iff the claim's <program> cell is a bare K variable (it abstracts
    the program). A concrete `#parseByteStack("…")`/hex program is NOT abstract
    — such a summary needs no bridge (inject == discharge == one hash)."""
    m = _PROGRAM.search(claim_text)
    if not m:
        return False
    return _is_kvar(m.group(1).strip())


def binding_errors(summary_text: str, at_p_text: str, addr_int: int,
                   prefix: str) -> list[str]:
    """The anti-proxy binding S<=>B across the program-abstraction boundary.

    B (the summary re-proved with <program> := P) must (a) start execution at
    #execute like S, (b) agree with S on every top-level cell S pins — same
    entry (LHS), and same asserted effect (RHS) where S rewrites, (c) carry S's
    exact callee-account storage delta, and (d) be at least as GENERAL as S at
    entry: any extra cell B pins that S frames must itself be framed (a variable),
    never a concrete literal. <program> is excepted (S abstract, B == P) and <k>
    is checked only for the #execute start (its RHS cell-frame differs between a
    SKIP summary and an EXECUTING proof).
    """
    errs: list[str] = []
    s_cells = _top_cells(summary_text)
    b_cells = _top_cells(at_p_text)

    for who, cells in (("summary", s_cells), ("bridge-at-P", b_cells)):
        k = cells.get("k")
        if k is None or _split_rw(k)[0] != "#execute":
            errs.append(f"{prefix}: {who} <k> does not start at #execute — not "
                        "an execution claim")

    for name, s_content in s_cells.items():
        if name in _BINDING_EXCLUDE:
            continue
        if name not in b_cells:
            errs.append(f"{prefix}: bridge-at-P is missing cell <{name}> that "
                        "the summary pins — the two must agree on the callee "
                        "entry/effect")
            continue
        s_l, s_r = _split_rw(s_content)
        b_l, b_r = _split_rw(b_cells[name])
        if s_l != b_l:
            errs.append(f"{prefix}: <{name}> entry differs — summary pins "
                        f"'{s_l}', bridge-at-P pins '{b_l}'")
        if "=>" in s_content and s_r != b_r:
            errs.append(f"{prefix}: <{name}> asserted effect differs — summary "
                        f"'=> {s_r}', bridge-at-P '=> {b_r}'")

    # B must not add an entry constraint the summary frames (else B proves the
    # delta for a narrower entry than S claims for).
    for name, b_content in b_cells.items():
        if name in _BINDING_EXCLUDE or name in s_cells:
            continue
        b_l, _ = _split_rw(b_content)
        if not _is_kvar(b_l):
            errs.append(f"{prefix}: bridge-at-P pins <{name}> entry to '{b_l}' "
                        "but the summary frames it — the bridge proof must be "
                        "at least as general as the summary at entry")

    s_store = _account_storage(summary_text, addr_int)
    b_store = _account_storage(at_p_text, addr_int)
    if s_store is None:
        errs.append(f"{prefix}: summary carries no <storage> for callee account "
                    f"{addr_int}")
    elif b_store is None:
        errs.append(f"{prefix}: bridge-at-P carries no <storage> for callee "
                    f"account {addr_int}")
    elif _norm(s_store) != _norm(b_store):
        errs.append(f"{prefix}: callee storage delta differs — summary "
                    f"'{_norm(s_store)}', bridge-at-P '{_norm(b_store)}': the "
                    "asserted delta is not the one re-proved over P")
    return errs


def structural_errors(summary_hash: str, nodes: dict, claim_text_of,
                      environment: dict | None):
    """Bundle-only structural discharge of an abstract-summary node.

    Returns (errors, refs) where refs == {"concrete": D_hash, "at_program":
    B_hash} once both resolve (so a caller can require D and B Accepted through
    its own all-nodes / replay discipline — this function does NOT itself check
    that D and B are Accepted). Everything here is pure text + keccak, so
    `graph check`, `freeze`, and `verify` re-derive an identical verdict.
    """
    node = nodes.get(summary_hash, {})
    loop, label = node.get("loop"), node.get("label")
    prefix = f"abstract-summary {loop}/{label}"
    refs: dict = {}
    errs: list[str] = []

    b = node.get("bridge")
    if not isinstance(b, dict):
        return ([f"{prefix}: node has no bridge block — an abstract summary "
                 "(free <program>) is discharged only by a bridge S<==D"], refs)
    for k in REQUIRED_BRIDGE_KEYS:
        if k not in b:
            errs.append(f"{prefix}: bridge block missing '{k}'")
    if errs:
        return (errs, refs)

    summary_text = claim_text_of(summary_hash)
    if not program_is_abstract_var(summary_text):
        errs.append(f"{prefix}: summary <program> is not a bare variable — an "
                    "abstract summary must abstract ONLY the program cell; a "
                    "concrete-program summary needs no bridge (discharge it as "
                    "one hash)")

    d_hash = resolve_ref(nodes, b["concrete_proof"])
    b_hash = resolve_ref(nodes, b["at_program_proof"])
    if d_hash is None:
        errs.append(f"{prefix}: concrete_proof {b['concrete_proof']} does not "
                    "resolve to a graph node")
    if b_hash is None:
        errs.append(f"{prefix}: at_program_proof {b['at_program_proof']} does "
                    "not resolve to a graph node")
    if d_hash is None or b_hash is None:
        return (errs, refs)
    refs = {"concrete": d_hash, "at_program": b_hash}

    addr_int = _int_token(str(b["callee_address"]))
    if addr_int is None:
        errs.append(f"{prefix}: callee_address {b['callee_address']!r} is not a "
                    "number")
        return (errs, refs)

    ext = (environment or {}).get("external_code") or {}
    p_hex = None
    for key, val in ext.items():
        if _int_token(str(key)) == addr_int:
            p_hex = val
            break
    if p_hex is None:
        errs.append(f"{prefix}: environment.external_code has no entry for "
                    f"callee address {b['callee_address']} — code-identity "
                    "cannot be established")
        return (errs, refs)
    p_bytes = _hex_to_bytes(p_hex)
    if p_bytes is None:
        errs.append(f"{prefix}: external_code[{b['callee_address']}] is not "
                    "valid hex")
        return (errs, refs)

    # (2) code-identity: keccak256(P) == declared on-chain hash — PERFORMED.
    computed = keccak256_hex(p_bytes)
    if computed != _norm_hex(b["code_hash"]):
        errs.append(f"{prefix}: code-identity FAILED — keccak256(external_code"
                    f"[{b['callee_address']}]) = {computed} != declared "
                    f"code_hash {_norm_hex(b['code_hash'])}")

    # (1)+(3) D and B must be proved over exactly P (byte-for-byte).
    d_prog = extract_program_bytes(claim_text_of(d_hash))
    b_prog = extract_program_bytes(claim_text_of(b_hash))
    if d_prog != p_bytes:
        errs.append(f"{prefix}: concrete proof D <program> is not the declared "
                    f"external_code[{b['callee_address']}] (P) — D proves a "
                    "delta over a DIFFERENT program")
    if b_prog != p_bytes:
        errs.append(f"{prefix}: bridge-at-P B <program> is not the declared "
                    f"external_code[{b['callee_address']}] (P) — B re-proves "
                    "over a DIFFERENT program")

    # The summary must frame exactly the declared callee address.
    sid = _top_cells(summary_text).get("id")
    if sid is None or _int_token(_split_rw(sid)[0]) != addr_int:
        errs.append(f"{prefix}: summary <id> is not the declared callee address "
                    f"{addr_int} — the summary does not frame the bound callee")

    # (3) anti-proxy binding S<=>B across the abstraction boundary.
    errs += binding_errors(summary_text, claim_text_of(b_hash), addr_int, prefix)
    return (errs, refs)
