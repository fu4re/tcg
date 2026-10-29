# Bundle pilot — implementation plan

- **Drafted:** 2026-10-29, branch `feat/e2e-bundle` (off `main` @ `be9b280`). **Status:** §1 answered 2026-10-29: Q1 agreed (3 getters + 2 rebuilt revert roots); Q2 no commits at all, the author orders them later; Q3 TCG v3 = https://claude.ai/artifact/57GjxDSW4qC8aqEiwnX3Jo, snapshot in `tcg_v3_snapshot.md`; Q4 the author generates the oracle key when asked; Q5 the naive-loop series is not needed for the pilot, so the VM is free. Decisions drafted in `pilot/bundle/DECISIONS.md`.
- **Working rules:** nothing is committed and nothing is pushed to origin during the pilot. All files in English.
- **Location (moved 2026-10-29):** ALL pilot work lives on the VM `tcg` in `~/sheaf/tcg` (branch `feat/e2e-bundle`, at main `be9b280`), plus `~/evm-smith` (working-tree copy, no .git; see PROVENANCE_COPY.txt). The laptop has almost no free disk: nothing pilot-related is written there. The unmerged branches p1-b-vat-slip, p1-korerpc-probe, p1-c-weth and callee-vat-slip-summary are present on the VM clone.

## 0. Ground truth vs the task files (checked 2026-10-29)

The task files describe a set of artefacts. This is what actually exists today.

| Task claim | Reality | Consequence |
|---|---|---|
| GemJoin ETH-A at `0x2F0b23f53734252Bda4277357e97e53Ba49FF04c` (task 03) | **Wrong address.** The real one, used in every Finding and iface, is `0x2F0b23f53734252Bda2277357e97e1517d6B042A` (codehash `0x8661c673…74fa`, 3462 bytes) | Fix in 03 before assembly. If the typo makes it into T̂, L0 fails (that would be correct behaviour) |
| "five KEVM claims, 10/10 replay already on record" | The 5-root G4 bundle (cert `668f3d7d…`, Finding 0003) lived in an August session scratchpad that **no longer exists**. Its claim sources were never committed. What can be reproduced on `main`: the **3 full getter claims** `vat()/ilk()/gem()` (`scripts/build-getters-full.sh`, Finding 0003b) | 2 of the 5 claims have to be rebuilt from Finding 0003's prose. That is new content, which breaks task 02's "nothing new" rule, so it goes in `provenance/decision-stub.md`. See Q1 |
| "Lean arithmetic lemmas (tcg F0004)" | F0004 is about **K** `[simplification]` lemmas (`theory/patches/lemmas.diff`), not Lean. No Lean theorem about GemJoin exists | Under variant A, role `c` holds **zero** real certificates: all 5 claims go in `claims_without_certificate`. The K lemmas go in `a` and in T̂ (`A_simp_lemmas`). Lean only appears with variant B |
| Requirements like "join moves exactly `wad` WETH … credits `gem[ilk][usr]`" (task 02) | Not proved. Stage C (join/exit caller composition) is open (Finding 0006 + correction) | These requirements go to `declared_blind_spots`. That is the honest coverage result, not a defect to fix |
| "the KEVM image" (tasks 06/08) | No image exists. KEVM = nix `kprove` 7.1.337 + kompiled `~/toolchains/kevm-1.0.678-lemmas` on the laptop only. The VM has no K, nix or Lean (only cast/forge/solc/z3) | Packaging the checker is its own workstream (WS-C). Known trap: `definition.kore` is not byte-deterministic across kompiles, so the consumer must pull the producer's exact artefact by hash and must not rebuild it |
| TCG v3 (Definition 4, §3–§10, the six `not_claimed` sentences) | Not in the repo. `~/Documents` is not readable from this session | Needed verbatim for D10/D11 and the schema. See Q3. Note that the task 01 example lists **five** sentences, while D11 says six |
| EVMYulLean covers GemJoin's opcodes (task 08 precondition) | `~/evm-smith/EVMYulLean` @ `56253eb`, Lean `v4.22.0` installed, 1.6 MB, so it can be vendored. The opcode check itself has not been re-run | WS-B re-checks it in its first hour |
| Python stdlib for the verifier | stdlib has neither keccak256 (`sha3_256` ≠ keccak) nor ed25519 | keccak: vendor `tcg/keccak.py` (pure, vector-tested). ed25519: see D3 |

## 1. Questions for the author (blocking)

