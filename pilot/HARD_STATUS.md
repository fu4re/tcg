# WS-H status: hard layer (b, φ, a, c) + trusted base T̂

> Working log, NOT bundle content. Moved from pilot/bundle/HARD_STATUS.md to pilot/HARD_STATUS.md on 2026-10-29 (assemble.py claims no role for it). Every path below is relative to pilot/bundle unless absolute.

Owner: WS-H. Updated 2026-10-29 ~14:45 UTC (session 2, after the VM reboot). **Tasks 02 + 03: done-when lists met (details below), except the author's review and signature of phi.json + requirements.md, which is not WS-H's to give.** Nothing committed or pushed. Every bundle tool invocation is recorded via `pilot/tools/ledger.py` in `provenance/ledger.jsonl`; `python3 pilot/tools/verify_ledger.py pilot/bundle/provenance/ledger.jsonl` → `67 events; chain intact` (the ledger is shared with WS-E, e.g. seq 66).

## Result in one table

| Claim | Form | Quantifies over (short; full text in phi.json `quantifies_over`) | Reachable? | OSAKA verdict (shipped) | Controls (OSAKA) |
|---|---|---|---|---|---|
| claim-01 | `vat()` | any storage with slot 1 a 256-bit word; any caller/id | yes, deployed storage at the pin | **Accept** 130.1 s, seq 37 | vacuity NotAccept · discriminator **Refute** · wrong-slot NotAccept |
| claim-02 | `ilk()` | same, slot 2 | yes; concrete pre_witness replays | **Accept** 128.7 s, seq 41 | vacuity NotAccept · discriminator **Refute** · wrong-slot NotAccept |
| claim-03 | `gem()` | same, slot 3 | yes, deployed storage at the pin | **Accept** 181.6 s, seq 48 | vacuity NotAccept · discriminator **Refute** · wrong-slot NotAccept |
| claim-04 | `cage()` reverts, `cagews` | any storage with wards[caller] == 0 (keccak-keyed slot, keccak opaque); any non-ward caller | **yes, shown on chain**: deployed storage + caller 0x…dEaD (wards slot = 0 on 3 RPCs) | **Accept** 202.1 s, seq 35 | vacuity NotAccept · discriminator **Refute** |
| claim-05 | `join(usr,wad)` reverts, `joinsym` | any storage with live == 0; every 256-bit usr, wad (68-byte calldata) | by judgement only (post-cage state; live = 1 at the pin) | **Accept** 180.9 s, seq 42 | vacuity NotAccept · discriminator **Refute** |

Shipped fork: **osaka** (`<schedule> OSAKA </schedule>`; rule: all 5 Accept with clean controls; met). The same 5 claims + controls also hold under SHANGHAI (table below). Pre-witness replay (claims 02, 04, 05): exit 0, seq 63.

**Where the proof could still be empty or say less than it seems** (the honest list):
1. **Vacuity probes are weak evidence by themselves.** Every `ensures false` probe ends exit 1 with the *initial* Pre configuration as kore's residual (no `#halt` state is printed). That shows `false` was not derivable. It does not exhibit a halted run. Positive non-vacuity evidence comes from (a) every discriminator being a **Refute** (the prover reached terminal states with the claimed status), and (b) the concrete pre_witness instances for claims 02/04/05 (Accept, with their own vacuity NotAccept).
2. **claim-05's Pre is reachable by judgement, not on chain** (live == 1 at the pin). claim-04's is shown on chain.
3. **claim-04 needs A_keccak for its meaning**: KEVM keccak = Keccak-256 + the solc 0.5.12 mapping layout. The witness evaluates keccak concretely, but the slot is absent from the concrete map, so the witness does not discriminate the hash value. That the chain slot is 0 is checked by `cast storage` at the slot cast computes.
4. **KEVM OSAKA ≠ mainnet osaka.** OSAKA = PRAGUE + CLZ only. MODEXP (7823/7883), P256VERIFY (7951), 7825, 7918, 7934 and the BPO blob params are not modelled. KEVM's own failing.llvm lists 498 Osaka-fork fixtures. GemJoin uses no post-Shanghai opcode and no proved path calls a precompile → `A_osaka_model`, `A_blob_params` (assumptions, not checks).
5. **Gas is not modelled.** Claims hold for executions that do not run out of gas. Out-of-gas is outside every claim. No termination-within-gas guarantee.
6. **z3 4.12.1** (image) produced every verdict, not the CLAUDE.md pin 4.16.0 (T̂ checker.solver, A3).
7. **0/5 certified.** All claims are in `claims_without_certificate` (variant A: kprove emits no proof object).

