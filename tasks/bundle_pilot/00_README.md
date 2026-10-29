# Bundle pilot — task index

- **Set:** 2026-10-29 · **Goal:** assemble one complete proof-carrying bundle per TCG v3 (Definition 4, β = (b, φ, a, c, T̂, V, P)) for an already-verified Solidity contract, hand it from a producing agent to a consuming agent, and recompute the verdict ladder L0–L4 from the bundle alone.
- **Contract:** GemJoin ETH-A (deployed; five KEVM claims; Lean arithmetic lemmas; keccak binding; assumption ledger; 10/10 replay already on record). Non-trivial environment E (external code: WETH, Vat) is the point, not an obstacle.
- **Only new code:** the verifier (task 06). Everything else is serialisation of artefacts that exist.
- **Two checker variants, both tried:** pinned KEVM re-discharge (variant A) and Lean kernel over EVMYulLean (variant B). See task 08.
- **Hypothesis under test:** a second party with no access to the producing session recomputes the ladder from the bundle alone, and the list of what it had to fetch from outside the bundle is the finding.

## Order

| # | Task | Effort | Depends on |
|---|---|---|---|
| 00 | Decisions before code | one evening | — |
| 01 | Manifest schema | one evening | 00 |
| 02 | Hard layer: b, φ, a, c | one day | 01 |
| 03 | Trusted base T̂ as data | half a day | 01 |
| 04 | Evidence layer V (minimal) | one day | 02, 03 |
| 05 | Provenance layer P (minimal) | half a day | 01 |
| 06 | Verifier | two to three days | 01–05 |
| 07 | Hand-off protocol and acceptance | one evening + one human | 06 |
| 08 | Checker variants A and B | runs inside 02 and 06 | — |

Total: roughly one and a half weeks to the first handed-off bundle.

## What the pilot does not do

No composition across artefacts. No interpretability traces. No decision records beyond a stub. No second language. No benchmark. Those are project work, not pilot work.
