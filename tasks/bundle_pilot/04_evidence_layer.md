# Task 04 — Evidence layer V, minimal

- **Type:** the only part of the pilot that produces new material · **Effort:** one day · **Output:** `bundle/evidence/`
- **Source:** TCG v3 §7; vacuity gate machinery (sheaf F0005: Probe R / Probe M); solver-as-judge rule (judge = solver or kernel, never LLM)
- **Principle:** everything here is produced by untrusted tools and consumed by the human H. Nothing here is an input to Check′. The verifier runs the tools and reports; it never judges.

## Four pieces, in order of cost

### 1. Coverage matrix — `evidence/coverage.json`

Built from `hard/spec/phi.json` and `hard/spec/requirements.md`. Two maps: `requirement → [claims]` and `claim → [requirements]`. A script checks totality both ways. A requirement with no claim goes to `declared_blind_spots` with one sentence; a claim with no requirement goes to `unreferenced_clauses` (either a strengthening H should know about, or implementation detail leaking into φ). Both lists are allowed to be non-empty; they are not allowed to be hidden.

### 2. Blind back-translation — `evidence/backtranslation.json`

A model that has **not** seen `requirements.md` (fresh session, only `phi.json` and the K claims as input) translates each claim into one or two English sentences. A second step (script or second fresh session) places each translation beside the requirement it references and flags disagreement. Output per claim: `{ claim, translation, referenced_requirement, agreement: "agree" | "disagree" | "unclear", note }`. Disagreements are **reported, not resolved**. Record the model id and the fact that `requirements.md` was withheld.

### 3. Mutant witnesses — `evidence/mutants/claim-0N/`

For each of the five claims, at least one artefact b′ that violates the intended property, together with a `Refute(ce)` from the checker or a concrete trace under the pinned semantics showing the violation. Reuse Probe M: mutate GemJoin's bytecode or a harness around it (e.g. join credits `wad+1`, exit skips the Vat call, join does not pull WETH) and show the claim refutes it. A claim no mutant violates is reported as `no_witness` — that is the v2 Proposition 1 caveat made visible, not a failure to hide.

Each witness: `mutant.bin` (or harness), `refutation.json` (checker output or trace), `replay.sh` (one command the consumer runs).

### 4. Non-vacuity witness — `evidence/pre_witness/`

The concrete σ₀ ⊨ Pre from `trusted_base.json`, with a replay script. Same object, stored here as evidence that the guarantee quantifies over a non-empty set.

### 5. Versioned approval — `evidence/approval.json` + `approval.sig`

- `phi` is versioned: `evidence/phi_versions.json` lists every hash of `phi.json` from the first version H saw to the one proven, with a one-line note per change.
- H (the author, D5) signs `sha256(phi.json) ∥ sha256(requirements.md)` with the oracle key (D4). The signed hash **must equal** the hash of the `phi.json` in `hard/`. If φ changed after signing, the signature is stale and L3 fails — that is the intended behaviour.
- Coverage indicators (mutation score, obligation coverage, exit-status coverage) are reported as numbers with the computation method named and the label `heuristic`. For the pilot, mutation score alone is enough.

## What V refuses to contain

No sentence, from any tool, claiming that φ matches n. If the back-translation step emits one, it is moved to `provenance/` and tagged `U`.

## Done when

- Totality script passes or every gap is listed.
- Back-translation ran with `requirements.md` provably withheld (session transcript in P).
- Five claims → ≥5 witness directories, each with a working `replay.sh`; `no_witness` claims listed.
- `approval.sig` verifies against the oracle pubkey and the hash of the proven `phi.json`.
