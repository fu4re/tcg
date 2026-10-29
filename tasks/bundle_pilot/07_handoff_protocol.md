# Task 07 — Hand-off protocol and acceptance

- **Type:** the experiment · **Effort:** one evening of agent time, one human with a stopwatch · **Output:** `handoff/` report
- **Hypothesis:** a party with no access to the producing session recomputes the ladder from the bundle alone. The list of what it needed from outside the bundle is the result.

## Roles

| Role | Who | Has access to |
|---|---|---|
| Producer, agent A | one agent session (model id recorded) | the repo, the existing artefacts, tasks 00–05, the verifier source |
| Consumer, agent B | a different model if possible, otherwise a fresh session with no shared files | the bundle directory, the verifier source, the two public keys, an RPC URL or the state snapshot. **Nothing else.** No repo, no session of A, no chat history |
| Consumer, human | one person outside the project (ideally without formal-methods background) | same as agent B, plus a stopwatch |

## Protocol

**Step 1 — A assembles.** Following tasks 00–05, A produces `bundle/` and signs the root. A runs the verifier once on its own output and stores `handoff/ladder_A.json`. A's session transcript goes to `provenance/sessions/`.

**Step 2 — Transfer.** `bundle/` is copied to a clean location. Nothing from A's working directory travels except the bundle and the verifier source. The copy's root hash is recorded.

**Step 3 — B verifies.** B receives one instruction:

> You have a proof-carrying bundle and a verifier's source. Build the verifier, confirm its hash matches the one named in the bundle's trusted base, run it, and produce `ladder_B.json`. Then write `gaps.md`: every piece of information or tooling you needed that was not inside the bundle, every point where you were unsure what a field meant, and every step where you had to guess. Do not fix the bundle. Do not consult anything outside what you were given.

B's full transcript is kept.

**Step 4 — Human replays.** Same instruction, same inputs, stopwatch running from "bundle received" to "ladder produced". Record where they got stuck and for how long.

**Step 5 — Compare.** `ladder_A.json` vs `ladder_B.json` vs `ladder_human.json`, level by level.

## Acceptance

| Criterion | Pass condition |
|---|---|
| Re-verifiability (v3 Proposition 1) | L0, L1, L3, L4 statuses identical across A, B, human. L2 may differ only in the back-translation agreement flags (those are judgement) |
| Self-containment, variant A | B's `outside_bundle` lists exactly the items A's does (KEVM image by hash, RPC/snapshot) and nothing more |
| Self-containment, variant B | B's `outside_bundle` lists only the RPC/snapshot |
| Gaps are the finding | `gaps.md` from B and from the human are non-empty. An empty gaps list is treated as suspicious and triggers a check that B did not have hidden access |
| Human replay time | recorded, not thresholded. The proposal's "<30 minutes" is a target for M3, not a pilot pass/fail |
| Monotonicity held | the five mutated bundles from task 06 each produce a strictly lower ladder in B's hands too |

## Report — `handoff/report.md`

1. Three ladders side by side.
2. `gaps.md` from B and from the human, merged, each item classified: **missing from bundle** (format change needed) · **present but unclear** (schema or docs change) · **outside by design** (named in T̂; acceptable) · **consumer error**.
3. Human time, with the longest single stall and its cause.
4. One paragraph: what the bundle format must change before a second contract.
5. Honest ladder for GemJoin, variant A, as the sentence that goes into the proposal's Evidence section.

## Expected honest result (written before the run, so it can be wrong)

L0 pass. L1 pass with `self_contained: false` under A; under B, pass and self-contained if the EVMYulLean port lands. L2: coverage total, mutants replay, back-translation shows at least one disagreement. L3 pass. L4 partial (iteration records from June are likely incomplete). `gaps.md`: the KEVM image is the largest outside dependency; `phi.json` field semantics will need a README.

If the actual result is better than this on every line, check for leakage before believing it.
