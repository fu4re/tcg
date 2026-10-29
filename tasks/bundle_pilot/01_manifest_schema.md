# Task 01 — Manifest schema

- **Type:** format definition · **Effort:** one evening · **Output:** `bundle/schema/manifest.schema.json` + one worked example
- **Source of truth:** TCG v3 §4 (Definition 4, Structure, Signatures, "The checker travels with the bundle", "What is deliberately absent"), §10 (`not_claimed`)

## What the manifest is

The root of the Merkle DAG. One JSON file. Lists every child by hash, trust class and media type. Carries the producer's signature and the `not_claimed` list. Contains no verdict of any kind: verdicts are recomputed by whoever holds the bundle.

## Required fields

```
{
  "format":          "tcg-bundle/0.1",
  "domain":          "evm-bytecode",
  "root_hash":       "<sha256 over the canonical serialisation of everything below this line>",
  "producer_sig":    { "alg": "ed25519", "pubkey": "...", "sig": "..." },
  "self_contained":  false,
  "self_contained_reason": "KEVM claims re-discharged by a pinned external prover; no proof object",
  "children": [
    { "path": "hard/artifact.bin",          "hash": "...", "class": "T",  "media": "application/octet-stream", "role": "b"  },
    { "path": "hard/spec/claim-01.k",       "hash": "...", "class": "T",  "media": "text/x-k",                 "role": "phi" },
    { "path": "hard/annotations.json",      "hash": "...", "class": "T",  "media": "application/json",         "role": "a"  },
    { "path": "hard/certs/lemma-01.olean",  "hash": "...", "class": "T",  "media": "application/x-lean-olean", "role": "c"  },
    { "path": "trusted_base.json",          "hash": "...", "class": "T",  "media": "application/json",         "role": "T_hat" },
    { "path": "evidence/coverage.json",     "hash": "...", "class": "T*", "media": "application/json",         "role": "V"  },
    { "path": "evidence/approval.sig",      "hash": "...", "class": "T*", "media": "application/octet-stream", "role": "V"  },
    { "path": "provenance/ledger.jsonl",    "hash": "...", "class": "U",  "media": "application/x-ndjson",     "role": "P"  }
  ],
  "not_claimed": [
    "The artefact is secure.",
    "φ is complete.",
    "The generator is reliable, its reasoning was sound, or its traces are faithful.",
    "Economic or game-theoretic properties of the surrounding system.",
    "Anything about an artefact whose identity differs from id(b) by one byte."
  ]
}
```

## Rules the schema must enforce

1. Every child has exactly one `class` from {U, T, T*} and one `role` from {b, phi, a, c, T_hat, V, P, checker}.
2. Roles b, phi, a, T_hat and checker are mandatory. Role c is mandatory per claim; a claim without a certificate must appear in `trusted_base.json` under `claims_without_certificate` with the reason.
3. `root_hash` covers everything except `producer_sig` (so the signature is over the root).
4. Nothing in the manifest is allowed to carry a verdict, a level, a score or the word "proved". A linter rejects a manifest containing any of `verdict`, `level`, `proved`, `pass` as keys.
5. `self_contained` is a boolean, and `false` requires `self_contained_reason`.

## Output

- `manifest.schema.json` (JSON Schema draft 2020-12)
- `examples/manifest.example.json` validated against it
- `tools/lint_manifest.py`: validates schema, recomputes `root_hash`, checks rule 4, exits non-zero on any failure

## Done when

The example validates, the linter rejects a manifest with a `verdict` key, and the linter rejects a manifest whose `root_hash` was computed over a different child list.