## Verdicts, full matrix (judge = kprove in image `sha256:7d4a35bc…c465` via `pilot/checker/run-claim.sh`, classified by `tcg/verdict.py`; command per row = `provenance/rebuild/run-controls.sh <tsv> <spec>:<MODULE>:<expected>`)

| Module | Schedule | Expected | Verdict | Exit | Wall s | Ledger seq | Spec |
|---|---|---|---|---|---|---|---|
| CAGE-CAGE-PROVE | OSAKA | Accept | **Accept** | 0 | 153.3 | 49 | `provenance/rebuild/controls-osaka/cage-cage-prove.k` |
| CAGE-CAGE-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 73.8 | 51 | `provenance/rebuild/controls-osaka/cage-cage-vacuity.k` |
| JOINEMPTY-JOINEMPTY-PROVE | OSAKA | Accept | **Accept** | 0 | 168.6 | 53 | `provenance/rebuild/controls-osaka/joinempty-joinempty-prove.k` |
| JOINEMPTY-JOINEMPTY-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 76.9 | 54 | `provenance/rebuild/controls-osaka/joinempty-joinempty-vacuity.k` |
| VAT-VAT-PROVE | OSAKA | Accept | **Accept** | 0 | 130.1 | 37 | `provenance/rebuild/controls-osaka/vat-vat-prove.k` |
| VAT-VAT-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 64.0 | 38 | `provenance/rebuild/controls-osaka/vat-vat-vacuity.k` |
| VAT-VAT-DISCRIMINATOR | OSAKA | NotAccept | **Refute** | 1 | 144.0 | 40 | `provenance/rebuild/controls-osaka/vat-vat-discriminator.k` |
| ILK-ILK-PROVE | OSAKA | Accept | **Accept** | 0 | 128.7 | 41 | `provenance/rebuild/controls-osaka/ilk-ilk-prove.k` |
| ILK-ILK-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 75.9 | 43 | `provenance/rebuild/controls-osaka/ilk-ilk-vacuity.k` |
| ILK-ILK-DISCRIMINATOR | OSAKA | NotAccept | **Refute** | 1 | 158.5 | 45 | `provenance/rebuild/controls-osaka/ilk-ilk-discriminator.k` |
| GEM-GEM-PROVE | OSAKA | Accept | **Accept** | 0 | 181.6 | 48 | `provenance/rebuild/controls-osaka/gem-gem-prove.k` |
| GEM-GEM-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 74.5 | 50 | `provenance/rebuild/controls-osaka/gem-gem-vacuity.k` |
| GEM-GEM-DISCRIMINATOR | OSAKA | NotAccept | **Refute** | 1 | 195.0 | 52 | `provenance/rebuild/controls-osaka/gem-gem-discriminator.k` |
| WRONG-SLOT-VAT-SPEC | OSAKA | NotAccept | **Unknown** (c) | 1 | 167.4 | 55 | `provenance/rebuild/controls-osaka/wrong-slot.k` |
| WRONG-SLOT-ILK-SPEC | OSAKA | NotAccept | **Unknown** (c) | 1 | 122.2 | 56 | `provenance/rebuild/controls-osaka/wrong-slot.k` |
| WRONG-SLOT-GEM-SPEC | OSAKA | NotAccept | **Unknown** (c) | 1 | 190.2 | 58 | `provenance/rebuild/controls-osaka/wrong-slot.k` |
| CAGEWS-CAGEWS-PROVE | OSAKA | Accept | **Accept** | 0 | 202.1 | 35 | `provenance/rebuild/controls-osaka/cagews-cagews-prove.k` |
| CAGEWS-CAGEWS-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 62.1 | 36 | `provenance/rebuild/controls-osaka/cagews-cagews-vacuity.k` |
| CAGEWS-CAGEWS-DISCRIMINATOR | OSAKA | NotAccept | **Refute** | 1 | 220.4 | 39 | `provenance/rebuild/controls-osaka/cagews-cagews-discriminator.k` |
| JOINSYM-JOINSYM-PROVE | OSAKA | Accept | **Accept** | 0 | 180.9 | 42 | `provenance/rebuild/controls-osaka/joinsym-joinsym-prove.k` |
| JOINSYM-JOINSYM-VACUITY | OSAKA | NotAccept | **Unknown** (c) | 1 | 71.6 | 44 | `provenance/rebuild/controls-osaka/joinsym-joinsym-vacuity.k` |
| JOINSYM-JOINSYM-DISCRIMINATOR | OSAKA | NotAccept | **Refute** | 1 | 202.6 | 47 | `provenance/rebuild/controls-osaka/joinsym-joinsym-discriminator.k` |
| CAGEWS-CAGEWS-PROVE | SHANGHAI | Accept | **Accept** | 0 | 235.4 | 17 | `provenance/rebuild/controls/cagews-cagews-prove.k` |
| JOINSYM-JOINSYM-PROVE | SHANGHAI | Accept | **Accept** | 0 | 163.7 | 19 | `provenance/rebuild/controls/joinsym-joinsym-prove.k` |
| CAGEWS-CAGEWS-VACUITY | SHANGHAI | NotAccept | **Unknown** (c) | 1 | 67.8 | 20 | `provenance/rebuild/controls/cagews-cagews-vacuity.k` |
| JOINSYM-JOINSYM-VACUITY | SHANGHAI | NotAccept | **Unknown** (c) | 1 | 72.7 | 22 | `provenance/rebuild/controls/joinsym-joinsym-vacuity.k` |
| CAGEWS-CAGEWS-DISCRIMINATOR | SHANGHAI | NotAccept | **Refute** | 1 | 237.8 | 30 | `provenance/rebuild/controls/cagews-cagews-discriminator.k` |
| JOINSYM-JOINSYM-DISCRIMINATOR | SHANGHAI | NotAccept | **Refute** | 1 | 164.1 | 33 | `provenance/rebuild/controls/joinsym-joinsym-discriminator.k` |
| VAT-VAT-PROVE | SHANGHAI | Accept | **Accept** | 0 | 145.3 | 12 | `provenance/rebuild/controls/vat-vat-prove.k` |
| VAT-VAT-VACUITY | SHANGHAI | NotAccept | **Unknown** (c) | 1 | 68.8 | 16 | `provenance/rebuild/controls/vat-vat-vacuity.k` |
| VAT-VAT-DISCRIMINATOR | SHANGHAI | NotAccept | **Refute** | 1 | 150.0 | 18 | `provenance/rebuild/controls/vat-vat-discriminator.k` |
| ILK-ILK-PROVE | SHANGHAI | Accept | **Accept** | 0 | 119.5 | 21 | `provenance/rebuild/controls/ilk-ilk-prove.k` |
| ILK-ILK-VACUITY | SHANGHAI | NotAccept | **Unknown** (c) | 1 | 73.5 | 25 | `provenance/rebuild/controls/ilk-ilk-vacuity.k` |
| ILK-ILK-DISCRIMINATOR | SHANGHAI | NotAccept | **Refute** | 1 | 123.4 | 26 | `provenance/rebuild/controls/ilk-ilk-discriminator.k` |
| GEM-GEM-PROVE | SHANGHAI | Accept | **Accept** | 0 | 171.9 | 31 | `provenance/rebuild/controls/gem-gem-prove.k` |
| GEM-GEM-VACUITY | SHANGHAI | NotAccept | **Unknown** (c) | 1 | 66.4 | 32 | `provenance/rebuild/controls/gem-gem-vacuity.k` |
| GEM-GEM-DISCRIMINATOR | SHANGHAI | NotAccept | **Refute** | 1 | 149.7 | 34 | `provenance/rebuild/controls/gem-gem-discriminator.k` |

