# LEDGER READY

`pilot/tools/ledger.py` + `pilot/tools/verify_ledger.py` work (stdlib only, python 3.12). Usage:

```
# wrap a deterministic tool call: inputs hashed before, outputs after; exit code propagates
python3 pilot/tools/ledger.py run --ledger pilot/bundle/provenance/ledger.jsonl --root pilot/bundle \
    --in hard/spec/claim-01.k --out out/claim-01.result --stdout out/claim-01.log -- kprove ...

# docker / non-file tool: give the tool hash explicitly (image digest)
python3 pilot/tools/ledger.py run --ledger L --tool kevm-prove --tool-hash sha256:<digest> -- docker run ...

# non-replayable step (prover with timeouts, network)
python3 pilot/tools/ledger.py run --ledger L --nondeterministic -- ...

# generator / model call (never replayed; deterministic:false)
python3 pilot/tools/ledger.py note --ledger L --tool claude --model claude-opus-5-5 \
    --prompt prompt.txt --completion completion.txt --text "blind back-translation, requirements.md withheld"

# bookkeeping note (e.g. DECISIONS.md hash as event #1)
python3 pilot/tools/ledger.py note --ledger L --tool manual --in pilot/bundle/DECISIONS.md --text "D1-D11 draft"

python3 pilot/tools/ledger.py tip --ledger L          # "<seq> <sha256 of last line>"
python3 pilot/tools/verify_ledger.py L                # exit 0 intact, 1 broken (every break printed)
```

Event format `tcg-ledger/0.1` (one canonical-JSON line per event: sorted keys, no whitespace, UTF-8):
`format, kind (run|note), seq (1-based), prev (sha256 of the previous line's bytes without "\n"; "0"*64 for seq 1),
tool, tool_hash, argv, cwd, stdout, stderr, inputs [{path, sha256}], outputs [{path, sha256|null}], exit, started, ended (UTC "Z"),
deterministic`; notes add `model, prompt_sha256, completion_sha256, text`.
Paths are relative to `--root` (default `.`). Pass `--root pilot/bundle` so the ledger replays from the bundle root.
Appends take an exclusive `flock`, so several sessions can share one ledger. A missing `--in` file aborts (exit 2, nothing appended); a missing output is recorded with `sha256: null`.

`stdout`/`stderr` (the paths the `--stdout`/`--stderr` streams were captured to) were added after the first
events of `pilot/bundle/provenance/ledger.jsonl` were written. Events 1–3 there lack them, which is fine: they
are non-deterministic, so they are never replayed. **L4 can only replay an event whose inputs, outputs, stdout
and cwd all lie inside the bundle root.** Event 4 records an output at `../../../../pilot-hard/round1/logs/…`, so L4
will report it as "not replayed: an output path lies outside the bundle" (status `partial` at best).

---

# WS-A status (schema / tools / verifier)

Updated: 2026-10-29 (on the VM `tcg:~/sheaf/tcg/pilot/`; nothing written on the laptop after the move).
Nothing is committed or pushed.

## Done
- [x] **Ledger tooling** (task 05 §1): `tools/ledger.py`, `tools/verify_ledger.py` (the chain walk lives in `verifier/tcgverify/ledger_walk.py` and is shared with L4).
- [x] **Task 01:** `schema/manifest.schema.json` (JSON Schema 2020-12), `schema/examples/manifest.example.json` (real ed25519 signature from a throwaway key), `tools/lint_manifest.py`.
  Done-when, by test (`tests/test_manifest.py`): the example validates (`test_example_validates`); a `verdict` key is rejected (`test_rejects_verdict_key`, with root_hash recomputed so only rule 4 can fail it); a root_hash computed over a different child list is rejected (`test_rejects_root_hash_over_different_child_list`). Also tested: forbidden keys at any depth, the word "proved" in values, `not_claimed` altered or short, `self_contained:false` without a reason, class/role mismatches, missing mandatory roles, path escapes, duplicate paths, child bytes changed, unlisted files, rule 2 (claim with neither a certificate nor a `claims_without_certificate` entry).
  Also: `schema/trusted_base.schema.json`, `schema/rediscuss.schema.json`, `schema/README.md` (every format the verifier reads), `tools/tree_hash.py`.
