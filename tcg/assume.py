"""Typed-stub assumption (STUB) — an abstract callee-summary node discharged by
a *named, typed assumption* instead of a proof over the callee's code.

The in-graph bridge S<==D (tcg/bridge.py) discharges an abstract callee-summary
`S` (free `<program>`, cannot itself Accept) by re-proving it over the real
callee code `P`; the cross-bundle linker (tcg/xbridge.py) discharges it by
REUSE of a vendored, independently-verified callee bundle. The **stub** does
NEITHER: the callee is opaque (its code is not proved), and the caller chooses
to *assume* a typed frame for it. That assumption is:

  * **real / load-bearing** — `S` is still injected as a trusted child into the
    caller's replay, so a root that consumes it genuinely depends on it. It is
    NOT bridged and NOT replayed (its symbolic `<program>` cannot Accept);
  * **never silent** — every assume-node is enumerated in the trust ledger
    under `A_callee_<addr>`, and a stub is NEVER a clean exit 0 without a trace:
    default `verify` surfaces a prominent `⚠` section, `--strict` refuses, and a
    missing-or-orphan ledger entry refuses (`consistency_errors`).

verify MUST NOT try to "check" the frame text against the callee — the frame is
an ASSUMPTION the caller chose precisely because the callee is not proved.
Interpreting or validating it would be unsound theatre. The tool only checks
ledger CONSISTENCY and SURFACES the frame.

Assume-block variant (in `spec/graph.json`, mutually exclusive with `bridge`):

    "assume": {
      "callee_address": "0x...",
      "frame": "human-readable typed frame: what the opaque callee MAY and MAY
                NOT do — storage-frame + reentrancy, conservative by default",
      "ledger_id": "A_callee_<addr>"
    }

Pure functions over the graph dict + claim text (stdlib only). NO tcg.workspace
/ tcg.commands import — the structural verdict is shared verbatim by `graph
check`, `freeze`, and the bundle-only `verify` (three-way agreement;
scripts/repo-checks.sh guards the import line). Ledger CONSISTENCY additionally
needs trust-manifest.json, which only `freeze` (writer) and `verify` (re-check)
have; `graph check` checks only the structural half.
"""
from __future__ import annotations

from tcg.bridge import _int_token, _split_rw, _top_cells, program_is_abstract_var

# Keys the assume block requires. `ledger_id` is derivable (A_callee_<addr>) but
# stored explicitly so the graph and the ledger are cross-checkable by content.
REQUIRED_ASSUME_KEYS = ("callee_address", "frame", "ledger_id")

# The ledger key prefix that marks an author-chosen opaque-callee assumption,
# distinguishing it from the baseline environment assumptions (A_keccak, …).
LEDGER_PREFIX = "A_callee_"


def ledger_id_for(callee_address) -> str:
    """The canonical trust-ledger key for an opaque callee at `callee_address`."""
    return f"{LEDGER_PREFIX}{callee_address}"


def is_assume_node(node: dict) -> bool:
    """True iff `node` is an abstract-summary node discharged by a typed stub:
    it carries an `assume` block (mutually exclusive with `bridge`)."""
    return isinstance(node.get("assume"), dict)


def assume_nodes(nodes: dict) -> list[str]:
    """The hashes of every assume-node, sorted for determinism."""
    return sorted(h for h, n in nodes.items() if is_assume_node(n))


def roots_injecting(summary_hash: str, nodes: dict, edges: list) -> list[str]:
    """The root claim hashes whose proof injects `summary_hash` as a trusted
    child — i.e. the roots that transitively depend on this stub over
    trusted-lemma edges. This is exactly `load_bearing_for`: a stub is load-
    bearing iff a root reaches it. Pure graph reachability, sorted."""
    children: dict[str, list[str]] = {h: [] for h in nodes}
    for e in edges:
        if e.get("type") == "trusted-lemma" and e.get("from") in children:
            children[e["from"]].append(e.get("to"))
    out: list[str] = []
    for r in (h for h, n in nodes.items() if n.get("root")):
        seen: set[str] = set()
        stack = [r]
        while stack:
            h = stack.pop()
            if h in seen:
                continue
            seen.add(h)
            stack.extend(children.get(h, []))
        if summary_hash in seen:
            out.append(r)
    return sorted(out)