Unknown (c) on a vacuity / wrong-slot control = kprove exit 1, `false`/the wrong return value not derivable; it counts as NotAccept, never as a pass of the claim itself. CAGE-CAGE-* and JOINEMPTY-* are the Finding-0003 EMPTY-storage forms, recorded as controls only (unreachable Pre). TSVs + logs: `provenance/rebuild/results/matrix-{osaka,shanghai}/`.


## Task 02 done-when

| Item | State | Command / evidence |
|---|---|---|
| keccak(artifact.bin) = development constant | ✅ `0x8661c673…74fa`, 3462 B, identical to `tests/reference/getters/subject/runtime.hex` | `assemble_hard.py chain` (seq 2) |
| phi.json references every claim file by hash; every claim ≥1 requirement | ✅ 5 claims, sha256 per file, R1–R5; R4–R9 partial/uncovered in `declared_blind_spots`; `quantifies_over` per claim; `declared_limits` | `assemble_hard.py hardspec --bundle . --controls provenance/rebuild/controls-osaka --results provenance/rebuild/results/matrix-osaka/{getters,revert}.tsv --schedule OSAKA --claim04 cagews --claim05 joinsym` (seq 59; refuses unless each claim has an Accept ledger event on exactly that file + clean controls) |
| requirements.md (n) | DRAFT R1–R9, **not signed** (author reviews; oracle signs per D4) | `hard/spec/requirements.md` |
| annotation closure passes | ✅ `closure: OK (13 annotations, 5 claims, 0 problems)` | `python3 ../tools/assemble_hard.py closure --bundle . --k-src ~/pilot-hard/kevm-src/evm-semantics-source` (seq 61) |
| closure is not vacuous | ✅ dropping any of Aasm-keccak-wards-slot / Aasm-rangeUInt-args / Aasm-rangeUInt-storage / Aasm-gas-abstraction → FAILED; unmodified → OK. (The first run found a hole: a keccak conjunct declared as Pre scope passed without an annotation. Closure now requires an annotation for any `keccak(` conjunct.) | `bash provenance/rebuild/controls-closure/closure_neg.sh` (seq 62) |
| every KEVM claim certified or listed | ✅ 5/5 in `claims_without_certificate`; `hard/certs/claim-0N.rediscuss.json` validate against `pilot/schema/rediscuss.schema.json` (argv, image_id, claim_file_sha256, ledger_seq) | hardspec (seq 59) |

