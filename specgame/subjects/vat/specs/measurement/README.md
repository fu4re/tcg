# Vat measurement specs (protocol v3, not a ladder)

`vat_measure.sol` holds one check of each kind, used to measure Check v2 on
the Vat subject before the Vat ladder is built (step 2):

| Check | kind | 60 000 ms / 600 s | 300 000 ms / 1500 s |
|---|---|---|---|
| `check_suck_needs_auth` | must-revert auth | Accept, 3.5 s | Accept, 3.9 s |
| `check_frob_conserves_collateral` | linear per-transition on frob (2 asserts) | Unknown (unproved), 123.3 s | Unknown (unproved), 603.4 s |
| `check_two_dai_balances_within_debt` | global invariant over two keys | Unknown (unproved), 61.8 s | Unknown (unproved), 302.1 s |

`check_60000ms.json` and `check_300000ms.json` are the full `check.py --json`
outputs (exact solc inputs and raw outputs), run with `--no-cache`, 4 workers:

    python tools/check.py subjects/vat/specs/measurement/vat_measure.sol --subject vat --no-cache \
        [--timeout-ms 300000 --wall-timeout-s 1500] --json <out>

## Historical note: engine probe (BMC: deprecated upstream, not used)

**BMC: deprecated upstream, not used.** Per the author's decision (2026-11-02), the SMTChecker BMC
engine is deprecated in recent solc releases and is not used in any protocol version; CHC is the
only engine. The numbers below were measured before that decision and are kept only as a record.

`engine_probe.py` (output `engine_probe.json`) runs each check's isolated
harness with SMTChecker engine `bmc` and `all` at the frozen per-query
timeout (60 000 ms), reading solc's per-target messages directly (the core's
classifier accepts only CHC results, by protocol):

    python -I -B subjects/vat/specs/measurement/engine_probe.py <out.json>

| Check | engine `chc` (protocol) | engine `bmc` | engine `all` |
|---|---|---|---|
| `check_frob_conserves_collateral` | Unknown (unproved), 123.3 s | **both asserts safe, 2.3 s** | CHC might happen ×2, BMC safe ×2, 124.9 s |
| `check_two_dai_balances_within_debt` | Unknown (unproved), 61.8 s | violation "happens here", 1.1 s | CHC might happen, BMC happens here, 62.7 s |
| `check_suck_needs_auth` | Accept, 3.5 s | safe, 1.2 s | CHC safe (BMC not re-run on a CHC-proved target), 3.9 s |

What was observed: BMC (each function from an unconstrained state) reported
the frob check safe in 2.3 s and a spurious violation of the global
invariant (from an unreachable state). This does not change any protocol:
CHC remains the only engine, and the frob check stays Unknown under the
protocol.

## κ over the havoc base (protocol v3, struct mappings supported)

`kappa.json`: `python tools/kappa.py subjects/vat/specs/measurement/vat_measure.sol --subject vat`
gives κ = 4 of 4 asserts (determined): the two frob asserts and the
two-balance invariant are unproved over H (non-tautological), the must-revert
assert of `check_suck_needs_auth` is violated over H (its `suck` is a no-op
there), so none is a tautology. Check over H took 121 s, 60 s and 61 s per
check (in parallel, 122 s wall).
