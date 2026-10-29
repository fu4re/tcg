# ladder_A: final variant-A verifier run (TCG v3 bundle pilot)

Machine-readable result: `handoff/ladder_A.json`. Each level is reported separately. There is deliberately no summary mark.

## Setup
| item | value |
|---|---|
| bundle root (recomputed = declared) | `ef3cab535e7a5858c178ee9bbea70e153e21e5d4af4e09b8254755ffb3d14126` |
| manifest.json sha256 | `1236328d7e5edd2f18d4d00a74934a70c3a0c4b4cac83c4ca4c3a45fbd06439e` (381 children, 151 ledger events) |
| verifier hash (`verify.py --self-hash`) | `f7bde819d11db29babaf52cdf9fe4c3560651ff38ebfc9839ca679ed3321f364` (= T̂ `tcg-verifier`; frozen, `verifier/FROZEN.txt`) |
| producer key / oracle key | `~/pilot-keys/producer.pub.pem` / `~/pilot-keys/oracle.pub.pem` (consumer-supplied, outside the bundle) |
| variant | A (KEVM re-discharge in docker) |
| chain source | `--rpc https://eth.drpc.org` (worked first time; no fallback used) |
| docker limits | `--memory=6g --cpus=2`, the whole run inside `~/pilot-locks/with-slot.sh prover` (slot 1/3) |
| L4 provers | replay attempted (`--l4-skip-provers` **not** set); see L4 for why none ran to completion |
| started / ended (UTC) | 2026-10-29T17:39:11Z / 2026-10-29T19:15:33Z (handoff/ladder_A.started, .ended) |
| total wall | 1:35:25 (`/usr/bin/time -v`); verifier exit 0; max RSS of the verifier process 31 MB |

Command (run from `pilot/`):
```
~/pilot-locks/with-slot.sh prover -- /usr/bin/time -v python3 verifier/verify.py bundle \
  --producer-pubkey ~/pilot-keys/producer.pub.pem --oracle-pubkey ~/pilot-keys/oracle.pub.pem \
  --rpc https://eth.drpc.org --variant A --docker-limit=--memory=6g --docker-limit=--cpus=2 \
  --out handoff/ladder_A.json > handoff/ladder_A.log
```

## Wall time per level (`wall_s`)
| L0 | L1 | L2 | L3 | L4 |
|---|---|---|---|---|
| 0.53 s | 828.9 s | 4891.5 s | 0.005 s | 4.45 s |

## Bundle unchanged during the run
- `python3 tools/lint_manifest.py bundle/manifest.json` after the run: 0 problems, exit 0.
- `handoff/ladder_A.bundle_before.sha256` (taken at launch) vs `handoff/ladder_A.bundle_after.sha256` (taken after it): 382 files each, `diff` empty. Also `find bundle -newer handoff/ladder_A.started` lists nothing.
- `verify.py --self-hash` after the run is still `f7bde819…f364`.

## L0: pass
- Manifest schema, rule-4 forbidden keys, structure, root hash, children (0 problems, 0 unlisted files), and trusted base all OK.
- Producer signature: valid under the supplied key, and the manifest pubkey equals the supplied key.
- Identity: artifact keccak = declared = on-chain keccak `0x8661c673…74fa` for `0x2F0b23f53734252Bda2277357e97e1517d6B042A` at block 26298481 (code size 3462).
- Environment: chain_id 1 OK. Fork `osaka`, as declared and as derived from the block; the blob-param fork is `bpo2`. External code hashes for WETH9 and MCD_Vat match the chain.
- Declared but not checked: fee_schedule, caller_assumptions, precompiles, resource_limits. These are reported verbatim in the JSON.

## L1: pass
Verifier hash matches T̂. Lean axiom whitelist: {Classical.choice, Quot.sound, propext}. There are no Lean certificates in variant A.

| claim | checker | result | exit | wall |
|---|---|---|---|---|
| claim-01 | kevm-prove, image `sha256:7d4a35bc…c465` | accept | 0 | 146.6 s |
| claim-02 | kevm-prove | accept | 0 | 110.3 s |
| claim-03 | kevm-prove | accept | 0 | 154.6 s |
| claim-04 | kevm-prove | accept | 0 | 257.0 s |
| claim-05 | kevm-prove | accept | 0 | 160.2 s |

