"""Mechanical lint for spec harnesses and artifacts (specs/SPEC_FORMAT.md).

Text-level and strict: comments and string literals are blanked first, then
every rule is a regular expression or a brace-depth scan. A spec that this lint
rejects is not a spec; nothing downstream (Check, adversary, scorer) runs on it.

    python tools/speclint.py spec  <Spec.sol> [--subject capped_token] [--artifact <file>]
    python tools/speclint.py artifact <file.sol> [--subject capped_token]

The subject's profile (subjects/<name>/profile.json) fixes the contract name,
the import, the spec constructor and the allowed check_* signatures.

Exit 0 = clean, 1 = violations (one line each, `RULE line: message`), 2 = usage.
"""
from __future__ import annotations

import argparse
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402

PRAGMA = f"pragma solidity {core.SOLC_VERSION.split('+')[0]};"


class SubjectRules:
    """The subject-specific shapes the lint checks (from the profile)."""

    def __init__(self, subject: core.Subject):
        self.subject = subject
        c = re.escape(subject.contract)
        self.spec_import = f'import "./{subject.unit}";'
        self.spec_head = re.compile(rf"^contract\s+Spec\s+is\s+{c}\s*\{{$")
        self.spec_ctor = " ".join(subject.spec_constructor.replace("(", " ( ").replace(")", " ) ")
                                  .replace("{", " { ").replace("}", " } ").replace(",", " , ").split())
        heads = []
        for sig in subject.probes:
            params = r"\s*,\s*".join(rf"{t}\s+{n}" for n, t in sig)
            heads.append(re.compile(rf"^function\s+(check_[A-Za-z0-9_]+)\s*\(\s*{params}\s*\)\s*external\s*\{{$"))
        self.check_heads = heads
        self.check_sigs = ["(" + ", ".join(f"{t} {n}" for n, t in sig) + ")" for sig in subject.probes]
        self.art_head = re.compile(rf"^contract\s+{c}\s*\{{$")
        self.ctor_types = [t for _, t in subject.ctor_params]

    def check_head(self, head: str):
        for h in self.check_heads:
            m = h.match(head)
            if m:
                return m
        return None

    def norm_ctor(self, text: str) -> str:
        return " ".join(text.replace("(", " ( ").replace(")", " ) ").replace("{", " { ").replace("}", " } ")
                        .replace(",", " , ").split())

# Tokens no spec may contain (rule S5). Member access is allowed only as
# msg.sender and type(T).max / type(T).min (rule S6).
SPEC_FORBIDDEN = [
    "assembly", "this", "super", "new", "delete", "selfdestruct", "payable", "storage",
    "memory", "calldata", "try", "catch", "revert", "emit", "event", "error", "modifier",
    "override", "virtual", "fallback", "receive", "for", "while", "do", "unchecked",
    "gasleft", "blockhash", "block", "tx", "interface", "library", "struct", "enum",
    "mapping", "using", "constant", "immutable", "public", "private", "internal",
    "view", "pure", "returns", "return",
]
ALLOWED_MEMBERS = re.compile(r"\bmsg\s*\.\s*sender\b|\btype\s*\(\s*u?int\d*\s*\)\s*\.\s*(max|min)\b")
# Struct field reads on token state (protocol v3): `ilks[i].rate`, `urns[i][u].ink`.
ELEMENTARY_CALLS = re.compile(r"^(u?int\d*|address|bool|bytes\d*)$")
KEYWORDS_BEFORE_PAREN = {"if", "else", "require", "assert", "type"}
ASSIGN_OPS = r"(?:\+\+|--|(?:[-+*/%|&^]|<<|>>)?=(?!=))"

ART_FORBIDDEN = ["assert", "assembly", "import", "interface", "library", "immutable",
                 "selfdestruct", "delegatecall", "staticcall", "this", "new", "external", "error"]


@dataclass
class Violation:
    rule: str
    line: int
    message: str

    def __str__(self) -> str:
        return f"{self.rule} line {self.line}: {self.message}"


# The parser lives in the core (the verifier re-derives isolated harnesses with it).
strip_source = core.strip_source
_match_brace = core.match_brace
top_level_items = core.top_level_items


def line_of(text: str, pos: int) -> int:
    return text.count("\n", 0, pos) + 1


def _pragma_rule(raw: str, s: str, v: list[Violation], rule: str) -> None:
    pragmas = [m for m in re.finditer(r"\bpragma\b[^;]*;", s)]
    if len(pragmas) != 1 or " ".join(pragmas[0].group(0).split()) != PRAGMA:
        pos = pragmas[0].start() if pragmas else 0
        v.append(Violation(rule, line_of(s, pos), f"exactly one `{PRAGMA}` and no other pragma"))


# ---------------------------------------------------------------- spec lint

