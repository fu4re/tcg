# Task 03 — Trusted base T̂ as data

- **Type:** serialisation · **Effort:** half a day · **Output:** `bundle/trusted_base.json`
- **Source:** TCG v3 §4 (T̂ = data form of v2's Assumptions 1–6), §5 ("Assumptions that become checks", "What stays an assumption"), existing assumption ledger
- **Why it matters:** this is the file that makes Assumptions 2 and 4 mechanical and names the ones that stay assumptions. The verifier reads it for L0 and L1. It is also the file where the pilot's honesty lives.

## Fields

```
{
  "semantics": [
    { "name": "KEVM", "version": "1.0.678", "hash": "<sha256 of the semantics tarball or git tree>",
      "adequacy_evidence": "conformance suite <name>, <pass/total>", "role": "primary" },
    { "name": "EVMYulLean", "commit": "<sha>", "hash": "...",
      "adequacy_evidence": "Cancun execution tests 22330/22332", "role": "cross-check" }   // present only under variant B
  ],
  "checker": [
    { "name": "kevm-prove", "hash": "<sha256 of the pinned binary/image>", "size_loc": null,
      "self_contained": false, "note": "external prover, re-discharge only" },
    { "name": "lean", "version": "<from lean-toolchain>", "hash": "...", "self_contained": true,
      "note": "kernel checks .olean; axioms enumerated per theorem" }
  ],
  "identity": {
    "function": "keccak256(runtime_bytecode)",
    "value": "0x...",
    "address": "0x2F0b23f53734252Bda4277357e97e53Ba49FF04c",
    "block": <pinned block>,
    "constructor_and_immutables": "none; runtime code only"
  },
  "environment": {
    "chain_id": 1,
    "fork": "<name>",
    "fee_schedule": "<name>",
    "external_code": [
      { "name": "WETH", "address": "0x...", "code_hash": "0x..." },
      { "name": "Vat",  "address": "0x...", "code_hash": "0x..." }
    ],
    "caller_assumptions": "msg.sender arbitrary; no delegatecall into GemJoin",
    "precompiles": "standard",
    "resource_limits": "gas-bounded; termination guaranteed"
  },
  "assumptions": [
    { "id": "A1", "name": "semantics adequacy", "status": "assumption", "evidence": "conformance", "risk_if_false": "..." },
    { "id": "A2", "name": "environment adequacy", "status": "checked_at_L0" },
    { "id": "A3", "name": "checker soundness", "status": "assumption", "hashes": ["..."] },
    { "id": "A4", "name": "artefact identity", "status": "checked_at_L0" },
    { "id": "A5", "name": "annotation discipline", "status": "partially_checked", "note": "every Aasm listed; justifications not checked" },
    { "id": "A6", "name": "spec well-formedness", "status": "partially_checked", "note": "Pre witness replays; reachability is judgement" },
    { "id": "Aasm-01", "name": "<each Aasm fact>", "status": "assumption", "justification": "...", "risk_if_false": "..." }
  ],
  "pre_witness": { "config": "<concrete σ₀ ⊨ Pre, machine-readable>", "replay": "<how to replay it>" },
  "claims_without_certificate": [
    { "claim": "claim-01", "reason": "K prover emits no proof object; re-discharged by pinned prover" }
  ]
}
```

## Honest-reporting rule (carried over from the proposal)

If `assumptions` is empty, or any Aasm fact used by a proof is missing from it, the bundle is malformed and the verifier refuses to report L1. This is the "no proved with an empty ledger" rule in its bundle form.

## Done when

- Every hash in the file is recomputable by a script from the referenced object.
- Every Aasm fact in `hard/annotations.json` appears here with `risk_if_false`.
- `pre_witness.config` replays under the pinned semantics (a one-command script).
- The `external_code` hashes match the chain at the pinned block.