- [x] **Task 06 verifier:** `verifier/verify.py` + `verifier/tcgverify/`. Stdlib only, CLI and `ladder.json` as in 06. **1888 lines of Python** (`wc -l verify.py tcgverify/*.py`, including docstrings and the 90-line vendored keccak) + 182 lines of vendored JSON schemas. Budget 2000.
  - keccak: vendored `tcg/keccak.py` + its vector tests (`tests/test_keccak.py`).
  - ed25519: RFC 8032 verify (`tcgverify/ed25519.py`), tested against the RFC 8032 vectors and against `openssl pkeyutl -sign -rawin` signatures (OpenSSL 3.0.13 on the VM; `-rawin` works).
  - L0 reads the chain itself (`--rpc` via urllib: eth_getCode / eth_chainId / eth_getBlockByNumber; or the consumer's `--state-snapshot`). Tests: `test_chain_read_happens` (a local JSON-RPC server logs the eth_getCode call for the subject address at the pinned block) and `test_artifact_substitution_on_chain_fails_L0` (the chain serves WETH's code at the subject address; the bundle is untouched; L0 fails, L1 still passes).
  - L1: `refused`, with no claim results, on an empty or unclosed assumption ledger. KEVM variant A: `docker image inspect` digest vs T̂ **before** any run (a mismatch → `checker_hash_mismatch`, and a test asserts `docker run` was never called). The docker/kprove argv is built by the verifier (the same shape as `pilot/checker/run-claim.sh`); the judge is ported from `tcg/verdict.py`. Lean: rebuild from source in a scratch copy (shipped `.olean` deleted), `#print axioms`, whitelist ⊆ {propext, Classical.choice, Quot.sound} (T̂ can only narrow it), `sorry`/`admit` in source rejected. Result values kept distinct: accept / refute / unknown / not_accept / checker_hash_mismatch / checker_unavailable / malformed / not_checked.
  - L2 (reported, not judged), L3 (oracle vs producer key, approved vs proven hash, both shown), L4 (chain walk, replay by tool hash, output-consistency check).
  - No summary mark: `NoSummaryMark` greps the verifier source for collapse patterns and pins the ladder's top-level keys.
- [x] **Monotonicity suite** (`tests/test_monotonicity.py`), on the synthetic toy bundle (`tests/fixtures/toy_bundle.py`, fake docker = stub KEVM checker `fixtures/fakebin/docker`, fake Lean toolchain `fixtures/fakelean/`, throwaway openssl keys generated at test time, ledger written by the real `ledger.py`). Baseline: L0 pass, L1 pass, L2 coverage total + mutant refute + pre-witness replays, L3 pass, L4 pass. All five mutations from 06, each **naive** (manifest untouched) and **re-signed by an adversarial producer**:
  1. garbage child: every child naive (L0 drops). Re-signed: 14 children each lower the level that owns them. Garbage in the stored `evidence/coverage.json` lowers nothing but raises nothing either: coverage is recomputed, and the mismatch is flagged in `stored_coverage_matches`. Dropping a child (re-signed) also lowers;
  2. approval forged with the producer key → L3 ("approval signed by producer");
  3. fabricated ledger event → L0 (naive) / L4 replay mismatch (re-signed); an unchained line → L4;
  4. phi.json edited after approval → L0 / L3 (both hashes shown);
  5. artifact.bin swapped for (toy) WETH bytecode → L0 identity, including the case where the producer also rewrites `identity.value`: the chain read still catches it.
  In every case at least one level is lowered and none is raised.