## Task 03 done-when

| Item | State | Command / evidence |
|---|---|---|
| every hash recomputable by a script | ✅ `rehash: OK (58 recomputed, 0 failures)`: identity + block hash + WETH9/Vat code vs 3 archive RPCs at block 26298481, image Id, in-image tarballs/patches/definition.kore/MANIFEST, verifier hash, every phi/cert/witness/hashed-object file | `python3 ../tools/assemble_hard.py rehash --bundle . --rpc https://eth.drpc.org --rpc https://mainnet.gateway.tenderly.co --rpc https://eth-mainnet.public.blastapi.io` (seq 67, under a slot) |
| rehash is not vacuous | ✅ tampered copy (WETH code_hash zeroed + claim-04.k edited) → `FAILED (3 failures)`, exit 1 | same command on a temp copy (not ledgered) |
| every Aasm fact in annotations.json appears with risk_if_false | ✅ 13/13 annotation ids map to an assumption (id or `covers`) with risk_if_false; 16 assumptions, all with risk_if_false; trusted_base.json validates against `pilot/schema/trusted_base.schema.json` | script check (see transcript), WS-A's `jsonschema_min.validate` |
| pre_witness replays (one command) | ✅ `cd provenance/rebuild/pre_witness && sh replay.sh` → 6 lines, exit 0; stdout sha256 `d7ad4c93…73ba` in `expected.json` | seq 63 (10 min, 6 containers, each under a slot) |
| external_code hashes match chain at the pin | ✅ WETH9 `0xd0a06b12…5e23`, MCD_Vat `0x808b98f6…1a59`, 3 RPCs | rehash (seq 67) |

