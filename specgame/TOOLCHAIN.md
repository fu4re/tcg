# Specification Games toolchain (WP0)

Pinned environment for everything under `specgame/`. Installed by `make setup`
(`setup.sh`, idempotent) into project-local, gitignored paths; checked by
`make check` (`smoke/check.py`). Nothing is installed into `/usr/local`; the
system-wide `solc` 0.8.38, `z3` 5.3.2 and `forge` are never used by the
Makefile (binaries are referenced by absolute path, and solc's solver PATH is
reduced to `.toolchain/bin:/usr/bin:/bin`).

## Pins

| Component | Version | Location | Obtained from | sha256 |
|---|---|---|---|---|
| solc | `0.8.35+commit.47b9dedd` (official static Linux release, `Linux.g++`) | `.toolchain/bin/solc` | `https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v0.8.35+commit.47b9dedd` (sha256 matches `list.json` of the same host) | `fa8ac9a32d301ad023a36ee5a29f8e291fe3200c60244e43c142539e82a617f4` |
| z3 | `4.16.0` (64 bit) | `.toolchain/bin/z3` (+ `.toolchain/z3-LICENSE.txt`) | `https://github.com/Z3Prover/z3/releases/download/z3-4.16.0/z3-4.16.0-x64-glibc-2.39.zip`, only `bin/z3` extracted | zip `7288c49a5bd6dbafd7b0b0d1f65956b91672da24b08f09242919af159be3418e`; binary `e583c4186a45e72411fa2cb2048401eed03f0f8e5f24694676a8f6271a50b765` |
| Python | `3.12.3` (Ubuntu `python3.12` 3.12.3-1ubuntu0.17) | `.venv/` (stdlib `venv`, pip 24.0 as shipped) | apt `python3.12`, `python3.12-venv` | — |
| pyrevm | `0.3.7` | `.venv/` | PyPI, wheel `pyrevm-0.3.7-cp312-cp312-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`, installed `--require-hashes --only-binary=:all: --no-deps` from `requirements.lock` | `d055860c3352d6bc180b80255d8563f0b3c0fe6ce62b5c2a52e1bc7ecc4fad4f` |
| OS | Ubuntu 24.04.5 LTS, x86_64, glibc 2.39, kernel 7.0.0-1014-gcp | — | — | — |

Compiler settings used everywhere: `--evm-version cancun`, optimizer off
(solc CLI default; verified from the emitted metadata, `optimizer.enabled=false`),
`--metadata-hash none`. pyrevm runs with `spec_id="CANCUN"` to match.
SMTChecker settings: `--model-checker-engine chc --model-checker-solvers z3
--model-checker-targets assert --model-checker-timeout 20000
--model-checker-show-proved-safe --model-checker-show-unproved`.

Foundry (optional in PLAN.md section 1) is not installed by WP0; nothing on the
check path needs it.

## Findings while pinning (read before building on this)

1. **solc 0.8.35 needs an external z3 process; without one it silently skips
   CHC and exits 0.** The static binary does not link z3; it looks up `z3` on
   `PATH`. Actual output with `PATH=/usr/bin:/bin` (no z3 there), tautology
   harness, exit code 0:

   ```
   Warning: Solver z3 was selected for SMTChecker but it is not available.

   Warning: CHC analysis was not possible since no Horn solver was found and enabled. The accepted solvers for CHC are Eldarica and z3.
   ```

   Neither line is an assertion warning, so a parser that reads "no assertion
   violation reported" as "proved" turns a run that did no analysis into a
   green. (Without `--model-checker-show-proved-safe`, a real proof shows up
   only as a count summary, `Info: CHC: 1 verification condition(s) proved
   safe! ...`, not tied to any location.) Hence: z3 4.16.0 is
   pinned as a separate binary, every SMTChecker run gets a PATH that resolves
   `z3` to the pinned one (check step (0) asserts this), proved requires the
   positive `Info: CHC: Assertion violation check is safe!` line at the target
   location, and check step (b0) runs the no-solver case as a negative control
   that must not classify as proved. With the system PATH, solc would silently
   use `/usr/local/bin/z3` (5.3.2) instead.

2. **A solver-budget timeout is not labelled as a timeout.** With
   `--model-checker-timeout 1` on a nonlinear harness, solc prints only
   `Warning: CHC: Assertion violation might happen here.` (exit 0), the same
   text as an over-approximation unknown. The smoke classifier maps it to
   `unknown` = FAIL. Downstream (`check.py` in WP3) must treat "might happen"
   as Unknown, never as Accept, and cannot tell budget from incompleteness
   from the text alone.

3. **pyrevm `get_code` returns the runtime bytecode followed by zero
   padding** (revm's analysed legacy bytecode: 1892 compiled bytes, 1925
   returned, the extra 33 bytes all zero). Mutant identity must hash the
   compiled `bin-runtime`, not `get_code()`; the smoke check asserts
   "deployed code = compiled runtime + zero padding".

