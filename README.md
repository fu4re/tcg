# tcg

A CLI for building and verifying **proof-carrying bundles** for EVM contracts.

A bundle packages, in one content-addressed tree: the deployed runtime bytecode,
a set of formally proved reachability claims over it, the composition graph that
connects them, the vendored formal semantics they were proved against, and the
evidence needed to re-run every proof. A third party with the bundle — and no
trust in its author, tooling, or the session that produced it — re-establishes
the guarantee mechanically: `tcg verify` replays every proof in topological
order and refuses the certificate on any failure.

The format is specified in [docs/bundle-spec.md](docs/bundle-spec.md).

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

v0, under active development. The command surface above is scaffolded; commands
land incrementally. The bundle format spec is stable at v1.

## Requirements

Python 3.12+, no runtime dependencies. Proving requires a pinned K / KEVM
toolchain (see `toolchain.lock` in a scaffolded workspace); verification of a
bundle requires only Docker.