- [x] **WS-H request (rediscuss fields):** `rediscuss.schema.json` gained OPTIONAL `argv`, `image_id`, `k_commit`, `evm_semantics_commit`, `claim_file_sha256`, `ledger_seq`. `argv` is informational and never executed. `image_id` must be one of T̂'s `kevm-prove` hashes, and `claim_file_sha256` must equal the manifest hash of `claim_file`; either mismatch makes that claim `malformed` (test `test_rediscuss_record_fields_checked_for_consistency`). The requested `observed` object (verdict, exit, …) was **not** added: the bundle carries no verdict (v3 §4). The producer's result belongs in the ledger event that `ledger_seq` points to.

- [x] **Round 2 (2026-10-29), all on the VM:**
  - `tools/assemble.py <bundle> --check | --key <producer.pem>`: path rules → role/class/media (D10), claim ids from `phi.json`, from each `rediscuss.json`, and from a `hard/certs/**/theorems.json` sidecar for Lean; `not_claimed` (D11); `self_contained` + reason computed from which claims lack a proof object; `root_hash` (D2); signed with `openssl pkeyutl -sign -rawin` (D3). It refuses (exit 1, `manifest.json` untouched) on: a file matched by no rule, a symlink, a missing D1–D11 row, a missing required role, a stale `phi.json`/`rediscuss`/`theorems.json` reference, a broken ledger, or a lint failure (schema, rule 4, rule 2). Unclosed annotations only produce a warning (L1 then refuses). It writes atomically. The toy bundle is now built with it, so the whole suite exercises it. **On the real `pilot/bundle/` today, `--check` refuses** with: `HARD_STATUS.md` not claimed by a role, no `trusted_base.json`, no `hard/spec/phi.json`. That is expected while WS-H is unfinished; `HARD_STATUS.md` has to move out of the bundle dir.
  - `tools/coverage.py <bundle> [--out]`: totality in both directions, declared blind spots (plus ones that are unknown or actually covered), unreferenced clauses, unknown requirement refs, stale claim-file hashes. Exit 0 with gaps, 1 only on malformed input. It uses the same function as the verifier's L2 (`tcgverify/evidence.py`).
  - `tools/mutant_witness.py record | check`: the `evidence/mutants/<name>/{mutant.bin | harness/, replay.sh, refutation.json}` convention. Each kind has its own rule (refute / concrete_trace_violation / not_accept), shared with L2; replays must be byte-stable over two runs; a `mutant.bin` identical to the artefact is refused, and the verifier reports it as `malformed`.
  - `verifier/README.md` for consumer B: prerequisites, a self-hash recipe using only sh + sha256sum (a test extracts it from the README and compares it to `--self-hash`), how to run, how to read each level.
  - Verifier changes: rule 2 counts only children with a `theorem` as proof objects, and Lean support files (role c) may carry no claim id (schema updated). `--docker-limit=--memory=6g --docker-limit=--cpus=2` (only these forms accepted), recorded in the ladder.
  - Throwaway keys only (generated per test run). No real producer or oracle key was created.

- [x] **Round 3 (2026-10-29), from WS-H's real-bundle data:**
  - **Partial coverage is first-class** (`tcgverify/evidence.py`, shared by `tools/coverage.py` and L2). Each requirement is `covered` / `partial` / `blind` (`requirement_state` plus three lists). A claimed requirement with *any* blind-spot entry is `partial`, never `covered`. An entry without `"partial": true` on a claimed requirement is also listed in `blind_spots_actually_covered`. `total` is true only if everything is covered. `declared_blind_spots` is now `{R: {reason, partial}}`. The verifier's stored-copy check also compares `requirement_state`, so WS-H's current `evidence/coverage.json` (old shape) will show `stored_coverage_matches: false` until `coverage.py` is re-run. Real bundle (read-only run to a temp file): covered R1–R3, partial R4–R5, blind R6–R9, total false.
  - **L4 outside-bundle bucket:** any input, output, stdout/stderr, cwd or path-like argv element that is absolute or escapes the root makes the event `not_replayable: input|output outside bundle`. It is listed with its paths, counted in `counts.not_replayable_outside_bundle`, and named in `outside_bundle`; it is never replayed, never a mismatch, never a pass (L4 `partial`). This holds under `--no-exec` too. The output-consistency check still applies, so an outside input cannot mask a recorded output that disagrees with the bundle (monotonicity test). **Real bundle (static, nothing replayed): 81 of 88 deterministic events are outside-bundle** (`../tools/assemble_hard.py`, `../tools/coverage.py`, `../tools/mutant_witness.py`, `../checker/run-claim.sh`, `~/pilot-checker/pins.json`, the KEVM tarball and the extracted K source, `/home/vladimir/pilot-hard/edit_annotations.py`, two logs written above the root). Only seqs 63, 69, 72, 73, 76, 77 and 78 are replay candidates. So L4 on the real bundle will be `partial` unless the tools and pins ship inside the bundle (open question Q-A4).
  - Monotonicity: a fabricated outside-input event (naive and re-signed) lowers L4 from pass to partial and raises nothing.

