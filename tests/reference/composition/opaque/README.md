# opaque callee fixture — the STUB branch (Mechanism B)

The smallest opaque callee for the composition E2E's **typed-stub** leg. A caller
invokes this contract's single external entry point at an address it does **not**
own and does **not** prove; it discharges that external `CALL` with a *named,
typed assumption* (Mechanism B of `COMPOSITION_CONTRACT.md`) recorded in the trust
ledger — never a silent pass. This directory carries the callee's source, the
exact compile invocation, its pinned runtime bytecode, and the human-language
*typed frame* the STUB branch records.

This is a **fixture**, not a realistic contract. It exists only to give the STUB
branch a concrete pinned runtime and a frame to enumerate.

## Files

| file | role |
|---|---|
| `OpaqueNotify.sol` | the source: one external `hook()` that mutates the callee's OWN storage counter |
| `runtime.hex`      | the runtime bytecode, hex, one line — consumable by `tcg subject set --runtime` |
| `README.md`        | this file: provenance, exact solc invocation, typed frame |

## Provenance — exact solc invocation

Compiler: `/opt/homebrew/bin/solc` — `solc, Version: 0.8.35+commit.47b9dedd.Darwin.appleclang`
(the repo's pinned canonical core; verify with `solc --version`).

```
cd tests/reference/composition/opaque
/opt/homebrew/bin/solc --bin-runtime --optimize --optimize-runs 200 \
    --evm-version shanghai --metadata-hash none OpaqueNotify.sol
```

- `--bin-runtime` — emit the deployed (runtime) bytecode, i.e. what lives at the
  callee address and is executed on a `CALL`. (NOT the creation/init bytecode.)
- `--evm-version shanghai` — match the callext reference environment
  (`tests/reference/callext/tcg/subject/environment.json`, `fork: Shanghai`).
- `--metadata-hash none` — strip the nondeterministic IPFS metadata hash so the
  runtime is byte-reproducible across machines/paths. The trailing
  `a164736f6c6343000823000a` that remains is only the stable solc-version CBOR
  (`solc` `0.8.35`), fixed by the pinned compiler.
- `--optimize --optimize-runs 200` — standard settings; keep the runtime small.
  These settings are part of the reproducible invocation: changing them changes
  the bytes.

Re-running the command above prints the exact contents of `runtime.hex`.

## Derived identity (computed, not asserted)

Computed with `tcg.keccak` over `runtime.hex`:

- runtime length: **121 bytes** (242 hex chars)
- `keccak256(runtime)` = `547a6447572440e47d4457dddf4a1b9c232ee8291b515aab464bb168b801fa57`
  — this is the `code_hash` a caller node would declare for this callee address,
  and (in the linker form) the `keccak256` the verifier recomputes from the
  vendored dep's `subject/runtime.bin`.
- external entry: `hook()` → selector `7f5a7c7b` (present in the runtime dispatch
  as `…80637f5a7c7b14…`).

## Typed frame (the load-bearing STUB assumption)

This is the **human-language typed frame** the STUB branch records verbatim in
`spec/graph.json`'s `assume.frame` and mirrors into `trust-manifest.json` under
`ledger_id` (e.g. `A_callee_0x…`). It is **conservative by default**: it grants
the callee only the two bounds the caller's proof actually needs, names them as
*author-chosen, load-bearing* assumptions, and leaves everything else
unconstrained. Because the callee is opaque (its code is not proved here), every
grant below is an ASSUMPTION, not a theorem.

> **Frame `A_callee_<addr>` — opaque callee `OpaqueNotify` at `<callee_address>`.**
>
> **Storage-frame (load-bearing):** the callee MUST NOT write, and is assumed not
> to write, **any storage of the caller's account**. Its writes are confined to
> its OWN account's storage (here, a single counter slot). The caller's storage
> is therefore unchanged across the external `CALL`. *(This is what lets the
> caller keep its own storage invariants across the call without proving the
> callee.)*
>
> **Reentrancy (load-bearing):** the callee MUST NOT, and is assumed not to,
> **reenter the caller** — no nested `CALL`/`CALLCODE`/`DELEGATECALL`/`STATICCALL`
> back into the caller (directly or transitively) before it returns. The caller's
> intermediate state is therefore never observed or mutated mid-call.
>
> **MAY (unconstrained — NOT assumed away):** the callee may revert / run out of
> gas (the caller must handle a failed `CALL`); may consume an arbitrary amount of
> the forwarded gas; may write its own storage arbitrarily; may return arbitrary
> output data; may emit logs. None of these are assumed to be benign — the caller
> must not depend on any of them.
>
> **Status:** `assumed-callee (AUTHOR-CHOSEN, load-bearing)` — NOT discharged over
> the callee's code. Surfaced in the `⚠` section of `tcg verify` and refused by
> `tcg verify --strict`.

### Why these two bounds, and why conservative

An opaque callee could, in the worst EVM case, write the caller's storage (via a
`DELEGATECALL` misuse the caller set up) or reenter. The safe posture is to assume
it does the worst *unless the frame explicitly fences it*. The two fences above
are exactly the planks a caller-side proof leans on when it does not prove the
callee; naming them as load-bearing assumptions (rather than silently relying on
them) is the entire point of the STUB branch. A caller that needs a tighter grant
(e.g. "the callee returns success", "the callee increments a specific counter")
must either widen this frame — making the assumption bigger and still named — or
switch that leg to REUSE/RECURSE and actually prove it.
