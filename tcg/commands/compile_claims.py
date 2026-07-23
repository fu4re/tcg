"""`tcg compile-claims <loop>` — canonicalize claim bodies into content-addressed
spec modules.

The compiler invents nothing: claim bodies are authored by hand (decision D1).
Its job is form discipline and addressing:

- wrap each claim in its own spec module with pinned requires/imports;
- enforce the explicit all-path attribute on every claim;
- canonicalize text (whitespace normal form) and address by SHA-256;
- round-trip: re-read the emitted file, re-canonicalize, require the same hash;
- record loop -> claim hashes in spec/interfaces.json.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

from tcg.outcome import Exit
from tcg.workspace import (
    WorkspaceError, find_root, load_loop, loop_dir, read_json, save_loop,
    sha256_text, transition, write_json,
)

_CLAIM_HEAD = re.compile(r"^\s*claim\s*\[([^\]]*)\]\s*:", re.MULTILINE)


def canonicalize(text: str) -> str:
    """Whitespace normal form: no trailing spaces, LF endings, one final newline."""
    lines = [line.rstrip() for line in text.replace("\r\n", "\n").split("\n")]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def check_claim_body(body: str, label: str) -> list[str]:
    """Form discipline on one claim body. Returns error strings."""
    errors = []
    heads = _CLAIM_HEAD.findall(body)
    if len(heads) != 1:
        errors.append(f"expected exactly one claim, found {len(heads)}")
        return errors
    attrs = [a.strip() for a in heads[0].split(",")]
    if label not in attrs:
        errors.append(f"claim label {attrs[0]!r} does not match declared {label!r}")
    if "all-path" not in attrs:
        errors.append("missing explicit all-path attribute "
                      f"(write `claim [{label}, all-path]:`)")
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


def run(args) -> int:
    try:
        root = find_root()
        loop = load_loop(root, args.loop)
    except WorkspaceError as e:
        print(f"tcg: {e}", file=sys.stderr)
        return int(Exit.USAGE)

    d = loop_dir(root, args.loop)
    iface = read_json(d / "iface.json")
    claims = iface.get("claims", [])
    if not claims:
        print("tcg: interface declares no claims", file=sys.stderr)
        return int(Exit.USAGE)

    requires = iface.get("requires", ["evm.md"])
    imports = iface.get("imports", ["EVM"])
    claims_dir = root / "spec" / "claims"
    claims_dir.mkdir(parents=True, exist_ok=True)

    compiled: dict[str, str] = {}
    for entry in claims:
        label, rel = entry["label"], entry["file"]
        body_path = (d / rel) if not Path(rel).is_absolute() else Path(rel)
        try:
            body = body_path.read_text(encoding="utf-8")
        except OSError as e:
            print(f"tcg: {label}: cannot read body: {e}", file=sys.stderr)
            return int(Exit.USAGE)

        errors = check_claim_body(body, label)
        if errors:
            for msg in errors:
                print(f"tcg: {label}: {msg}", file=sys.stderr)
            return int(Exit.REFUSED)

        text = emit_module(args.loop, label, requires, imports, body)
        h = sha256_text(text)
        out = claims_dir / f"{h}.k"
        out.write_text(text, encoding="utf-8")

        # Round-trip: the artifact on disk must re-canonicalize to itself.
        back = canonicalize(out.read_text(encoding="utf-8"))
        if sha256_text(back) != h or check_claim_body(
            _strip_module(back), label
        ):
            print(f"tcg: {label}: round-trip check failed", file=sys.stderr)
            return int(Exit.REFUSED)
        compiled[label] = h
        print(f"{label} -> spec/claims/{h}.k")

    interfaces_path = root / "spec" / "interfaces.json"
    interfaces = read_json(interfaces_path) if interfaces_path.is_file() else {}
    interfaces[args.loop] = {
        "pre": iface["pre"], "post": iface["post"], "exit": iface["exit"],
        "footprint": iface["footprint"], "rely": iface["rely"], "guar": iface["guar"],
        "claims": compiled,
    }
    write_json(interfaces_path, interfaces)

    if loop["state"] != "Compiled":
        try:
            transition(loop, "Compiled")
        except WorkspaceError as e:
            print(f"tcg: {e}", file=sys.stderr)
            return int(Exit.USAGE)
        save_loop(root, args.loop, loop)

    print(f"compiled {len(compiled)} claim(s); {args.loop} is Compiled")
    return int(Exit.OK)


def _strip_module(text: str) -> str:
    """Drop the module wrapper so the body checks can re-run on emitted text."""
    lines = [
        line for line in text.split("\n")
        if not line.startswith(("requires \"", "module ", "endmodule"))
        and not line.strip().startswith("imports ")
    ]
    return "\n".join(lines)