- [x] **Integration dry run on the real bundle (2026-10-29, 15:14–15:58 UTC, wall 44 min 17 s).** Output `pilot/handoff/ladder_A.dryrun.json`, log `pilot/handoff/dryrun.log`; verifier hash at run time `4b843b3c…` (not frozen).
  - **Producer key (real, D3):** `tcg:~/pilot-keys/producer.key` (mode 600, outside the bundle) + `producer.pub.pem`. Pubkey PEM sha256 `f9c1f770d449c90f31df88183bab11132b2b5ed574ed77b409aa949bb2fba4c1`; raw pubkey `80ff2d553b8481b647099e2a0224ecb25a6c9996cd5394b001ab4cf5755091fa` (raw sha256 `72c5de00…`). Distinct from the oracle key (oracle PEM sha256 `8c5eefbf…`). No private key under `pilot/`.
  - **Assembly:** the first `--check` refused (`HARD_STATUS.md: not claimed by any role rule`). After WS-H moved the file: `--check` OK; assembled and signed, 454 children, root `3e21b117e8f965f9d4558537b05378370e7fbcd584fb0e1fcf5f607e459820f9`, lint 0 problems at signing.
  - **Run:** `with-slot.sh prover -- verify.py bundle --rpc https://eth.drpc.org --variant A --docker-limit=--memory=6g --docker-limit=--cpus=2`. KEVM time: L1 893 s (5 claims), L2 mutants ≈ 1,758 s (5 replays); L4 replayed no prover event (cost 0: none was replayable).
  - **L0 fail, verifier bug (fixed):** every RPC call got `HTTP Error 403: Forbidden`. drpc rejects urllib's default User-Agent (curl works); the identity and environment checks never ran. All bundle-side L0 checks passed (schema, rule 4, root_hash, 454 child hashes, producer signature, T̂ schema). Fix: explicit `User-Agent: tcg-verifier/0.1` (tested with the fake RPC; checked live against drpc).
  - **L1 fail:** claims 01–05 all **accept** under the real KEVM image (exit 0 + `#Top`; 131–274 s each). Fails only on `verifier_hash`: T̂ names `cd8c058d…` (a stale hash WS-H wrote early), running `4b843b3c…`. Expected before the freeze.
  - **L2 (reported):** coverage covered R1–R3 / partial R4–R5 / blind R6–R9, total false, stored copy matches. Back-translation: 0 `entries`; the file uses key `claims`, not `entries` (format mismatch: the verifier reads `entries`, see the open question). Mutants: claim-01 ×2, claim-02, claim-03 → `concrete_trace_violation` reproduced; claim-01-symbolic → `not_accept` (judge: unknown); 7 directories `malformed` (no hash-verified refutation.json at assembly: WS-C still in progress). `no_witness`: claim-04, claim-05. **Pre-witness: not replayed** (exit 1 after 0.17 s): the bundle's `pre_witness/replay.sh` calls `/home/vladimir/pilot-locks/with-slot.sh`, which keeps its locks under `$HOME/pilot-locks`. The verifier gives bundle scripts a scratch HOME, so every `docker run` fails → NotAccept. Not a verifier bug: on a machine without that path the script skips the wrapper; here it breaks. Fix belongs to the script (hold the slot around the caller, like the mutant scripts) or the wrapper (absolute lock dir).
  - **L3 pass:** oracle signature over `adf5371e… ‖ 94c93ab3…`, approved = proven.
  - **L4 fail:** chain intact, 110 events, 99 deterministic. 1 replayed and matched; 10 replayed with stand-ins and **mismatched** (seq 80, 82–86, 88–90, 94: `ModuleNotFoundError: No module named 'tcg'`, undeclared imports); 76 not replayable (outside bundle); 12 not replayed because of the tool-hash convention: WS-H recorded the *script* hash (python3 events) or the *docker image Id* (sh events 63, 102, 110) as `tool_hash`, which the verifier did not accept. Fixed: the tool hash may now be the program's hash, a locally present docker image Id, or the hash of a recorded input script named in argv.
  - **outside_bundle (18 items):** the KEVM image `sha256:7d4a35bc…`, sh/dash and python3.12 by hash, and the ledger's outside paths (pins.json, the KEVM tarball, the extracted K source, `../checker/run-claim.sh`, `../tools/*.py`, `/home/vladimir/pilot-hard/edit_annotations.py`, `pilot-keys/approval.msg` + `oracle.pub.pem` (seq 98), `../HARD_STATUS.md` (seq 103), two round-1 logs).
  - **The bundle changed during the run:** after the run, lint finds 31 problems against the signed manifest (WS-C's `evidence/mutants/` claim-04/05 and `*-symbolic`, WS-B's `semantics/evmyullean/`, and the ledger). The run itself is internally consistent (the verifier works on the hash-verified copy made at start), but the next run needs a freeze by **all** writers, not only WS-H.