T̂ highlights: `environment.fork: osaka`; `semantics[0].adequacy_evidence` = KEVM OSAKA model vs mainnet osaka EIP list + KEVM failing.llvm counts (`provenance/kevm_osaka_adequacy.json`, seq 15); `adequacy_evidence_for_this_artifact` = opcode sweep (`provenance/opscan.json`, seq 13: 1582 instructions, 0 post-Shanghai opcodes, 4 CALLs, no SELFDESTRUCT/BLOCKHASH); `resource_limits` = gas-bounded wording; assumptions `A_osaka_model`, `A_blob_params`, `A_keccak` (relied on by claim-04), `Aasm-03` (no out-of-gas), `Aasm-05` (ABI words), A3 notes z3 4.12.1 vs pin 4.16.0; A6 states the reachability of each claim.

## Reproduce (from `pilot/bundle`, on the VM)

```
P=~/pilot-locks/with-slot.sh   # every prover container takes one of 3 VM slots
provenance/rebuild/run-controls.sh <results.tsv> provenance/rebuild/controls-osaka/<n>-<n>-prove.k:<N>-<N>-PROVE:Accept ...
python3 ../tools/assemble_hard.py hardspec ... ; ... closure ... ; ... tbase --bundle . --schedule OSAKA --witness-dir provenance/rebuild/pre_witness ; ... rehash --rpc ...
(cd provenance/rebuild/pre_witness && sh replay.sh)
```
(`run-controls.sh` wraps each ledger call in the slot lock; `run-claim.sh` adds `--memory=6g --cpus=2`.)

## Files WS-H owns / produced

`hard/{artifact.bin, annotations.json, spec/claim-0{1..5}.k, spec/phi.json, spec/requirements.md, certs/claim-0{1..5}.rediscuss.json}`, `trusted_base.json`, `provenance/{chain_fetch.json, rpc_probe.json, opscan.json, kevm_osaka_adequacy.json, closure.out, rehash.out, decision-stub.md}`, `provenance/rebuild/{src,iface,controls,controls-osaka,controls-closure,edits,pre_witness,results/matrix-*}`, `pilot/tools/assemble_hard.py` (subcommands chain, probe, spec, variant, opscan, osaka-evidence, hardspec, tbase, rehash, witness, closure).

## Open / for others

- **Author:** review + rewrite `hard/spec/requirements.md`, review `phi.json`, then the oracle signs (D4). Any edit changes the hashes, so hardspec + tbase + rehash must be re-run after it (phi.json embeds requirements_sha256; trusted_base.json hashes phi.json).
- **WS-E:** `provenance/rebuild/pre_witness/` is laid out as `evidence/pre_witness/` (replay.sh + expected.json); move it verbatim and re-run tbase (its `pre_witness.files` paths change).
- **WS-A / WS-I:** `checker[tcg-verifier].hash` is the verifier hash at tbase time (seq 65); re-run tbase + rehash when the verifier freezes.
- Pre-crash dirs `provenance/rebuild/results/{round1,shanghai,osaka}/` and `~/pilot-hard/round1` are history only; nothing shipped reads them.

## Final state before assembly (WS-H frozen, 2026-10-29 ~17:40 UTC)

