"""Pure claim-text helpers: canonical form, module emission, discipline checks.

No workspace or filesystem state — shared by the workspace commands and by
`verify`, which must stay a bundle-only path.
"""
from __future__ import annotations

import hashlib
import re

_CLAIM_KW = re.compile(r"^\s*claim\b", re.MULTILINE)
# Trailing attribute list of the claim, e.g. `[label(deposit-main), all-path]`.
# This position (after requires/ensures) is what the pinned prover parses; a
# bracket group in the `claim [x]:` head position does not accept attributes.
_ATTR_TAIL = re.compile(r"\[([^\[\]]*)\](\s*)$")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonicalize(text: str) -> str:
    """Whitespace normal form: no trailing spaces, LF endings, one final newline."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def check_claim_body(body: str, label: str) -> list[str]:
    """Form discipline on one claim body. Returns error strings."""
    errors = []
    if len(_CLAIM_KW.findall(body)) != 1:
        errors.append("expected exactly one claim")
        return errors
    tail = _ATTR_TAIL.search(body.rstrip())
    attrs = [a.strip() for a in tail.group(1).split(",")] if tail else []
    if f"label({label})" not in attrs:
        errors.append(f"trailing attributes must carry label({label})")
    if "all-path" not in attrs:
        errors.append("missing explicit all-path attribute "
                      f"(end the claim with `[label({label}), all-path]`)")
    if "trusted" in attrs:
        errors.append("authored claims must not be marked trusted; "
                      "`tcg prove` injects trusted children itself")
    if "one-path" in attrs:
        errors.append("one-path claims are outside the canonical form")
    if re.search(r"^\s*(module|endmodule|requires\s+\")", body, re.MULTILINE):
        errors.append("body must contain only the claim; the module wrapper is emitted")
    return errors


def module_name(loop: str, label: str) -> str:
    return f"{loop}-{label}-SPEC".upper().replace("_", "-")


def emit_module(loop: str, label: str, requires: list[str],
                imports: list[str], body: str) -> str:
    head = "".join(f'requires "{r}"\n' for r in requires)
    imp = "".join(f"  imports {m}\n" for m in imports)
    indented = "\n".join(
        ("  " + line if line else "") for line in body.strip("\n").split("\n")
    )
    return canonicalize(
        f"{head}\nmodule {module_name(loop, label)}\n{imp}\n{indented}\nendmodule\n"
    )


def extract_body(text: str) -> str:
    """Inverse of emit_module: recover the claim body from a canonical module."""
    lines = [
        line for line in text.split("\n")
        if not line.startswith(("requires \"", "module ", "endmodule"))
        and not line.strip().startswith("imports ")
    ]
    return canonicalize(
        "\n".join(line[2:] if line.startswith("  ") else line for line in lines)
    )


def module_header(text: str) -> tuple[list[str], list[str]]:
    """(requires, imports) declared by a canonical claim module."""
    reqs = re.findall(r'^requires "([^"]+)"$', text, re.MULTILINE)
    imps = re.findall(r"^\s+imports (\S+)$", text, re.MULTILINE)
    return reqs, imps


def mark_trusted(body: str) -> str:
    """Append `trusted` to the claim's trailing attribute list."""
    text = body.rstrip()
    m = _ATTR_TAIL.search(text)
    if not m:
        raise ValueError("claim body has no trailing attribute list")
    return canonicalize(text[: m.start()] + f"[{m.group(1)}, trusted]")


def assemble_prove_module(name: str, requires: list[str], imports: list[str],
                          trusted_bodies: list[str], goal_bodies: list[str]) -> str:
    """One prove/replay module: trusted children first, then the goals."""
    head = "".join(f'requires "{r}"\n' for r in requires)
    imp = "".join(f"  imports {m}\n" for m in imports)
    bodies = (*[mark_trusted(b) for b in trusted_bodies], *goal_bodies)
    parts = "\n".join(
        "\n".join("  " + line if line else "" for line in b.strip("\n").split("\n"))
        for b in bodies
    )
    return canonicalize(f"{head}\nmodule {name}\n{imp}\n{parts}\nendmodule\n")


# --- Program binding (P0-A) --------------------------------------------------
#
# A ROOT claim must prove a property OF THE SUBJECT BYTECODE. The mechanical
# tie is: the claim's <program> cell bytes must equal subject/runtime.bin. A
# root that never references the subject's bytecode (Hole 1 from gate G3) is
# refused at freeze and, bundle-only, at verify. This stays in the format's
# "cheaper than the tool" spirit: text extraction + a raw byte compare, no
# prover. See docs/bundle-spec.md §9 and docs/findings/0002.
#
# Honest limits (documented in the finding): this is a TEXT extraction, not a
# K parse, so it is not adversarial-K-proof — a claim could in principle carry
# a decoy <program> cell the real proof does not use, or express the program
# in a form this does not recognize (a raw `b"…"` byte literal). It recognizes
# the two forms real authored claims use: `#parseByteStack("<hex>")` (the tcg
# canonical form, hex optionally 0x-prefixed) and a bare hex literal. Anything
# else extracts as "no program", which is itself a refusal for a root.

