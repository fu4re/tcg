# Task 00 — Decisions before code

- **Type:** design decisions · **Effort:** one evening · **Output:** `bundle/DECISIONS.md`, committed before any bundle code
- **Why first:** every decision below is one the producing agent will otherwise take silently. Taking them in a file makes them part of the bundle's provenance and keeps variant A and variant B comparable.

## Decisions to record

| # | Decision | Proposed default | Alternatives |
|---|---|---|---|
| D1 | Content hash | sha256 over raw bytes; hex-encoded | blake3; multihash/CID if IPFS compatibility matters later |
| D2 | Addressing | Merkle DAG: manifest lists each child by hash; children stored as files named by hash; no archive format | tar with manifest inside (rejected by v3 §4: "a Merkle DAG, not an archive") |
| D3 | Producer signature | ed25519 (minisign or `openssl pkeyutl`); signs the manifest root hash | — |
| D4 | Oracle signature (H) | separate ed25519 key held by the author personally; signs `sha256(φ) ∥ sha256(n)` | same key as producer (rejected: v3 §4 says these are different keys with different meanings) |
| D5 | Who is H for the pilot | the author, personally | — |
| D6 | Check′ for KEVM claims | variant A: pinned KEVM re-discharge, binary hash in T̂, bundle reports `self_contained: false` | variant B: Lean kernel over EVMYulLean (task 08) |
| D7 | Check′ for Lean lemmas | `lean` kernel check of the `.olean`/source with `#print axioms` for each theorem; no `sorry` | — |
| D8 | Identity id(b) | keccak256 of runtime bytecode as read from chain at a pinned block | — |
| D9 | Environment snapshot for L0 | pinned block number + archive-node RPC, or a committed state snapshot (bytecode of GemJoin, WETH, Vat at that block) | live RPC only (rejected: non-reproducible) |
| D10 | Trust-class labels | `U`, `T`, `T*` exactly as v3 §3; every manifest child carries one | — |
| D11 | What is `not_claimed` | the six sentences of v3 §10 verbatim, as a list | — |

## Output

`bundle/DECISIONS.md`: one line per decision, chosen option, one sentence why. Reviewed by the author, committed, hash recorded in the first manifest.

## Done when

All eleven rows have a chosen option. If a row is left open, the producing agent is instructed to refuse to assemble rather than guess.