- Dry-run fixes: `evidence/pre_witness/replay.sh` has no host paths (seq 121-122); re-replayed under env -i + scratch HOME, same stdout `d7ad4c93…` (seq 132). Imports declared: seq 124-130 re-run variant ×4 / opscan / witness 02, 05 with `../../tcg/{__init__,keccak,claims}.py` inputs, all 19 outputs identical, hermetic producer replay of each OK. `provenance/tools/versions/` keeps every bundled script version so earlier stand-ins stay resolvable.
- T̂: `checker[kevm-prove].recipe_files` = the 8 files of WS-C's `checker/` (hashes checked against WS-C's list); `environment.archive_rpc_status` from `provenance/rpc_status.json` (live probe seq 145: drpc / tenderly / blastapi serve the pin; 1rpc pruned; publicnode errors; earlier blastapi 429 at seq 136-137); `checker[tcg-verifier].hash` = **f7bde819d11db29babaf52cdf9fe4c3560651ff38ebfc9839ca679ed3321f364** (frozen verifier, `verify.py --self-hash` = `verifier_hash()`), tbase seq 149.
- `rehash: OK (63 recomputed, 0 failures)` (seq 150, drpc + tenderly). `assemble.py bundle --check: OK, 381 children`. Ledger `151 events; chain intact`. trusted_base.json sha256 9ef970e1…; phi.json adf5371e… and requirements.md 94c93ab3… unchanged (= the signed hashes).
- From here WS-H writes nothing under pilot/bundle/ until the final ladder_A is out.

## Task 04 (minus mutants) + task 05 content (WS-H, 2026-10-29 ~15:00 UTC)

| Item | State | Evidence |
|---|---|---|
| `evidence/coverage.json` | written by WS-A's `pilot/tools/coverage.py` (seq 68). Both maps; 6 declared blind spots (R4-R9); unreferenced_clauses `[]`; **total = false**, solely because R4/R5 are claimed AND listed as `partial` blind spots (`blind_spots_actually_covered: [R4, R5]`). The verifier has no partial-coverage notion; phi.json left unchanged (decision-stub N6) | `python3 ../tools/coverage.py . --out evidence/coverage.json` |
| `evidence/pre_witness/` | byte-identical copy of `provenance/rebuild/pre_witness/` (seq 69; original kept so seq 27-29/63 stay replayable); tbase + rehash re-run on it (seq 79-80, `rehash: OK (58 recomputed, 0 failures)`) | `cd evidence/pre_witness && sh replay.sh` |
| `evidence/phi_versions.json` | 1 phi.json version so far (`adf5371e…`, seq 59, not yet seen by H) + pre-history by claim-file hash: claim-04 EMPTY→reachable, claim-05 concrete→symbolic args, all five SHANGHAI→OSAKA, each with the ledger seq that proved it (seq 72) | `provenance/rebuild/edits/make_phi_versions.py` |
| blind back-translation | one `claude -p` call (claude-opus-5-5, Claude Code 2.1.312) as unix user `agent` (cannot read /home/vladimir: checked), cwd holding ONLY claim-01..05.k + a stripped phi.json (30 requirement-describing / judgement fields removed; 0 six-word shingles of requirements.md left); `--tools ""`, no MCP, no session persistence; whole input = recorded stdin. Ledger note seq 74. Transcript + listings: `provenance/sessions/bt-20261029T144536Z.*` | `provenance/rebuild/edits/bt_run.sh` |
| `evidence/backtranslation.json` | script pairing (seq 76): 5 translations beside R1-R5 text, every `agreement: "unclear"` (H judges). 0 sentences quarantined; the quarantine filter was checked on a planted "matches the informal specification" sentence (fires, sentence kept out of V). Caveats: the translator saw phi.json's English pre/post (may echo it); same model family as the producer; one sample | `provenance/rebuild/edits/bt_pair.py bt-20261029T144536Z` |
| `provenance/iterations.json` | August: `iterations_retained: false` + reason; today: retained, 40 kprove runs each matched to its TSV verdict by log hash, per-claim lineage, 2 infra_fail runs listed; no Refute/Unknown ever preceded an Accept in a shipped lineage (seq 77) | `provenance/rebuild/edits/make_iterations.py` |
| `provenance/generators.json`, `traces.json` | 4 generator entries (back-translator, WS-H sessions 1 and 2, August agents), all `attestation: "none available"`; traces "not recorded" (seq 78) | `provenance/rebuild/edits/make_generators.py` |
| `provenance/decision-stub.md` | D1-D11 + P1-P5 by reference; N1-N6 new-content records | — |
| ledger | `80 events; chain intact` | `python3 ../tools/verify_ledger.py provenance/ledger.jsonl` |

