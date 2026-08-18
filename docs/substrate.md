# Prover substrate (Track B, gate G1)

Getting a usable kompiled KEVM definition onto this machine, and validating
`tcg.commands.prove.classify()` against **real** `kprove` output rather than
assumed text. Everything below is either a command that was actually run, a
file path that actually exists, or a verdict that actually came out of the
Haskell-backend `kprove`/`kore-exec` binaries — no simulated output, except
where a section says explicitly that a case is synthesized (one classify()
unit test — see §4a).

This document was revised after a code review found a real correctness bug
in the first version of the classify() fix (§4a), plus several process/
evidence-discipline gaps; the whole document was re-validated against that
review, not just patched at the edges.

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
~/toolchains/kevm-1.0.678/provenance.json           (resolved paths + hashes)
```

Verified it actually loads with a trivial `kprove` invocation (details in
§3). This whole step took a few minutes of investigation and a few seconds
of copying — no multi-hour build was needed for the **unpatched** definition.

`scripts/build-kevm.sh` automates this discovery+copy end to end, and was
substantially hardened after the first review pass (see §6a):

- **Version-verified, not glob-first-match.** The expected kevm version is
  read from `tcg/commands/init.py`'s `TOOLCHAIN` dict (the one place this
  repo pins it) and cross-checked by *content* (not nix package naming,
  which doesn't carry a `1.0.678`-shaped string for the prebuilt definition
  package) against a version-tagged `kevm-pyk-<version>` package. If more
  than one candidate definition or source tree matches the store globs, the
  script refuses loudly and lists every candidate rather than taking the
  first match.
- **`edsl.md`/`EDSL` fallback**, matching the prebuilt target's own main
  module (see "module alignment" note in the script) — not `evm.md`/`EVM` —
  so a from-source build produces an equivalent substrate, not a silently
  different one.
- **Per-component (haskell / source / plugin), atomic, never-destructive
  install.** Each of the three components is copied into a temp sibling
  directory, verified complete, and only then swapped into place; a missing
  12KB `krypto.md` never triggers deleting or re-copying the intact 151MB
  definition, and `--force` can never leave the machine without a working
  install (the old tree is deleted only after the new one is confirmed
  installed).
- **`cp -Rc` (APFS clonefile)** first, falling back to plain `cp -R` when
  unavailable — confirmed on this machine, where `/nix` and `~/toolchains`
  are different APFS volumes (`disk3s7` vs. `disk3s5`), so clonefile always
  falls back here and the fallback path is exactly what actually runs.
- **`provenance.json`** written next to the installed definition: resolved
  store paths, the pinned/confirmed kevm version, and `definition.kore`'s
  own sha256, so a later mismatch between what's on disk and what
  `/nix/store` currently has is at least detectable.

All of the above was tested directly (fast idempotent path, full
discovery+copy into a throwaway `TOOLCHAIN_DIR`, per-component repair after
deleting only the plugin component, and the version-mismatch refusal path by
temporarily pointing the pinned version at a nonexistent `9.9.999` and
confirming a loud, correct refusal with no side effects).

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
   enough for the backend to discharge the residual side condition. This
   exact claim is committed verbatim as `tests/control/underspecified-true.k`
   and became the seed for a real classify() bug — see §4a.
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

A fourth spec, `tests/control/refutable-structural.k`, was added later
(§4a) specifically to capture the *other* half of the `WarnStuckClaimState`
warning cleanly: it asserts the executed program's final `<k>` cell is the
literal, unexecuted `STOP` opcode (never true) with the cell's RHS **closed**
(no trailing `...`), which avoids inviting the §5 crash and lets `kore-exec`
report "doesn't unify" instead of crashing before it can say anything.

## 3. Control specs (task 3)

All run directly against `~/toolchains/kevm-1.0.678/haskell`:

```
kprove tests/control/<name>.k \
  --definition ~/toolchains/kevm-1.0.678/haskell \
  --spec-module <MODULE> \
  -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
  -I ~/toolchains/kevm-1.0.678/plugin
