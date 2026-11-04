"""Specification Games shared core (hashed into every bundle).

The one module that adversary, scorer, bundle builder and verifier all use for
the judge path: hashing, compilation with the pinned flags, the deterministic
executor (pyrevm), the outcome rule (Condition D) and the strict SMTChecker
classifier. Stdlib + pyrevm only; no network, no LLM. The definitions it
implements are fixed in `protocol.md` and `specs/SPEC_FORMAT.md`; where this
file and those documents disagree, that is a bug in one of them.
"""
from __future__ import annotations

import enum
import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

CORE_VERSION = 2  # v2: Spec deploys lift EIP-170 / EIP-3860 (protocol.json executor)

ROOT = Path(__file__).resolve().parent.parent  # specgame/

# ---------------------------------------------------------------- pins

# Every value that affects a verdict or reproduction is read from protocol.json
# (authoritative, frozen); nothing here duplicates it. protocol_json_sha256 is
# recorded in every bundle and compared by the verifier.
def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


PROTOCOL_PATH = ROOT / "protocol.json"
PROTOCOL: dict = json.loads(PROTOCOL_PATH.read_text())
PROTOCOL_VERSION: int = PROTOCOL["protocol_version"]
if PROTOCOL_VERSION != 3 or PROTOCOL["check"]["mode"] != "isolated":
    raise ImportError(f"this core implements protocol v3 (subjects, isolated Check); protocol.json says "
                      f"version {PROTOCOL_VERSION}, mode {PROTOCOL['check'].get('mode')}")

SOLC_VERSION = PROTOCOL["compiler"]["solc_version"]
Z3_VERSION = PROTOCOL["compiler"]["z3_version"]
PYREVM_VERSION = PROTOCOL["executor"]["pyrevm_version"]
EVM_VERSION = PROTOCOL["compiler"]["settings"]["evmVersion"]
SPEC_ID = PROTOCOL["executor"]["spec_id"]

SPEC_UNIT = PROTOCOL["compiler"]["units"]["spec"]
SPEC_CONTRACT = "Spec"
CHECK_PREFIX = "check_"
TYPES = ("address", "bytes32", "uint256", "int256")

UINT256_MAX = 2**256 - 1
INT256_MIN, INT256_MAX = -2**255, 2**255 - 1


# ---------------------------------------------------------------- subjects (protocol v3)

class ProfileError(Exception):
    pass


@dataclass(frozen=True)
class Subject:
    """A subject = one artifact b with its profile (subjects/<name>/profile.json,
    sha256 pinned in protocol.json). Everything subject-specific the judge path
    needs comes from here."""
    name: str
    profile: dict
    dir: Path

    @property
    def unit(self) -> str:                       # solc unit name of the artifact = spec import
        return self.profile["contract"]["file"]

    @property
    def contract(self) -> str:
        return self.profile["contract"]["name"]

    @property
    def source_path(self) -> Path:
        return self.dir / self.unit

    @property
    def mutants_dir(self) -> Path:
        return self.dir / "mutants"

    @property
    def specs_dir(self) -> Path:
        return self.dir / "specs"

    @property
    def intent_path(self) -> Path:
        return self.dir / "intent.md"

    @property
    def ctor_params(self) -> list[tuple[str, str]]:
        return [(p["name"], p["type"]) for p in self.profile["constructor"]["params"]]

    @property
    def spec_constructor(self) -> str:
        return self.profile["spec"]["constructor"]

    @property
    def probes(self) -> list[list[tuple[str, str]]]:
        return [[(p["name"], p["type"]) for p in sig] for sig in self.profile["spec"]["probes"]]

    @property
    def probe_sigs(self) -> list[str]:
        """Canonical parameter lists, e.g. "(address,address,uint256,uint256)"."""
        return ["(" + ",".join(t for _, t in sig) + ")" for sig in self.probes]

    @property
    def probe_names(self) -> list[str]:
        return [n for sig in self.probes for n, _ in sig]

    @property
    def senders(self) -> tuple[str, ...]:
        return tuple(self.profile["senders"])

    def pool(self, typ: str) -> dict[str, str]:
        return dict(self.profile["pools"].get(typ, {}))

    @property
    def addresses(self) -> dict[str, str]:
        return self.pool("address")

    @property
    def functions(self) -> list[str]:
        return list(self.profile["functions"])

    @property
    def setup(self) -> list[dict]:
        return list(self.profile["setup"])

    @property
    def observation(self) -> list[dict]:
        return list(self.profile["observation"])

    def header(self) -> str:
        """The fixed spec header (speclint S1-S4 make it the only legal one)."""
        return ("// SPDX-License-Identifier: MIT\n"
                f"pragma solidity {SOLC_VERSION.split('+')[0]};\n\n"
                f'import "./{self.unit}";\n\n'
                f"contract Spec is {self.contract} {{\n"
                f"    {self.spec_constructor}\n\n    ")


SUBJECTS_DIR = ROOT / "subjects"
DEFAULT_SUBJECT: str = PROTOCOL["default_subject"]
_SUBJECTS: dict[str, Subject] = {}


def _check_profile(prof: dict, name: str) -> None:
    """The structural rules the schema cannot express."""
    if prof.get("version") != 1 or prof.get("name") != name:
        raise ProfileError(f"profile {name}: version must be 1 and name {name!r}")
    addrs = prof["pools"]["address"]
    if not set(prof["senders"]) <= set(addrs):
        raise ProfileError(f"profile {name}: senders not in pools.address")
    for t in prof["setup"]:
        if t.get("sender") is not None and t["sender"] not in prof["senders"]:
            raise ProfileError(f"profile {name}: setup sender {t['sender']!r} not in senders")
    names = [p["name"] for sig in prof["spec"]["probes"] for p in sig]
    if len(set(names)) != len(names) or "sender" in names or "check" in names:
        raise ProfileError(f"profile {name}: probe parameter names must be distinct, not sender/check")
    for typ in ("address", "bytes32"):
        for k in prof["pools"].get(typ, {}):
            if not re.match(r"^[A-Za-z_][A-Za-z0-9_]*$", k):
                raise ProfileError(f"profile {name}: pool name {k!r}")


def load_subject(name: str | None = None) -> Subject:
    """The subject `name` (default: protocol.json default_subject). Its profile's
    sha256 must equal the one protocol.json pins for it."""
    name = name or DEFAULT_SUBJECT
    if name not in _SUBJECTS:
        pin = PROTOCOL["subjects"].get(name)
        if pin is None:
            raise ProfileError(f"subject {name!r} is not in protocol.json")
        path = ROOT / pin["profile"]
        raw = path.read_bytes()
        if sha256_hex(raw) != pin["profile_sha256"]:
            raise ProfileError(f"{path}: sha256 {sha256_hex(raw)[:16]}… != protocol.json pin "
                               f"{pin['profile_sha256'][:16]}…")
        prof = json.loads(raw)
        _check_profile(prof, name)
        _SUBJECTS[name] = Subject(name, prof, path.parent)
    return _SUBJECTS[name]