**L4 caveat (bundle-level, for WS-A / WS-I):** deterministic events 14-15, 59, 65, 70, 79 read inputs outside the bundle root (`~/pilot-checker/pins.json`, the KEVM tarball copied out of the image); 4-5 wrote logs outside it; most WS-H tool events run `../tools/assemble_hard.py` (in `pilot/tools`, not in the bundle) and closure names the extracted K source by absolute path. A consumer holding only the bundle cannot replay those events. Either ship the tools (and pins) inside the bundle, or have L4 report them as `outside_bundle`.

## Approval by H (2026-10-29, signature mtime 14:55:31 UTC)

- `evidence/approval.sig` (64 B, sha256 c2ddee23...bdd8) over `phi_sha256 adf5371e...90e9 || requirements_sha256 94c93ab3...4e14`; both equal the current hard/spec files. Producer cross-check: `openssl pkeyutl -verify` and `tcgverify.ed25519` both valid; a 1-char tampered message fails. The binding check belongs to L3.
- `evidence/approval.json` derived from approval.msg ONLY (seq 98, `provenance/rebuild/edits/make_approval.py`); signed_at_utc = mtime of approval.sig (not a signed timestamp).
- `oracle.pub.pem` and `approval.msg` MOVED out of the bundle to `~/pilot-keys/` (mode 700): the trust anchor ships out of band, and the verifier rebuilds the message from approval.json.
- Ledger note seq 99; `evidence/phi_versions.json` marks adf5371e as approved_by_H (seq 100). make_phi_versions.py was extended for this, so seq 72's version of it is superseded by seq 100.
- tbase/rehash not re-run: neither covers evidence/approval* or phi_versions.json (tbase hashes only evidence/pre_witness, which is unchanged).
- **phi.json and requirements.md must not change from here on**: any edit makes the signature stale and L3 fails.

## L4: producer tools bundled (orchestrator decision, 2026-10-29 ~15:20 UTC)