@dataclass
class ArtifactNames:
    state_variables: list[str]
    public_functions: list[str]
    internal_functions: list[str]
    struct_fields: tuple[str, ...] = ()


def names_from_entry(e: dict) -> ArtifactNames:
    return ArtifactNames(e["state_variables"], e["public_functions"], e["internal_functions"],
                         tuple(e.get("struct_fields", ())))


# Names of the placeholder CappedToken; the CLI recomputes them with solc.
DEFAULT_NAMES = ArtifactNames(["balanceOf", "cap", "owner", "totalSupply"], ["mint", "transfer"], ["onlyOwner"])


def lint_spec(raw: str, names: ArtifactNames = DEFAULT_NAMES,
              subject: core.Subject | str | None = None) -> list[Violation]:
    R = SubjectRules(subject if isinstance(subject, core.Subject) else core.load_subject(subject))
    SPEC_IMPORT, SPEC_HEAD = R.spec_import, R.spec_head
    v: list[Violation] = []
    s = strip_source(raw)
    sk = strip_source(raw, keep_strings=True)

    # S1 pragma
    _pragma_rule(raw, s, v, "S1")
    # S2 import
    imports = list(re.finditer(r"\bimport\b[^;]*;", sk))
    if len(imports) != 1 or " ".join(imports[0].group(0).split()) != SPEC_IMPORT:
        v.append(Violation("S2", line_of(s, imports[0].start()) if imports else 1,
                           f"exactly one import, `{SPEC_IMPORT}`"))

    # S3 exactly one top-level contract `contract Spec is CappedToken`
    top = [it for it in top_level_items(s, 0, len(s))
           if not it[2].startswith("pragma ") and not it[2].startswith("import ")]
    contracts = [it for it in top if SPEC_HEAD.match(it[2])]
    for it in top:
        if not SPEC_HEAD.match(it[2]):
            v.append(Violation("S3", line_of(s, it[0]), f"only `contract Spec is CappedToken {{...}}` "
                               f"may appear at top level, got `{it[2][:60]}`"))
    if len(contracts) != 1:
        if not any(x.rule == "S3" for x in v):
            v.append(Violation("S3", 1, "exactly one `contract Spec is CappedToken`"))
        return v
    c_start, c_end, _ = contracts[0]
    body_open = s.index("{", c_start)

    # S4 members: the constructor and check_* functions only
    ctors, checks = [], []
    for st, en, head in top_level_items(s, body_open + 1, c_end - 1):
        if head.startswith("constructor"):
            if R.norm_ctor(s[st:en]) == R.spec_ctor:
                ctors.append(st)
            else:
                v.append(Violation("S4", line_of(s, st), "constructor must be exactly "
                                   "`{R.subject.spec_constructor}`"))
        elif R.check_head(head):
            checks.append((R.check_head(head).group(1), st, en))
        else:
            v.append(Violation("S4", line_of(s, st), "only the constructor and "
                               f"`function check_<name>{' or '.join(R.check_sigs)} external`"
                               f" may be declared in Spec, got `{head[:60]}`"))
    if len(ctors) != 1:
        v.append(Violation("S4", line_of(s, c_start), "exactly one constructor"))
    if not checks:
        v.append(Violation("S4", line_of(s, c_start), "at least one check_* function"))

    # S5 forbidden tokens anywhere
    for tok in SPEC_FORBIDDEN:
        for m in re.finditer(rf"\b{tok}\b", s):
            v.append(Violation("S5", line_of(s, m.start()), f"forbidden token `{tok}`"))

    # S6 member access only msg.sender / type(T).max|min (no external calls, no .balance/.code)
    masked = ALLOWED_MEMBERS.sub(lambda m: " " * len(m.group(0)), s)
    if names.struct_fields:
        fields = "|".join(map(re.escape, names.struct_fields))
        masked = re.sub(rf"\]\s*\.\s*({fields})\b", lambda m: " " * len(m.group(0)), masked)
    for m in re.finditer(r"\.\s*[A-Za-z_]", masked):
        v.append(Violation("S6", line_of(s, m.start()), "member access other than msg.sender / type(T).max|min"))

    # S7 no writes to, or shadowing of, token state; no tuple assignment
    token_names = names.state_variables + names.public_functions + names.internal_functions
    for nm in names.state_variables:
        for m in re.finditer(rf"\b{nm}\b(\s*\[[^\]]*\]|\s*\.\s*\w+)*\s*{ASSIGN_OPS}", s):
            v.append(Violation("S7", line_of(s, m.start()), f"write to token state `{nm}`"))
        for m in re.finditer(rf"(\+\+|--)\s*\b{nm}\b", s):
            v.append(Violation("S7", line_of(s, m.start()), f"write to token state `{nm}`"))
    for nm in token_names + list(names.struct_fields) + R.subject.probe_names:
        for m in re.finditer(rf"\b(u?int\d*|address|bool|bytes\d*|string)\s+{nm}\b(?!\s*[,)])", s):
            v.append(Violation("S7", line_of(s, m.start()), f"declaration shadows `{nm}`"))
    for m in re.finditer(r"\)\s*=(?!=)", s):
        v.append(Violation("S7", line_of(s, m.start()), "tuple assignment"))

    # S8 calls: only public token functions, require, assert, type conversions
    allowed_calls = set(names.public_functions) | KEYWORDS_BEFORE_PAREN
    for _, st, en in checks:
        body_start = s.index("{", st) + 1
        for m in re.finditer(r"\b([A-Za-z_]\w*)\s*\(", s[body_start:en]):
            nm = m.group(1)
            if nm not in allowed_calls and not ELEMENTARY_CALLS.match(nm):
                v.append(Violation("S8", line_of(s, body_start + m.start()),
                                   f"call to `{nm}`: only public token functions, require, assert, type(...)"))

    # S9 check bodies: leading requires = Pre; asserts one per line as statements;
    # at least one assert; the check observes the token.
    for name, st, en in checks:
        body_start = s.index("{", st) + 1
        stmts = top_level_items(s, body_start, en - 1)
        lead_end = body_start
        for _, b_, head in stmts:
            if not re.match(r"^require\s*\(", head):
                break
            lead_end = b_
        for m in re.finditer(r"\brequire\s*\(", s[body_start:en]):
            if body_start + m.start() >= lead_end:
                v.append(Violation("S9", line_of(s, body_start + m.start()),
                                   f"{name}: require only in the leading block (Pre)"))
        asserts = list(re.finditer(r"\bassert\s*\(", s[body_start:en]))
        if not asserts:
            v.append(Violation("S9", line_of(s, st), f"{name}: at least one assert"))
        seen_lines = set()
        for m in asserts:
            pos = body_start + m.start()
            ln = line_of(s, pos)
            line_text = s.splitlines()[ln - 1]
            if not re.match(r"^\s*assert\s*\(", line_text) or ln in seen_lines:
                v.append(Violation("S9", ln, f"{name}: each assert must start its own line, one per line"))
            seen_lines.add(ln)
        body = s[body_start:en]
        if not any(re.search(rf"\b{nm}\b", body) for nm in names.state_variables + names.public_functions):
            v.append(Violation("S9", line_of(s, st), f"{name}: reads no token state and calls no token function"))
    return v


