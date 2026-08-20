"""Cross-bundle linker (REUSE) — discharge of an abstract callee-summary node
by a vendored, independently-verified callee bundle instead of an in-graph D+B.

The in-graph bridge S<==D (tcg/bridge.py, Finding 0005) discharges an abstract
callee-summary `S` (free `<program>`, cannot itself Accept) by proving, IN THE
SAME workspace, a concrete callee proof `D` over the real code `P` and a
bridge-at-P proof `B` re-proving `S` over `P` by execution. The REUSE branch
keeps the SAME anti-proxy binding but drops the caller-side re-execution: the
caller references an ALREADY-FROZEN callee bundle, vendored under
`deps/<callee_root>/`, whose declared root claim is itself a tight execution
proof over `P`. That dep root plays the role of BOTH D and B:

  * it is a genuine, dep-verified execution proof over the real callee code `P`
    (like D), and
  * the anti-proxy binding `S<=>D` is run against its claim text with the SAME
    strictness as the in-graph bridge's `S<=>B` (`tcg.bridge.binding_errors`).

Why no caller-side B is sound: `binding_errors(S, D)` enforces the rule of
consequence `S<==D` across the program-abstraction boundary — S's entry is at
least as general as D's, S's asserted effects and storage delta equal D's — and
D is a real execution proof over `P` that the dep bundle itself verified (the
caller re-runs the FULL verifier protocol on the dep before trusting it). A dep
root in a shape too loose to pin S fails binding, correctly; the dep must export
a root in the summary shape. Nothing about `P` is re-executed in the caller, and
nothing is assumed that the in-graph bridge discharged: code-identity is still
COMPUTED (keccak256 of the dep's own runtime), the binding is still performed,
and the dep's own proof over P is re-verified, not taken on faith.

Bridge-block variant (in `spec/graph.json`, the abstract-summary node):

    "bridge": {
      "callee_address": "0x...",
      "code_hash": "...",                       # keccak256 of the callee runtime
      "concrete_proof": {"dep": "<callee_root>", "root": "<claim_hash>"}
      # at_program_proof: OMITTED — the dep root is both D and B
    }

`<callee_root>` == sha256(deps/<callee_root>/MANIFEST.json): the vendored dep is
content-addressed, so a bundle can never contain itself (the DAG is acyclic for
free) and a tampered dep MANIFEST no longer hashes to its own directory name.

Pure functions over claim text + graph/environment dicts + the vendored deps/
tree (stdlib fs only). NO tcg.workspace / tcg.commands import — shared verbatim
by `graph check`, `freeze`, and the bundle-only `verify` so all three compute an
IDENTICAL structural verdict (scripts/repo-checks.sh guards the import line).
The kprove recursion into the dep is verify-only and lives in the command; it is
NOT part of this structural verdict (exactly as D/B replay is not part of the
in-graph bridge's structural verdict).
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

from tcg.bridge import (
    _hex_to_bytes, _int_token, _norm_hex, _split_rw, _top_cells,
    binding_errors, program_is_abstract_var,
)
from tcg.claims import extract_program_bytes
from tcg.keccak import keccak256_hex

# Keys the cross-bundle form of the bridge block requires / forbids. The
# in-graph form (tcg/bridge.py) instead carries `at_program_proof`; the two
# forms are distinguished by the SHAPE of `concrete_proof`.
REQUIRED_XBRIDGE_KEYS = ("callee_address", "code_hash", "concrete_proof")


def is_xbundle_ref(concrete_proof) -> bool:
    """True iff a bridge's `concrete_proof` is a cross-bundle ref `{dep, root}`
    (as opposed to the in-graph `{loop, label}` ref)."""
    return (isinstance(concrete_proof, dict)
            and "dep" in concrete_proof and "root" in concrete_proof)


def is_xbridge_node(node: dict) -> bool:
    """True iff `node` is an abstract-summary node discharged by the linker: it
    carries a bridge block whose `concrete_proof` is a cross-bundle ref."""
    b = node.get("bridge")
    return isinstance(b, dict) and is_xbundle_ref(b.get("concrete_proof"))


def xbundle_deps(nodes: dict) -> set[str]:
    """The set of `<callee_root>` a graph's cross-bundle nodes reference. Used
    by freeze (to vendor each) and verify (to recurse into each, post-order)."""
    out: set[str] = set()
    for n in nodes.values():
        if is_xbridge_node(n):
            out.add(n["bridge"]["concrete_proof"]["dep"])
    return out


@dataclass
class DepView:
    """A read-only view of a vendored dep sub-bundle under deps/<callee_root>/.
    stdlib fs only; the same content read from a workspace `deps/` or a bundle
    `deps/` yields the same view (three-way agreement)."""
    root_dir: Path
    manifest_hash: str        # sha256(deps/<callee_root>/MANIFEST.json)
    roots: set[str]           # the dep MANIFEST's declared root claim hashes

    def runtime_bytes(self) -> bytes | None:
        p = self.root_dir / "subject" / "runtime.bin"
        return p.read_bytes() if p.is_file() else None

    def claim_text(self, claim_hash: str) -> str | None:
        p = self.root_dir / "spec" / "claims" / f"{claim_hash}.k"
        return p.read_text(encoding="utf-8") if p.is_file() else None


def load_dep(deps_dir: Path, callee_root: str) -> DepView | None:
    """Read the vendored dep at deps_dir/<callee_root>/. None if absent or its
    MANIFEST is missing/unreadable — an absent dep is a refusal upstream, never
    a pass."""
    root_dir = Path(deps_dir) / callee_root
    mpath = root_dir / "MANIFEST.json"
    if not mpath.is_file():
        return None
    raw = mpath.read_bytes()
    manifest_hash = hashlib.sha256(raw).hexdigest()
    try:
        manifest = json.loads(raw.decode("utf-8"))
    except (ValueError, UnicodeDecodeError):
        return None
    roots = set(manifest.get("roots", {}) or {})
    return DepView(root_dir=root_dir, manifest_hash=manifest_hash, roots=roots)


def structural_errors(summary_hash: str, nodes: dict, claim_text_of,
                      environment: dict | None, deps_dir):
    """Bundle-only structural discharge of a cross-bundle abstract-summary node.

    Returns (errors, ref) where ref == {"dep": callee_root, "root": claim_hash}
    once the dep root resolves. Everything here is pure text + keccak + a read
    of the vendored deps/ tree, so `graph check`, `freeze`, and `verify`
    re-derive an identical verdict. The kprove recursion into the dep (verify
    obligation #1) is NOT performed here — it is the command's job, exactly as
    replaying D/B is for the in-graph bridge.

    Checks, in order (each a refusal):
      * the bridge block has the cross-bundle shape and OMITS at_program_proof;
      * the summary abstracts ONLY its <program> cell;
      * the vendored dep deps/<callee_root>/ exists and is content-addressed
        (sha256(its MANIFEST.json) == the declared <callee_root>);
      * concrete_proof.root is one of the dep's declared roots (membership);
      * code-identity, COMPUTED: keccak256(dep runtime) == declared code_hash,
        AND environment.external_code[callee] == dep runtime byte-for-byte;
      * the dep root D proves over exactly P (its <program> == dep runtime);
      * the summary <id> frames the declared callee address;
      * the anti-proxy binding S<=>D (D as B), tcg.bridge.binding_errors, same
        strictness as the in-graph bridge.
    """
    node = nodes.get(summary_hash, {})
    loop, label = node.get("loop"), node.get("label")
    prefix = f"xbundle-summary {loop}/{label}"
    ref: dict = {}
    errs: list[str] = []

    b = node.get("bridge")
    if not isinstance(b, dict):
        return ([f"{prefix}: node has no bridge block"], ref)
    cp = b.get("concrete_proof")
    if not is_xbundle_ref(cp):
        return ([f"{prefix}: concrete_proof is not a cross-bundle ref "
                 "{{dep, root}} — route this node through the in-graph bridge"],
                ref)
    for k in REQUIRED_XBRIDGE_KEYS:
        if k not in b:
            errs.append(f"{prefix}: bridge block missing '{k}'")
    if "at_program_proof" in b:
        errs.append(f"{prefix}: cross-bundle form must OMIT at_program_proof — "
                    "the dep root plays the role of both D and B; a caller-side "
                    "re-execution over P is exactly what REUSE avoids")
    if errs:
        return (errs, ref)

    summary_text = claim_text_of(summary_hash)
    if not program_is_abstract_var(summary_text):
        errs.append(f"{prefix}: summary <program> is not a bare variable — an "
                    "abstract summary must abstract ONLY the program cell; a "
                    "concrete-program summary needs no bridge (discharge it as "
                    "one hash)")

    callee_root = str(cp["dep"])
    root_hash = str(cp["root"])
    dep = load_dep(deps_dir, callee_root)
    if dep is None:
        errs.append(f"{prefix}: vendored dep deps/{callee_root}/ is absent or "
                    "has no MANIFEST.json — a cross-bundle summary is discharged "
                    "only by a vendored, self-contained callee bundle")
        return (errs, ref)
    if dep.manifest_hash != callee_root:
        errs.append(f"{prefix}: dep MANIFEST hash {dep.manifest_hash} != declared "
                    f"callee_root {callee_root} — the vendored dep is not "
                    "content-addressed (tampered or mis-named directory)")
        return (errs, ref)
    if root_hash not in dep.roots:
        errs.append(f"{prefix}: concrete_proof.root {root_hash[:12]} is not one "
                    "of the dep bundle's declared roots — a NON-root dep claim "
                    "is not a guaranteed execution proof over P")
        return (errs, ref)
    d_text = dep.claim_text(root_hash)
    if d_text is None:
        errs.append(f"{prefix}: dep root claim file "
                    f"deps/{callee_root}/spec/claims/{root_hash[:12]}.k is missing")
        return (errs, ref)
    p_bytes = dep.runtime_bytes()
    if p_bytes is None:
        errs.append(f"{prefix}: dep deps/{callee_root}/subject/runtime.bin is "
                    "missing — code-identity cannot be established")
        return (errs, ref)
    ref = {"dep": callee_root, "root": root_hash}

    addr_int = _int_token(str(b["callee_address"]))
    if addr_int is None:
        errs.append(f"{prefix}: callee_address {b['callee_address']!r} is not a "
                    "number")
        return (errs, ref)

    # code-identity (1): environment.external_code[callee] == P byte-for-byte.
    ext = (environment or {}).get("external_code") or {}
    env_hex = None
    for key, val in ext.items():
        if _int_token(str(key)) == addr_int:
            env_hex = val
            break
    if env_hex is None:
        errs.append(f"{prefix}: environment.external_code has no entry for callee "
                    f"address {b['callee_address']} — code-identity cannot be "
                    "established")
        return (errs, ref)
    env_bytes = _hex_to_bytes(env_hex)
    if env_bytes is None:
        errs.append(f"{prefix}: external_code[{b['callee_address']}] is not valid hex")
        return (errs, ref)
    if env_bytes != p_bytes:
        errs.append(f"{prefix}: external_code[{b['callee_address']}] != the dep's "
                    "subject/runtime.bin — the summary is bound to code the dep "
                    "did NOT prove over")

    # code-identity (2): keccak256(dep runtime) == declared code_hash, COMPUTED.
    computed = keccak256_hex(p_bytes)
    if computed != _norm_hex(b["code_hash"]):
        errs.append(f"{prefix}: code-identity FAILED — keccak256(dep runtime) = "
                    f"{computed} != declared code_hash {_norm_hex(b['code_hash'])}")

    # The dep root D must be a proof over exactly P (byte-for-byte). The dep's
    # own P0-A root-program binding already guarantees this; re-checked here so
    # this module's verdict does not depend on the dep having been re-verified.
    d_prog = extract_program_bytes(d_text)
    if d_prog != p_bytes:
        errs.append(f"{prefix}: dep root D <program> is not the dep's runtime P — "
                    "D proves a delta over a DIFFERENT program than the one whose "
                    "keccak binds the summary")

    # The summary must frame exactly the declared callee address.
    sid = _top_cells(summary_text).get("id")
    if sid is None or _int_token(_split_rw(sid)[0]) != addr_int:
        errs.append(f"{prefix}: summary <id> is not the declared callee address "
                    f"{addr_int} — the summary does not frame the bound callee")

    # anti-proxy binding S<=>D (the dep root plays the role of B). IDENTICAL
    # strictness to the in-graph bridge — the same tcg.bridge.binding_errors.
    errs += binding_errors(summary_text, d_text, addr_int, prefix)
    return (errs, ref)