Every `stdout_sha256` is `8d9586e8…b45d` (the `#Top` output). The verifier built each docker argv itself; the argv is recorded per claim.

## L2: reported, no status (for H)
**Coverage** (recomputed; the stored `evidence/coverage.json` matches; `total` false):
- covered: R1, R2, R3.
- partial: R4 and R5. Their blind-spot reasons are in the JSON.
- blind: R6, R7, R8, R9, each with a declared reason.
- Every consistency list is empty: uncovered_undeclared, phi hash mismatch, unknown references, and the rest.

**Back-translation:** 5/5 claims translated. `agreement` = `unclear` for all five, which is H's judgement to make. The caveats are carried verbatim in `backtranslation_meta`:
- The translator saw phi's paraphrase.
- It is the same model family as the producer.
- There was one sample.

**Pre-witness:** replays. Exit 0, output sha256 `d7ad4c93…73ba` = expected, 543.0 s.

**Mutants:** 12 replayed, every kind rule holds, every result reproduced. `no_witness` is empty.

| mutant | kind | outcome | wall |
|---|---|---|---|
| claim-01 | concrete_trace_violation | concrete_trace_violation | 302.1 s |
| claim-01-mask | concrete_trace_violation | concrete_trace_violation | 376.1 s |
| claim-01-mask-symbolic | not_accept | not_accept (judge: unknown) | 158.3 s |
| claim-01-symbolic | not_accept | not_accept (judge: unknown) | 149.0 s |
| claim-02 | concrete_trace_violation | concrete_trace_violation | 327.0 s |
| claim-02-symbolic | not_accept | not_accept (judge: unknown) | 131.0 s |
| claim-03 | concrete_trace_violation | concrete_trace_violation | 368.8 s |
| claim-03-symbolic | not_accept | not_accept (judge: unknown) | 165.0 s |
| claim-04 | concrete_trace_violation | concrete_trace_violation | 379.4 s |
| claim-04-symbolic | refute | refute | 259.5 s |
| claim-05 | concrete_trace_violation | concrete_trace_violation | 793.1 s |
| claim-05-symbolic | not_accept | not_accept (judge: unknown) | 938.2 s |

`not_accept` is reported only, never as a witness. Every claim has at least one concrete_trace_violation witness, and claim-04 also has a symbolic refute.

## L3: pass
Oracle-signed approval: phi sha256 `adf5371e…90e9` = the proven phi, and requirements sha256 `94c93ab3…4e14` = the approved one. The signer is the oracle.

## L4: fail
The chain is intact (0 chain errors), with 151 events, 136 of them `deterministic: true`. Counts, which sum to 136:

| replayed_matched | replayed_mismatched | not_replayable_outside_bundle | skipped_by_consumer | not_replayed_other |
|---|---|---|---|---|
| 11 | 9 | 88 | 0 | 28 |

There are 15 stand-in replays (seq 82–86, 88–90 and 124–130). `inconsistent_outputs` is empty.

**Mismatches (9).** Exit is recorded as 0 and replayed as 1 in every case.
- **seq 82–86, 88–90 (8 events).** The replay ran `assemble_hard.py` from its byte-identical bundle stand-in. It failed with `ModuleNotFoundError: No module named 'tcg'` because the recordings did not declare that import.
  - These are kept as mismatches (Q-A5: no retraction).
  - WS-H's re-recordings seq 124–130 declare `../../tcg/*` as inputs. They replay with stand-ins and do **not** appear among the mismatches.
- **seq 63** (`kevm-prove`, pre-witness via `provenance/rebuild/pre_witness/replay.sh`).
  - The verifier accepted the tool by the docker image Id convention and replayed it. It exited 1 with empty stderr after a few seconds, so its output hash differs.
  - Likely cause (an inference, not checked by a separate run): that recorded copy of replay.sh is the old one, which looks for `/home/vladimir/pilot-locks/with-slot.sh`. Under the verifier's scratch HOME the locks are not there, which is the same failure as in the dry run.
  - The fixed copy in `evidence/pre_witness/replay.sh` replays in L2.