_PROGRAM_CELL = re.compile(r"<program>(.*?)</program>", re.DOTALL)
_PARSE_BYTESTACK = re.compile(r'#parseByteStack\(\s*"([^"]*)"\s*\)')
_BARE_HEX = re.compile(r"(?:0[xX])?([0-9a-fA-F]+)\Z")


def _hex_to_bytes(hexstr: str) -> bytes | None:
    h = hexstr.strip()
    if h.lower().startswith("0x"):
        h = h[2:]
    if not h or len(h) % 2 != 0 or not re.fullmatch(r"[0-9a-fA-F]+", h):
        return None
    return bytes.fromhex(h)


def extract_program_bytes(claim_text: str) -> bytes | None:
    """The bytes of a claim's <program> cell, or None if none is extractable.

    Handles `#parseByteStack("<hex>")` (0x-prefixed or bare hex — KEVM strips
    the prefix) and a bare hex literal. If the cell rewrites (`X => Y`), the
    INSTALLED (left) program is what binds to the deployed bytecode. Returns
    None for an absent cell or an unrecognized form (e.g. a raw `b"…"` byte
    literal) — for a root, None is a refusal, not a pass.
    """
    m = _PROGRAM_CELL.search(claim_text)
    if not m:
        return None
    content = m.group(1).strip()
    if "=>" in content:  # program cell rewrites: bind on the initial program
        content = content.split("=>", 1)[0].strip()
    pb = _PARSE_BYTESTACK.search(content)
    if pb:
        return _hex_to_bytes(pb.group(1))
    bare = _BARE_HEX.fullmatch(content)
    if bare:
        return _hex_to_bytes(content)
    return None


def program_binding_error(claim_text: str, subject_bytes: bytes) -> str | None:
    """None if the claim's <program> equals the subject bytes; else a reason
    string naming the fix. For ROOT claims only (non-roots need not carry a
    subject-matching program — see docs/bundle-spec.md §9)."""
    prog = extract_program_bytes(claim_text)
    if prog is None:
        return ("root claim has no extractable <program> cell binding it to the "
                "subject; author it as `<program> #parseByteStack(\"<hex>\") "
                "</program>` with <hex> = subject/runtime.bin")
    if prog != subject_bytes:
        return (f"root <program> ({len(prog)} bytes, 0x{prog[:8].hex()}…) does "
                f"not match subject/runtime.bin ({len(subject_bytes)} bytes, "
                f"0x{subject_bytes[:8].hex()}…) — the proof is about a different "
                "program than the installed subject")
    return None


# --- Vacuity probe mutation (P0-B) -------------------------------------------
#
# Ports the spirit of Finding 0005's Probe R (sheaf: assert(false)-proves ⇒
# unreachable ⇒ vacuous) into this reachability CLI. The mutation FALSIFIES the
# postcondition (`ensures false`) while keeping the antecedent (requires + LHS
# cells) intact. If the falsified claim STILL proves Accept, the antecedent is
# infeasible (no initial state satisfies it), so the ORIGINAL proof held for an
# empty reason — vacuous. Empirically pinned on the real Haskell backend:
# a feasible claim's `ensures false` mutant does NOT prove (kore-exec:
# "unifies with the destination … implication check has failed" → Unknown);
# an infeasible-antecedent claim's mutant proves ("claim proven during
# initialization … left-hand side may be undefined" → #Top). See docs/findings/
# 0002 and the shared judge tcg.verdict.classify().


def falsify_body(body: str) -> str:
    """Vacuity-probe mutant of a claim body: postcondition → `false`, antecedent
    kept. Drops any existing `ensures` clause (idiomatic K states `requires`
    before `ensures`, so this preserves the antecedent) and appends
    `ensures false`. Pure text; the prover is the judge of the result."""
    text = body.rstrip()
    m = _ATTR_TAIL.search(text)
    if not m:
        raise ValueError("claim body has no trailing attribute list")
    attrs = m.group(1)
    head = text[: m.start()].rstrip()
    e = re.search(r"(?s)\bensures\b.*\Z", head)
    if e:
        head = head[: e.start()].rstrip()
    return canonicalize(f"{head}\n    ensures false\n [{attrs}]\n")