- **Q1 — claim set.** Recommended: the 3 getters (reproducible, FULL) plus 2 rebuilt G4 revert roots. Candidates: `cage()` reverts with empty wards (∀ caller) and `join` reverts when `live==0` (∀ caller), since both are universal and fire before any external call. Alternatives: 3 getters only (honest, but not "five"), or all 7 G4 roots rebuilt.
- **Q2 — no commits at all?** Task 00 wants `DECISIONS.md` "committed before any bundle code" as a timestamped pre-commitment. Without commits, the proposed substitute is: record `sha256(DECISIONS.md)` plus a UTC time as ledger event #1, and have the oracle (H) sign it. Alternatively, one local commit for that file only.
- **Q3 — where is TCG v3?** The path, or the Claude Doc link.
- **Q4 — oracle key and H.** The author generates the oracle ed25519 key personally. No agent ever holds the private key. The author reviews and signs `requirements.md` + `phi.json` (L3), and finds the outside human for task 07.
- **Q5 — VM contention.** The naive-loop N=10 series is paused (L4 at 1/10, needs amendment 1 synced). WS-C (KEVM image build on the VM) and the task 07 consumer run use the same 4 vCPUs. The two must not overlap with L4 runs. Which goes first?

## 2. Decisions D1–D11: proposed defaults (to go into `pilot/bundle/DECISIONS.md` once the author signs off)

| # | Proposed | Note |
|---|---|---|
| D1 | sha256, hex, raw bytes | as the task proposes |
| D2 | Merkle DAG, children as files, manifest lists by path + hash | the existing tcg v1 bundle already works this way; reuse the canonical-JSON rule |
| D3 | ed25519 via **pure-Python RFC 8032** in the verifier (~120 lines, stdlib only). Signing via `minisign` or the same code | keeps the verifier stdlib-only and adds no `outside_bundle` entry for a crypto binary. Alternative: `cryptography` |
| D4 | separate oracle key, signs `sha256(phi.json) ∥ sha256(requirements.md)` | as proposed |
| D5 | H = the author | as proposed |
| D6 | variant A = pinned KEVM **docker image by digest** (amd64, built on the VM, lemmas2 def baked in) | the image digest is the `checker[kevm-prove].hash` |
| D7 | `lean` kernel + `#print axioms`, axiom set ⊆ {propext, Classical.choice, Quot.sound} | as proposed |
| D8 | keccak256(runtime) at a pinned block | as proposed |
| D9 | `--rpc` (archive node, `eth_getCode` at block N) **primary**; `--state-snapshot` fetched by the **consumer**, never shipped inside the bundle | a snapshot inside the bundle would make L0 circular (the bundle vouching for itself) |
| D10 | U / T / T* verbatim from v3 §3 | needs Q3 |
| D11 | v3 §10 sentences verbatim | needs Q3; settle five vs six |

## 3. Layout (all under `pilot/`, so it never clashes with the v1 `WORKDIR/bundle` that `tcg freeze` writes)

```
pilot/
  bundle/            # β: manifest.json, DECISIONS.md, hard/, trusted_base.json, evidence/, provenance/, semantics/ (B)
  schema/            # manifest.schema.json, examples/
  tools/             # lint_manifest.py, verify_ledger.py, ledger.py (wrapper), assemble.py, closure/totality scripts
  verifier/          # task 06, stdlib-only Python, < 2000 LOC
  checker/           # WS-C: Dockerfile + build/pin scripts for the KEVM image
  variant_b/         # WS-B: Lean project over vendored EVMYulLean
  handoff/           # task 07 outputs
```

The hard layer is **derived from a tcg v1 frozen bundle**: rerun `build-getters-full.sh` (+ the 2 rebuilt claims) → `tcg freeze`, then `assemble.py` maps v1 → v3. This makes it a serialisation of existing artefacts, as task 02 requires.

## 4. Workstreams and parallelism

Ownership is by directory, so sessions can share this checkout without worktrees (which fits the no-commit rule). No two writers touch the same directory.

