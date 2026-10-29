# Task 05 — Provenance layer P, minimal

- **Type:** serialisation of session records · **Effort:** half a day · **Output:** `bundle/provenance/`
- **Source:** TCG v3 §8; existing run records (`artifact.json`, transcripts, `halmos_invocations`)
- **Principle:** everything here is class U. Nothing in P is an input to Check′, to the ladder below L4, or to H's approval. Its readers are auditors and engineers. Fabricating it can only make L4 fail.

## Three pieces for the pilot; three deferred

### 1. Session ledger — `provenance/ledger.jsonl`

Append-only, hash-chained. One line per tool invocation during assembly and during the original pilot runs where records exist:

```
{ "seq": 17, "prev": "<hash of line 16>", "tool": "kevm-prove", "tool_hash": "...",
  "inputs": ["<hash>", "<hash>"], "outputs": ["<hash>"], "exit": 0,
  "argv": [...], "started": "...", "ended": "...", "deterministic": true }
```

Generator calls are recorded as events too, with `deterministic: false`, model id, and hashes of prompt and completion; they are never replayed.

### 2. Iteration log — `provenance/iterations.json`

For each prover run that preceded the accepted one (where records exist): hashes of the claim, annotations and result; for `Refute`, the counterexample; for `Unknown`, the claim. If the original pilot discarded these, say so: `"iterations_retained": false, "reason": "..."`. This is the completeness signal v2 threw away; the pilot records whether it was kept, not that it was.

### 3. Generator attestation — `provenance/generators.json`

For each model used (synthesis, back-translation): provider, model id, sampling parameters if known, and `"attestation": "none available"` where the provider offers no signed attestation. Says which untrusted component produced what; says nothing about correctness.

### Deferred (not in pilot)

- Decision records: one stub file `provenance/decision-stub.md` listing decisions D1–D11 by reference to `DECISIONS.md`; no per-decision evidence links.
- Interpretability traces: none; `"traces": "not recorded"`.
- Specification lineage beyond `evidence/phi_versions.json`: none.

## Output

```
provenance/
  ledger.jsonl
  iterations.json
  generators.json
  decision-stub.md
  sessions/<producer-session-transcript>   (U; for the back-translation withholding proof)
```

## Done when

- `tools/verify_ledger.py` walks the chain and confirms every `prev` hash.
- Every event with `deterministic: true` has argv and input hashes sufficient to replay it (task 06 L4 tries).
- The back-translation session transcript shows `requirements.md` was not provided.
