# The E1 "second machine": isolated verification

PLAN.md gate E1: `verify.py`, on a machine that never saw the build session,
recomputes `ms_cert` from the bundle alone and refuses a bundle with a swapped
witness and one with swapped bytecode. PLAN.md section 6, Q2 accepts any
isolation boundary on the VM "as long as the verifier run never sees the
build session's workspace". This directory implements it as a container.

## What the container is

- **Image** (`Dockerfile`): `ubuntu:24.04`, pinned by digest, plus exactly six
  inputs from `specgame/`: `setup.sh`, `requirements.lock`,
  `tools/specgame_core.py`, `tools/verify.py`, `schemas/`, `protocol.json`
  (since the protocol split; `protocol.md` is prose and is not needed).
  `setup.sh` installs the pinned solc / z3 / pyrevm inside the image
  (it refuses any binary whose sha256 is not the pinned one). The build
  context is a staging directory `run_isolated.sh` fills with those files
  only, so nothing else of the workspace (no `contracts/`, `mutants/`,
  `specs/`, `tests/`, `bundles/`, no `.toolchain/` or `.venv/` of the host)
  is ever sent to the Docker daemon.
- **Run** (`run_isolated.sh <bundle-dir> [<report.json>]`):
  `docker run --rm --network none --read-only --tmpfs /tmp`, the bundle
  bind-mounted **read-only** at `/bundle`, and, only if a report path is
  given, that file's directory at `/out`. Entrypoint:
  `python -I -B /opt/specgame/tools/verify.py /bundle`.
- The verifier's own trust base is what is in the image: its source, the
  core, the schemas, protocol.json and the toolchain. Step (1) compares the
  sha256 of each (and the recomputed `toolchain_fingerprint()`) with the
  bundle's provenance layer; a different verifier, core or toolchain gives
  exit 2 (could not verify), a different protocol.json gives exit 3
  (refused: the bundle was produced under other frozen values), never a
  pass. The logs below predate the split and show the older single
  `protocol sha256` line.

Exit code = the verifier's:

| exit | verdict | when |
|---|---|---|
| 0 | `HOLDS` | every step passes; Check = Accept on every check, recorded and re-run |
| 2 | `NOT_CERTIFIED` | the bundle records Check = Unknown and the re-run reproduces the same per-check verdicts (reasons are reported, not compared); steps 3–6 still run and the certified kill set and ms_cert are reported (Def. 5.3) |
| 2 | `COULD_NOT_VERIFY` | toolchain / core / verifier mismatch, missing tool, unknown subject, a recorded Unknown that re-runs to Accept (the bundled table does not reproduce), an internal error inside a step |
| 3 | `REFUSED` | any Refute (recorded or re-run); a recorded Accept that re-runs to Unknown or Refute; a recorded Unknown that re-runs to Refute; a Check aggregate that does not combine from its per-check table; protocol.json, hash, schema, id, properness, witness or claim mismatch; a V-completeness claim |

Precedence: REFUSED over COULD_NOT_VERIFY over NOT_CERTIFIED. The two exit-2
verdicts are told apart by the report's `verdict` string. A docker failure
(missing docker, build failure, container exit other than 0/2/3) is 2. Note: `make verify-isolated` (and `make verify-fixture`) print the real
code as `Error 3` but make itself exits 2 on any failing recipe; use
`run_isolated.sh` directly when the exit code matters.

What it proves and what it does not: the container rules out the verifier
reading the build workspace (it is not mounted and not in the image) and any
network access during verification. It shares the host kernel and CPU with
the build session, so it is not a defence against a compromised host; Q2
accepts this boundary. The orchestrator's own E1 run is on a machine that
never saw the build session.

## Recorded runs

Docker 29.1.3 on the `tcg` VM (Ubuntu 24.04.5, x86_64), commit `2d46599` of
branch `claude/specgames-wp5-bcdb8c`. Tamper bundles were generated from the
committed fixture by `tests/fixtures/bundle/tamper.py` into a scratch
directory. stderr (docker build chatter) omitted.

### Good fixture: `tests/fixtures/bundle/good` → exit 0

