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