- [x] **Round 4 (2026-10-29): parent's answers to Q-A1–Q-A4 applied.**
  - **L4 stand-ins** (MAP.json / ledger note seq 97 rule, applied by hash alone; MAP.json itself is not trusted): a recorded outside input that is relative and whose sha256 equals a verified bundle child is materialized at its recorded location in a nested sandbox, and the event is replayed (`replayed_with_stand_ins`). Absolute paths, missing hashes, inputs with no byte-identical child, and outside outputs keep the event in `not_replayable_outside_bundle`, with a per-path `why`. Every mismatch now carries `replay_stderr_tail` and `used_stand_ins`.
  - **`--l4-skip-provers`:** prover/container events (tool hash = docker image Id, or kprove/docker/run-claim.sh/lake/lean named) go to `skipped_by_consumer` ("not replayed: skipped by consumer"), L4 at best `partial`; recorded as `l4_skip_provers` in the ladder.
  - **Static preview on the real ledger (99 deterministic events, nothing replayed):** 23 replay candidates, 12 of them through stand-ins (seq 80, 82–86, 88–90, 94: `assemble_hard.py`; 106, 108: four tools). 76 stay outside (42 argv paths with no stand-in, mostly `../checker/run-claim.sh` with `hash_not_recorded`; 24 inputs with no byte-identical child (KEVM pins/tarball/K source, earlier script versions); 13 absolute paths; 4 outputs outside). 43 events are prover events.
  - **Expected L4 = fail:** a manual hermetic replay of seq 82 exits 1 with `ModuleNotFoundError: No module named 'tcg'`. `assemble_hard.py` imports `tcg.keccak`/`tcg.claims` from `REPO = parents[2]`, and the events did not record those imports as inputs. In the dry run those stand-in events will be mismatches (honest: the recorded inputs do not reproduce the outputs). Fix on the producer side: record the imports with `--in` (they would then be stood in from `provenance/tools/tcg/*` by hash), or mark such events `--nondeterministic`.