def pre_probe_source(raw: str, check: str) -> str:
    """Vacuity check (a): the spec text with `assert(false);` inserted right after
    the leading requires of `check` (or at the top of its body if none)."""
    s = strip_source(raw)
    m = re.search(rf"function\s+{re.escape(check)}\s*\(", s)
    if not m:
        raise ValueError(f"no function {check}")
    body_open = s.index("{", m.end())
    end = _match_brace(s, body_open)
    insert_at = body_open + 1
    for a, b_, head in top_level_items(s, body_open + 1, end):
        if re.match(r"^require\s*\(", head):
            insert_at = b_
        else:
            break
    return raw[:insert_at] + "\n        assert(false); // SPECGAME-PRE-PROBE" + raw[insert_at:]


# ---------------------------------------------------------------- artifact lint

def pragma_admits(expr: str, version: str) -> bool:
    """Does a `pragma solidity <expr>` admit `version`? Supports conjunctions of
    `x.y.z`, `=x.y.z`, `^x.y.z`, `~x.y.z`, `>=`, `>`, `<=`, `<` (no `||`)."""
    v = tuple(int(x) for x in version.split("."))
    toks = expr.replace(">= ", ">=").replace("<= ", "<=").replace("> ", ">").replace("< ", "<").split()
    if not toks or "||" in expr:
        return False
    for t in toks:
        m = re.match(r"^(\^|~|>=|<=|>|<|=)?(\d+)(?:\.(\d+))?(?:\.(\d+))?$", t)
        if not m:
            return False
        op, parts = m.group(1) or "=", tuple(int(x) for x in m.groups()[1:] if x is not None)
        w = parts + (0,) * (3 - len(parts))
        if op == "=":
            ok = v[:len(parts)] == parts
        elif op == "^":
            ok = v >= w and (v[:1] == w[:1] if w[0] > 0 else v[:2] == w[:2])
        elif op == "~":
            ok = v >= w and v[:2] == w[:2]
        else:
            ok = {">=": v >= w, ">": v > w, "<=": v <= w, "<": v < w}[op]
        if not ok:
            return False
    return True