**Prover events were attempted but did not run.** The pre-run estimate, from my static scan of the ledger, was 7 replayable prover events at about 2 h. That estimate was **wrong**: only seq 63 got as far as executing. Seq 102, 110, 112, 114, 118 and 120 (the mutant `replay-sh` events) are in `not_replayed_other`:
- The reason is "tool 'sh' not available by hash sha256:<replay.sh hash>".
- **Cause (verifier gap, not fixed under the freeze):** these events record `tool_hash` as `sha256:<hex of replay.sh>` and argv as `sh -c "cd <dir> && sh replay.sh"`.
- The script-hash convention (`levels.py` ~line 538) compares the input sha256 with `tool_hash` byte for byte. The input is stored as bare hex, so the `sha256:` prefix breaks the match.
- The convention also matches only argv elements that are paths, and here the script sits inside one `-c` string.
- **Effect:** these events are reported as not replayed. They are never counted as matched, so this is fail-closed and not a false green. The replays they stand for are the same `replay.sh` runs that L2 executed and reproduced.

**Other not_replayed (22):**
- An input file is not in the bundle with the recorded hash: trusted_base.json, ledger.jsonl, pre_witness/replay.sh and expected.json, bundle_tools.py, make_phi_versions.py, make_generators.py.
- These are files that were rewritten after the event recorded them, and the re-recordings were not made.

**not_replayable_outside_bundle (88).** Every path is listed with a per-path `why` in the JSON. The main groups:
- `../checker/run-claim.sh`: 40 events.
- `../tools/assemble_hard.py` with no matching stand-in: 18.
- `/home/vladimir/sheaf/tcg/pilot/tools/mutant_witness.py`: 13.
- `../../../../pilot-checker/pins.json`: 9.
- `../tools/coverage.py`: 4.
- The KEVM source tarball and source tree.
- `../verifier/verify.py`.
- The oracle key and approval.msg.
- `../HARD_STATUS.md`.
- `/tmp/wsh_replay.out`.
- Round-1 logs.

**WS-C note, reported as is:** mutant_witness.py imports `tcgverify`, which is not bundled. Its `record` events (seq 46, 57, 66, 75, 101, 109, 111, 113, 115–117, 119, 131) therefore stay not-replayable outside the bundle.

## outside_bundle (26 items)
Full list in `ladder_A.json["outside_bundle"]`:
- JSON-RPC `https://eth.drpc.org`.
- KEVM docker image `sha256:7d4a35bc…c465`.
- `/usr/bin/sh` (`86d31f6f…`), used to run bundle-supplied scripts.
- `/usr/bin/dash` and `/usr/bin/python3.12`, used for replays.
- The ledger-event dependency groups listed above.

**Verifier labelling defect (not fixed under the freeze):** the "used to replay ledger events" lines print `ev.tool_hash` and not the binary's own hash (`levels.py` ~line 552).
- When the tool was accepted by the image-Id or script-hash convention, the line attributes that hash to the interpreter.
- Example: `/usr/bin/dash (sha256 sha256:7d4a35bc…)` is the KEVM image Id.
- Example: `/usr/bin/python3.12 (sha256 6eba170b…)` is the hash of `bt_pair.py`.
- The binaries' real hashes are `86d31f6f…` for sh/dash and `e50d468e…` for python3.12. (`ac841202…` is `bt_prepare.py` and `10ebcfe6…` is `make_generators.py`.)
- Read these lines as "the replay used this binary, and the tool was accepted under hash X".

## Not established by this run
- No L4 prover replay completed. The KEVM results stand on the L1 re-discharge and the L2 mutant and pre-witness replays.
- `agreement` stays `unclear` for every back-translation, pending H.
- R6–R9 are blind and R4/R5 are partial, as the bundle declares.
- The environment items under `declared_not_checked` are declared by the producer and not checked.