- [ ] **Final ladder_A: waiting for GO from the orchestrator.** Protocol: (1) GO after WS-C finishes mutants 04/05, WS-H fixes `pre_witness/replay.sh` (no host paths) and re-records the key steps with `--in ../../tcg/*`, and WS-B moves `semantics/` out of the bundle; (2) freeze the verifier, send `verify.py --self-hash` to WS-H for the T̂ `tcg-verifier` entry + rehash; (3) assemble + sign, full variant A (provers replayed in L4 if time allows, else `--l4-skip-provers`, recorded), write `pilot/handoff/ladder_A.json` + `ladder_A.md`. Until GO: verifier fixes only.

## Test command (on the VM, from `~/sheaf/tcg`)
```
python3 -m unittest discover -s pilot/tools/tests -t pilot/tools/tests
python3 -m unittest discover -s pilot/verifier/tests -t pilot/verifier/tests
```
Actual output, last run 2026-10-29 (after the VM restart, 8 vCPU / 32 GB; mocks only, no prover slot used):
```
Ran 15 tests in 4.2s
OK
Ran 108 tests in 76.3s (1 skipped: the opt-in real-Lean test)
OK
```

## What is NOT verified (honest caveats)
- **What the suite runs for real, and what it fakes.** KEVM in the unit tests is the fake docker; the real KEVM path is exercised by the integration dry run (`docker` = `/usr/bin/docker`, image `sha256:7d4a35bc…` loaded). Lean: `checkers.lean_project` locates the toolchain by name under `~/.elan/toolchains/` (or `$TCG_LEAN_TOOLCHAINS`) and puts that toolchain's `bin/` on the PATH it passes to `lake`, so it does not depend on `~/.elan/bin` being on the non-interactive PATH. The **real Lean 4 kernel** (v4.22.0) is covered by an opt-in test: `TCG_REAL_LEAN=1 ~/pilot-locks/with-slot.sh lean -- python3 -m unittest test_round4.RealLeanKernel` (run from `pilot/verifier/tests`) checks `rfl` → accept, `sorry` → not_accept [sorryAx], custom axiom → not_accept [Toy.Ax.cheat]. It passed in 3 s on 2026-10-29. The fake toolchain still drives the 15 Lean edge-case tests.
- The KEVM judge is the `tcg/verdict.py` logic (validated there against real kprove logs). A KEVM "refute" is a symbolic stuck state, **not** a concrete counterexample. The output says `refute` and carries no witness.
- Fork table (`tcgverify/chain.py`): **verified** against go-ethereum `params/chainspecs/mainnet.json` @ `748cca24` (osakaTime 1764798551, bpo1 1765290071, bpo2 1767747671; cited in the code) and cross-checked against the `eth_config` of three RPCs in `provenance/chain_fetch.json` (current = bpo2: activation 1767747671, target 14 / max 21). BPO1/BPO2 derive as execution fork `osaka`; the BPO is reported as `blob_param_fork`. Only the Paris *block number* (15537394, pre-Shanghai, irrelevant to the pilot) is still from memory.
- L2/L4 **execute bundle-supplied code** (`replay.sh`, recorded argv) by default, as 06 asks. `--no-exec` disables this, and the fields then say "not run". Run the consumer as an isolated user (P5).
- A fabricated **non-deterministic** ledger note that is properly chained cannot be detected (it is counted, not replayed). The suite asserts it does not raise anything; v3 accepts this limit.
- OpenSSL 3.0.13 cannot `-rawin` sign or verify an **empty** message ("Could not allocate 0 bytes"). The pilot never signs an empty message. That case is a documented check (`test_openssl_empty_message_limitation`); RFC TEST 1 (the empty message) is checked against the RFC value only, and TESTs 2–3 are also checked by openssl.