4. **pyrevm reverts surface as `RuntimeError("Revert { gas_used: N, output:
   0x... }")`**, not as a result object; the revert data has to be parsed out
   of the message (the smoke check does this to verify `Panic(0x01)` and the
   `require` reason strings).

5. The runtime bytecode hash of `contracts/CappedToken.sol` does not depend on
   the source's absolute path (checked in step (a) by recompiling a copy in a
   temporary directory). The CBOR tail with `--metadata-hash none` is
   `a164736f6c6343000823000a` = `{solc: 0.8.35}`.

## Targets

- `make setup` — `bash setup.sh`. Installs missing apt packages with sudo
  (`ca-certificates curl unzip python3.12 python3.12-venv`), downloads solc and
  z3 only if the pinned sha256 is not already in place, creates the venv only
  if missing, installs pyrevm only if not at 0.3.7. A second run prints
  `present (skip)` for every item and downloads nothing.
- `make check` — `smoke/check.py`, steps (0), (a), (b0), (b), (c), (d); exits
  1 on any FAIL. Since WP-I it runs through the shared core
  (`tools/specgame_core.py`): compile and Check via `solc --standard-json`,
  the strict Check classifier (Unknown, solver-unavailable, compile errors,
  unparsed output and a target without a result line are never Accept), and
  the pyrevm executor. The smoke harnesses are in the spec format of
  `specs/SPEC_FORMAT.md`. Step (c) replays the solver's counterexample as a
  σ on pyrevm (the probe must end in `Panic(0x01)`), which shows the path of
  the step (b) proof is reachable, i.e. that proof is not vacuous.
- `make test` — unit tests in `tests/` (stdlib unittest; the classifier tests
  run on captured solc outputs in `tests/fixtures/smt/`, regenerated by
  `tests/make_fixtures.py`; a few tests run the pinned solc live).
- `make lint` — `tools/speclint.py` on the placeholder artifact and a smoke
  harness.
- `make clean` — removes `build/` only, so `make clean && make setup` is a
  no-op setup on an installed tree.
- `make distclean` — also removes `.venv/` and `.toolchain/` (full reset).

## Verification log

Ran from a fully reset tree: `make distclean`, then
`make clean && make setup && make check` twice. Run 1 downloaded solc, z3 and
the pyrevm wheel (pip with `--no-cache-dir`) and ended `check: 6/6 PASS`, exit 0.
Run 2 output, verbatim (exit 0):

```
rm -rf /home/vladimir/sheaf/tcg-specgames/specgame/build
bash /home/vladimir/sheaf/tcg-specgames/specgame/setup.sh
setup: apt packages present (skip): ca-certificates curl unzip python3.12 python3.12-venv
setup: solc 0.8.35+commit.47b9dedd present (skip)
setup: z3 4.16.0 present (skip)
setup: venv /home/vladimir/sheaf/tcg-specgames/specgame/.venv present (skip)
setup: pyrevm 0.3.7 present (skip)
setup: done: solc=/home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/solc z3=/home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/z3 python=/home/vladimir/sheaf/tcg-specgames/specgame/.venv/bin/python
/home/vladimir/sheaf/tcg-specgames/specgame/.venv/bin/python -I /home/vladimir/sheaf/tcg-specgames/specgame/smoke/check.py --solc /home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/solc --z3 /home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/z3
[PASS] (0) toolchain pins
       solc 0.8.35+commit.47b9dedd.Linux.g++
       z3 on solver PATH: .toolchain/bin/z3 (Z3 version 4.16.0 - 64 bit)
       python 3.12.3, pyrevm 0.3.7
[PASS] (a) compile CappedToken
       cmd: .toolchain/bin/solc --evm-version cancun --metadata-hash none --combined-json abi,bin,bin-runtime,hashes,metadata contracts/CappedToken.sol
       settings (from metadata): evmVersion=cancun optimizer.enabled=false bytecodeHash=none
       runtime bytecode: 1892 bytes
       sha256(runtime) = c7761d01ada538f5a478bce8861f9812b5c29a81de9c80cbbcce91f42abc063c
       same sha256 when compiled from a different absolute path: yes
       written: build/CappedToken.json
[PASS] (b0) negative control: no z3 on PATH is not proved
       solc exit code 0, classified: solver_unavailable (not proved, as required)
       solc said: Warning: Solver z3 was selected for SMTChecker but it is not available.
[PASS] (b) SMTChecker CHC tautology -> proved
       cmd: .toolchain/bin/solc --model-checker-engine chc --model-checker-solvers z3 --model-checker-targets assert --model-checker-timeout 20000 --model-checker-show-proved-safe --model-checker-show-unproved smoke/ProvedTautology.sol
       verdict: proved at smoke/ProvedTautology.sol:11
[PASS] (c) SMTChecker CHC reachable assert(false) -> counterexample
       cmd: .toolchain/bin/solc --model-checker-engine chc --model-checker-solvers z3 --model-checker-targets assert --model-checker-timeout 20000 --model-checker-show-proved-safe --model-checker-show-unproved smoke/ReachableFalse.sol
       verdict: counterexample at smoke/ReachableFalse.sol:10, witness x = 6
       trace: ReachableFalse.constructor() ; ReachableFalse.probe(6)
       pyrevm replay: probe(6) reverts with Panic(0x01) (assert failure)
[PASS] (d) pyrevm deploy + owner mint + totalSupply
       deployed at 0x2bda4a99d5be88609d23b1e4ab5d1d34fb1c2feb (spec_id=CANCUN, cap=1000); code = compiled runtime + zero padding
       owner mint(700) -> totalSupply() = 700, balanceOf(alice) = 700
       non-owner mint reverts ('not owner'); owner mint over cap reverts ('cap exceeded')
check: 6/6 PASS
```

