"""κ: non-tautological conjunct count via the havoc base (protocol.md section 11).

    python tools/kappa.py <spec.sol> [--artifact subjects/capped_token/CappedToken.sol]
                          [--timeout-ms N] [--wall-timeout-s S] [--json out.json]
    python tools/kappa.py --write-havoc [--artifact ...] [--out specs/havoc/CappedToken.sol]

The havoc base H is generated from the artifact's AST (never hand-edited), so
a change of the subject propagates: same state variables (names, types,
visibility), a public `havoc_<var>` setter per state variable (mappings take
one key per level), b's constructor signature with an empty body, and every
public token function with b's signature whose body makes one external call to
an unknown address and then returns free values (`__ret_*` storage, itself
havoc-settable). Under SMTChecker's untrusted external-call model the call may
re-enter any setter, so after a token call every state variable, mapping entry
and return value is unconstrained.

Check v2: every check of φ gets its own isolated harness over H (in the
worker pool). An `assert(e)` of φ is tautological iff Check over H reports it `safe`; it is
read at its program point, i.e. under the check's Pre and the asserts before
it on the same path. κ(φ) = number of asserts that are not `safe` over H;
`unproved` / no result count as non-tautological and are listed separately.

Exit codes: 0 κ computed, 2 κ undetermined (Check over H did not classify:
compile error, solver unavailable, unparsed, wall timeout), 1 usage / lint.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402
import check as check_cli  # noqa: E402

DEFAULT_ARTIFACT = core.load_subject().source_path
DEFAULT_HAVOC = core.load_subject().specs_dir / "havoc" / core.load_subject().unit
FREE_ADDRESS = "0xF4EE"
UNDETERMINED = {"compile_error", "solver_unavailable", "unparsed", "wall_timeout", "no_targets"}


class HavocError(Exception):
    pass


def _src(text: bytes, node: dict) -> str:
    start, length = (int(v) for v in node["src"].split(":")[:2])
    return text[start:start + length].decode()


def _mapping_levels(type_node: dict, text: bytes, structs: dict) -> tuple[list[str], str]:
    """Key types and the value type (elementary, or a struct of the contract)."""
    keys = []
    while type_node["nodeType"] == "Mapping":
        keys.append(_src(text, type_node["keyType"]))
        type_node = type_node["valueType"]
    value = _src(text, type_node)
    if type_node["nodeType"] != "ElementaryTypeName" and value not in structs:
        raise HavocError(f"unsupported mapping value type {value}")
    return keys, value


def _setter(var: str, keys: list[str], value: str, structs: dict) -> str:
    """havoc_<var>(keys..., value or one value per struct field): any entry, any field values."""
    params = [f"{k} k{i}" for i, k in enumerate(keys)]
    index = "".join(f"[k{i}]" for i in range(len(keys)))
    if value in structs:
        params += [f"{t} v_{f}" for f, t in structs[value]]
        body = " ".join(f"{var}{index}.{f} = v_{f};" for f, _ in structs[value])
    else:
        params.append(f"{value} v")
        body = f"{var}{index} = v;"
    return f"    function havoc_{var}({', '.join(params)}) public {{ {body} }}"


def generate_havoc(artifact_path: str | Path, tc: core.Toolchain | None = None, subject=None) -> str:
    """Havoc base source for the artifact (deterministic text)."""
    tc = tc or core.Toolchain.default()
    raw = Path(artifact_path).read_text()
    text = raw.encode()
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    out, _, _ = core.run_solc(core.solc_input({subj.unit: raw}), tc, 120)
    if out is None or any(e.get("severity") == "error" for e in out.get("errors", [])):
        raise HavocError("artifact does not compile")
    contract = next((n for n in core._ast_nodes(out["sources"][subj.unit]["ast"])
                     if n.get("nodeType") == "ContractDefinition" and n.get("name") == subj.contract), None)
    if contract is None:
        raise HavocError(f"no contract {subj.contract}")

    state, setters, ctor, functions, rets, struct_defs = [], [], None, [], [], []
    structs: dict[str, list[tuple[str, str]]] = {}
    for m in contract["nodes"]:
        if m.get("nodeType") == "StructDefinition":
            fields = [(x["name"], _src(text, x["typeName"])) for x in m["members"]]
            if any(x["typeName"]["nodeType"] != "ElementaryTypeName" for x in m["members"]):
                raise HavocError(f"struct {m['name']}: only elementary field types are supported")
            structs[m["name"]] = fields
            struct_defs.append("    struct " + m["name"] + " { " + " ".join(f"{t} {f};" for f, t in fields) + " }")
    for m in contract["nodes"]:
        nt = m.get("nodeType")
        if nt == "VariableDeclaration" and m.get("stateVariable"):
            if m.get("mutability") != "mutable":
                raise HavocError(f"state variable {m['name']} is {m.get('mutability')}")
            tn = m["typeName"]
            vis = m["visibility"]
            state.append(f"    {_src(text, tn)} {vis} {m['name']};")
            if tn["nodeType"] == "Mapping":
                keys, value = _mapping_levels(tn, text, structs)
                setters.append(_setter(m["name"], keys, value, structs))
            elif tn["nodeType"] == "ElementaryTypeName" or _src(text, tn) in structs:
                setters.append(_setter(m["name"], [], _src(text, tn), structs))
            else:
                raise HavocError(f"unsupported state variable type {_src(text, tn)}")
        elif nt == "FunctionDefinition" and m.get("kind") == "constructor":
            ctor = f"    constructor{_src(text, m['parameters'])} {{}}"
        elif nt == "FunctionDefinition" and m.get("kind") == "function" and m.get("visibility") in ("public", "external"):
            params = _src(text, m["parameters"])
            names = []
            for i, p in enumerate(m["returnParameters"]["parameters"]):
                if p["typeName"]["nodeType"] != "ElementaryTypeName":
                    raise HavocError(f"unsupported return type in {m['name']}")
                rname = f"__ret_{m['name']}_{len(rets)}"
                ptype = _src(text, p["typeName"])
                rets.append(f"    {ptype} private {rname};")
                setters.append(f"    function havoc_{rname}({ptype} v) public {{ {rname} = v; }}")
                names.append(rname)
            returns = f" returns {_src(text, m['returnParameters'])}" if names else ""
            body = f"IFree(address({FREE_ADDRESS})).next();"
            if names:
                body += f" return {names[0] if len(names) == 1 else '(' + ', '.join(names) + ')'};"
            mut = m.get("stateMutability")
            mut = "" if mut == "nonpayable" else f" {mut}"
            if mut.strip() in ("view", "pure"):
                raise HavocError(f"{m['name']} is {mut.strip()}: an external call is not allowed there")
            functions.append(f"    function {m['name']}{params} public{mut}{returns} {{ {body} }}")
    if ctor is None:
        raise HavocError("no constructor")
    sha = core.sha256_hex(text)
    lines = [
        "// SPDX-License-Identifier: MIT",
        "// GENERATED by tools/kappa.py --write-havoc; do not edit.",
        f"// Havoc base H for the kappa tautology test (protocol.md section 11),",
        f"// generated from an artifact with source sha256 {sha}.",
        "pragma solidity 0.8.35;",
        "",
        "interface IFree {",
        "    function next() external;",
        "}",
        "",
        f"contract {subj.contract} {{",
        *struct_defs,
        *state,
        *rets,
        "",
        ctor,
        "",
        *setters,
        "",
        *functions,
        "}",
        "",
    ]
    return "\n".join(lines)


def kappa(spec: Path, artifact: Path, timeout_ms: int, wall_timeout_s: float,
          tc: core.Toolchain | None = None, workers: int | None = None,
          cache_dir: Path | None = core.CACHE_DIR, subject=None) -> dict:
    """κ with Check v2 isolation: one isolated harness per check over H, in the pool."""
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    havoc = generate_havoc(artifact, tc, subj)
    t0 = time.monotonic()
    checks = core.check_functions(Path(spec).read_text(), subj)
    rows_by_check = core.smtcheck_harnesses([(n, core.isolated_harness(t, subj)) for n, t in checks], havoc,
                                            timeout_ms, wall_timeout_s, tc, workers, cache_dir, subj)
    rows, per_check = [], []
    for rc in rows_by_check:
        r = rc["result"]
        per_check.append({"check": rc["check"], "verdict": r["verdict"], "reason": r["reason"],
                          "duration_s": r["duration_s"], "cached": rc["cached"],
                          "solc_input_sha256": r["solc_input_sha256"]})
        for t in r["targets"]:
            rows.append({"function": t["function"], "line": t["line"], "status_over_H": t["status"] or "no result",
                         "tautological": t["status"] == "safe"})
    undetermined = [c for c in per_check if c["reason"] in UNDETERMINED]
    determined = bool(per_check) and not undetermined
    return {
        "spec": str(spec),
        "artifact": str(artifact),
        "mode": "isolated",
        "havoc_sha256": core.sha256_hex(havoc.encode()),
        "determined": determined,
        "kappa": sum(not x["tautological"] for x in rows) if determined else None,
        "asserts": len(rows),
        "non_tautological_unproved": sum(x["status_over_H"] in ("unproved", "no result") for x in rows),
        "rows": rows,
        "checks_over_H": per_check,
        "check_over_H": {"duration_s": round(time.monotonic() - t0, 3),
                         "reason": undetermined[0]["reason"] if undetermined else "determined",
                         "cpu_s": round(sum(c["duration_s"] for c in per_check), 3)},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("spec", type=Path, nargs="?")
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--artifact", type=Path, help="default: the subject's b")
    ap.add_argument("--timeout-ms", type=int, default=check_cli.DEFAULT_TIMEOUT_MS)
    ap.add_argument("--wall-timeout-s", type=float, default=check_cli.DEFAULT_WALL_TIMEOUT_S)
    ap.add_argument("--json", type=Path)
    ap.add_argument("--write-havoc", action="store_true", help="write the generated H and exit")
    ap.add_argument("--out", type=Path, help="default: subjects/<subject>/specs/havoc/<file>")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 1 if e.code else 0
    subj = core.load_subject(a.subject)
    a.artifact = a.artifact or subj.source_path
    if a.write_havoc:
        a.out = a.out or subj.specs_dir / "havoc" / subj.unit
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(generate_havoc(a.artifact, subject=subj))
        print(f"wrote {a.out}")
        return 0
    if a.spec is None or not a.spec.is_file():
        print("kappa: spec file required", file=sys.stderr)
        return 1
    problems = check_cli.lint(a.spec, a.artifact, subject=subj)
    if problems:
        for p in problems:
            print(f"{a.spec}: {p}")
        return 1
    res = kappa(a.spec, a.artifact, a.timeout_ms, a.wall_timeout_s, subject=subj)
    print(f"spec {a.spec}  over havoc base (sha256 {res['havoc_sha256'][:16]}...)")
    for x in res["rows"]:
        print(f"  {x['function']:40s} line {x['line']!s:>4}  {x['status_over_H']:10s} "
              f"{'tautological' if x['tautological'] else 'non-tautological'}")
    if res["determined"]:
        print(f"kappa = {res['kappa']} of {res['asserts']} asserts "
              f"({res['non_tautological_unproved']} of them unproved/no result over H)")
    else:
        print(f"kappa undetermined: Check over H gave {res['check_over_H']['reason']}")
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(res, indent=1, sort_keys=True) + "\n")
    return 0 if res["determined"] else 2


if __name__ == "__main__":
    sys.exit(main())