```
$ verifier/run_isolated.sh tests/fixtures/bundle/good
verify /bundle
[PASS            ] (0) manifest
       manifest.json validates against schemas/manifest.schema.json (+ validate_sigma on every sigma)
[PASS            ] (1) hashes
       8 files, every sha256 matches, no unlisted file
       core sha256 c5b6722400066e654520a2c95f0e9072d325433d96f0964fe0cd011667f2e37e (running = bundled copy = provenance)
       verifier sha256 1e6bc4c7e1102a90541bddfd70b79df9b1edd9e6b5524180e2c468c8c1ce8033
       protocol sha256 7dd65494e6d7821a951e8622846f2785253fc531d391e32cc662214a1231db48
       semantics version matches: solc 0.8.35+commit.47b9dedd.Linux.g++, Z3 version 4.16.0 - 64 bit, python 3.12.3, pyrevm 0.3.7, CANCUN
[PASS            ] (2) check
       solc input re-derived from b + phi + timeout_ms=20000: sha256 c100a4343ea3e71376a8ee4859f618546a07574edf5d0b3e193486bf26aaac35 (= bundled)
       b runtime sha256 c7761d01ada538f5a478bce8861f9812b5c29a81de9c80cbbcce91f42abc063c
       Spec over b runtime sha256 8ff8409ea85e933b62acad9a4c08e3f2b907a130c8d87f22a880ee153f062091, checks ['check_cap', 'check_mint_adds']
       solc --standard-json re-run (0.334 s): Accept (all_targets_safe)
         target check_mint_adds line 16: safe
         target check_cap line 20: safe
       raw solc output identical to the bundled one: yes
[PASS            ] (3) M
       mutant 8e1a17895ccc: id recomputed = listed; properness sigma[0] gives run(b) != run(m)
       mutant 94eaa220eb26: id recomputed = listed; properness sigma[0] gives run(b) != run(m)
       mutant cc76b36aebea: id recomputed = listed; properness sigma[0] gives run(b) != run(m)
[PASS            ] (4) W
       2 of 2 witnesses replay to a violation; 0 discarded (discarding is not a refusal)
       W[0] mutant 8e1a17895ccc: violation in ['check_mint_adds']
       W[1] mutant cc76b36aebea: violation in ['check_cap']
[PASS            ] (5) score
       recomputed ms_cert = 2/3, kill set ['8e1a17895ccc', 'cc76b36aebea']
[PASS            ] (6) V-completeness
       no V-completeness claim; named in not_claimed
ms_cert = 2/3  kill set ['8e1a17895ccca5a512af32eaabe4cad06782b5897cd712f7400d57767f5ac2d9', 'cc76b36aebea6c116e21f74e5599f20ac476ef19c4b4d88109baad39eee66fed']
mutants without a valid witness: ['94eaa220eb26e0bbef5623ce4e29e203e2e641943ab0b805178acbea8225dad3']
label (T*, affects no verdict): mutant 8e1a17895ccc operator=statement_deletion fault_class=missing_state_update
label (T*, affects no verdict): mutant 94eaa220eb26 operator=statement_deletion fault_class=missing_state_update
label (T*, affects no verdict): mutant cc76b36aebea operator=require_deletion fault_class=missing_bound_check
discarded (producer): mutant 94eaa220eb26 no check ends in violation: check_cap=success, check_mint_adds=success [alice.check_cap(alice,zero,100,1): success -> success; alice.check_mint_adds(alice,zero,100,1): success -> success]
verdict: HOLDS, exit 0
```

### Swapped mutant bytecode → exit 3, refused at step 3 (properness)

m01's source is replaced by b's source and relabelled consistently (new id =
b's runtime sha256, file renamed, `files` table, W, metadata and kill set
all updated), so every hash and the id recomputation pass; properness is
what refuses it.