### After WP-I (smoke check moved onto the shared core)

`make clean && make setup && make check`, setup a no-op, output verbatim
(exit 0). The runtime sha256 of `CappedToken` is unchanged from WP0 although
`mint`/`transfer` became `public` and compilation moved from the CLI to
standard JSON.

```
rm -rf /home/vladimir/sheaf/tcg-specgames/specgame/build
bash /home/vladimir/sheaf/tcg-specgames/specgame/setup.sh
setup: apt packages present (skip): ca-certificates curl unzip python3.12 python3.12-venv
setup: solc 0.8.35+commit.47b9dedd present (skip)
setup: z3 4.16.0 present (skip)
setup: venv /home/vladimir/sheaf/tcg-specgames/specgame/.venv present (skip)
setup: pyrevm 0.3.7 present (skip)
setup: done: solc=/home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/solc z3=/home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/z3 python=/home/vladimir/sheaf/tcg-specgames/specgame/.venv/bin/python
/home/vladimir/sheaf/tcg-specgames/specgame/.venv/bin/python -I -B /home/vladimir/sheaf/tcg-specgames/specgame/smoke/check.py --solc /home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/solc --z3 /home/vladimir/sheaf/tcg-specgames/specgame/.toolchain/bin/z3
[PASS] (0) toolchain pins
       solc 0.8.35+commit.47b9dedd.Linux.g++ sha256 fa8ac9a32d301ad023a36ee5a29f8e291fe3200c60244e43c142539e82a617f4
       z3 .toolchain/bin/z3: Z3 version 4.16.0 - 64 bit
       python 3.12.3, pyrevm 0.3.7, spec_id CANCUN
[PASS] (a) compile CappedToken
       solc --standard-json, unit CappedToken.sol, input sha256 cd18f75b66a893001d12228d8aaa2b3e337ca116c115cd0935cae0aad924aef5
       settings (from metadata): evmVersion=cancun optimizer.enabled=false bytecodeHash=none
       runtime bytecode: 1892 bytes
       sha256(runtime) = c7761d01ada538f5a478bce8861f9812b5c29a81de9c80cbbcce91f42abc063c
       same sha256 when compiled from another path: yes
       written: build/CappedToken.json
[PASS] (b0) negative control: no z3 on PATH is Unknown
       verdict: Unknown (solver_unavailable), as required
       solc said: Warning: Solver z3 was selected for SMTChecker but it is not available.
       solc said: Warning: CHC analysis was not possible since no Horn solver was found and enabled. The accepted solvers for CHC are Eldarica and z3.
       solc said: Warning: CHC analysis was not possible since no Horn solver was found and enabled. The accepted solvers for CHC are Eldarica and z3.
[PASS] (b) Check tautology -> Accept
       Check(contracts/CappedToken.sol, smoke/ProvedTautology.sol): Accept (all_targets_safe), timeout 20000 ms, input sha256 257259d4c1a0240b3cf30a358a136e81a36fdb7273ed05d5642c9a1fc09e366c
       target check_tautology line 15: safe
[PASS] (c) Check reachable assert(false) -> Refute, witness replayed
       Check(contracts/CappedToken.sol, smoke/ReachableFalse.sol): Refute, check_reachable line 14, x = 6
       trace: Spec.constructor(0) ; State: owner = 0x0, cap = 0, totalSupply = 0 ; Spec.check_reachable(0x0, 0x0, 6, 0)
       pyrevm replay of σ: probe alice.check_reachable(alice,alice,6,0): Panic(0x01) -> violation
[PASS] (d) pyrevm deploy + owner mint + totalSupply
       σ: alice deploys (cap=1000), mints 700 to bob; bob mints 1; alice mints over cap
         deploy: success
         tx[0] alice.mint(address,uint256)('bob', '700'): success
         tx[1] bob.mint(address,uint256)('bob', '1'): Error("not owner")
         tx[2] alice.mint(address,uint256)('bob', '301'): Error("cap exceeded")
       totalSupply() = 700, balanceOf(bob) = 700, owner() = alice
       tx outcomes ['success', 'pre_unmet', 'pre_unmet']; observation sha256 6b7fa3dc9d0f9c15c78b93fcad68d8f3c889893748602e95502badc222700f3c (identical on a second run)
check: 6/6 PASS
```
