"""Bundle verifier: the note's Section 10 "Verifier contract" (protocol.md section 14).

    python tools/verify.py <bundle-dir> [--json report.json]

Reads ONLY the bundle directory, plus this verifier's own installation: this
file, `specgame_core.py` next to it, `../schemas/` and `../protocol.json`, and
the pinned toolchain the core resolves (`../.toolchain/bin/{solc,z3}` or
SPECGAME_SOLC / SPECGAME_Z3). Imports: stdlib, pyrevm (through the core) and
specgame_core only. It never applies a mutation operator and never calls an
adversary; `operator` / `fault_class` are printed as labels and affect nothing.

Steps, in order (the report names the first failing one):

  0  manifest   manifest.json parses and validates against
                schemas/manifest.schema.json (stdlib subset validator below)
  1  hashes     every file hash in `files` matches its bytes, no unlisted file,
                every manifest path is listed; the semantics version
                (toolchain_fingerprint recomputed), the running core, this
                verifier match the provenance layer (else could-not-verify);
                protocol.json matches protocol_json_sha256 (else REFUSED);
                protocol_md_sha256 is reported, never compared
  2  check      Check v2: for every check_* of phi, the isolated harness's solc
                standard-JSON input re-derived from the bundled b and phi equals
                the bundled one (sha256); b and Spec-over-b runtime ids
                recomputed; every input re-run (worker pool, no cache) and
                classified strictly; the re-run per-check verdicts must equal
                the bundled table (Accept on each = pass; Unknown recorded and
                reproduced = NOT CERTIFIED, steps 3-6 still run)
  3  M          per mutant: id = sha256(runtime) recomputed from the bundled
                source; some properness sigma gives run(b, s) != run(m, s)
  4  W          every witness replayed: Spec over its mutant deploys and some
                check_* ends in violation (evaluate_witness); failures are
                discarded, with reasons
  5  score      ms_cert = {killed, total} and the kill set recomputed from the
                pairs that passed (4) and compared with `claimed`
  6  V-compl.   no V-completeness claim anywhere; "V-completeness" in not_claimed

Exit codes: 0 HOLDS; 2 NOT CERTIFIED (the bundle records Check = Unknown and
the re-run reproduces the per-check verdicts; ms_cert and the kill set are
still recomputed and reported, Def. 5.3) or COULD NOT VERIFY (toolchain / core /
verifier mismatch, missing tool, a recorded Unknown that re-runs to Accept);
3 REFUSED (protocol.json mismatch, any bundle hash mismatch, schema violation,
any Refute, a recorded Accept that re-runs to Unknown or Refute, a recorded
Unknown that re-runs to Refute, failed id or properness, claim mismatch, a
V-completeness claim). A refusal wins over could-not-verify, which wins over
not-certified; an unanticipated exception inside a step is could-not-verify.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import specgame_core as core  # noqa: E402

INSTALL_ROOT = HERE.parent
SCHEMA_DIR = INSTALL_ROOT / "schemas"
PROTOCOL_JSON = INSTALL_ROOT / "protocol.json"  # frozen values: compared (step 1)
PROTOCOL_MD = INSTALL_ROOT / "protocol.md"      # narrative: recorded in bundles, never compared
MANIFEST = "manifest.json"

EXIT_HOLDS, EXIT_UNVERIFIABLE, EXIT_REFUSED = 0, 2, 3
EXIT_NOT_CERTIFIED = EXIT_UNVERIFIABLE  # exit 2, distinguished by the verdict string
PASS, FAIL, UNVERIFIABLE, SKIPPED = "pass", "fail", "could_not_verify", "skipped"
NOT_CERTIFIED = "not_certified"  # step 2: bundle records Unknown and the re-run reproduces it
STEP_NAMES = {0: "manifest", 1: "hashes", 2: "check", 3: "M", 4: "W", 5: "score", 6: "V-completeness"}
V_COMPLETENESS = "V-completeness"
_V_RE = re.compile(r"v[-_ ]?complete", re.I)


# ---------------------------------------------------------------- JSON-Schema subset

class SchemaError(ValueError):
    pass


# Keywords this validator implements. Any other keyword in a schema is an error
# (fail closed), so a schema that grows a keyword we ignore cannot pass silently.
_ANNOTATIONS = {"$schema", "$id", "title", "description", "examples", "$defs"}
_KEYWORDS = {"type", "const", "enum", "pattern", "required", "properties", "additionalProperties",
             "items", "minItems", "contains", "minimum", "exclusiveMinimum", "oneOf", "anyOf",
             "allOf", "$ref", "if", "then", "else"}
_TYPES = {
    "object": lambda v: isinstance(v, dict),
    "array": lambda v: isinstance(v, list),
    "string": lambda v: isinstance(v, str),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "boolean": lambda v: isinstance(v, bool),
    "null": lambda v: v is None,
}


def _json_eq(a: Any, b: Any) -> bool:
    """JSON equality: booleans are not numbers (Python's True == 1 is not JSON's)."""
    if isinstance(a, bool) or isinstance(b, bool):
        return type(a) is type(b) and a == b
    return a == b


class SchemaValidator:
    """Validates the subset of JSON Schema 2020-12 used by specgame/schemas/:
    the keywords in _KEYWORDS, local `#/$defs/<name>` refs and refs to sibling
    schema files by file name. Unknown keywords raise SchemaError."""

    def __init__(self, schema_dir: Path):
        self.dir = schema_dir
        self.docs: dict[str, dict] = {}

    def doc(self, name: str) -> dict:
        if name not in self.docs:
            self.docs[name] = json.loads((self.dir / name).read_text())
        return self.docs[name]

    def validate(self, inst: Any, name: str) -> list[str]:
        errors: list[str] = []
        self._v(inst, self.doc(name), name, "$", errors)
        return errors

    def _resolve(self, ref: str, doc_name: str) -> tuple[dict, str]:
        file, _, frag = ref.partition("#")
        doc_name = file or doc_name
        node: Any = self.doc(doc_name)
        for part in [p for p in frag.split("/") if p]:
            node = node[part]
        return node, doc_name

    def _v(self, x: Any, s: dict, doc: str, at: str, errs: list[str]) -> None:
        unknown = set(s) - _KEYWORDS - _ANNOTATIONS
        if unknown:
            raise SchemaError(f"{doc}: unsupported schema keywords {sorted(unknown)}")
        if "$ref" in s:
            sub, sdoc = self._resolve(s["$ref"], doc)
            self._v(x, sub, sdoc, at, errs)
        if "type" in s:
            types = s["type"] if isinstance(s["type"], list) else [s["type"]]
            if not any(_TYPES[t](x) for t in types):
                errs.append(f"{at}: want type {s['type']}, got {type(x).__name__}")
                return
        if "const" in s and not _json_eq(x, s["const"]):
            errs.append(f"{at}: want const {s['const']!r}")
        if "enum" in s and not any(_json_eq(x, e) for e in s["enum"]):
            errs.append(f"{at}: {x!r} not in {s['enum']}")
        if "pattern" in s and isinstance(x, str) and not re.search(s["pattern"], x):
            errs.append(f"{at}: {x!r} does not match {s['pattern']}")
        if isinstance(x, (int, float)) and not isinstance(x, bool):
            if "minimum" in s and x < s["minimum"]:
                errs.append(f"{at}: {x} < minimum {s['minimum']}")
            if "exclusiveMinimum" in s and x <= s["exclusiveMinimum"]:
                errs.append(f"{at}: {x} <= exclusiveMinimum {s['exclusiveMinimum']}")
        if isinstance(x, dict):
            for k in s.get("required", []):
                if k not in x:
                    errs.append(f"{at}: missing required key {k!r}")
            props = s.get("properties", {})
            for k, v in x.items():
                if k in props:
                    self._v(v, props[k], doc, f"{at}.{k}", errs)
                elif "additionalProperties" in s:
                    ap = s["additionalProperties"]
                    if ap is False:
                        errs.append(f"{at}: unexpected key {k!r}")
                    elif isinstance(ap, dict):
                        self._v(v, ap, doc, f"{at}.{k}", errs)
        if isinstance(x, list):
            if "minItems" in s and len(x) < s["minItems"]:
                errs.append(f"{at}: {len(x)} items < minItems {s['minItems']}")
            if "items" in s:
                for i, v in enumerate(x):
                    self._v(v, s["items"], doc, f"{at}[{i}]", errs)
            if "contains" in s and not any(not self._sub(v, s["contains"], doc) for v in x):
                errs.append(f"{at}: no item matches 'contains'")
        for sub in s.get("allOf", []):
            self._v(x, sub, doc, at, errs)
        if "anyOf" in s and not any(not self._sub(x, sub, doc) for sub in s["anyOf"]):
            errs.append(f"{at}: matches none of anyOf")
        if "oneOf" in s:
            n = sum(1 for sub in s["oneOf"] if not self._sub(x, sub, doc))
            if n != 1:
                errs.append(f"{at}: matches {n} of oneOf, want exactly 1")
        if "if" in s:
            branch = "then" if not self._sub(x, s["if"], doc) else "else"
            if branch in s:
                self._v(x, s[branch], doc, at, errs)

    def _sub(self, x: Any, s: dict, doc: str) -> list[str]:
        errs: list[str] = []
        self._v(x, s, doc, "$", errs)
        return errs


# ---------------------------------------------------------------- report

class Report:
    def __init__(self, bundle: Path):
        self.bundle = str(bundle)
        self.steps: list[dict] = []
        self.score: dict | None = None
        self.kill_set: list[str] | None = None
        self.no_valid_witness: list[str] | None = None
        self.discarded: list[dict] = []
        self.labels: list[dict] = []

    def step(self, n: int, status: str, details: list[str], **extra) -> dict:
        d = {"step": n, "name": STEP_NAMES[n], "status": status, "details": details, **extra}
        self.steps.append(d)
        return d

    def skip_from(self, n: int, why: str) -> None:
        done = {s["step"] for s in self.steps}
        for k in range(n, 7):
            if k not in done:
                self.step(k, SKIPPED, [why])

    def outcome(self) -> tuple[str, int, int | None]:
        fails = [s["step"] for s in self.steps if s["status"] == FAIL]
        unk = [s["step"] for s in self.steps if s["status"] == UNVERIFIABLE]
        if fails:
            return "REFUSED", EXIT_REFUSED, min(fails)
        if unk:
            return "COULD_NOT_VERIFY", EXIT_UNVERIFIABLE, min(unk)
        nc = [s["step"] for s in self.steps if s["status"] == NOT_CERTIFIED]
        if nc:
            return "NOT_CERTIFIED", EXIT_NOT_CERTIFIED, min(nc)
        return "HOLDS", EXIT_HOLDS, None

    def as_dict(self) -> dict:
        verdict, code, first = self.outcome()
        steps = sorted(self.steps, key=lambda s: s["step"])
        return {
            "version": 1, "bundle": self.bundle, "verdict": verdict, "exit_code": code,
            "first_failing_step": first,
            "failing_steps": [s["step"] for s in steps if s["status"] in (FAIL, UNVERIFIABLE, NOT_CERTIFIED)],
            "ms_cert": self.score, "kill_set": self.kill_set,
            "mutants_without_valid_witness": self.no_valid_witness,
            "discarded": self.discarded, "labels": self.labels, "steps": steps,
        }


def summary(rep: dict) -> str:
    lines = [f"verify {rep['bundle']}"]
    for s in rep["steps"]:
        lines.append(f"[{s['status'].upper():16s}] ({s['step']}) {s['name']}")
        lines += [f"       {d}" for d in s["details"]]
    if rep["ms_cert"] is not None:
        lines.append(f"ms_cert = {rep['ms_cert']['killed']}/{rep['ms_cert']['total']}"
                     f"  kill set {rep['kill_set']}")
        lines.append(f"mutants without a valid witness: {rep['mutants_without_valid_witness']}")
    for l in rep["labels"]:
        lines.append(f"label (T*, affects no verdict): mutant {l['id'][:12]} "
                     f"operator={l['operator']} fault_class={l['fault_class']}")
    for d in rep["discarded"]:
        lines.append(f"discarded ({d['by']}): mutant {d['mutant'][:12]} {d['reason']}")
    tail = "" if rep["first_failing_step"] is None else \
        f" at step {rep['first_failing_step']} ({STEP_NAMES[rep['first_failing_step']]})"
    lines.append(f"verdict: {rep['verdict']}{tail}, exit {rep['exit_code']}")
    return "\n".join(lines)


# ---------------------------------------------------------------- helpers

def _safe_rel(p: str) -> bool:
    pp = Path(p)
    return bool(p) and not pp.is_absolute() and ".." not in pp.parts and p == pp.as_posix()


def _bundle_files(root: Path) -> tuple[set[str], list[str]]:
    """All regular files under root (relative posix paths), and anything else
    found (symlinks, special files), which a bundle may not contain."""
    files, odd = set(), []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        for name in dirnames + filenames:
            p = Path(dirpath) / name
            rel = p.relative_to(root).as_posix()
            if p.is_symlink():
                odd.append(rel)
            elif name in filenames:
                if p.is_file():
                    files.add(rel)
                else:
                    odd.append(rel)
    return files, sorted(odd)


def _v_completeness_claims(node: Any, at: str = "$") -> list[str]:
    """Every place outside `not_claimed` where a V-completeness claim appears
    (a key or a string value naming it)."""
    found = []
    if isinstance(node, dict):
        for k, v in node.items():
            if at == "$" and k == "not_claimed":
                continue
            if _V_RE.search(k):
                found.append(f"{at}.{k}")
            found += _v_completeness_claims(v, f"{at}.{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            found += _v_completeness_claims(v, f"{at}[{i}]")
    elif isinstance(node, str) and _V_RE.search(node):
        found.append(at)
    return found


def discard_reason(ev: "core.WitnessEval") -> str:
    """Why a presented pair is not a witness: the outcome per check, with the
    revert detail of each probe (logged, never compared)."""
    if not ev.deploy_ok:
        return "deploy of Spec over the mutant failed"
    probes = [l[len("probe "):] for l in ev.log if l.startswith("probe ")]
    return "no check ends in violation: " + ", ".join(
        f"{k}={v}" for k, v in sorted(ev.outcomes.items())) + (f" [{'; '.join(probes)}]" if probes else "")


def _manifest_paths(m: dict) -> list[str]:
    paths = [m["hard"]["b"]["path"], m["hard"]["phi"]["path"], m["provenance"]["core_path"],
             m["provenance"]["subject_profile_path"]]
    for row in m["hard"]["c"]["checks"]:
        paths += [row["solc_input_path"], row["solc_output_path"]]
    return paths + [e["path"] for e in m["evidence"]["M"]]


# ---------------------------------------------------------------- steps

def step0_manifest(root: Path, rep: Report) -> dict | None:
    mpath = root / MANIFEST
    if not mpath.is_file() or mpath.is_symlink():
        rep.step(0, FAIL, [f"{MANIFEST} missing (or not a regular file)"])
        return None
    try:
        m = json.loads(mpath.read_bytes())
    except (ValueError, UnicodeDecodeError) as e:
        rep.step(0, FAIL, [f"{MANIFEST} does not parse: {e}"])
        return None
    try:
        errs = SchemaValidator(SCHEMA_DIR).validate(m, "manifest.schema.json")
    except (OSError, ValueError, KeyError) as e:
        rep.step(0, UNVERIFIABLE, [f"verifier schemas unusable: {e}"])
        return None
    sigma_errs = []
    if not errs:
        # σ are validated against the bundle's subject profile (pinned by
        # protocol.json), not against any default: ctor keys, setup, typed
        # arguments and probe keys are all subject-specific (protocol v3).
        # The subject's profile is the copy carried by the bundle, accepted only
        # if it is the one protocol.json pins (never a workspace copy).
        name, ppath = m["provenance"]["subject"], m["provenance"]["subject_profile_path"]
        if name not in core.PROTOCOL["subjects"]:
            rep.step(0, UNVERIFIABLE, [f"subject {name!r} is not in this verifier's protocol.json"])
            return None
        pfile = root / ppath
        if not _safe_rel(ppath) or not pfile.is_file() or pfile.is_symlink():
            rep.step(0, FAIL, [f"subject profile {ppath!r} missing from the bundle"])
            return None
        try:
            subj = core.subject_from_bytes(name, pfile.read_bytes())
        except (core.ProfileError, ValueError) as e:
            rep.step(0, FAIL, [f"bundled subject profile refused: {e}"])
            return None
        for i, e in enumerate(m["evidence"]["M"]):
            for j, s in enumerate(e["properness_sigma"]):
                try:
                    core.validate_sigma(s, subject=subj)
                    if "probe" in s:
                        raise core.SigmaError("a properness sigma has no probe")
                except core.SigmaError as ex:
                    sigma_errs.append(f"$.evidence.M[{i}].properness_sigma[{j}]: {ex}")
        for i, w in enumerate(m["evidence"]["W"]):
            try:
                core.validate_sigma(w["sigma"], need_probe=True, subject=subj)
            except core.SigmaError as ex:
                sigma_errs.append(f"$.evidence.W[{i}].sigma: {ex}")
    if errs or sigma_errs:
        rep.step(0, FAIL, ["schema violation"] + (errs + sigma_errs)[:20])
        return None
    rep.step(0, PASS, ["manifest.json validates against schemas/manifest.schema.json "
                       f"(+ validate_sigma against subject {subj.name} on every sigma)"])
    return m


def step1_hashes(root: Path, m: dict, rep: Report) -> str:
    fails, unk, info = [], [], []
    listed = m["files"]
    present, odd = _bundle_files(root)
    present.discard(MANIFEST)
    for p in odd:
        fails.append(f"not a regular file: {p}")
    for p in sorted(listed):
        if not _safe_rel(p) or p == MANIFEST:
            fails.append(f"bad path in files: {p!r}")
        elif p not in present:
            fails.append(f"listed but missing: {p}")
        else:
            got = core.sha256_file(root / p)
            if got != listed[p]:
                fails.append(f"sha256 mismatch: {p}: manifest {listed[p][:16]}…, bytes {got[:16]}…")
    for p in sorted(present - set(listed)):
        fails.append(f"unlisted file in bundle: {p}")
    for p in _manifest_paths(m):
        if p not in listed:
            fails.append(f"manifest path not in files: {p}")
    if not fails:
        info.append(f"{len(listed)} files, every sha256 matches, no unlisted file")
        hard, prov = m["hard"], m["provenance"]
        for what, p, want in [("b", hard["b"]["path"], hard["b"]["source_sha256"]),
                              ("phi", hard["phi"]["path"], hard["phi"]["source_sha256"]),
                              ("core copy", prov["core_path"], prov["core_sha256"])]:
            if listed[p] != want:
                fails.append(f"{what}: files[{p}] {listed[p][:16]}… != declared {want[:16]}…")
        for row in hard["c"]["checks"]:
            if listed[row["solc_input_path"]] != row["solc_input_sha256"]:
                fails.append(f"c[{row['check']}]: bundled solc input file sha256 != solc_input_sha256")
    if not fails:
        # Semantics version: what this verifier runs on must be what the bundle
        # was produced under. A mismatch is not evidence against the bundle, so
        # it is could-not-verify, not a refusal.
        prov = m["provenance"]
        mine = {"core": core.sha256_file(core.__file__), "verifier": core.sha256_file(__file__)}
        if mine["core"] != prov["core_sha256"]:
            unk.append(f"running core sha256 {mine['core'][:16]}… != bundle {prov['core_sha256'][:16]}…")
        else:
            info.append(f"core sha256 {mine['core']} (running = bundled copy = provenance)")
        if mine["verifier"] != prov["verifier_sha256"]:
            unk.append(f"running verifier sha256 {mine['verifier'][:16]}… != bundle "
                       f"{prov['verifier_sha256'][:16]}…")
        else:
            info.append(f"verifier sha256 {mine['verifier']}")
        # protocol.json holds the frozen values the bundle's claims depend on; a
        # bundle produced under other values is refused. protocol.md is prose and
        # is never compared (its hash is recorded for information only).
        if not PROTOCOL_JSON.is_file():
            unk.append(f"verifier install has no protocol.json at {PROTOCOL_JSON}")
        elif core.sha256_file(PROTOCOL_JSON) != prov["protocol_json_sha256"]:
            fails.append(f"protocol.json sha256 {core.sha256_file(PROTOCOL_JSON)[:16]}… != bundle "
                         f"{prov['protocol_json_sha256'][:16]}…: produced under other frozen values")
        else:
            info.append(f"protocol.json sha256 {prov['protocol_json_sha256']}")
        info.append(f"protocol.md sha256 {prov['protocol_md_sha256']} (recorded, not compared)")
        info.append(f"subject {prov['subject']}: bundled profile {prov['subject_profile_path']} = protocol.json pin "
                    f"({core.PROTOCOL['subjects'][prov['subject']]['profile_sha256'][:16]}…)")
        try:
            fp = core.toolchain_fingerprint()
        except (OSError, ValueError) as e:
            unk.append(f"toolchain missing: {e}")
            fp = None
        if fp is not None:
            if core.canonical_json(fp) != core.canonical_json(prov["toolchain"]):
                diff = sorted(k for k in set(fp) | set(prov["toolchain"])
                              if fp.get(k) != prov["toolchain"].get(k))
                unk.append(f"semantics version differs in {diff}")
                for k in diff:
                    unk.append(f"  {k}: here {json.dumps(fp.get(k))}, bundle "
                               f"{json.dumps(prov['toolchain'].get(k))}")
            else:
                info.append(f"semantics version matches: solc {fp['solc']['version']}, "
                            f"{fp['z3']['version'] if fp['z3'] else 'no z3'}, python {fp['python']}, "
                            f"pyrevm {fp['pyrevm']}, {fp['spec_id']}")
    status = FAIL if fails else (UNVERIFIABLE if unk else PASS)
    rep.step(1, status, fails + unk + info)
    return status


def step2_check(root: Path, m: dict, rep: Report) -> tuple[str, dict | None]:
    """Check v2: every check_* of phi has an isolated-harness certificate; every
    input is re-derived from the bundled b and phi, every one is re-run (in the
    worker pool, never from a cache) and must reproduce the bundled per-check
    verdicts: all Accept = pass; recorded Unknown reproduced = not certified.
    Verdicts are compared, reasons only reported (budget vs unproved is timing)."""
    hard = m["hard"]
    c = hard["c"]
    b_path, phi_path = root / hard["b"]["path"], root / hard["phi"]["path"]
    fails, unk, nc, info = [], [], [], []
    b_text, phi_text = b_path.read_text(), phi_path.read_text()
    subj = core.load_subject(m["provenance"]["subject"])
    if (c["timeout_ms"], c["wall_timeout_s"]) != (core.CHECK_TIMEOUT_MS, core.CHECK_WALL_TIMEOUT_S):
        fails.append(f"c: timeout_ms {c['timeout_ms']} / wall {c['wall_timeout_s']} s are not the frozen "
                     f"{core.CHECK_TIMEOUT_MS} / {core.CHECK_WALL_TIMEOUT_S} s of protocol.json")
    try:
        derived = [(n, core.solc_input({core.SPEC_UNIT: core.isolated_harness(t, subj), subj.unit: b_text},
                                       core.model_checker_settings(c["timeout_ms"])))
                   for n, t in core.check_functions(phi_text, subj)]
    except core.CompileError as e:
        rep.step(2, FAIL, [f"phi: check_* functions cannot be isolated: {e}"])
        return FAIL, None
    if c.get("mode") != "isolated":
        fails.append(f"c.mode {c.get('mode')!r}: this verifier checks protocol v2 (isolated) certificates")
    if [n for n, _ in derived] != [row["check"] for row in c["checks"]]:
        fails.append(f"certificates {[row['check'] for row in c['checks']]} != check_* of phi "
                     f"{[n for n, _ in derived]}")
    else:
        for (n, inp), row in zip(derived, c["checks"]):
            want = core.json_sha256(inp)
            try:
                bundled_inp = json.loads((root / row["solc_input_path"]).read_bytes())
            except ValueError as e:
                fails.append(f"c[{n}]: bundled solc input does not parse: {e}")
                continue
            if want != row["solc_input_sha256"]:
                fails.append(f"c[{n}]: re-derived solc input sha256 {want[:16]}… != bundled "
                             f"{row['solc_input_sha256'][:16]}…")
            elif core.canonical_json(bundled_inp) != core.canonical_json(inp):
                fails.append(f"c[{n}]: bundled solc input differs from the one re-derived from b and phi")
        if not fails:
            info.append(f"{len(derived)} isolated-harness solc inputs re-derived from b + phi + "
                        f"timeout_ms={c['timeout_ms']} (= bundled)")
    b_entry = None
    if not fails:
        try:
            b_entry = core.compile_artifact(b_path, subject=subj)
            pair = core.compile_spec_over(phi_path, b_path, subject=subj)
        except core.CompileError as e:
            rep.step(2, FAIL, [f"b or Spec over b does not compile: {e}"])
            return FAIL, None
        if b_entry["runtime_sha256"] != hard["b"]["runtime_sha256"]:
            fails.append(f"b runtime sha256 {b_entry['runtime_sha256'][:16]}… != declared")
        if pair["runtime_sha256"] != hard["phi"]["pair_runtime_sha256"]:
            fails.append(f"Spec-over-b runtime sha256 {pair['runtime_sha256'][:16]}… != declared")
        if pair["checks"] != sorted(hard["phi"]["checks"]):
            fails.append(f"checks {pair['checks']} != declared {hard['phi']['checks']}")
        if not fails:
            info.append(f"b runtime sha256 {b_entry['runtime_sha256']}")
            info.append(f"Spec over b runtime sha256 {pair['runtime_sha256']}, checks {pair['checks']}")
    if fails:
        rep.step(2, FAIL, fails + info)
        return FAIL, b_entry
    try:
        r = core.smtcheck_isolated(phi_path, b_path, c["timeout_ms"], c["wall_timeout_s"], cache_dir=None,
                                   subject=subj)
    except (core.CompileError, OSError) as e:
        rep.step(2, UNVERIFIABLE, [f"solc could not run: {e}"] + info)
        return UNVERIFIABLE, b_entry
    info.append(f"{len(r.checks)} checks re-run in {r.workers} workers ({r.duration_s} s wall, {r.cpu_s} s solc): "
                f"{r.verdict} ({r.reason})")
    for (n, inp), row, rr in zip(derived, c["checks"], r.checks):
        res = rr["result"]
        if res["solc_input_sha256"] != core.json_sha256(inp):
            fails.append(f"internal: re-run input for {n} differs from the re-derived input")
        try:
            same = (root / row["solc_output_path"]).read_text() == res["raw_output"]
        except (OSError, UnicodeDecodeError):
            same = None
        info.append(f"  {n}: {res['verdict']} ({res['reason']}, {res['duration_s']} s); raw output "
                    f"{'identical to the bundled one' if same else 'differs from the bundled one (informational)' if same is False else 'unreadable (informational)'}")
        rec, got = row["verdict"], res["verdict"]
        if got == core.Verdict.REFUTE.value:
            fails.append(f"Check(b, phi) = Refute on re-run ({n})")
        elif rec == core.Verdict.REFUTE.value:
            fails.append(f"bundle records Check({n}) = Refute")
        elif rec == core.Verdict.ACCEPT.value and got != rec:
            fails.append(f"bundle records Check({n}) = Accept but the re-run gives {got} ({res['reason']})")
        elif rec == core.Verdict.UNKNOWN.value and got == core.Verdict.UNKNOWN.value:
            nc.append(f"Check({n}) = Unknown, recorded and reproduced (re-run reason {res['reason']}, "
                      f"recorded {row.get('reason')})")
        elif rec == core.Verdict.UNKNOWN.value:
            unk.append(f"bundle records Check({n}) = Unknown but the re-run gives {got}: the bundled "
                       f"per-check table does not reproduce")
    agg, _ = core.combine_verdicts(c["checks"])
    if c["verdict"] != agg:
        fails.append(f"bundle records Check verdict {c['verdict']}, but its per-check table combines to {agg}")
    elif c["verdict"] != core.Verdict.ACCEPT.value and not unk:
        nc.append(f"bundle records Check verdict {c['verdict']}: not certified (Def. 5.3); "
                  f"steps 3-6 still run and report ms_cert")
    status = FAIL if fails else UNVERIFIABLE if unk else NOT_CERTIFIED if nc else PASS
    rep.step(2, status, fails + unk + nc + info)
    return status, b_entry


def step3_mutants(root: Path, m: dict, b_entry: dict | None, rep: Report) -> dict[str, dict]:
    """Returns id -> compiled mutant entry for the mutants whose id checks out."""
    fails, info, details = [], [], []
    entries: dict[str, dict] = {}
    seen: set[str] = set()
    if b_entry is None:
        try:
            b_entry = core.compile_artifact(root / m["hard"]["b"]["path"], subject=m["provenance"]["subject"])
        except core.CompileError as e:
            rep.step(3, FAIL, [f"b does not compile: {e}"])
            return entries
    for e in m["evidence"]["M"]:
        mid = e["id"]
        d = {"id": mid, "id_matches_source": False, "properness": None, "pairs": []}
        details.append(d)
        if mid in seen:
            fails.append(f"mutant {mid[:12]}: listed twice in M")
            continue
        seen.add(mid)
        try:
            ent = core.compile_artifact(root / e["path"], subject=m["provenance"]["subject"])
        except core.CompileError as ex:
            fails.append(f"mutant {mid[:12]}: does not compile: {ex}")
            continue
        if ent["runtime_sha256"] != mid:
            fails.append(f"mutant {mid[:12]}: recomputed id {ent['runtime_sha256'][:12]} != listed id")
            continue
        d["id_matches_source"] = True
        entries[mid] = ent
        ok = False
        for j, s in enumerate(e["properness_sigma"]):
            try:
                ob, om = core.run_sequence(b_entry, s), core.run_sequence(ent, s)
                differs = not core.observation_equal(ob, om)
                d["pairs"].append({"index": j, "differs": differs,
                                   "obs_b_sha256": ob.sha256(), "obs_m_sha256": om.sha256()})
            except (core.ExecutorError, core.SigmaError) as ex:
                d["pairs"].append({"index": j, "differs": False, "error": str(ex)})
                differs = False
            ok = ok or differs
        d["properness"] = ok
        if ok:
            j = next(p["index"] for p in d["pairs"] if p["differs"])
            info.append(f"mutant {mid[:12]}: id recomputed = listed; properness sigma[{j}] "
                        f"gives run(b) != run(m)")
        else:
            fails.append(f"mutant {mid[:12]}: properness FAILED: no sigma of "
                         f"{len(e['properness_sigma'])} gives run(b, s) != run(m, s)")
    rep.step(3, FAIL if fails else PASS, fails + info, mutants=details)
    return entries


def step4_witnesses(root: Path, m: dict, entries: dict[str, dict], rep: Report) -> dict[str, list[int]]:
    """Returns mutant id -> indices of W pairs that passed (4)."""
    phi_path = root / m["hard"]["phi"]["path"]
    paths = {e["id"]: root / e["path"] for e in m["evidence"]["M"]}
    spec_over: dict[str, dict | str] = {}
    passed: dict[str, list[int]] = {}
    info = []
    for d in m["evidence"]["discarded"]:
        rep.discarded.append({"by": "producer", "mutant": d["witness"]["mutant"], "reason": d["reason"]})
    for i, w in enumerate(m["evidence"]["W"]):
        mid = w["mutant"]
        reason = None
        if mid not in paths:
            reason = "mutant not in M"
        elif mid not in entries:
            reason = "mutant failed step 3 (id)"
        else:
            if mid not in spec_over:
                try:
                    spec_over[mid] = core.compile_spec_over(phi_path, paths[mid], subject=m["provenance"]["subject"])
                except core.CompileError as ex:
                    spec_over[mid] = f"Spec does not compile over the mutant: {ex}"
            se = spec_over[mid]
            if isinstance(se, str):
                reason = se
            else:
                try:
                    ev = core.evaluate_witness(se, w["sigma"])
                except (core.ExecutorError, core.SigmaError) as ex:
                    reason = f"replay error: {ex}"
                else:
                    if ev.violated:
                        passed.setdefault(mid, []).append(i)
                        hit = sorted(k for k, v in ev.outcomes.items() if v == core.Outcome.VIOLATION.value)
                        info.append(f"W[{i}] mutant {mid[:12]}: violation in {hit}")
                    else:
                        reason = discard_reason(ev)
        if reason is not None:
            rep.discarded.append({"by": "verifier", "index": i, "mutant": mid, "reason": reason})
            info.append(f"W[{i}] mutant {mid[:12]}: DISCARDED ({reason})")
    n = sum(len(v) for v in passed.values())
    head = [f"{n} of {len(m['evidence']['W'])} witnesses replay to a violation; "
            f"{len(m['evidence']['W']) - n} discarded (discarding is not a refusal)"]
    rep.step(4, PASS, head + info)
    return passed


def step5_score(m: dict, passed: dict[str, list[int]], rep: Report) -> None:
    ids = [e["id"] for e in m["evidence"]["M"]]
    kill = sorted(i for i in set(ids) if passed.get(i))
    score = {"killed": len(kill), "total": len(set(ids))}
    rep.score, rep.kill_set = score, kill
    rep.no_valid_witness = sorted(set(ids) - set(kill))
    claimed = m["claimed"]
    fails = []
    if claimed["ms_cert"] != score:
        fails.append(f"claimed ms_cert {claimed['ms_cert']['killed']}/{claimed['ms_cert']['total']} "
                     f"!= recomputed {score['killed']}/{score['total']}")
    if claimed["kill_set"] != kill:
        fails.append(f"claimed kill_set {[k[:12] for k in claimed['kill_set']]} "
                     f"!= recomputed {[k[:12] for k in kill]}")
    info = [f"recomputed ms_cert = {score['killed']}/{score['total']}, kill set {[k[:12] for k in kill]}"]
    rep.step(5, FAIL if fails else PASS, fails + info)


def step6_vcompleteness(m: Any, rep: Report) -> None:
    fails = []
    if not isinstance(m, dict):
        rep.step(6, SKIPPED, ["manifest is not an object"])
        return
    claims = _v_completeness_claims(m)
    if claims:
        fails.append(f"V-completeness claim present at {claims} (the prototype never carries one)")
    nc = m.get("not_claimed")
    if not (isinstance(nc, list) and V_COMPLETENESS in nc):
        fails.append(f"not_claimed does not name {V_COMPLETENESS!r}")
    rep.step(6, FAIL if fails else PASS,
             fails or [f"no V-completeness claim; named in not_claimed"])


def verify(bundle: Path) -> dict:
    """Run steps 0-6 on `bundle`. An exception the steps do not anticipate (e.g.
    a source that is not UTF-8 but hashes consistently) is recorded on the step
    that raised it as could-not-verify: never a pass, never a crash."""
    rep = Report(bundle)
    try:
        return _verify(bundle.resolve(), rep)
    except Exception as e:  # noqa: BLE001
        done = {s["step"] for s in rep.steps}
        n = next(k for k in range(7) if k not in done)
        rep.step(n, UNVERIFIABLE, [f"internal error: {type(e).__name__}: {e}"])
        rep.skip_from(n + 1, f"step {n} raised")
        return rep.as_dict()


def _verify(root: Path, rep: Report) -> dict:
    m = step0_manifest(root, rep)
    if m is None:
        # Step 6 is a raw scan that needs no schema; it still runs.
        try:
            raw = json.loads((root / MANIFEST).read_bytes())
        except (OSError, ValueError, UnicodeDecodeError):
            raw = None
        step6_vcompleteness(raw, rep)
        rep.skip_from(1, "manifest invalid")
        return rep.as_dict()
    rep.labels = m["metadata"]["mutants"]  # T*: printed, never used
    if step1_hashes(root, m, rep) != PASS:
        step6_vcompleteness(m, rep)
        rep.skip_from(2, "step 1 did not pass")
        return rep.as_dict()
    status2, b_entry = step2_check(root, m, rep)
    if status2 == UNVERIFIABLE and b_entry is None:
        step6_vcompleteness(m, rep)
        rep.skip_from(3, "step 2 could not run")
        return rep.as_dict()
    entries = step3_mutants(root, m, b_entry, rep)
    passed = step4_witnesses(root, m, entries, rep)
    step5_score(m, passed, rep)
    step6_vcompleteness(m, rep)
    return rep.as_dict()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("bundle", type=Path)
    ap.add_argument("--json", type=Path, help="write the JSON report here")
    ap.add_argument("--quiet", action="store_true", help="no human summary")
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return EXIT_UNVERIFIABLE if e.code else 0
    if not a.bundle.is_dir():
        print(f"verify: no bundle directory {a.bundle}", file=sys.stderr)
        return EXIT_UNVERIFIABLE
    rep = verify(a.bundle)
    if not a.quiet:
        print(summary(rep))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(rep, indent=1, sort_keys=True) + "\n")
    return rep["exit_code"]


if __name__ == "__main__":
    sys.exit(main())
