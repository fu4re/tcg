# Control spec (c): UNDECIDED

Unlike (a)/(b), "undecided" is not a property of the claim text — it is a
property of the *prover budget*. Both variants below reuse `provable.k`
verbatim (a claim that genuinely *is* provable) and force the prover to give
up before it can finish.

## (c1) Wall-clock timeout — the mechanism `tcg prove` actually uses

`tcg.commands.prove.run()` never passes a depth/iteration flag to `kprove`;
it wraps the whole `kprove` invocation in `subprocess.run(..., timeout=...)`
using `toolchain.lock`'s `replay.timeout_seconds`. Proving `provable.k` takes
~15-20s on this machine, so a 2s wall-clock budget reliably times out mid-run.

Reproduced directly (bypassing tcg, same subprocess pattern):

```
python3 - <<'PY'
import subprocess, time
argv = ["kprove", "tests/control/provable.k",
        "--definition", "~/toolchains/kevm-1.0.678/haskell",
        "--spec-module", "STOP-EVM-SPEC",
        "-I", "~/toolchains/kevm-1.0.678/evm-semantics-source",
        "-I", "~/toolchains/kevm-1.0.678/plugin"]
try:
    subprocess.run(argv, capture_output=True, text=True, timeout=2)
except subprocess.TimeoutExpired as e:
    print("timed_out", e.stdout, e.stderr)
PY
```

Result: `subprocess.TimeoutExpired` after 2.0s, `e.stdout`/`e.stderr` both
empty (kprove had not flushed any output yet). See
`logs/undecided-timeout.log`. In `tcg prove`, this sets `timed_out=True`,
and `classify()` returns `("Unknown", "b")` unconditionally on that flag —
confirmed end-to-end through the real CLI (see docs/substrate.md, "Task 5").

## (c2) `--depth` bound — a secondary finding, NOT how tcg invokes kprove today

```
kprove tests/control/provable.k --definition ~/toolchains/kevm-1.0.678/haskell \
  --spec-module STOP-EVM-SPEC \
  -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
  -I ~/toolchains/kevm-1.0.678/plugin \
  --depth 1
```

Result: exit 1. The log (`logs/undecided-depth-bound.log`) ends with the
**exact same** phrase used for genuine refutation:

```
[Error] Prover: backend terminated because the configuration cannot be
rewritten further. See output for more details.
```

Real `kprove` (Haskell backend, this K version) does not emit a distinct
"depth bound"/"iteration bound"/"max iterations" phrase when `--depth` is
hit — from the backend's perspective, "ran out of steps" and "no more rules
apply" both terminate the search the same way, with the same message. This
means `classify()`'s `"depth bound" / "iteration bound" / "max iterations"`
branch (`tcg/commands/prove.py`, the `Unknown, "a"` case) is currently dead
code for the real backend: nothing it can observe would ever hit that
branch, and if `--depth`/`--branching-allowed` were ever added to
`prove.py`'s `kprove` invocation, a genuinely-inconclusive bounded run would
be misclassified as `Refute` (a defect found) rather than `Unknown`. Today
this is **not reachable** — `prove.py` never passes `--depth` — so no code
fix is proposed for it; it is recorded here as a documented latent risk. See
docs/substrate.md, "classify() validation" for the full discussion and
`tests/test_classify.py::test_depth_bound_is_indistinguishable_from_refute`
for a regression pin.
