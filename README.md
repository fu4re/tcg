# tcg

A CLI for building and verifying **proof-carrying bundles** for EVM contracts.

A bundle packages, in one content-addressed tree: the deployed runtime bytecode,
a set of formally proved reachability claims over it, the composition graph that
connects them, the pinned formal semantics (KEVM) they were proved against, and
the evidence needed to re-run every proof. A third party with the bundle — and no
trust in its author, tooling, or the session that produced it — re-establishes
the guarantee mechanically: `tcg verify` replays every proof in topological
order and refuses the certificate on any failure.

The format is specified in [docs/bundle-spec.md](docs/bundle-spec.md).
The agent-facing audit workflow (driving tcg end-to-end on a subject) is packaged as the [tcg-evm-audit skill](.claude/skills/tcg-evm-audit/SKILL.md).
The research record lives in [docs/findings/](docs/findings/) (numbered, immutable, negative results included) and in the companion repository of the June 2026 source-level pilots (`sheaf`, SMTChecker + Lean).

## What has been established (as of 2026-08-28)

Every "proved" below is a prover verdict reproduced from committed sources; see the Finding for the exact command, the honest caveats and what remains open.

| Finding | Result |
|---|---|
| [0001](docs/findings/0001_reference_bundle_e2e.md) | First end-to-end bundle on the KEVM Haskell backend: 3 claims Accept, a drain variant structurally Refuted, 5/5 conformance controls refuse tampered bundles |
| [0002](docs/findings/0002_false_green_vacuity_program_binding.md) | A blind agent obtained `Accept` on a claim bound to no bytecode and asserting nothing. Closed by root program binding and an antecedent-reachability vacuity probe; residual false-green surface listed |
| [0003](docs/findings/0003_gemjoin_blind_battle_audit.md) | Blind agent audit of live MakerDAO GemJoin ETH-A (3,462-byte on-chain runtime, ~$515M): 7 revert/authorisation properties, 5 in a bundle re-verified independently; coverage complementary to k-dss |
| [0003a](docs/findings/0003a_getter_partial_coverage.md) / [0003b](docs/findings/0003b_getter_full_coverage.md) | GemJoin getters proved to the full k-dss behaviour (side-effect-free and exact return value), wrong-slot discriminators refuse |
| [0004](docs/findings/0004_simplification_lemmas.md) | KEVM's own 287 `[simplification]` rules vendored as `theory/patches/lemmas.diff`; a mandatory consistency control (known-false identities must not prove); named in the trust ledger as not provably closed |
| [0005](docs/findings/0005_callsite_summary_probe.md) | Raw `kprove` applies an injected callee summary at an unresolved `CALL`; no driver migration needed |
| [0006](docs/findings/0006_callsite_composition_frontier.md) | Call-site composition: bridge `S ⟸ D` with anti-proxy binding (7/7 tampers refuse); WETH9 `transfer`/`transferFrom` and `Vat.slip` proved over the real mainnet bytecode (on branches `p1-c-weth`, `p1-b-vat-slip`); §4's "substrate ceiling" corrected to a claim-shape bug |

Cross-bundle reuse (REUSE) and typed callee assumptions (STUB, surfaced by `verify` as `⚠` and refused under `--strict`) landed on 2026-08-20; see bundle-spec §5b–5c and `tests/reference/composition/`.

Not done, honestly: the `join`/`exit` caller composition over the proved callee legs; vendoring the semantics into the bundle (today it is pinned by version and patch hash); proof objects (verify re-proves every claim, ~28 s each); a load-bearing (weak-postcondition) vacuity probe.

## Design rules

- **The prover is the judge.** "Proved" and "refuted" verdicts come from the
  prover, never from this tool's own reasoning. A refutation carries a concrete
  counterexample; an inconclusive result ("unknown") is a refusal, never a pass.
- **Freeze and verify are separate paths.** `verify` reads only the bundle,
  never the workspace. This keeps the guarantee transferable: what the verifier
  checks is exactly what the bundle carries.
- **Format cheaper than the tool.** All structural checks are JSON + SHA-256 and
  are re-implementable in an evening. A verifier does not have to trust `tcg`
  itself — only the prover and the semantics.

## Commands

```
tcg init                  # scaffold a workspace + pinned toolchain.lock
tcg status                # workspace overview: loop states, graph, oracle, subject, next-step hints
tcg loop new <name>       # create a loop workspace
tcg iface set <loop>      # set the loop interface (Pre, Post, Exit, footprint, rely, guar)
tcg compile-claims <loop> # compile the interface into canonical claims (+ round-trip check)
tcg approve               # human sign-off: oracle record over current root hashes
tcg prove <loop|junction> # run the prover; verdict is Accept / Refute / Unknown
tcg vacuity <loop>        # antecedent-reachability probe: refuse vacuous (empty) proofs
tcg junction <i> <j>      # consequence claim: Post_i implies Pre_j
tcg compat <i> <j>        # interference obligation: Guar_j implies Rely_i
tcg graph check           # structural checks on the claim DAG
tcg subject set           # install subject/runtime.bin (+ subject/environment.json)
tcg freeze                # assemble the bundle: hash tree + MANIFEST
tcg verify <bundle>       # full verifier protocol on a bundle (bundle-only input)
tcg roots <bundle>        # render the root claims for human reading
```

Exit codes are uniform across commands: `0` success, `1` usage error,
`2` unknown / could not verify, `3` refuted / check failed. "Could not verify"
never shares an exit code with "found a defect".

## Status

v0, research prototype. All commands above are implemented and exercised by the
Findings; the bundle format spec is stable at v1. Soundness holes found so far
are recorded as Findings, not silently fixed.

## Requirements

Python 3.12+, no runtime dependencies (`pip install -e .`). Proving **and**
verifying both need the pinned K / KEVM toolchain on the machine: K v7.1.337,
kore-exec 0.1.155, KEVM 1.0.678 (kompiled Haskell backend with the two vendored
patches applied), z3 4.16.0. `scripts/build-kevm.sh` obtains and pins it under
`~/toolchains/`; `tcg init` records the paths and patch hashes in
`toolchain.lock`. A bundle does not yet carry the semantics, so a verifier
without this toolchain cannot replay it (Finding 0001, caveat 2). A container
image for verification is planned, not shipped.

## Reproduce

Each script asserts exact exit codes and refuses on regression. Set
`TCG_PYTHON` if `python3` is not your 3.12 interpreter.

```
scripts/smoke.sh               # installed-CLI acceptance walk (init → … → verify → roots)
scripts/repo-checks.sh         # patch parity + bundle-only import guard
scripts/build-reference.sh     # Finding 0001: reference bundle, 3 Accepts + drain Refute
scripts/conformance.sh <b>     # bundle-spec §9 controls on a copy of a frozen bundle
scripts/false-green.sh         # Finding 0002: both G3 false greens now refused
scripts/lemma-consistency.sh   # Finding 0004: known-false identities must not prove
scripts/build-getters-full.sh  # Finding 0003b: GemJoin getters, full k-dss behaviour
tests/reference/callext/run-tcg-linker-discriminators.sh   # REUSE, real prover
tests/reference/composition/run-stub-e2e.sh                 # STUB, real prover
python3 -m unittest discover -s tests                       # 91 unit tests
```

Prover logs that back each Finding are committed under `tests/control/` and
`tests/reference/**/logs/`; they contain the original machine's absolute paths.

## License

MIT, see [LICENSE](LICENSE). The vendored patches under `theory/patches/`
modify KEVM (BSD-3-Clause, Runtime Verification); the four simplification
submodules in `lemmas.diff` are KEVM's own.