def structural_errors(summary_hash: str, nodes: dict, claim_text_of) -> list[str]:
    """Bundle-only structural discharge of a typed-stub assume-node.

    Returns a list of errors (each a refusal). Everything here is pure graph +
    claim text, so `graph check`, `freeze`, and `verify` re-derive an identical
    verdict. The frame text is NEVER interpreted — that would be unsound
    theatre; it is surfaced, not validated.

    Checks, in order (each a refusal):
      * the node carries an assume block and NOT a bridge block (an abstract
        summary is discharged by exactly one mechanism);
      * the assume block is well-formed (required keys present, frame non-empty,
        callee_address numeric);
      * the ledger_id is exactly A_callee_<callee_address> (so the graph node
        and its ledger entry are cross-checkable by content);
      * the summary abstracts ONLY its <program> cell (program_is_abstract_var);
      * the summary <id> frames the declared callee_address.
    """
    node = nodes.get(summary_hash, {})
    loop, label = node.get("loop"), node.get("label")
    prefix = f"assume-summary {loop}/{label}"
    errs: list[str] = []

    a = node.get("assume")
    if not isinstance(a, dict):
        return [f"{prefix}: node has no assume block — a typed stub is discharged "
                "only by a well-formed assume block"]
    if isinstance(node.get("bridge"), dict):
        errs.append(f"{prefix}: node carries BOTH an assume and a bridge block — "
                    "an abstract summary is discharged by exactly one mechanism "
                    "(assume XOR bridge)")
    for k in REQUIRED_ASSUME_KEYS:
        if k not in a:
            errs.append(f"{prefix}: assume block missing '{k}'")
    if errs:
        return errs

    frame = a["frame"]
    if not isinstance(frame, str) or not frame.strip():
        errs.append(f"{prefix}: assume frame must be non-empty human text stating "
                    "the callee's storage-frame and reentrancy (conservative by "
                    "default)")

    addr_int = _int_token(str(a["callee_address"]))
    if addr_int is None:
        errs.append(f"{prefix}: callee_address {a['callee_address']!r} is not a "
                    "number")
        return errs

    expected_id = ledger_id_for(a["callee_address"])
    if str(a["ledger_id"]) != expected_id:
        errs.append(f"{prefix}: ledger_id {a['ledger_id']!r} is not the canonical "
                    f"{expected_id!r} for the declared callee_address — the graph "
                    "node and its ledger entry must be cross-checkable by content")

    summary_text = claim_text_of(summary_hash)
    if not program_is_abstract_var(summary_text):
        errs.append(f"{prefix}: summary <program> is not a bare variable — an "
                    "abstract summary must abstract ONLY the program cell; a "
                    "concrete-program summary needs no stub (discharge it as one "
                    "hash)")

    sid = _top_cells(summary_text).get("id")
    if sid is None or _int_token(_split_rw(sid)[0]) != addr_int:
        errs.append(f"{prefix}: summary <id> is not the declared callee address "
                    f"{addr_int} — the summary does not frame the assumed callee")
    return errs


def ledger_entry(node: dict, load_bearing_for: list[str]) -> dict:
    """The trust-manifest entry for an assume-node, keyed under its ledger_id.
    `status` MUST make it distinguishable from the baseline environment
    assumptions (A_keccak etc.): author-chosen, per-bundle, load-bearing."""
    a = node["assume"]
    return {
        "status": "assumed-callee (AUTHOR-CHOSEN, load-bearing) — opaque callee "
                  "summary, NOT discharged over the callee's code",
        "callee_address": a["callee_address"],
        "frame": a["frame"],
        "load_bearing_for": list(load_bearing_for),
    }


def consistency_errors(nodes: dict, trust_manifest: dict) -> list[str]:
    """The stub-is-never-silent ledger consistency verdict (verify-only; freeze
    writes it consistent by construction). Every assume-node's ledger_id must be
    present in trust-manifest.json, AND every A_callee_* ledger entry must be
    referenced by some assume-node. A missing or orphan entry REFUSES."""
    trust_manifest = trust_manifest or {}
    declared: set[str] = set()
    for _h, n in nodes.items():
        if is_assume_node(n):
            lid = n["assume"].get("ledger_id")
            if lid is not None:
                declared.add(str(lid))
    ledger_ids = {str(k) for k in trust_manifest if str(k).startswith(LEDGER_PREFIX)}

    errs: list[str] = []
    for lid in sorted(declared):
        if lid not in trust_manifest:
            errs.append(f"assume-node ledger_id {lid} is absent from "
                        "trust-manifest.json — an author-chosen assumption must be "
                        "enumerated in the ledger (a stub is never a silent pass)")
    for lid in sorted(ledger_ids):
        if lid not in declared:
            errs.append(f"trust-manifest ledger entry {lid} is not referenced by "
                        "any assume-node — orphan ledger entry (a stub record "
                        "without its graph node)")
    return errs