| WS | Scope (tasks) | Where | Owns | Depends on | Effort |
|---|---|---|---|---|---|
| **WS-0** | decisions, fixes to the task files, Q1–Q5; orchestration + review | me + author | `pilot/bundle/DECISIONS.md`, `tasks/` | — | evening |
| **WS-A** | 01 schema + linter, `ledger.py`/`verify_ledger.py` (05 tooling, needed **before** assembly so assembly gets recorded), then verifier 06 L0/L1-Lean/L2/L3/L4 + monotonicity suite on a **synthetic toy bundle** | laptop, own session | `schema/ tools/ verifier/` | D1–D4, D9 | 3–4 days |
| **WS-H** | 02 + 03: pinned block, `eth_getCode` for GemJoin/WETH/Vat, rebuild claims via tcg, `phi.json`, `requirements.md` draft, annotation closure, `rediscuss.json`, `trusted_base.json` | laptop (KEVM), own session | `bundle/hard/ bundle/trusted_base.json` | Q1, WS-A ledger tool | 1.5 days |
| **WS-C** | variant A checker: amd64 docker image with `kprove` + kompiled `-lemmas2` def, pinned by digest; smoke = one getter claim Accepts inside the image on the VM | VM, own session | `checker/` | Q5 | 1–2 days (check for an upstream RV `kevm:…1.0.678` image first; otherwise nix-in-docker) |
| **WS-B** | 08 variant B: re-check opcode coverage, vendor EVMYulLean, prove **`ilk()`** (bare `SLOAD`, no mask) in Lean, then `vat()` if time allows. 2-day timebox; if it stalls, the Lean goal state is the result | laptop (Lean 4.22), own session | `variant_b/ bundle/semantics/` | claim statement from WS-H (can start from Finding 0003b's RHS on day 1) | 2 days |
| **WS-E** | 04: coverage/totality, mutants (bytecode mutants + **concrete trace** witness, because the substrate often yields Unknown, not Refute, on a wrong postcondition), pre-witness replay, `phi_versions.json`; back-translation in a **fresh `claude -p` under the isolated `agent` user** with `requirements.md` withheld (transcript → P) | laptop + VM | `bundle/evidence/` | WS-H, WS-C (to replay in the image) | 1 day |
| **WS-P** | 05 content: `iterations.json` (expect `iterations_retained: false` for August), `generators.json`, `decision-stub.md` | laptop | `bundle/provenance/` | WS-H, WS-E | half a day |
| **WS-I** | integration: `assemble.py` → manifest + producer signature → verifier variant A on the real bundle → `ladder_A.json`; then variant B | me + WS-A session | — | everything above + the author's L3 signature | 1 day |
| **WS-X** | 07 hand-off: copy to a clean location on the VM under a separate unix user with no read access to `~/sheaf`; consumer B = a fresh `claude -p` with only bundle + verifier + pubkeys + RPC; then the human consumer; `report.md`, `variants.md` | VM + author | `handoff/` | WS-I, Q4 | evening + human |

**Critical path:** WS-0 → WS-H → WS-E → WS-I → author's signature → WS-X. WS-A, WS-C and WS-B run in parallel from day 1, so the critical path is about 1 week instead of the README's 1.5.

**Launch order once §1 is answered:** three sessions at once: WS-A (laptop), WS-C (VM), WS-B (laptop, Lean). WS-H starts as soon as `ledger.py` from WS-A exists (day 1, a few hours). I review and re-run every verdict myself (judge = solver/kernel).

## 5. Soundness traps to hold the line on (where the green could be empty)

1. **L0 identity must read the chain.** A test monkeypatches the RPC to return different bytecode and asserts L0 fails. Without that test, comparing `identity.value` with itself passes everything.
2. **Vacuity carries over.** Each KEVM claim keeps its v1 vacuity probe. The getter claims carry `#rangeUInt(256, …)` in `requires` (Finding 0003b), so the pre-witness must satisfy it concretely.
3. **Mutant "refutation" ≠ Refute.** The verifier reports `not_accept` vs `refute(ce)` vs `concrete_trace_violation` as distinct values and never collapses them.
4. **Checker hash before run.** Compare the image digest, not the tag. Under variant A, the `outside_bundle` entries name the digest.
5. **Approval binding.** Re-stating φ for variant B creates a new `phi.json` version, so the old signature goes stale and L3 must fail until H re-signs. This is a monotonicity case, tested.
6. **No summary mark.** No function in `verifier/` returns a single pass/fail for the bundle (enforced by grep in the test suite).
7. **The rebuilt revert claims** need the `<log>` cell abstracted only if the path emits a log (Finding 0006 correction). Revert paths emit no log, but check the claim anyway.

## 6. Expected honest outcome (written before running; can be wrong)

Variant A: L0 pass · L1 pass, 0/5 certified, `self_contained: false` · L2 coverage **not** total (join/exit accounting = declared blind spots), mutants replay for the getters, revert-claim mutants are likely concrete-trace only · L3 pass after H signs · L4 partial (no August iteration records). Variant B: `ilk()` closes in Lean or stalls with a recorded goal; `vat()`/`gem()` likely need the Frame library for the mask. `outside_bundle` (A) = image digest + RPC.