```
$ python tests/fixtures/bundle/tamper.py tests/fixtures/bundle/good swapped_bytecode /tmp/sb
$ verifier/run_isolated.sh /tmp/sb
verify /bundle
[PASS            ] (0) manifest
       manifest.json validates against schemas/manifest.schema.json (+ validate_sigma on every sigma)
[PASS            ] (1) hashes
       8 files, every sha256 matches, no unlisted file
       core sha256 c5b6722400066e654520a2c95f0e9072d325433d96f0964fe0cd011667f2e37e (running = bundled copy = provenance)
       verifier sha256 1e6bc4c7e1102a90541bddfd70b79df9b1edd9e6b5524180e2c468c8c1ce8033
       protocol sha256 7dd65494e6d7821a951e8622846f2785253fc531d391e32cc662214a1231db48
       semantics version matches: solc 0.8.35+commit.47b9dedd.Linux.g++, Z3 version 4.16.0 - 64 bit, python 3.12.3, pyrevm 0.3.7, CANCUN
[PASS            ] (2) check
       solc input re-derived from b + phi + timeout_ms=20000: sha256 c100a4343ea3e71376a8ee4859f618546a07574edf5d0b3e193486bf26aaac35 (= bundled)
       b runtime sha256 c7761d01ada538f5a478bce8861f9812b5c29a81de9c80cbbcce91f42abc063c
       Spec over b runtime sha256 8ff8409ea85e933b62acad9a4c08e3f2b907a130c8d87f22a880ee153f062091, checks ['check_cap', 'check_mint_adds']
       solc --standard-json re-run (0.331 s): Accept (all_targets_safe)
         target check_mint_adds line 16: safe
         target check_cap line 20: safe
       raw solc output identical to the bundled one: yes
[FAIL            ] (3) M
       mutant c7761d01ada5: properness FAILED: no sigma of 1 gives run(b, s) != run(m, s)
       mutant 94eaa220eb26: id recomputed = listed; properness sigma[0] gives run(b) != run(m)
       mutant cc76b36aebea: id recomputed = listed; properness sigma[0] gives run(b) != run(m)
[PASS            ] (4) W
       1 of 2 witnesses replay to a violation; 1 discarded (discarding is not a refusal)
       W[0] mutant c7761d01ada5: DISCARDED (no check ends in violation: check_cap=success, check_mint_adds=success [alice.check_cap(alice,zero,100,1): success -> success; alice.check_mint_adds(alice,zero,100,1): success -> success])
       W[1] mutant cc76b36aebea: violation in ['check_cap']
[FAIL            ] (5) score
       claimed ms_cert 2/3 != recomputed 1/3
       claimed kill_set ['c7761d01ada5', 'cc76b36aebea'] != recomputed ['cc76b36aebea']
       recomputed ms_cert = 1/3, kill set ['cc76b36aebea']
[PASS            ] (6) V-completeness
       no V-completeness claim; named in not_claimed
ms_cert = 1/3  kill set ['cc76b36aebea6c116e21f74e5599f20ac476ef19c4b4d88109baad39eee66fed']
mutants without a valid witness: ['94eaa220eb26e0bbef5623ce4e29e203e2e641943ab0b805178acbea8225dad3', 'c7761d01ada538f5a478bce8861f9812b5c29a81de9c80cbbcce91f42abc063c']
label (T*, affects no verdict): mutant c7761d01ada5 operator=statement_deletion fault_class=missing_state_update
label (T*, affects no verdict): mutant 94eaa220eb26 operator=statement_deletion fault_class=missing_state_update
label (T*, affects no verdict): mutant cc76b36aebea operator=require_deletion fault_class=missing_bound_check
discarded (producer): mutant 94eaa220eb26 no check ends in violation: check_cap=success, check_mint_adds=success [alice.check_cap(alice,zero,100,1): success -> success; alice.check_mint_adds(alice,zero,100,1): success -> success]
discarded (verifier): mutant c7761d01ada5 no check ends in violation: check_cap=success, check_mint_adds=success [alice.check_cap(alice,zero,100,1): success -> success; alice.check_mint_adds(alice,zero,100,1): success -> success]
verdict: REFUSED at step 3 (M), exit 3
```

### Swapped witness → exit 3, refused at step 5

The two witnesses' sigma are exchanged (manifest consistent). Both pairs are
discarded at step 4; the recomputed score disagrees with the claim:

```
[FAIL            ] (5) score
       claimed ms_cert 2/3 != recomputed 0/3
       claimed kill_set ['8e1a17895ccc', 'cc76b36aebea'] != recomputed []
verdict: REFUSED at step 5 (score), exit 3
```

All tamper kinds (and the in-process verdicts) are in
`tests/fixtures/bundle/tamper.py` (`--list`) and asserted by
`tests/test_verify.py`.