- `provenance/tools/` = copies of every script a deterministic ledger event executes, plus their in-repo imports: assemble_hard.py, coverage.py, mutant_witness.py, run-claim.sh, run-controls.sh, tcg/{keccak,claims,verdict}.py. Scripts that already live in the bundle (provenance/rebuild/edits/*, closure_neg.sh, pre_witness/replay.sh) are mapped in place. Per-event table in `provenance/tools/MAP.json` (seq 95), with status `same_bytes` / `hash_not_recorded` / `version_not_retained`. Ledger note seq 97 maps old paths to the bundled copies by hash. Seq 96 is the same note with its text lost to a shell quoting error, corrected by 97. No past event was rewritten.
- `assemble_hard.py` was extended during assembly, so 17 earlier events ran versions that were not retained. **Every one of those deterministic steps was re-run with the current, bundled version (seq 82-92, `provenance/rebuild/edits/rerun_current.sh`): all 35 outputs byte-identical.** Every shipped output therefore has at least one `same_bytes` event.
- `run-claim.sh`: its 40 kevm-prove events recorded the image Id, not the script hash (`hash_not_recorded`). The bundled copy is the current script; identity with the version that ran (WS-C added `--memory/--cpus` around the reboot) is not proven.
- Not bundled: `pilot/verifier/tcgverify` (the tcg-verifier checker, WS-A), KEVM pins / tarball / extracted K source (outside_bundle by decision).
- tbase + rehash re-run afterwards (seq 93-94): `rehash: OK (58 recomputed, 0 failures)`. Ledger `97 events; chain intact`.

## Session 1 record (predecessor, kept)

### Done in session 1

| Item | State | Evidence |
|---|---|---|
| Ledger event #1 | sha256 `87eb69dd…e54a` of `DECISIONS.md` + UTC time `2026-10-29T12:57:39.020Z` | ledger seq 1 |
| **b** pinned block | **26298481** (finalized at fetch time), hash `0x21bc8ec3e7a3d67c7f387dcb076dd22f91545d9299c265e183cbc7dc13c684e0`, chain id 1 | `provenance/chain_fetch.json`, ledger seq 2 |
| **b** RPC agreement | 5 RPCs agree on chain id, block hash and all three code blobs: publicnode, drpc, 1rpc, tenderly, blastapi. flashbots (504) and llamarpc (525) failed, recorded | `chain_fetch.json` |
| **b** archive-capable RPCs | drpc, 1rpc, tenderly and blastapi serve `eth_getCode` at block 25782890 (Finding 0003's fetch block). publicnode refuses archive requests ("require a personal token") | `provenance/rpc_probe.json`, ledger seq 3 |
| **b** identity | GemJoin `0x2F0b23f53734252Bda2277357e97e1517d6B042A`: 3462 bytes, keccak (`cast keccak` = pure-Python `tcg/keccak.py`) `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa` = dev constant, bytes **identical** to `tests/reference/getters/subject/runtime.hex`. Written to `hard/artifact.bin` (sha256 `c5f9e8e8…bd27`) | `chain_fetch.json` |
| external code | WETH9 `0xC02a…6Cc2`: 3124 B, keccak `0xd0a06b12ac47863b5c7be4185c2deaad1c61557033f56c7d4ea74429cbb25e23`. MCD Vat `0x35D1…492B`: 13493 B, keccak `0x808b98f6475736d56c978e4fb476175ecd9d7abdab0797017fc10c7f46311a59` | `chain_fetch.json` |
| GemJoin storage at pin | slot0 0, vat=Vat, ilk="ETH-A", gem=WETH, dec=18, live=1. 4 RPCs agree | `rpc_probe.json` |
| Fork at pin | `eth_config` (3 RPCs): current activationTime 1767747671 (BPO2 blob schedule 14/21), forkId `0x07c9462e`, i.e. execution rules **osaka** | `chain_fetch.json` `.eth_config` |

### Recovery after the VM reboot (session 2, 2026-10-29 ~13:30 UTC)

- Ledger chain checked first: `python3 pilot/tools/verify_ledger.py pilot/bundle/provenance/ledger.jsonl` -> `6 events; chain intact`.
- **infra_fail, not counted:** two kprove runs were in flight at the crash and have no ledger event and empty logs: `ILK-ILK-PROVE` (controls-osaka, OSAKA) and `CAGE-CAGE-VACUITY` (controls, SHANGHAI). Recorded as ledger note seq 7. Both are re-run inside the new matrix below. The pre-crash partial result dirs `provenance/rebuild/results/{round1,shanghai,osaka}/` are kept as history only; nothing in phi.json / trusted_base.json reads them.
- Ledger events 4 and 5 (round 1) wrote their outputs outside the bundle root (`../../../../pilot-hard/round1/...`), so they are not replayable from the bundle; superseded by the matrix.
- Probable cause of the hang: the predecessor ran two unbounded run queues (`~/pilot-hard/queue{A,B}.txt`) at once. From now on every prover container goes through `~/pilot-locks/with-slot.sh prover --` (wrapped around the ledger call in `provenance/rebuild/run-controls.sh`) and `pilot/checker/run-claim.sh` adds `--memory=6g --cpus=2`. WS-H holds at most 2 of the 3 VM slots at a time (lanes chained with `pgrep` waits, `~/pilot-hard/lanes/lane{1..6}.sh`).
- New results live in `provenance/rebuild/results/matrix-{shanghai,osaka}/*.tsv` (+ `logs/`).