```

| control | file | spec-module | exit | verdict | log |
|---|---|---|---|---|---|
| (a) provable | `provable.k` | `STOP-EVM-SPEC` | 0 | Accept (`#Top`) | `logs/provable.log` |
| (b) refutable, noisy | `refutable.k` | `REFUTE-EVM-SPEC` | 1 | Refute (crash-recovered, no warning preamble) | `logs/refutable.log` |
| (b') refutable, clean | `refutable-structural.k` | `REFUTE-CLOSED2-SPEC` | 1 | Refute ("doesn't unify" warning, no crash) | `logs/refutable-structural.log` |
| (regression) true-but-underspecified | `underspecified-true.k` | `UNDERSPECIFIED-TRUE-SPEC` | 1 | Unknown ("unifies... implication failed" warning) | `logs/underspecified-true.log` |
| (c) undecided, timeout | `provable.k` + 2s wall-clock timeout | `STOP-EVM-SPEC` | n/a (killed) | Unknown(b) | `logs/undecided-timeout.log` |
| (c') undecided, depth (documented, not a fix target) | `provable.k` + `--depth 1` | `STOP-EVM-SPEC` | 1 | Refute (indistinguishable from genuine refutation — §4b) | `logs/undecided-depth-bound.log` |

All `tests/control/logs/*.log` files were (re-)captured directly against
the exact, final, committed `.k` spec files (not predecessor drafts still
sitting in a scratch directory) so that every `Location:` line number in a
log matches the file as committed.

(b) and (b') are the same false claim (a 1-byte STOP program cannot end with
`<pc> 999`, nor can its `<k>` cell still contain a bare unexecuted `STOP`),
captured two different ways: (b) is what a naive false claim actually
produces on this backend (a crash, then the generic trailer, no warning
preamble at all); (b') closes the `<k>` cell's RHS specifically to dodge
that crash and show the "doesn't unify" `WarnStuckClaimState` text cleanly
— see §4a for why both had to be captured. (c) is documented in full,
including the `--depth 1` experiment, in `tests/control/undecided.md`.

Wall time for a direct `kprove` call: 15-20s (provable / underspecified-true
/ refutable-structural), ~30-40s (refutable — the backend does more search
before crash-recovering; see §5).

## 4. classify() validation (task 4)

`tcg.commands.prove.classify(returncode, log, timed_out)` now returns a
3-tuple, `(verdict, unknown_class, hint)` — the `hint` is new (§4c) and is
what `tcg prove` appends to the printed Unknown message.

### 4a. `WarnStuckClaimState` has (at least) three sub-messages — a review found the first fix over-matched

The first version of this fix (before this review round) matched the bare
tag `"warnstuckclaimstate"` in the log. That is wrong, and would have been a
**second** real classify() bug shipped in the name of fixing the first one:
`kore-exec`'s own message templates (extracted directly from the binary —
`strings .../kore-exec/bin/.kore-exec-wrapped | grep -i destination`) show
the warning has (at least) two textually opposite bodies under the same tag:

```
Kore.Log.WarnStuckClaimState.TermsNotUnifiableStuck:
  "The configuration's term doesn't unify with the destination's term
   and the configuration cannot be rewritten further."

Kore.Log.WarnStuckClaimState.TermsUnifiableStuck:
  "The configuration's term unifies with the destination's term, but
   the implication check between the conditions has failed."
```

Only `TermsUnifiableStuck` ("unifies... but implication failed") is a valid
Unknown signal — the rewrite target *was* reached, only a residual boolean
side condition is undischarged. `TermsNotUnifiableStuck` ("doesn't
unify...") is a genuine structural refutation and must stay Refute. The
bare-tag match swallowed both into Unknown, which turns a found defect into
a false "could not verify" — the exact confusion `tcg/outcome.py` forbids.

**Both variants were captured for real** to pin this precisely (not just
inferred from the binary's strings):

- `TermsUnifiableStuck` (Unknown): `tests/control/underspecified-true.k`,
  the true-but-underspecified claim from §2 attempt 1, committed and
  re-captured verbatim — `tests/control/logs/underspecified-true.log`.
- `TermsNotUnifiableStuck` (Refute): needed a false claim that reaches the
  stuck-state path *without* the §5 Krypto crash cutting the search short
  first (the original `refutable.k` never shows either warning body — the
  crash always intervenes before `kore-exec` gets to print it). Closing the
  `<k>` cell's RHS (no trailing `...`, so there's no open match-variable for
  the backend to speculatively fill with an ECRECOVER hypothesis) avoids the
  crash: `tests/control/refutable-structural.k`, exit 1, log opens with
  `Warning (WarnStuckClaimState): ... doesn't unify with the destination's
  term and the configuration cannot be rewritten further.` — no crash trace
  anywhere in the log. See `tests/control/logs/refutable-structural.log`.

**Fix, corrected**: match only the specific phrase `"unifies with the
destination"` (present in `TermsUnifiableStuck`, absent from
`TermsNotUnifiableStuck` — the two use different verb forms, "unifies" vs.
"unify", so a plain substring check distinguishes them correctly), not the
bare tag. Matching is whitespace-normalized (`kore-exec` wraps long
sentences; the generic trailer is already observed wrapping as `"cannot
be\nrewritten further"`) via one precompiled, case-insensitive alternation
run once against a single whitespace-collapsed copy of the log — not
several full lowercased copies, since real proof logs (unlike today's
KB-sized control logs) can reach tens of MB. The two unvalidated Refute
signals from the first fix draft (`"#not"` — matches K's `#Not`/`#notBool`
connectives inside any dumped configuration, never seen in a real captured
log — and `"implication check failed"` — that string is literally the
`TermsUnifiableStuck` sentence, so it could never correctly signal Refute at
all) were removed outright: Refute's only textual signal is now the
empirically-validated generic trailer, checked *after* the stuck-guard, and
anything unrecognized stays Unknown, never Refute.

**Per-branch ambiguity.** A single `kprove` call's search can visit several
branches, each logging its own `WarnStuckClaimState` verdict independently —
so a log can in principle contain *both* signals. classify() resolves this
by giving the `TermsUnifiableStuck` ("stuck") signal priority regardless of
where in the log it appears, not merely whichever comes first textually: an
unresolved branch anywhere makes the whole call's verdict unreliable, so it
stays Unknown. No real captured log demonstrates this combination on its
own, so it is pinned with a synthesized test
(`tests/test_classify.py::TestClassifyMixedSignalsPreferUnknown`, explicitly
documented as synthetic in its docstring) covering both orderings.

Validated against every real log after the corrected fix:

| control | classify() | correct? |
|---|---|---|
| provable | Accept | yes |
| refutable (crash, no warning) | Refute | yes — a crash is never itself a classification signal; the generic trailer alone still correctly closes it out |
| refutable-structural ("doesn't unify") | **Refute** | **yes — this is the regression case for the over-broad first-draft fix, which would have wrongly said Unknown** |
| underspecified-true ("unifies... failed") | Unknown(c), hint: *"residual implication undischarged — claim may need more concretized cells; see log"* | yes |
| undecided (timeout) | Unknown(b) | yes |

Unit tests: `tests/test_classify.py`, 10 tests, all passing — run with
`PYTHONPATH=. python3 -m unittest tests.test_classify -v`.

**Why per-claim invocation matters here too** (§6a): `run()` used to prove
every goal claim of a loop in *one* `kprove` call and classify the single
concatenated log, so one claim's `WarnStuckClaimState` (of either kind)
could sit in the same log as a sibling claim's clean Refute or Accept
signal, misattributing the verdict. `run()` now invokes `kprove` once per
goal claim, so each classify() call sees exactly one claim's log — the
mixed-signal handling above is retained as a same-call, multi-branch
safeguard, not a substitute for per-claim isolation.

### 4b. Documented, not fixed: `--depth` bound is indistinguishable from Refute

Running `kprove tests/control/provable.k --depth 1 ...` (same true claim,
cut short at 1 rewrite step) also exits 1, also ends in the generic
`"cannot be rewritten further"` trailer, and shows **no** `WarnStuckClaimState`
preamble at all (the search never got far enough to attempt an implication
check). So §4a's fix does not, and structurally cannot, catch this case
using log text alone — real `kprove` (Haskell backend, K v7.1.337) gives
*zero* distinguishing signal between "ran out of depth budget" and
"genuinely refuted."

This is **not fixed**, and is deliberately left unfixed rather than papered
over, because:

- `tcg.commands.prove.run()` never passes `--depth` or `--branching-allowed`
  to `kprove` today, so this path is not reachable through the shipped CLI.
- The `classify()` branch that used to watch for `"depth bound" / "iteration
  bound" / "max iterations"` text was **removed** (it was dead code against
  the real backend, which never emits that text) rather than kept as
  misleading no-op code. `"a"` (iteration bound exhausted) remains defined
  in `tcg.outcome.UNKNOWN_CLASSES` as spec vocabulary only, with a comment
  saying so.

Recorded as a regression-pinning test
(`tests/test_classify.py::TestKnownLimitationDepthBoundIsUnresolved`, which
asserts the *current, undesired* behavior on purpose) and in
`tests/control/undecided.md`, so a future change that adds a `--depth`
budget to `prove.py` trips over this instead of silently shipping a
soundness bug (Unknown reported as Refute).

### 4c. Accept now requires corroboration, not just exit 0

`classify()` no longer treats `returncode == 0` alone as Accept. The one
real success shape observed on this substrate is `provable.log`'s exact
content: `"#Top\n"`, 5 bytes, nothing else on stdout — the pretty-printed
`\top` formula kprove emits when every path of an all-path claim discharges
cleanly. `classify()` now requires `"#Top" in log` in addition to `rc == 0`;
otherwise it returns `Unknown("c", "prover exited 0 but no proof pattern
found")`. Demonstrated end to end through the real CLI in §6a (the
underspecified-true claim's Unknown(c) run shows the analogous hint for the
stuck-implication case).

### 4d. Honest substrate limit: some FALSE claims look identical to under-specified TRUE ones

Restating §4a's finding plainly, because it is a substrate limit worth
naming rather than a bug to chase further right now: a claim whose rewrite
target *is* reached, but whose postcondition is actually **false** (e.g. an
off-by-one in an arithmetic bound, expressed via variables rather than a
concrete literal mismatch), produces the exact same `TermsUnifiableStuck`
`WarnStuckClaimState` text as a claim that is merely under-specified but
true. `kore-exec`'s own output does not, as far as this investigation found,
distinguish "the implication is provably false" from "the solver returned
unknown on the implication" — both print the identical sentence.

So on this substrate: **arithmetic/logical postcondition defects surface as
Unknown(c) with a residual-implication hint, not Refute.** Refute is
reliably reachable only for *structural* non-unification (the
`TermsNotUnifiableStuck` case, §4a, `refutable-structural.k`). This is the
conservative-safe direction (Unknown, not a false Refute), consistent with
`docs/bundle-spec.md` §6 and `tcg/outcome.py`'s "refusal on unknown is
conservative" principle — but it does mean this substrate, as it stands,
under-detects a class of real defects rather than mis-detecting them. Lifting
this needs structured per-claim counterexample extraction (e.g. `kore-rpc`'s
`implies`/`get-model` endpoints, or `pyk`'s `APRProof` machinery, to pull an
actual model/counterexample out of a failed implication rather than reading
kore-exec's pretty-printed text) — **not attempted in this pass**; recorded
in §9 as the roadmap item that lifts this limit.

## 5. A real backend crash, independent of any of the above

Any claim on this definition whose destination does **not** unify trivially
(confirmed with three independently-false claims: wrong `<statusCode>`,
wrong `<pc>`, and the closed-`<k>`-cell wrong-opcode claim) can, but does not
always (`refutable-structural.k` shows it's avoidable — see §4a), trigger a
native assertion failure partway through the search:

```
kore-exec: [...] Error (ErrorException):
    Assertion failed
    CallStack (from HasCallStack):
      assert, called at src/Kore/Builtin/Krypto.hs:313:5 in kore-0.1.155-...
Created bug report: kore-exec.tar.gz
```

immediately followed by output showing the backend was evaluating
`#ecrec ( #range ( b"" , 0 , 32 ) , ... )` — the ECRECOVER precompile — on
symbolic/empty `Bytes` arguments. This points to the prover speculatively
exploring an ECRECOVER-dispatch hypothesis via the trailing `...` match
variable in `#halt`'s continuation whenever the direct match doesn't close
*and that variable is left open* — closing it (`refutable-structural.k`)
avoids the crash entirely, which is itself useful confirmation of the
mechanism, not just a workaround.

**This does not corrupt the final verdict**: `kore-exec` still recovers and
prints the standard terminal message afterward, so `classify()` still lands
on the right answer (`refutable.log`, crash-and-recover, still correctly
Refute — pinned explicitly as that case in
`tests/test_classify.py::TestClassifyAgainstRealLogs.test_refutable_is_refute`).
A crash marker (`Error (ErrorException)`, `Created bug report:`) is **never**
itself a classification signal, in either direction: crash-with-trailer is
still Refute (as observed); crash-without-trailer would fall through to the
safe default, Unknown.

**Crash artifacts are now collected into the workspace, not left wherever
`kprove` happened to run.** `tcg.commands.prove.run()` now invokes each
per-claim `kprove` call with `cwd` set to `.tcg/build/`, and after each call
checks for a `kore-exec.tar.gz` there; if present, it's moved to
`.tcg/logs/<target>-<label>-kore-exec.tar.gz` next to that claim's prove log,
and the printed Refute/Unknown message for that claim gets an appended
`; backend crash report: <path>` note. Demonstrated in §6a's 2-claim run.
(Earlier in this investigation, before this was wired up, one such file
appeared in this repo's own worktree root from an ad hoc `kprove` invocation
during exploration and was removed before committing — exactly the
workspace-pollution failure mode this now prevents for real `tcg prove`
runs.)

## 6. End-to-end through the real CLI (task 5 — the acceptance)

In throwaway workspaces under `/private/tmp/.../scratchpad/workspace-demo*`
(outside any repo), driving the real pipeline with:

```
PYTHONPATH=<this worktree> /Users/akkedeline/.pyenv/versions/3.12.2/bin/python3 -m tcg <cmd>
```

`tcg init`, `tcg loop new demo`, `tcg iface set demo --file iface.json`
(the recipe from the task, `requires: ["evm.md"]`, `imports: ["EVM"]`),
claim bodies in `.tcg/loops/demo/*.k` (just the `claim ... [label(...),
all-path]` block, no module wrapper — that's what `tcg compile-claims`
enforces), `tcg compile-claims demo`, then `.tcg/toolchain.lock` edited to
add:

```json
"definition": "/Users/akkedeline/toolchains/kevm-1.0.678/haskell",
"includes": [
  "/Users/akkedeline/toolchains/kevm-1.0.678/evm-semantics-source",
  "/Users/akkedeline/toolchains/kevm-1.0.678/plugin"
]
```

### 6a. Per-claim invocation (§4a's "why this matters", implemented)

`tcg.commands.prove.run()` was reworked to invoke `kprove` once per goal
claim (same assembled trusted-children lemmas each time, one module per
claim), classify each log independently, write Accept evidence only for
individually-accepted claims, and aggregate the loop's state as: any Refute
→ Refuted, else any Unknown → Unknown, else Accepted. This is a ~137-line
change in `tcg/commands/prove.py`'s `run()` function (measured via `git
diff -U0`, isolated from the classify()-only changes) — N× `kprove` startup
cost, accepted for correctness (a single stuck/refuted claim can no longer
mask a sibling's genuine result, and evidence/graph edges, which are
per-claim data, can no longer be written from a run-wide verdict that
doesn't actually apply to every claim in it).

**Single-claim Accept** (`workspace-demo3`, `provable.k`'s body as `main`):

```
Accept: demo/main (0 trusted child(ren), 16.318s)
Accept: demo (1 claim(s): 1 accepted, 0 refuted, 0 unknown)
```
exit **0**. `evidence/replay/9314552e....json` written; loop state `Accepted`.

**Single-claim Unknown(b)** (same workspace, `"replay":{"timeout_seconds":3}`,
same claim — its real proof time is ~16s, so 3s reliably times out):

```
Unknown(b): demo/main — refusal; log: .../.tcg/logs/demo-main-prove.log
Unknown: demo (1 claim(s): 0 accepted, 0 refuted, 1 unknown)
```
exit **2**. Loop state `Unknown`.

**Two-claim loop, mixed verdict** (`workspace-demo2`, `iface.json` declaring
both `main` (`provable.k`'s true claim) and `broken` (the false `<pc> 0 =>
999` claim) as goal claims of the *same* loop):

```
Accept: demo/main (0 trusted child(ren), 16.2s)
Refute: demo/broken — prover left a residual goal; witness log: .../.tcg/logs/demo-broken-prove.log; backend crash report: .../.tcg/logs/demo-broken-kore-exec.tar.gz
Refute: demo (2 claim(s): 1 accepted, 1 refuted, 0 unknown)
```
exit **3** (`Exit.REFUSED`, matching the aggregate). Verified directly on
disk, not just from the printed summary:

- `evidence/replay/` contains **only** `main`'s claim hash
  (`9314552e....json`) — `broken`'s hash never gets an evidence file.
- `.tcg/logs/` contains two separate per-claim logs
  (`demo-main-prove.log` = 5 bytes, `#Top`; `demo-broken-prove.log` = the
  crash+trailer Refute log) **and** the collected crash artifact
  (`demo-broken-kore-exec.tar.gz`, 604KB) sitting next to `broken`'s log —
  confirming §5's crash-collection wiring works through the real CLI, not
  just in isolated `kprove` calls.
- `.tcg/build/` contains two separate single-claim spec modules
  (`demo-main-prove.k`, `demo-broken-prove.k`), each `grep -c '^\s*claim
  \['`-verified to contain exactly one claim.
- Loop state: `Refuted`.

**Unknown(c) with the actionable hint, through the real CLI** (fresh
workspace, `underspecified-true.k`'s claim body as the loop's only claim):

```
Unknown(c): demo/main — refusal — residual implication undischarged — claim may need more concretized cells; see log; log: .../.tcg/logs/demo-main-prove.log
Unknown: demo (1 claim(s): 0 accepted, 0 refuted, 1 unknown)
```
exit **2**. Confirms §4c's hint text reaches the actual printed message, not
just the unit-tested `classify()` return value.

All of Accept / Refute / Unknown(b) / Unknown(c)-with-hint, and the
aggregate-over-mixed-verdicts behavior specifically called for in the
review, are demonstrated through the actual shipped CLI on this worktree's
code, not simulated.

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

**Exit 0, `#Top`.** This is byte-identical to `tests/control/logs/provable.log`
(confirmed with `diff`), so no separate log file is committed for the ghost
run — see `provable.log` itself.

**Not done** (out of scope for gate G1, flagged as open): no claim was
written that actually *exercises* the ghost cells (e.g. a CALL-reentrancy
scenario checking `<inFunc>`/`<callCounter>` update correctly) — this only
confirms the patch applies, kompiles, and doesn't break an unrelated proof.
Validating the ghost monitor's own semantics is future work.

## 8. Wall-times summary

| step | wall time |
|---|---|
| discover + copy prebuilt unpatched definition | a few minutes (investigation) + seconds (copy) |
| single trivial `kprove` run (provable / underspecified-true / refutable-structural) | 15-20s |
| single trivial `kprove` run (refutable, more search + backend crash/recovery) | ~30-40s |
| ghost patch: `patch -p1` apply | instant |
| ghost patch: `kompile --backend haskell` (Haskell target only) | **≈4 minutes** |
| ghost patch: trivial claim re-proof | ~15-20s |
| full `tcg` CLI pipeline, one verdict (init → prove), single claim | well under a minute (excluding the `kprove` run itself) |
| full `tcg` CLI pipeline, 2-claim loop (per-claim invocation) | ~2× a single claim's `kprove` wall time (N× startup, by design — §6a) |

No build in this pass took anywhere near the 1-2 hour envelope the brief
budgeted for — the unpatched definition didn't need building at all, and the
patched one only needed the Haskell (proving) target, not the full
LLVM+Haskell dual build.

## 9. What remains open

- **Arithmetic/logical postcondition defects surface as Unknown, not Refute
  (§4d)** — the substrate's most important remaining limit. Lifting it needs
  structured per-claim counterexample extraction (`kore-rpc`
  `implies`/`get-model`, or `pyk`'s `APRProof` machinery) instead of reading
  `kore-exec`'s pretty-printed warning text. Not attempted here; this is the
  roadmap item that actually moves the needle past what text-classification
  of `kprove`'s stdout/stderr can ever achieve.
- **`--depth`/iteration-bound ambiguity (§4b)**: no known fix using log text
  alone; not reachable today since `prove.py` doesn't pass `--depth`, but
  pinned with a regression test so it can't be silently shipped later.
- **Krypto/ECRECOVER backend crash (§5)**: a real Haskell-backend limitation
  on this K/kore-exec version, not a `tcg` bug; recovers to a correct verdict
  every time observed, and crash artifacts are now collected into
  `.tcg/logs/` instead of polluting wherever `tcg` was invoked from.
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
- **`scripts/build-kevm.sh`'s ambiguity-refusal paths are only tested via the
  "zero candidates" and version-mismatch cases** (§1) — this machine only
  ever has one real candidate definition and one real candidate source tree,
  so the ">1 candidate, refuse and list them" branches are exercised by code
  review, not by an actual multi-candidate machine state.
