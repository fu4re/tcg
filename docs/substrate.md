# Prover substrate (Track B, gate G1)

Getting a usable kompiled KEVM definition onto this machine, and validating
`tcg.commands.prove.classify()` against **real** `kprove` output rather than
assumed text. Everything below is either a command that was actually run, a
file path that actually exists, or a verdict that actually came out of the
Haskell-backend `kprove`/`kore-exec` binaries — no simulated output.

## 1. A kompiled KEVM definition already existed on this machine

Before building anything, the local `/nix/store` was searched (per the task
brief) for a pre-built kompiled definition:

```
ls /nix/store | grep -i -E 'evm-semantics|kevm'
```

This turned up a fully-kompiled KEVM tree, built as a dependency of the
`kontrol` package already on `~/.nix-profile/bin`:

```
/nix/store/a9lyzn037b879r448fk9qsbkzf4nibr6-kevm-d4bf484a5dfe1e38d729a30434cd6f41e3590fb2/
  evm-semantics/
    haskell/            <- Haskell backend, main module EDSL (kompiled from edsl.md)
    haskell-standalone/ <- Haskell backend, main module ETHEREUM-SIMULATION (driver.md)
    haskell-summary/, summary/, llvm/, llvm-summary/, plugin/, ...
```

`evm-semantics/haskell/` is a complete, valid K "kompiled" directory
(`definition.kore`, `compiled.txt`, `timestamp`, `backend.txt` = `haskell`,
`macros.kore`, ...), and `grep '^module EVM ' compiled.txt` confirms the
`EVM` module (the one `tcg`'s default `iface.json` template imports) is
compiled in — `edsl.md` requires `evm.md` transitively.

The companion K **source** (needed as `-I` include paths so `requires
"evm.md"` resolves when kprove parses a spec on top of the definition) lives
in the `kevm-pyk` Python package's data files:

```
/nix/store/<hash>-kevm-pyk-1.0.678/lib/python3.10/site-packages/kevm_pyk/kproj/
  evm-semantics/   <- evm.md, edsl.md, network.md, ... (the actual K sources)
  plugin/plugin/   <- krypto.md (crypto builtin hook declarations)
```

Since the nix store is read-only and not a stable GC root, all of this was
**copied out** (not symlinked) to a persistent, non-repo, non-tmp location:

```
~/toolchains/kevm-1.0.678/haskell/                 (151M, the kompiled definition)
~/toolchains/kevm-1.0.678/evm-semantics-source/     (960K, K sources)
~/toolchains/kevm-1.0.678/plugin/plugin/krypto.md   (12K)
```

Verified it actually loads with a trivial `kprove` invocation (details in
§3). This whole step took a few minutes of investigation and a few seconds
of copying — no multi-hour build was needed for the **unpatched** definition.
`scripts/build-kevm.sh` automates this discovery+copy, with a from-source
`kompile --backend haskell` fallback if no prebuilt target is ever found (see
§6 for a from-source build that *was* actually run, timed at ~4 minutes).

## 2. Iterating the provable claim against the real parser

The task explicitly calls for iterating against the real `kprove` parser
rather than guessing KEVM's claim format from memory, so that's what
happened. Three iterations, in order:

1. **First attempt** (`<k> #execute => #halt ... </k>` with most call-frame
   cells left completely symbolic): kprove exit 1, but the output is a real
   proof-search artifact, not a parse error — `kore-exec` reports:
   *"The configuration's term unifies with the destination's term, but the
   implication check between the conditions has failed."* The claim is
   actually **true** (STOP really does succeed); it just wasn't specific
   enough for the backend to discharge the residual side condition. This log
   became the seed for a real classify() bug — see §4.
2. **Second attempt**: fully concretized every non-transitioning cell in the
   call frame (`<id>`, `<caller>`, `<gas>`, `<static>`, `<callDepth>`,
   `<jumpDests>`, ...) and made the target `<output>`/`<statusCode>`
   transitions explicit. This is `tests/control/provable.k` today, minus one
   more fix below. **Exit 0, `#Top`.**
3. Picking `<id>`/`<caller>` values naively (large made-up decimals) turned
   out to matter: one such value, reduced mod 2^160, landed on address `0x1`
   — the ECRECOVER precompile — and triggered a genuine backend crash (see
   §5). Final control specs use small, obviously-non-precompile addresses
   (`1234567890`, `999999999999`).

## 3. Control specs (task 3)

All three run directly against `~/toolchains/kevm-1.0.678/haskell`:

```
kprove tests/control/<name>.k \
  --definition ~/toolchains/kevm-1.0.678/haskell \
  --spec-module <MODULE> \
  -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
  -I ~/toolchains/kevm-1.0.678/plugin
```

| control | file | spec-module | exit | verdict | log |
|---|---|---|---|---|---|
| (a) provable | `tests/control/provable.k` | `STOP-EVM-SPEC` | 0 | Accept (`#Top`) | `tests/control/logs/provable.log` |
| (b) refutable | `tests/control/refutable.k` | `REFUTE-EVM-SPEC` | 1 | Refute | `tests/control/logs/refutable.log` |
| (c) undecided | `tests/control/provable.k` + 2s wall-clock timeout | `STOP-EVM-SPEC` | n/a (killed) | Unknown | `tests/control/logs/undecided-timeout.log` |

(b) asserts the same STOP program reaches a final `<pc>` of `999`, which is
false for a 1-byte program starting at pc 0. (c) is documented in full,
including a secondary `--depth 1` experiment, in `tests/control/undecided.md`
— summary in §4 below.

Wall time for each direct `kprove` call: 15-20s (provable), ~30-40s
(refutable — the backend does more search before giving up; see §5).

## 4. classify() validation (task 4)

`tcg.commands.prove.classify(returncode, log, timed_out)` against the real
logs above, **before** any fix:

| control | rc | timed_out | key log line (verbatim) | classify() (before) | correct? |
|---|---|---|---|---|---|
| provable | 0 | False | `#Top` | Accept | yes |
| refutable | 1 | False | `[Error] Prover: backend terminated because the configuration cannot be`<br>`rewritten further.` | Refute | yes |
| undecided (timeout) | -1 | True | *(empty — kprove killed before flushing output)* | Unknown(b) | yes |
| **under-specified but semantically TRUE** claim (§2 attempt 1) | 1 | False | same generic `cannot be\nrewritten further` trailer, preceded by:<br>`Warning (WarnStuckClaimState):`<br>`The configuration's term unifies with the destination's term, but the implication check between the conditions has failed.` | **Refute** | **no — false defect report on a valid claim** |
| `provable.k` run with `kprove --depth 1` (§4a below) | 1 | False | same generic trailer, **no** WarnStuckClaimState preamble | Refute | **no — same bug, no available fix** |

Two distinct findings came out of this:

### 4a. Real bug, real fix: `WarnStuckClaimState` collapses into Refute

The attempt-1 log in §2 is real, captured `kprove` output for a claim that
**is true**. `classify()`'s only textual signal for "the backend gave up" is
the generic `"cannot be rewritten further"` trailer, which `kore-exec`
prints identically whether the search terminated because (a) no rule
matched anywhere (genuine structural refutation) or (b) the destination
pattern *did* structurally unify but a residual boolean implication could
not be discharged (a solver-decidability gap on a side condition, not a
counterexample). Case (b) has an extra preamble case (a) does not:
`Warning (WarnStuckClaimState): ... unifies with the destination's term,
but the implication check ... has failed.` — confirmed absent from
`refutable.log` (a *genuinely* false claim), so this is a real,
observable distinguishing signal, not a coincidence of one example.

**Fix shipped** (`tcg/commands/prove.py`, not merged — for review): check for
`"warnstuckclaimstate"` / `"unifies with the destination"` before the
generic Refute check, and route it to `Unknown("c")` instead. Re-validated
against all captured logs after the fix:

| control | classify() (after fix) | correct? |
|---|---|---|
| provable | Accept | yes (unchanged) |
| refutable | Refute | yes (unchanged — the fix does not blunt real defect detection) |
| undecided (timeout) | Unknown(b) | yes (unchanged) |
| under-specified but TRUE claim | **Unknown(c)** | **yes — fixed** |

Unit tests: `tests/test_classify.py` (6 tests, all passing — run with
`PYTHONPATH=. python3 -m unittest tests.test_classify -v`), using the real
captured logs in `tests/control/logs/` plus the verbatim `WarnStuckClaimState`
excerpt from attempt 1 above.

This bug is **currently reachable** through completely ordinary use: nothing
exotic (no special flags) is needed to hit it, just an honestly-written,
true, but insufficiently-concretized claim — a very common state for a claim
to be in mid-development. Before the fix, `tcg prove` would have told a user
their correct claim was refuted.

### 4b. Documented, not fixed: `--depth` bound is indistinguishable from Refute

Running `kprove tests/control/provable.k --depth 1 ...` (same true claim,
cut short at 1 rewrite step) also exits 1, also ends in the generic
`"cannot be rewritten further"` trailer, and shows **no** `WarnStuckClaimState`
preamble (the search never got far enough to attempt an implication check).
So the 4a fix does not, and structurally cannot, catch this case using log
text alone — real `kprove` (Haskell backend, K v7.1.337) gives *zero*
distinguishing signal between "ran out of depth budget" and "genuinely
refuted."

This is **not fixed**, and is deliberately left unfixed rather than papered
over, because:

- `tcg.commands.prove.run()` never passes `--depth` or `--branching-allowed`
  to `kprove` today, so this path is not reachable through the shipped CLI.
- `classify()`'s existing `"depth bound" / "iteration bound" / "max
  iterations"` branch is therefore dead code against the real backend — it
  watches for text the backend does not emit.

Recorded as a regression-pinning test
(`tests/test_classify.py::TestKnownLimitationDepthBoundIsUnresolved`, which
asserts the *current, undesired* behavior on purpose) and in
`tests/control/undecided.md`, so a future PR that adds a `--depth` budget to
`prove.py` trips over this instead of silently shipping a soundness bug
(Unknown reported as Refute).

## 5. A real backend crash, independent of any of the above

Any claim on this definition whose destination does **not** unify trivially
(i.e. both the genuinely-false `refutable.k` and an earlier wrong-`<pc>` /
wrong-`<statusCode>` draft) triggers, partway through the search, a native
assertion failure:

```
kore-exec: [...] Error (ErrorException):
    Assertion failed
    CallStack (from HasCallStack):
      assert, called at src/Kore/Builtin/Krypto.hs:313:5 in kore-0.1.155-...
Created bug report: kore-exec.tar.gz
```

immediately followed by output showing the backend was evaluating
`#ecrec ( #range ( b"" , 0 , 32 ) , ... )` — the ECRECOVER precompile — on
symbolic/empty `Bytes` arguments. This reproduces identically regardless of
which cell makes the claim false (confirmed with both a wrong `<statusCode>`
and a wrong `<pc>` variant), which points to the prover speculatively
exploring an ECRECOVER-dispatch hypothesis via the trailing `...` match
variable in `#halt`'s continuation whenever the direct match doesn't close,
not to anything specific about this claim's content.

**This does not corrupt the final verdict**: `kore-exec` still recovers and
prints the standard terminal message afterward, so `classify()` (before or
after the 4a fix) still lands on the right answer — but it is a real,
reproducible infrastructure wall, and it means any real proof attempt that
fails to close on this machine will also drop a `kore-exec.tar.gz` bug
report in whatever directory `kprove` was invoked from (confirmed — one such
file appeared in this repo's worktree root during this investigation and was
removed before committing). `tcg.commands.prove.run()` invokes `kprove`
without `--temp-dir`, inheriting the workspace root as cwd; a follow-up
hardening item worth considering is pinning `--temp-dir` so a failed proof
doesn't leave debris in the workspace. Not fixed here — flagged, per the
"documented wall is a valid Track B result" instruction, since it's a
backend/native-library limitation, not something in `tcg`'s own code.

## 6. End-to-end through the real CLI (task 5 — the acceptance)

In a throwaway workspace (`/private/tmp/.../scratchpad/workspace-demo`,
outside any repo), driving the real pipeline with:

```
PYTHONPATH=/Users/akkedeline/sheaf/tcg /Users/akkedeline/.pyenv/versions/3.12.2/bin/python3 -m tcg <cmd>
```

`tcg init`, `tcg loop new demo`, `tcg iface set demo --file iface.json`
(the recipe from the task, `requires: ["evm.md"]`, `imports: ["EVM"]`, one
claim `{"label": "main", "file": "main.k"}`), `.tcg/loops/demo/main.k` set to
the `tests/control/provable.k` claim body (just the `claim ... [label(main),
all-path]` block, no module wrapper — that's what `tcg compile-claims`
enforces), `tcg compile-claims demo`, then `.tcg/toolchain.lock` edited to add:

```json
"definition": "/Users/akkedeline/toolchains/kevm-1.0.678/haskell",
"includes": [
  "/Users/akkedeline/toolchains/kevm-1.0.678/evm-semantics-source",
  "/Users/akkedeline/toolchains/kevm-1.0.678/plugin"
]
```

Three runs of `tcg prove demo`, real outcomes:

| step | main.k body | toolchain.lock | command output | exit |
|---|---|---|---|---|
| 1 | provable (correct `<pc>`) | default timeout (3600s) | `Accept: demo (1 claim(s), 0 trusted child(ren), 15.597s)` | **0** |
| 2 | refutable (`<pc> 0 => 999`), after `iface set` again (forces `Stale`) + `compile-claims` | default timeout | `Refute: demo — prover left a residual goal; witness log: .../.tcg/logs/demo-prove.log` | **3** |
| 3 | same refutable claim | `"replay": {"timeout_seconds": 3}` | `Unknown(b): demo — refusal; log: .../.tcg/logs/demo-prove.log` | **2** |

Step 1 also wrote `evidence/replay/9314552e....json` (Accept-only evidence,
per `prove.py`) with the exact replayable invocation recorded; step 2's exit
3 matches `Exit.REFUSED`; step 3's exit 2 matches `Exit.UNKNOWN`, and its
3-second wall-clock cutoff (well under the ~30-40s the refute claim actually
takes) is what genuinely triggered `subprocess.TimeoutExpired` inside
`prove.py`, not a contrived flag. Loop state after each step: `Accepted`,
`Refuted`, `Unknown` respectively (`.tcg/loops/demo/loop.json`), matching
`tcg/workspace.py`'s state machine.

All three acceptance verdicts (Accept/Refute/Unknown) are demonstrated
through the actual shipped CLI, not simulated.

## 7. Ghost patch (task 6)

`theory/patches/ghost.diff` targets `evm.md` and adds three top-level ghost
cells (`<callCounter>`, `<inFunc>`, `<monitoredAddr>`) plus additive,
`[total]` helper functions (`#selKey`, `#ifGet`, `#bump`) and hooks them into
the message-call frame push/pop rules (`CALL`/`CALLCODE`/`DELEGATECALL`/
`STATICCALL`/`CREATE`/`CREATE2` entry, and the three exit rules:
`return.success`, `return.revert`, and normal `#halt`). Per its own
docstring, it's a reentrancy-frame-counting ghost monitor: `<inFunc>[sig]`
tracks active call frames into a single monitored contract `C`, keyed by
calldata selector, so `reentered(sig) := inFunc[sig] >= 2` can be stated as
an invariant; it never appears on the LHS of a stock rule, so it's designed
not to change stock-rule applicability.

Applied to a **copy** of the KEVM sources (the nix store copy is read-only):

```
cp -R ~/toolchains/kevm-1.0.678/evm-semantics-source ~/toolchains/kevm-1.0.678-ghost/evm-semantics-source
patch -p1 -d ~/toolchains/kevm-1.0.678-ghost/evm-semantics-source < theory/patches/ghost.diff
```

**Applied cleanly — zero rejects** (`patch -p1 --dry-run` succeeded first
try; the real apply matched it). Confirmed the three ghost cells and the
five hook sites landed in the patched `evm.md`.

Built a second, separate Haskell-backend definition from the patched
source (Haskell target only, not the LLVM/concrete-execution target — see
below on why that's in-scope for this gate):

```
kompile --backend haskell ~/toolchains/kevm-1.0.678-ghost/evm-semantics-source/evm.md \
  --main-module EVM --syntax-module EVM \
  -I ~/toolchains/kevm-1.0.678-ghost/evm-semantics-source \
  -I ~/toolchains/kevm-1.0.678/plugin \
  --md-selector "k & ! concrete" \
  --hook-namespaces "JSON KRYPTO" \
  --emit-json \
  -o ~/toolchains/kevm-1.0.678-ghost/haskell
```

**Succeeded. Wall time ≈4 minutes** (well under the 1-2 hour estimate in the
brief — this machine only builds the Haskell proving target, not the dual
LLVM+Haskell build kevm-pyk's own `kevm-pyk kdist` driver does by default;
no native/C++ compilation is needed for the Haskell backend itself). Verified
`module EVM` compiled with the ghost cells present (`grep -c
'callCounter\|inFunc\|monitoredAddr' compiled.txt` → 11 hits).

Proved the trivial claim (`tests/control/provable.k`, same STOP claim,
unmodified — it never touches the ghost cells) against the patched
definition:

```
kprove tests/control/provable.k \
  --definition ~/toolchains/kevm-1.0.678-ghost/haskell \
  --spec-module STOP-EVM-SPEC \
  -I ~/toolchains/kevm-1.0.678-ghost/evm-semantics-source \
  -I ~/toolchains/kevm-1.0.678/plugin
```

**Exit 0, `#Top`.** Log: `tests/control/logs/provable-ghost-patched.log`.

**Not done** (out of scope for gate G1, flagged as open): no claim was
written that actually *exercises* the ghost cells (e.g. a CALL-reentrancy
scenario checking `<inFunc>`/`<callCounter>` update correctly) — this only
confirms the patch applies, kompiles, and doesn't break an unrelated proof.
Validating the ghost monitor's own semantics is future work.

## 8. Wall-times summary

| step | wall time |
|---|---|
| discover + copy prebuilt unpatched definition | a few minutes (investigation) + seconds (copy) |
| single trivial `kprove` run (provable) | 15-20s |
| single trivial `kprove` run (refutable, more search + backend crash/recovery) | ~30-40s |
| ghost patch: `patch -p1` apply | instant |
| ghost patch: `kompile --backend haskell` (Haskell target only) | **≈4 minutes** |
| ghost patch: trivial claim re-proof | ~15-20s |
| full `tcg` CLI pipeline, one verdict (init → prove) | well under a minute (excluding the `kprove` run itself) |

No build in this pass took anywhere near the 1-2 hour envelope the brief
budgeted for — the unpatched definition didn't need building at all, and the
patched one only needed the Haskell (proving) target, not the full
LLVM+Haskell dual build.

## 9. What remains open

- **`--depth`/iteration-bound ambiguity (§4b)**: no known fix using log text
  alone; not reachable today since `prove.py` doesn't pass `--depth`, but
  pinned with a regression test so it can't be silently shipped later.
- **Krypto/ECRECOVER backend crash (§5)**: a real Haskell-backend limitation
  on this K/kore-exec version, not a `tcg` bug; recovers to a correct verdict
  every time observed, but worth a `--temp-dir` hardening follow-up so a
  failed proof doesn't drop `kore-exec.tar.gz` into the workspace root.
- **Ghost cells are untested semantically** (§7): patch applies and kompiles,
  but no claim exercises `<inFunc>`/`<callCounter>`/`<monitoredAddr>` yet.
- **Only the Haskell (proving) backend was built** — no LLVM/concrete backend
  on this machine. That's correct for `tcg prove` (which only calls
  `kprove`), but anything that later needs concrete execution (e.g.
  `kontrol`-style test running) would need a separate build.
- **Only one opcode (STOP) has been proven** — real loop claims will be far
  more complex (storage, calls, ABI decoding) and may re-trigger the §5
  crash pattern or new parser fights; this gate only establishes that the
  substrate *works*, not that it's been stress-tested.