def subject_from_bytes(name: str, raw: bytes) -> Subject:
    """A subject from a profile's bytes (e.g. the copy carried by a bundle),
    accepted only if its sha256 is the one protocol.json pins for `name`; it
    then replaces the cached subject of that name (same bytes, so the same
    profile as the installation's)."""
    pin = PROTOCOL["subjects"].get(name)
    if pin is None:
        raise ProfileError(f"subject {name!r} is not in protocol.json")
    if sha256_hex(raw) != pin["profile_sha256"]:
        raise ProfileError(f"profile of subject {name!r}: sha256 {sha256_hex(raw)[:16]}… is not the "
                           f"protocol.json pin {pin['profile_sha256'][:16]}…")
    prof = json.loads(raw)
    _check_profile(prof, name)
    subj = Subject(name, prof, (ROOT / pin["profile"]).parent)
    _SUBJECTS[name] = subj
    return subj


def subject_of(entry: dict) -> Subject:
    return load_subject(entry.get("subject"))


# Default-subject names kept for callers that predate subjects (capped token).
_D = load_subject()
ARTIFACT_UNIT = _D.unit
ARTIFACT_CONTRACT = _D.contract
POOL: dict[str, str] = _D.addresses
SENDERS = _D.senders
PROBE_PARAMS = _D.probe_sigs[0]
CTOR_PARAMS = tuple(n for n, _ in _D.ctor_params)


# Executor environment, fixed for every run.
TX_GAS = PROTOCOL["executor"]["tx_gas"]
BLOCK_ENV = dict(PROTOCOL["executor"]["block_env"])
CHAIN_ID = PROTOCOL["executor"]["chain_id"]
# Core v2: deploys run with a lifted code size limit (the Spec is a measurement
# harness, never deployed) and the block gas limit; b and every mutant must
# still fit EIP-170, so no subject-side observation can depend on the lift.
DEPLOY_GAS = PROTOCOL["executor"]["deploy_gas"]
CODE_SIZE_LIMIT = PROTOCOL["executor"]["contract_code_size_limit"]
INITCODE_SIZE_LIMIT = PROTOCOL["executor"]["initcode_size_limit"]  # revm derives 2 x CODE_SIZE_LIMIT
SUBJECT_RUNTIME_LIMIT = PROTOCOL["executor"]["subject_runtime_limit"]  # EIP-170
assert INITCODE_SIZE_LIMIT == 2 * CODE_SIZE_LIMIT and DEPLOY_GAS <= BLOCK_ENV["gas_limit"]

# Check(b, phi): frozen solver budget (protocol.md section 9).
CHECK_TIMEOUT_MS: int = PROTOCOL["check"]["timeout_ms"]
CHECK_WALL_TIMEOUT_S: float = PROTOCOL["check"]["wall_timeout_s"]

# ---------------------------------------------------------------- hashing

def sha256_file(path: str | Path) -> str:
    return sha256_hex(Path(path).read_bytes())


def canonical_json(obj: Any) -> bytes:
    """Canonical JSON bytes: sorted keys, no whitespace, ASCII, trailing newline."""
    return (json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True) + "\n").encode()