def custom_error_lines(s: str) -> list[int]:
    """Lines of `revert Name(...)` and of `require(cond, X)` whose second
    top-level argument is not a string literal (s: comments and strings blanked)."""
    out = [line_of(s, m.start()) for m in re.finditer(r"\brevert\s+[A-Za-z_]", s)]
    for m in re.finditer(r"\brequire\s*\(", s):
        depth, args, start, k = 0, [], m.end(), m.end()
        while k < len(s):
            ch = s[k]
            if ch in "([{":
                depth += 1
            elif ch in ")]}":
                if depth == 0:
                    args.append(s[start:k])
                    break
                depth -= 1
            elif ch == "," and depth == 0:
                args.append(s[start:k])
                start = k + 1
            k += 1
        if len(args) >= 2 and not args[1].strip().startswith(('"', "'")):
            out.append(line_of(s, m.start()))
    return out


def lint_artifact(raw: str, subject: core.Subject | str | None = None) -> list[Violation]:
    """Artifact rules (protocol v3, relaxed for real contracts): A1 one pragma
    admitting the pinned solc; A2 one top-level `contract <Name>`; A3 no assert,
    assembly, import, interface, library, immutable, selfdestruct,
    delegatecall, staticcall, this, new, external, error, no external calls or
    address members; A4 no custom errors; A5 one constructor with the profile's
    parameter types. Structs, modifiers, unchecked blocks, internal helpers,
    several mappings and reason strings are allowed."""
    R = SubjectRules(subject if isinstance(subject, core.Subject) else core.load_subject(subject))
    name = R.subject.contract
    v: list[Violation] = []
    s = strip_source(raw)
    pragmas = list(re.finditer(r"\bpragma\b[^;]*;", s))
    if len(pragmas) != 1:
        v.append(Violation("A1", line_of(s, pragmas[1].start()) if len(pragmas) > 1 else 1,
                           "exactly one pragma (`pragma solidity ...;`)"))
    else:
        m = re.match(r"pragma\s+solidity\s+(.*);$", " ".join(pragmas[0].group(0).split()))
        if not m or not pragma_admits(m.group(1), core.SOLC_VERSION.split("+")[0]):
            v.append(Violation("A1", line_of(s, pragmas[0].start()),
                               f"the pragma must admit solc {core.SOLC_VERSION.split('+')[0]}"))
    top = [it for it in top_level_items(s, 0, len(s)) if not it[2].startswith("pragma ")]
    heads = [it for it in top if R.art_head.match(it[2])]
    for it in top:
        if not R.art_head.match(it[2]):
            v.append(Violation("A2", line_of(s, it[0]), f"only `contract {name} {{...}}` at top level, "
                               f"got `{it[2][:60]}`"))
    if len(heads) != 1:
        if not any(x.rule == "A2" for x in v):
            v.append(Violation("A2", 1, f"exactly one `contract {name}`"))
        return v
    for tok in ART_FORBIDDEN:
        for m in re.finditer(rf"\b{tok}\b", s):
            v.append(Violation("A3", line_of(s, m.start()), f"forbidden token `{tok}`"))
    for m in re.finditer(r"\.\s*(call|send|transfer|code|balance)\b", s):
        v.append(Violation("A3", line_of(s, m.start()), "external interaction / address member"))
    for line_no in custom_error_lines(s):
        v.append(Violation("A4", line_no, "custom errors are forbidden (use require/revert with a string)"))
    c_start, c_end, _ = heads[0]
    ctors = [(st, en, h) for st, en, h in top_level_items(s, s.index("{", c_start) + 1, c_end - 1)
             if h.startswith("constructor")]
    ok = False
    if len(ctors) == 1:
        m = re.match(r"^constructor\s*\(([^)]*)\)", ctors[0][2])
        if m:
            params = [p.split()[0] for p in m.group(1).split(",") if p.strip()]
            ok = params == R.ctor_types
    if not ok:
        v.append(Violation("A5", line_of(s, ctors[0][0]) if ctors else 1,
                           f"exactly one constructor with parameter types {R.ctor_types}"))
    return v


# ---------------------------------------------------------------- CLI

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("kind", choices=["spec", "artifact"])
    ap.add_argument("path")
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--artifact", help="artifact whose names the spec may use (default: the subject's b); "
                    "compiled with the pinned solc")
    a = ap.parse_args(argv)
    raw = Path(a.path).read_text()
    subj = core.load_subject(a.subject)
    if a.kind == "artifact":
        vs = lint_artifact(raw, subj)
    else:
        e = core.compile_artifact(a.artifact or subj.source_path, subject=subj)
        vs = lint_spec(raw, names_from_entry(e), subj)
    for x in vs:
        print(f"{a.path}: {x}")
    if not vs:
        print(f"{a.path}: OK")
    return 1 if vs else 0


if __name__ == "__main__":
    sys.exit(main())