## Decisions / readings taken (the conservative choice where ambiguous; DECISIONS.md not edited)
1. **`not_claimed` wording:** D11 says the five v3 §10 sentences verbatim, but the task 01 example paraphrases them ("The artefact is secure."). I used the v3 text exactly ("It does not claim the artifact is secure, only that it satisfies φ." …), enforced as a schema `const`. Please confirm.
2. **Rule 4 over-rejects:** any key *containing* verdict/level/proved/pass/score, keys `L0`–`L4`, and the word "proved" in any string value ("carry … the word proved").
3. **Role `c` vs `claims_without_certificate`:** a `rediscuss.json` is role `c` (task 08 calls it "c for each KEVM claim") but does **not** count as a certificate for rule 2, so variant-A claims must still be listed in `claims_without_certificate`.
4. **Variant B:** a claim with no Lean certificate gets `not_checked` (KEVM is not run under B, so the image never enters `outside_bundle`), and L1 is then `fail`. The alternative, falling back to KEVM, would make B's `outside_bundle` contain the image.
5. **Verifier in T̂:** L1 fails unless T̂ has a `checker` entry `{"name": "tcg-verifier", "hash": <verify.py --self-hash>}`. Any edit to the verifier source changes this hash (currently `917b82d1…`; recompute with `python3 pilot/verifier/verify.py --self-hash` at integration, not now).
6. **Semantics role:** vendored EVMYulLean files need a role from the fixed enum. I suggest `checker` (class T). The verifier compares T̂ `semantics[].hash` with `tools/tree_hash.py <bundle>/<path>` under variant B.
7. **Lean checker hash** is the sha256 of the toolchain's `bin/lean`, so it is platform-specific. T̂ `hash` may be a list (one per platform).
8. **Environment fields** `fee_schedule`, `caller_assumptions`, `precompiles`, `resource_limits` are reported as `declared_not_checked` and do not decide L0. `chain_id`, the fork (derived from the block timestamp), and every external code hash do decide it.

## Open questions
- Q-A5: answered: no retraction. Old events whose recorded inputs do not reproduce their outputs stay mismatches (L4 = fail on this ledger). Correctly re-recorded events appended later are counted on their own (already the behaviour: each event is its own bucket entry).
- Q-A6: answered and done: L2 reads `claims`, falling back to `entries` or a bare list; documented in `pilot/schema/README.md`; test `BacktranslationKeys`.
- Q-A4: answered: tools bundled in `provenance/tools/` (stand-ins by hash, implemented). Open follow-up: the events' undeclared imports (see Round 4).
- Q-A1: answered: verbatim v3 §10 sentences, "artifact" spelling (as implemented).
- Q-A2: answered: WS-A freezes the verifier after the dry run shows no more verifier bugs, then sends `verify.py --self-hash` to WS-H, who adds the `tcg-verifier` entry to T̂.
- Q-A3: answered: kprove events stay as recorded; `--l4-skip-provers` added. The dry run replays provers once (no skip) to measure cost.

## FINAL ladder_A (2026-10-29T17:39:11Z → 19:15:33Z, wall 1:35:25)
Bundle root ef3cab53…4126, verifier f7bde819…f364 (frozen), drpc, docker 6g/2cpu inside prover slot, provers not skipped.
- L0 pass. L1 pass: 5/5 KEVM accept, 828.9 s.
- L2, reported with no status: covered R1–R3, partial R4/R5, blind R6–R9; 12/12 mutants reproduce their kind; pre-witness replays; back-translation agreement unclear ×5. 4891.5 s.
- L3 pass. L4 fail: 11 matched, 9 mismatched (seq 63; seq 82–86 and 88–90 tcg import), 88 outside the bundle, 28 not replayed. 4.45 s.
- Bundle unchanged (before/after sha256 listings identical; lint 0 problems).
- Verifier defects found, NOT fixed because of the freeze: (1) the script-hash convention misses `sh -c "cd D && sh replay.sh"` events whose tool_hash has a `sha256:` prefix, so mutant prover events 102/110/112/114/118/120 were not replayed and the pre-run estimate of 7 replayable prover events was wrong; (2) the outside_bundle "used to replay" lines print ev.tool_hash, not the binary hash.
Details: handoff/ladder_A.md.