def json_sha256(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


# ---------------------------------------------------------------- toolchain

@dataclass(frozen=True)
class Toolchain:
    solc: Path
    z3: Path | None  # None: solc runs with no z3 on PATH (negative controls only)

    @staticmethod
    def default() -> "Toolchain":
        solc = os.environ.get("SPECGAME_SOLC", str(ROOT / ".toolchain" / "bin" / "solc"))
        z3 = os.environ.get("SPECGAME_Z3", str(ROOT / ".toolchain" / "bin" / "z3"))
        return Toolchain(Path(solc).resolve(), Path(z3).resolve())

    def solver_env(self, empty_dir: str) -> dict[str, str]:
        # solc >= 0.8.29 runs z3 as an external process found on PATH. The PATH
        # holds only the pinned z3's directory plus /usr/bin:/bin, so a
        # system-wide z3 (e.g. /usr/local/bin/z3) can never be picked up.
        z3_dir = str(self.z3.parent) if self.z3 is not None else empty_dir
        path = f"{z3_dir}:/usr/bin:/bin" if self.z3 is not None else empty_dir
        return {"PATH": path, "LC_ALL": "C"}


def toolchain_fingerprint(tc: Toolchain | None = None) -> dict:
    """Semantics version: everything a verdict or a run depends on."""
    import importlib.metadata
    import platform
    tc = tc or Toolchain.default()
    solc_out = subprocess.run([str(tc.solc), "--version"], capture_output=True, text=True).stdout
    m = re.search(r"Version: (\S+)", solc_out)
    fp = {
        "solc": {"version": m.group(1) if m else None, "sha256": sha256_file(tc.solc)},
        "z3": None,
        "python": platform.python_version(),
        "pyrevm": importlib.metadata.version("pyrevm"),
        "evm_version": EVM_VERSION,
        "spec_id": SPEC_ID,
        "tx_gas": TX_GAS,
        "executor_limits": {"deploy_gas": DEPLOY_GAS, "contract_code_size_limit": CODE_SIZE_LIMIT,
                            "initcode_size_limit": INITCODE_SIZE_LIMIT,
                            "subject_runtime_limit": SUBJECT_RUNTIME_LIMIT},
        "block_env": BLOCK_ENV,
        "chain_id": CHAIN_ID,
        "core_version": CORE_VERSION,
        "core_sha256": sha256_file(__file__),
    }
    if tc.z3 is not None:
        z3_out = subprocess.run([str(tc.z3), "--version"], capture_output=True, text=True).stdout.strip()
        fp["z3"] = {"version": z3_out, "sha256": sha256_file(tc.z3)}
    return fp


def toolchain_problems(tc: Toolchain | None = None) -> list[str]:
    """Empty list iff the toolchain matches the pins."""
    fp = toolchain_fingerprint(tc)
    problems = []
    if not (fp["solc"]["version"] or "").startswith(SOLC_VERSION + "."):
        problems.append(f"solc {fp['solc']['version']}, want {SOLC_VERSION}")
    if fp["z3"] is None or not fp["z3"]["version"].startswith(f"Z3 version {Z3_VERSION} "):
        problems.append(f"z3 {fp['z3']}, want {Z3_VERSION}")
    if fp["pyrevm"] != PYREVM_VERSION:
        problems.append(f"pyrevm {fp['pyrevm']}, want {PYREVM_VERSION}")
    return problems


# ---------------------------------------------------------------- solc

class CompileError(Exception):
    pass


BASE_SETTINGS = json.loads(json.dumps(PROTOCOL["compiler"]["settings"]))
COMPILE_OUTPUTS = ["abi", "evm.bytecode.object", "evm.deployedBytecode.object",
                   "evm.methodIdentifiers", "metadata"]


def solc_input(sources: dict[str, str], model_checker: dict | None = None) -> dict:
    """The exact standard-JSON input. Sources are passed as content under fixed
    unit names; nothing is read from disk by solc."""
    settings = json.loads(json.dumps(BASE_SETTINGS))
    if model_checker is None:
        settings["outputSelection"] = {"*": {"": ["ast"], "*": COMPILE_OUTPUTS}}
    else:
        settings["modelChecker"] = model_checker
        settings["outputSelection"] = {"*": {"": ["ast"]}}
    return {"language": "Solidity",
            "sources": {name: {"content": text} for name, text in sorted(sources.items())},
            "settings": settings}


def run_solc(inp: dict, tc: Toolchain, wall_timeout_s: float) -> tuple[dict | None, str, float]:
    """Run `solc --standard-json` in an empty temp dir with a sanitized env.
    Returns (parsed output or None on wall timeout, raw stdout, seconds)."""
    with tempfile.TemporaryDirectory(prefix="specgame-solc-") as tmp:
        empty = os.path.join(tmp, "empty")
        os.mkdir(empty)
        t0 = time.monotonic()
        try:
            p = subprocess.run([str(tc.solc), "--standard-json"], input=json.dumps(inp),
                               cwd=tmp, env=tc.solver_env(empty), capture_output=True,
                               text=True, timeout=wall_timeout_s)
        except subprocess.TimeoutExpired:
            return None, "", time.monotonic() - t0
        dt = time.monotonic() - t0
    if p.returncode != 0:
        raise CompileError(f"solc exit {p.returncode}: {p.stderr.strip()[:500]}")
    return json.loads(p.stdout), p.stdout, dt


def _errors(out: dict) -> list[dict]:
    return [e for e in out.get("errors", []) if e.get("severity") == "error"]


def _ast_nodes(node: Any):
    if isinstance(node, dict):
        yield node
        for v in node.values():
            yield from _ast_nodes(v)
    elif isinstance(node, list):
        for v in node:
            yield from _ast_nodes(v)


def _artifact_names(out: dict, subject: Subject) -> dict:
    """State variable, function and struct field names of the subject's contract, from the AST."""
    ast = out["sources"][subject.unit]["ast"]
    state_vars, public_fns, other_fns, fields = [], [], [], []
    for n in _ast_nodes(ast):
        if n.get("nodeType") == "ContractDefinition" and n.get("name") == subject.contract:
            for m in n.get("nodes", []):
                if m.get("nodeType") == "VariableDeclaration" and m.get("stateVariable"):
                    state_vars.append(m["name"])
                elif m.get("nodeType") == "FunctionDefinition" and m.get("kind") == "function":
                    (public_fns if m.get("visibility") in ("public", "external") else other_fns).append(m["name"])
                elif m.get("nodeType") == "ModifierDefinition":
                    other_fns.append(m["name"])
                elif m.get("nodeType") == "StructDefinition":
                    fields += [x["name"] for x in m.get("members", [])]
    return {"state_variables": sorted(set(state_vars)), "public_functions": sorted(set(public_fns)),
            "internal_functions": sorted(set(other_fns)), "struct_fields": sorted(set(fields))}


def _entry(out: dict, unit: str, contract: str, inp: dict) -> dict:
    c = out["contracts"][unit][contract]
    runtime_hex = c["evm"]["deployedBytecode"]["object"]
    if not runtime_hex:
        raise CompileError(f"{unit}:{contract} has empty runtime bytecode")
    return {
        "contract": contract,
        "abi": c["abi"],
        "bin": c["evm"]["bytecode"]["object"],
        "bin_runtime": runtime_hex,
        "hashes": c["evm"]["methodIdentifiers"],
        "metadata": c["metadata"],
        "runtime_sha256": sha256_hex(bytes.fromhex(runtime_hex)),
        "solc_input_sha256": json_sha256(inp),
    }


def compile_artifact(artifact_path: str | Path, tc: Toolchain | None = None,
                     wall_timeout_s: float = 120, subject: Subject | str | None = None) -> dict:
    """Compile an artifact (b or a mutant) as the subject's contract.
    Identity of the artifact = `runtime_sha256` (sha256 of compiled runtime)."""
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    tc = tc or Toolchain.default()
    text = Path(artifact_path).read_text()
    inp = solc_input({subj.unit: text})
    out, _, _ = run_solc(inp, tc, wall_timeout_s)
    if out is None:
        raise CompileError("solc wall timeout")
    if _errors(out):
        raise CompileError("; ".join(e["message"] for e in _errors(out))[:800])
    entry = _entry(out, subj.unit, subj.contract, inp)
    entry["subject"] = subj.name
    entry["source_sha256"] = sha256_hex(text.encode())
    entry.update(_artifact_names(out, subj))
    return entry


def compile_spec_over(spec_path: str | Path, artifact_path: str | Path, tc: Toolchain | None = None,
                      wall_timeout_s: float = 120, subject: Subject | str | None = None) -> dict:
    """Compile spec φ (contract Spec is <subject contract>) over an artifact.
    Identity of the pair (φ, artifact) = `runtime_sha256` of Spec."""
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    tc = tc or Toolchain.default()
    spec_text = Path(spec_path).read_text()
    art_text = Path(artifact_path).read_text()
    inp = solc_input({SPEC_UNIT: spec_text, subj.unit: art_text})
    out, _, _ = run_solc(inp, tc, wall_timeout_s)
    if out is None:
        raise CompileError("solc wall timeout")
    if _errors(out):
        raise CompileError("; ".join(e["message"] for e in _errors(out))[:800])
    entry = _entry(out, SPEC_UNIT, SPEC_CONTRACT, inp)
    entry["subject"] = subj.name
    entry["spec_source_sha256"] = sha256_hex(spec_text.encode())
    entry["artifact_source_sha256"] = sha256_hex(art_text.encode())
    entry["check_sigs"] = check_signatures(entry, subj)
    entry["checks"] = sorted(entry["check_sigs"])
    return entry


def check_signatures(entry: dict, subject: Subject) -> dict[str, str]:
    """check_* name -> its parameter list; every one must be a probe signature of the subject."""
    out = {}
    for sig in entry["hashes"]:
        name = sig.split("(", 1)[0]
        if name.startswith(CHECK_PREFIX):
            params = sig[len(name):]
            if params not in subject.probe_sigs:
                raise CompileError(f"{sig}: check_* must have one of the signatures {subject.probe_sigs}")
            out[name] = params
    return out


def spec_checks(entry: dict) -> list[str]:
    """Names of the check_* probes, sorted (each with a probe signature of its subject)."""
    return sorted(check_signatures(entry, subject_of(entry)))


# ---------------------------------------------------------------- outcome rule (Condition D)

class Outcome(str, enum.Enum):
    SUCCESS = "success"      # call returned normally: the probe is satisfied
    VIOLATION = "violation"  # Panic(0x01) from the probe: a witness
    PRE_UNMET = "pre_unmet"  # Error(string) or empty revert: Pre not met, not a witness
    OTHER = "other"          # any other panic, custom error, malformed data, halt: not a witness


PANIC_SELECTOR = bytes.fromhex("4e487b71")
ERROR_SELECTOR = bytes.fromhex("08c379a0")


def _is_error_string(data: bytes) -> bool:
    """Strict ABI check of Error(string) revert data."""
    if len(data) < 4 + 64 or data[:4] != ERROR_SELECTOR or (len(data) - 4) % 32:
        return False
    body = data[4:]
    if int.from_bytes(body[:32], "big") != 32:
        return False
    n = int.from_bytes(body[32:64], "big")
    padded = (n + 31) // 32 * 32
    if len(body) != 64 + padded:
        return False
    return not any(body[64 + n:])


def classify_outcome(revert_data: bytes | None) -> Outcome:
    """The outcome rule. `None` = the call succeeded; bytes = revert data.
    (Halts such as out-of-gas never reach here; the executor maps them to OTHER.)"""
    if revert_data is None:
        return Outcome.SUCCESS
    if revert_data == b"":
        return Outcome.PRE_UNMET
    if len(revert_data) == 36 and revert_data[:4] == PANIC_SELECTOR:
        code = int.from_bytes(revert_data[4:], "big")
        return Outcome.VIOLATION if code == 1 else Outcome.OTHER
    if _is_error_string(revert_data):
        return Outcome.PRE_UNMET
    return Outcome.OTHER


def describe_revert(revert_data: bytes | None) -> str:
    """Human-readable detail for logs (never compared, never a verdict)."""
    if revert_data is None:
        return "success"
    if revert_data == b"":
        return "revert()"
    if len(revert_data) == 36 and revert_data[:4] == PANIC_SELECTOR:
        return f"Panic(0x{int.from_bytes(revert_data[4:], 'big'):02x})"
    if _is_error_string(revert_data):
        n = int.from_bytes(revert_data[36:68], "big")
        return "Error(" + json.dumps(revert_data[68:68 + n].decode("utf-8", "replace")) + ")"
    return "revert 0x" + revert_data.hex()


# ---------------------------------------------------------------- configurations σ

class SigmaError(ValueError):
    pass


_UINT_RE = re.compile(r"^(0|[1-9][0-9]*)$")
_INT_RE = re.compile(r"^(0|-?[1-9][0-9]*)$")
_SIG_RE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)\(((?:address|bytes32|uint256|int256)"
                     r"(?:,(?:address|bytes32|uint256|int256))*)?\)$")


def sig_types(sig: str) -> list[str]:
    inner = sig[sig.index("(") + 1:-1]
    return inner.split(",") if inner else []


def _value(v: Any, typ: str, what: str, subject: Subject) -> None:
    if typ in ("address", "bytes32"):
        pool = subject.pool(typ)
        if not isinstance(v, str) or v not in pool:
            raise SigmaError(f"{what}: want a {typ} pool name {sorted(pool)}, got {v!r}")
    elif typ == "uint256":
        if not isinstance(v, str) or not _UINT_RE.match(v) or int(v) > UINT256_MAX:
            raise SigmaError(f"{what}: want a decimal uint256 string, got {v!r}")
    elif typ == "int256":
        if not isinstance(v, str) or not _INT_RE.match(v) or not INT256_MIN <= int(v) <= INT256_MAX:
            raise SigmaError(f"{what}: want a decimal int256 string, got {v!r}")
    else:
        raise SigmaError(f"{what}: unsupported type {typ}")


def _uint(v: Any, what: str) -> int:
    _value(v, "uint256", what, load_subject())
    return int(v)


def validate_sigma(sigma: Any, need_probe: bool = False, subject: Subject | str | None = None) -> None:
    """Structural check of σ against schemas/sigma.schema.json and the subject's
    profile (hand-written, so the verifier needs no JSON-Schema library)."""
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    if not isinstance(sigma, dict):
        raise SigmaError("sigma must be an object")
    allowed = {"version", "deployer", "ctor", "setup", "txs", "probe"}
    if set(sigma) - allowed or not {"version", "deployer", "ctor", "txs"} <= set(sigma):
        raise SigmaError(f"sigma keys {sorted(sigma)}; want {sorted(allowed)} (setup, probe optional)")
    if sigma["version"] != 1:
        raise SigmaError("sigma.version must be 1")
    if sigma["deployer"] not in subj.senders:
        raise SigmaError(f"deployer: want one of {list(subj.senders)}, got {sigma['deployer']!r}")
    names = [n for n, _ in subj.ctor_params]
    if not isinstance(sigma["ctor"], dict) or set(sigma["ctor"]) != set(names):
        raise SigmaError(f"ctor must have exactly {names}")
    for n, t in subj.ctor_params:
        _value(sigma["ctor"][n], t, f"ctor.{n}", subj)
    # The subject's setup is part of σ (canonical form and hash): exactly the
    # profile's transactions, sent by σ's deployer; absent for a subject without one.
    want_setup = setup_for(subj, sigma["deployer"])
    if want_setup:
        if sigma.get("setup") != want_setup:
            raise SigmaError("setup must be exactly the profile's setup, sent by the deployer")
    elif "setup" in sigma:
        raise SigmaError(f"subject {subj.name} has no setup; sigma.setup must be absent")
    if not isinstance(sigma["txs"], list):
        raise SigmaError("txs must be a list")
    for i, tx in enumerate(sigma["txs"]):
        if not isinstance(tx, dict) or set(tx) != {"sender", "fn", "args"}:
            raise SigmaError(f"txs[{i}] must have exactly sender, fn, args")
        if tx["sender"] not in subj.senders:
            raise SigmaError(f"txs[{i}].sender: want one of {list(subj.senders)}, got {tx['sender']!r}")
        m = _SIG_RE.match(tx["fn"]) if isinstance(tx["fn"], str) else None
        if not m or m.group(1).startswith(CHECK_PREFIX):
            raise SigmaError(f"txs[{i}].fn {tx['fn']!r}: want a contract signature over {list(TYPES)}")
        types = sig_types(tx["fn"])
        if not isinstance(tx["args"], list) or len(tx["args"]) != len(types):
            raise SigmaError(f"txs[{i}].args: want {len(types)} args for {tx['fn']}")
        for j, (t, v) in enumerate(zip(types, tx["args"])):
            _value(v, t, f"txs[{i}].args[{j}]", subj)
    if "probe" in sigma:
        p = sigma["probe"]
        need = {"sender", *subj.probe_names}
        if not isinstance(p, dict) or not need <= set(p) or set(p) - need - {"check"}:
            raise SigmaError(f"probe must have {sorted(need)} (check optional)")
        if p["sender"] not in subj.senders:
            raise SigmaError(f"probe.sender: want one of {list(subj.senders)}")
        for sig in subj.probes:
            for n, t in sig:
                _value(p[n], t, f"probe.{n}", subj)
        if "check" in p and (not isinstance(p["check"], str) or not p["check"].startswith(CHECK_PREFIX)):
            raise SigmaError("probe.check must name a check_* function")
    elif need_probe:
        raise SigmaError("sigma has no probe")


def setup_for(subject: Subject, deployer: str) -> list[dict]:
    """The profile's setup as σ transactions: each sent by its profile `sender`
    if it names one, else by `deployer`."""
    return [{"sender": t.get("sender") or deployer, "fn": t["fn"], "args": list(t["args"])} for t in subject.setup]


def _enc(types: list[str], values: list[str], subject: Subject | None = None) -> bytes:
    subj = subject or load_subject()
    out = b""
    for t, v in zip(types, values):
        if t == "address":
            out += bytes(12) + bytes.fromhex(subj.addresses[v][2:])
        elif t == "bytes32":
            out += bytes.fromhex(subj.pool("bytes32")[v][2:])
        elif t == "int256":
            out += (int(v) % 2**256).to_bytes(32, "big")
        else:
            out += int(v).to_bytes(32, "big")
    return out


# ---------------------------------------------------------------- executor (Condition E)

class ExecutorError(Exception):
    """The executor could not run σ at all (not an outcome; never a verdict)."""


_REVERT_RE = re.compile(r"^Revert \{ gas_used: \d+, output: 0x([0-9a-fA-F]*) \}$")
_HALT_RE = re.compile(r"^Halt \{ reason: (.+), gas_used: \d+ \}$")


def _exec(fn, *args, **kw) -> tuple[Any, bytes | None, str | None]:
    """Run one pyrevm call. Returns (result, revert_data, halt_reason); exactly
    one of revert_data / halt_reason is set on failure."""
    try:
        return fn(*args, **kw), None, None
    except RuntimeError as e:
        msg = str(e)
        m = _REVERT_RE.match(msg)
        if m:
            return None, bytes.fromhex(m.group(1)), None
        m = _HALT_RE.match(msg)
        if m:
            return None, None, m.group(1)
        raise ExecutorError(f"pyrevm error: {msg}") from e


def _fresh_evm(legacy: bool = False):
    """legacy=True: the core v1 executor (pyrevm's default EIP-170 / EIP-3860
    limits); only for migration proofs and tests, never for a measurement."""
    from pyrevm import EVM, BlockEnv, CfgEnv, Env
    block = BlockEnv(number=BLOCK_ENV["number"], timestamp=BLOCK_ENV["timestamp"],
                     gas_limit=BLOCK_ENV["gas_limit"], basefee=BLOCK_ENV["basefee"],
                     coinbase=BLOCK_ENV["coinbase"], prevrandao=bytes.fromhex(BLOCK_ENV["prevrandao"]))
    cfg = CfgEnv(chain_id=CHAIN_ID) if legacy else CfgEnv(chain_id=CHAIN_ID, limit_contract_code_size=CODE_SIZE_LIMIT)
    return EVM(env=Env(block=block, cfg=cfg), spec_id=SPEC_ID)


def is_spec_entry(entry: dict) -> bool:
    """Spec over an artifact (compile_spec_over) vs the artifact itself."""
    return "check_sigs" in entry


def check_deployable(entry: dict) -> None:
    """b and every mutant must be deployable contracts (EIP-170), so lifting
    the limit for the Spec harness can never change a subject-side observation."""
    n = len(entry["bin_runtime"]) // 2
    if not is_spec_entry(entry) and n > SUBJECT_RUNTIME_LIMIT:
        raise ExecutorError(f"subject-side contract runtime is {n} bytes, above the EIP-170 limit "
                            f"{SUBJECT_RUNTIME_LIMIT}: b and every mutant must be deployable")


@dataclass
class Observation:
    data: dict              # compared by observation_equal (protocol.md "Observation")
    log: list[str] = field(default_factory=list)  # human-readable detail, never compared

    def sha256(self) -> str:
        return json_sha256(self.data)


def _step(outcome: Outcome, ret: bytes | None) -> dict:
    return {"outcome": outcome.value, "return": ret.hex() if (outcome is Outcome.SUCCESS and ret) else ""}


ZERO_ADDRESS = "0x" + "00" * 20


def observation_keys(subject: Subject) -> list[tuple[str, str, list[str]]]:
    """(key, getter signature, argument pool names) for every read of the
    post-state: `sig`, `sig[k]` or `sig[k1,k2]` over the profile's key spaces."""
    import itertools
    reads = []
    for o in subject.observation:
        if not o["keys"]:
            reads.append((o["getter"], o["getter"], []))
        else:
            for combo in itertools.product(*o["keys"]):
                reads.append((f"{o['getter']}[{','.join(combo)}]", o["getter"], list(combo)))
    return reads


def run_sequence(entry: dict, sigma: dict, probe_check: str | None = None,
                 legacy_executor: bool = False) -> Observation:
    """run(artifact, σ): deploy `entry` (a compiled artifact, or Spec over an
    artifact) with σ.ctor from σ.deployer, run the subject's setup from the
    deployer, execute σ.txs in order, optionally call `probe_check` with the
    σ.probe arguments of its signature, then read the post-state through the
    profile's getters. Fresh EVM per call; deterministic. The setup run is
    σ.setup (validated to be the profile's), so a witness replays it verbatim.
    legacy_executor: the core v1 limits and deploy gas (migration proofs only)."""
    subj = subject_of(entry)
    validate_sigma(sigma, need_probe=probe_check is not None, subject=subj)
    check_deployable(entry)
    addrs = subj.addresses
    hashes = entry["hashes"]
    evm = _fresh_evm(legacy_executor)
    log: list[str] = []
    data: dict = {"deploy": None, "txs": [], "probe": None, "state": None}

    init = bytes.fromhex(entry["bin"]) + _enc([t for _, t in subj.ctor_params],
                                              [sigma["ctor"][n] for n, _ in subj.ctor_params], subj)
    addr, rdata, halt = _exec(evm.deploy, addrs[sigma["deployer"]], init,
                              gas=TX_GAS if legacy_executor else DEPLOY_GAS)
    if addr is None:
        outcome = Outcome.OTHER if halt is not None else classify_outcome(rdata)
        data["deploy"] = _step(outcome, None)
        log.append(f"deploy: {halt or describe_revert(rdata)}")
        return Observation(data, log)
    runtime = bytes.fromhex(entry["bin_runtime"])
    code = evm.get_code(addr) or b""
    # revm returns analysed legacy bytecode: the runtime plus zero padding.
    if code[: len(runtime)] != runtime or any(code[len(runtime):]):
        raise ExecutorError("deployed code is not the compiled runtime (+ zero padding)")
    data["deploy"] = _step(Outcome.SUCCESS, None)
    log.append("deploy: success")

    def call(sender: str, fn: str, args: list[str]) -> tuple[Outcome, bytes | None, str]:
        if fn not in hashes:
            raise ExecutorError(f"{fn} not in the ABI")
        cd = bytes.fromhex(hashes[fn]) + _enc(sig_types(fn), args, subj)
        ret, rd, hl = _exec(evm.message_call, addrs[sender], addr, cd, gas=TX_GAS)
        outcome = Outcome.OTHER if hl is not None else classify_outcome(None if ret is not None else rd)
        return outcome, ret, hl or describe_revert(rd)

    if sigma.get("setup"):
        data["setup"] = []
        for i, tx in enumerate(sigma["setup"]):
            outcome, ret, why = call(tx["sender"], tx["fn"], tx["args"])
            data["setup"].append(_step(outcome, ret))
            log.append(f"setup[{i}] {sigma['deployer']}.{tx['fn']}{tuple(tx['args'])}: {why}")

    for i, tx in enumerate(sigma["txs"]):
        outcome, ret, why = call(tx["sender"], tx["fn"], tx["args"])
        data["txs"].append(_step(outcome, ret))
        log.append(f"tx[{i}] {tx['sender']}.{tx['fn']}{tuple(tx['args'])}: {why}")

    if probe_check is not None:
        params = entry.get("check_sigs", {}).get(probe_check) or check_signatures(entry, subj).get(probe_check)
        if params is None:
            raise ExecutorError(f"{probe_check} not in the spec ABI")
        p = sigma["probe"]
        names = [n for n, _ in subj.probes[subj.probe_sigs.index(params)]]
        outcome, ret, why = call(p["sender"], probe_check + params, [p[n] for n in names])
        data["probe"] = {"check": probe_check, **_step(outcome, ret)}
        log.append(f"probe {p['sender']}.{probe_check}({','.join(p[n] for n in names)}): {why} -> {outcome.value}")

    state: dict = {}
    for key, sig, args in observation_keys(subj):
        if sig not in hashes:
            raise ExecutorError(f"getter {sig} not in the artifact ABI")
        cd = bytes.fromhex(hashes[sig]) + _enc(sig_types(sig), args, subj)
        ret, rdata, halt = _exec(evm.message_call, ZERO_ADDRESS, addr, cd, gas=TX_GAS, is_static=True)
        outcome = Outcome.OTHER if halt is not None else classify_outcome(None if ret is not None else rdata)
        state[key] = _step(outcome, ret)
    data["state"] = state
    return Observation(data, log)


def observation_equal(o1: Observation, o2: Observation) -> bool:
    """run(b, σ) = run(b', σ) in the sense of Def. 4.2 (protocol.md "Observation")."""
    return canonical_json(o1.data) == canonical_json(o2.data)


@dataclass
class WitnessEval:
    violated: bool                       # some check_* ended in Panic(0x01)
    outcomes: dict[str, str]             # check name -> Outcome value
    deploy_ok: bool
    log: list[str] = field(default_factory=list)


def evaluate_witness(spec_entry: dict, sigma: dict, legacy_executor: bool = False) -> WitnessEval:
    """Does σ violate φ on the artifact `spec_entry` was compiled over?
    Each check_* of φ gets its own fresh replay of σ's prefix and is called
    with σ.probe; σ.probe.check is provenance only and is ignored here."""
    validate_sigma(sigma, need_probe=True, subject=subject_of(spec_entry))
    outcomes: dict[str, str] = {}
    log: list[str] = []
    deploy_ok = True
    for check in spec_entry["checks"]:
        obs = run_sequence(spec_entry, sigma, probe_check=check, legacy_executor=legacy_executor)
        log += obs.log
        if obs.data["deploy"]["outcome"] != Outcome.SUCCESS.value:
            deploy_ok = False
            outcomes[check] = "not_run"
            continue
        outcomes[check] = obs.data["probe"]["outcome"]
    violated = deploy_ok and any(v == Outcome.VIOLATION.value for v in outcomes.values())
    return WitnessEval(violated, outcomes, deploy_ok, log)


# ---------------------------------------------------------------- Check(b, φ): SMTChecker

class Verdict(str, enum.Enum):
    ACCEPT = "Accept"
    REFUTE = "Refute"
    UNKNOWN = "Unknown"


MSG_SAFE = "CHC: Assertion violation check is safe!"
MSG_VIOLATED = "CHC: Assertion violation happens here."
MSG_UNPROVED = "CHC: Assertion violation might happen here."
NO_SOLVER_MARKERS = ("was selected for SMTChecker but it is not available",
                     "CHC analysis was not possible")
SMT_MARKERS = re.compile(r"CHC|BMC|SMTChecker|[Ss]olver|[Mm]odel checker|Assertion checker")


@dataclass
class CheckResult:
    verdict: str                 # Accept | Refute | Unknown
    reason: str                  # why (for Unknown: compile_error, solver_unavailable, wall_timeout,
                                 # unparsed, no_targets, unproved, missing_target)
    targets: list[dict]          # one per assert: {unit, start, line, function, status, counterexample}
    diagnostics: list[str]       # non-target compiler messages (kept, not used for the verdict)
    solc_input: dict             # the exact standard-JSON input (hard layer `c`)
    solc_input_sha256: str
    raw_output: str              # solc stdout, verbatim
    command: list[str]
    timeout_ms: int
    wall_timeout_s: float
    duration_s: float


def model_checker_settings(timeout_ms: int) -> dict:
    c = PROTOCOL["check"]
    return {"engine": c["engine"], "solvers": list(c["solvers"]), "targets": list(c["targets"]),
            "timeout": timeout_ms, "contracts": {u: list(v) for u, v in c["contracts"].items()},
            "showProvedSafe": c["show_proved_safe"], "showUnproved": c["show_unproved"]}


def assert_targets(out: dict) -> list[dict]:
    """Every `assert(...)` call in every source unit, from the AST, with the
    enclosing function name. These are the targets that must each get a result."""
    targets = []
    for unit, s in sorted(out.get("sources", {}).items()):
        def walk(node, fn):
            if isinstance(node, dict):
                if node.get("nodeType") == "FunctionDefinition":
                    fn = node.get("name") or node.get("kind")
                if (node.get("nodeType") == "FunctionCall"
                        and node.get("expression", {}).get("nodeType") == "Identifier"
                        and node["expression"].get("name") == "assert"):
                    start = int(node["src"].split(":")[0])
                    targets.append({"unit": unit, "start": start, "function": fn})
                for v in node.values():
                    walk(v, fn)
            elif isinstance(node, list):
                for v in node:
                    walk(v, fn)
        walk(s.get("ast", {}), None)
    return targets


def parse_counterexample(message: str) -> dict | None:
    """Parse the text after 'happens here.' into assignments + transaction trace."""
    m = re.match(re.escape(MSG_VIOLATED) + r"\nCounterexample:\n(.*?)\n\nTransaction trace:\n(.*)\Z",
                 message, re.S)
    if not m:
        return None
    trace = [l for l in m.group(2).splitlines() if l.strip()]
    if not trace:
        return None
    return {"assignments": m.group(1).strip().splitlines(), "trace": trace}


def classify_smt_output(out: dict | None, sources: dict[str, str]) -> tuple[str, str, list[dict], list[str]]:
    """Strict classifier over a parsed solc standard-JSON output.
    Returns (verdict, reason, targets, diagnostics). Pure function (no solc)."""
    if out is None:
        return Verdict.UNKNOWN.value, "wall_timeout", [], []
    errs = out.get("errors", [])
    diagnostics = [f"{e.get('type')}: {e.get('message')}" for e in errs]
    if any(e.get("severity") == "error" for e in errs):
        return Verdict.UNKNOWN.value, "compile_error", [], diagnostics
    if any(mk in e.get("message", "") for e in errs for mk in NO_SOLVER_MARKERS):
        return Verdict.UNKNOWN.value, "solver_unavailable", [], diagnostics

    targets = assert_targets(out)
    for t in targets:
        t["line"] = sources[t["unit"]].count("\n", 0, t["start"]) + 1 if t["unit"] in sources else None
        t["status"] = None
        t["counterexample"] = None
    by_loc = {(t["unit"], t["start"]): t for t in targets}
    others = []
    for e in errs:
        msg = e.get("message", "")
        if not SMT_MARKERS.search(msg):
            others.append(f"{e.get('type')}: {msg}")
            continue
        loc = e.get("sourceLocation") or {}
        t = by_loc.get((loc.get("file"), loc.get("start")))
        if t is None or t["status"] is not None:
            return Verdict.UNKNOWN.value, "unparsed", targets, diagnostics
        if msg == MSG_SAFE and e.get("severity") == "info":
            t["status"] = "safe"
        elif msg.startswith(MSG_VIOLATED + "\n") and e.get("severity") == "warning":
            cex = parse_counterexample(msg)
            if cex is None:
                return Verdict.UNKNOWN.value, "unparsed", targets, diagnostics
            t["status"], t["counterexample"] = "violated", cex
        elif msg == MSG_VIOLATED and e.get("severity") == "warning":
            # solc found a violation but printed no counterexample (seen when the
            # violating path goes through an external call). Still a refutation.
            t["status"] = "violated"
        elif msg.startswith(MSG_UNPROVED) and e.get("severity") == "warning":
            t["status"] = "unproved"
        else:
            return Verdict.UNKNOWN.value, "unparsed", targets, diagnostics
    if not targets:
        return Verdict.UNKNOWN.value, "no_targets", targets, others
    statuses = [t["status"] for t in targets]
    if "violated" in statuses:
        with_cex = all(t["counterexample"] for t in targets if t["status"] == "violated")
        reason = "counterexample" if with_cex else "violation_without_counterexample"
        return Verdict.REFUTE.value, reason, targets, others
    if "unproved" in statuses:
        return Verdict.UNKNOWN.value, "unproved", targets, others
    if None in statuses:
        # No result line for some assert: the analysis did not cover it. This is
        # what a silent solver skip looks like, so it can never be an Accept.
        return Verdict.UNKNOWN.value, "missing_target", targets, others
    return Verdict.ACCEPT.value, "all_targets_safe", targets, others


def smtcheck_sources(sources: dict[str, str], timeout_ms: int, wall_timeout_s: float,
                     tc: Toolchain | None = None) -> CheckResult:
    """One SMTChecker run (CHC + z3, targets assert, contracts = Spec) on given sources."""
    tc = tc or Toolchain.default()
    inp = solc_input(sources, model_checker_settings(timeout_ms))
    out, raw, dt = run_solc(inp, tc, wall_timeout_s)
    verdict, reason, targets, diags = classify_smt_output(out, sources)
    return CheckResult(verdict, reason, targets, diags, inp, json_sha256(inp), raw,
                       [str(tc.solc), "--standard-json"], timeout_ms, wall_timeout_s, round(dt, 3))


def smtcheck(spec_path: str | Path, artifact_path: str | Path, timeout_ms: int,
             wall_timeout_s: float, tc: Toolchain | None = None, subject: Subject | str | None = None) -> CheckResult:
    """Whole-harness Check(artifact, φ) (protocol v1; `--mode whole`, kept for comparison)."""
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    sources = {SPEC_UNIT: Path(spec_path).read_text(), subj.unit: Path(artifact_path).read_text()}
    return smtcheck_sources(sources, timeout_ms, wall_timeout_s, tc)


def check_result_dict(r: CheckResult) -> dict:
    return asdict(r)


# ---------------------------------------------------------------- source parsing (shared with speclint)

def strip_source(text: str, keep_strings: bool = False) -> str:
    """Blank out comments (and string literals unless keep_strings), keeping
    every newline so line numbers survive."""
    out = []
    i, n = 0, len(text)
    while i < n:
        c = text[i]
        if text.startswith("//", i):
            j = text.find("\n", i)
            j = n if j < 0 else j
            out.append(" " * (j - i))
            i = j
        elif text.startswith("/*", i):
            j = text.find("*/", i + 2)
            j = n if j < 0 else j + 2
            out.append("".join(ch if ch == "\n" else " " for ch in text[i:j]))
            i = j
        elif c in "\"'":
            j = i + 1
            while j < n and text[j] != c:
                j += 2 if text[j] == "\\" else 1
            j = min(j + 1, n)
            out.append(text[i:j] if keep_strings else c + " " * (j - i - 2) + c)
            i = j
        else:
            out.append(c)
            i += 1
    return "".join(out)


def match_brace(s: str, open_pos: int) -> int:
    depth = 0
    for k in range(open_pos, len(s)):
        if s[k] == "{":
            depth += 1
        elif s[k] == "}":
            depth -= 1
            if depth == 0:
                return k
    return -1


def top_level_items(s: str, start: int, end: int) -> list[tuple[int, int, str]]:
    """Split s[start:end] into items at brace depth 0: either `...;` or
    `head { body }`. Returns (item_start, item_end, normalized_head)."""
    items = []
    k = start
    while k < end:
        while k < end and s[k].isspace():
            k += 1
        if k >= end:
            break
        j = k
        while j < end and s[j] not in ";{}":
            j += 1
        if j >= end:
            items.append((k, end, " ".join(s[k:end].split())))
            break
        if s[j] == ";":
            items.append((k, j + 1, " ".join(s[k:j + 1].split())))
            k = j + 1
        elif s[j] == "{":
            close = match_brace(s, j)
            if close < 0 or close >= end:
                items.append((k, end, " ".join(s[k:end].split())))
                break
            items.append((k, close + 1, " ".join(s[k:j + 1].split())))
            k = close + 1
        else:  # stray '}'
            items.append((k, j + 1, "}"))
            k = j + 1
    return items


_CHECK_HEAD_RE = re.compile(r"^function\s+(check_[A-Za-z0-9_]+)\s*\(")


def check_functions(spec_text: str, subject: Subject | str | None = None) -> list[tuple[str, str]]:
    """(name, verbatim function text) of every check_* declared at the top level
    of `contract Spec`, in source order."""
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    s = strip_source(spec_text)
    m = re.search(rf"\bcontract\s+Spec\s+is\s+{re.escape(subj.contract)}\s*\{{", s)
    if not m:
        raise CompileError(f"no `contract Spec is {subj.contract}`")
    open_ = m.end() - 1
    close = match_brace(s, open_)
    if close < 0:
        raise CompileError("unbalanced braces in contract Spec")
    out = []
    for st, en, head in top_level_items(s, open_ + 1, close):
        h = _CHECK_HEAD_RE.match(head)
        if h:
            out.append((h.group(1), spec_text[st:en]))
    names = [n for n, _ in out]
    if len(set(names)) != len(names):
        raise CompileError("duplicate check_* names")
    return out


# The fixed part of every harness of the default subject (speclint S1-S4).
ISOLATED_HEADER = load_subject().header()


def isolated_harness(check_text: str, subject: Subject | str | None = None) -> str:
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    return subj.header() + check_text + "\n}\n"


def isolate_check(spec_text: str, check: str, subject: Subject | str | None = None) -> str:
    """Check v2 harness for one check: the fixed header plus that check's text,
    verbatim; every other check_* is left out (protocol.md, Protocol v2)."""
    for name, text in check_functions(spec_text, subject):
        if name == check:
            return isolated_harness(text, subject)
    raise CompileError(f"no check {check}")


# ---------------------------------------------------------------- Check v2: isolated checks in a pool

CHECK_MODE: str = PROTOCOL["check"]["mode"]
CHECK_WORKERS: int = PROTOCOL["check"]["workers"]
CACHE_DIR = ROOT / "build" / "cache"


@dataclass
class SpecCheckResult:
    verdict: str            # Accept | Refute | Unknown (combined over the checks)
    reason: str             # all_checks_safe | counterexample | violation_without_counterexample |
                            # budget | unproved | compile_error | solver_unavailable | unparsed |
                            # missing_target | no_targets
    mode: str               # "isolated"
    checks: list[dict]      # per check: {check, harness_sha256, cached, result: CheckResult as dict}
    timeout_ms: int
    wall_timeout_s: float
    workers: int
    duration_s: float       # wall time of the whole pool
    cpu_s: float            # sum of the per-check solc durations (cached ones included)
    cache_hits: int


def combine_verdicts(results: list[dict]) -> tuple[str, str]:
    """Spec verdict from per-check CheckResults: Accept iff every check is Accept;
    Refute if any check is Refute; else Unknown with the most informative reason.
    `budget` = some check hit its wall timeout; a per-query solver timeout prints
    the same "might happen" as incompleteness and is reported as `unproved`."""
    if not results:
        return Verdict.UNKNOWN.value, "no_targets"
    vs = [r["verdict"] for r in results]
    rs = [r["reason"] for r in results]
    if Verdict.REFUTE.value in vs:
        ok = all(r["reason"] == "counterexample" for r in results if r["verdict"] == Verdict.REFUTE.value)
        return Verdict.REFUTE.value, "counterexample" if ok else "violation_without_counterexample"
    if all(v == Verdict.ACCEPT.value for v in vs):
        return Verdict.ACCEPT.value, "all_checks_safe"
    for why in ("compile_error", "solver_unavailable", "unparsed", "no_targets"):
        if why in rs:
            return Verdict.UNKNOWN.value, why
    if "wall_timeout" in rs:
        return Verdict.UNKNOWN.value, "budget"
    if "missing_target" in rs:
        return Verdict.UNKNOWN.value, "missing_target"
    return Verdict.UNKNOWN.value, "unproved"


def cache_key(inp: dict, wall_timeout_s: float, tc: Toolchain) -> str:
    """Verdict-cache key: the exact solc input, the wall budget, the solver binaries
    and this core (classifier) source. A pure optimization: verify.py never reads it."""
    return json_sha256({"solc_input_sha256": json_sha256(inp), "wall_timeout_s": wall_timeout_s,
                        "solc_sha256": sha256_file(tc.solc), "z3_sha256": sha256_file(tc.z3) if tc.z3 else None,
                        "core_sha256": sha256_file(__file__)})


def smtcheck_harnesses(harnesses: list[tuple[str, str]], artifact_text: str, timeout_ms: int,
                       wall_timeout_s: float, tc: Toolchain | None = None, workers: int | None = None,
                       cache_dir: Path | None = None, subject: Subject | str | None = None) -> list[dict]:
    """Run SMTChecker on each (name, harness text) over the artifact, up to
    `workers` solc processes at once. Returns one row per harness, in input order."""
    import concurrent.futures
    tc = tc or Toolchain.default()
    unit = (subject if isinstance(subject, Subject) else load_subject(subject)).unit

    def one(item: tuple[str, str]) -> dict:
        name, text = item
        sources = {SPEC_UNIT: text, unit: artifact_text}
        inp = solc_input(sources, model_checker_settings(timeout_ms))
        path = None
        if cache_dir is not None and tc.z3 is not None:
            path = Path(cache_dir) / f"{cache_key(inp, wall_timeout_s, tc)}.json"
            if path.is_file():
                try:
                    d = json.loads(path.read_text())
                    if d.get("solc_input_sha256") == json_sha256(inp):
                        return {"check": name, "harness_sha256": sha256_hex(text.encode()), "cached": True, "result": d}
                except ValueError:
                    pass
        r = asdict(smtcheck_sources(sources, timeout_ms, wall_timeout_s, tc))
        if path is not None:
            path.parent.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(f".{os.getpid()}.{threading.get_ident()}.tmp")
            tmp.write_text(json.dumps(r, sort_keys=True))
            os.replace(tmp, path)
        return {"check": name, "harness_sha256": sha256_hex(text.encode()), "cached": False, "result": r}

    with concurrent.futures.ThreadPoolExecutor(max_workers=workers or CHECK_WORKERS) as ex:
        return list(ex.map(one, harnesses))


def smtcheck_isolated(spec_path: str | Path, artifact_path: str | Path, timeout_ms: int,
                      wall_timeout_s: float, tc: Toolchain | None = None, workers: int | None = None,
                      cache_dir: Path | None = None, subject: Subject | str | None = None) -> SpecCheckResult:
    """Check v2 (protocol.md, Protocol v2): one isolated harness per check_*,
    run in a pool; the spec verdict combines the per-check verdicts."""
    spec_text, art_text = Path(spec_path).read_text(), Path(artifact_path).read_text()
    workers = workers or CHECK_WORKERS
    t0 = time.monotonic()
    subj = subject if isinstance(subject, Subject) else load_subject(subject)
    try:
        checks = check_functions(spec_text, subj)
    except CompileError:
        return SpecCheckResult(Verdict.UNKNOWN.value, "compile_error", "isolated", [], timeout_ms, wall_timeout_s,
                               workers, 0.0, 0.0, 0)
    rows = smtcheck_harnesses([(n, isolated_harness(t, subj)) for n, t in checks], art_text, timeout_ms,
                              wall_timeout_s, tc, workers, cache_dir, subj)
    verdict, reason = combine_verdicts([r["result"] for r in rows])
    return SpecCheckResult(verdict, reason, "isolated", rows, timeout_ms, wall_timeout_s, workers,
                           round(time.monotonic() - t0, 3), round(sum(r["result"]["duration_s"] for r in rows), 3),
                           sum(r["cached"] for r in rows))
