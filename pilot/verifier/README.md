# tcg bundle verifier — for a consumer who has only the bundle

This directory checks a `tcg-bundle/0.1` bundle and writes `ladder.json`: one entry per level, L0–L4. By design it gives **no overall verdict**. A level that could not be checked says so; it is never reported as passed.

## What you need
- The bundle directory (it has `manifest.json` at its root), and this `verifier/` directory.
- The **producer** public key and the **oracle** public key, as PEM files (`openssl pkey -pubout` output), obtained from their owners through a channel you trust, **not** from inside the bundle.
- A chain source of your own: an archive-node JSON-RPC URL (`--rpc`), or a state snapshot you produced yourself (`--state-snapshot <dir>` containing `snapshot.json`; format in `pilot/schema/README.md`). Never use a snapshot shipped with the bundle.
- `python3` ≥ 3.12. Stdlib only, nothing to install, nothing to build.
- Variant A (KEVM): `docker`, plus the checker image whose digest `trusted_base.json` names under `checker` → `kevm-prove`. If it is not loaded, the verifier tries `docker pull` of that entry's `image`. A tarball from the producer works too: `docker load -i <file>`. The verifier compares the image's digest with the trusted base before running anything.
- Variant B (Lean): `elan` with the toolchain named in the bundle's `lean-toolchain` (`elan toolchain install <name>`). `lake` may download the dependencies listed in `lake-manifest.json`; each one is reported under `outside_bundle`.

## 1. Check that this verifier is the one the bundle names
Compute the verifier's hash **without running its code**. Run this from inside `verifier/` (on macOS, replace `sha256sum` with `shasum -a 256`):

<!-- self-hash-recipe -->
```sh
{
  printf '['; sep=''
  for f in verify.py $(LC_ALL=C ls tcgverify | grep -E '\.(py|json)$' | LC_ALL=C sort | sed 's|^|tcgverify/|'); do
    printf '%s["%s","%s"]' "$sep" "$f" "$(sha256sum "$f" | cut -d' ' -f1)"; sep=','
  done
  printf ']'
} | sha256sum | cut -d' ' -f1
```

The result must equal the `hash` of the `checker` entry named `tcg-verifier` in the bundle's `trusted_base.json`. Also confirm that this file is the one the signed manifest lists: `sha256sum trusted_base.json` must equal that child's `hash` in `manifest.json`. `python3 verify.py --self-hash` prints the same value, and L1 re-checks it. The hash covers `verify.py` and `tcgverify/*.py|*.json` only; this README, `STATUS.md` and `tests/` are excluded.

A match means only that you are running the code the producer named. It does not mean the code is correct. The code is about 1,700 lines of stdlib Python; read it, especially `tcgverify/levels.py`.

## 2. Run it, as an unprivileged user with no access to anything you care about
By default the verifier executes scripts and commands that come from the bundle: L2 runs `evidence/**/replay.sh`, and L4 replays recorded commands. `--no-exec` turns all of that off; the affected fields then say "not run".

```sh
python3 verify.py <bundle-dir> --producer-pubkey producer.pub.pem --oracle-pubkey oracle.pub.pem \
    --rpc https://<archive-node> --variant A --out ladder.json
```
`--variant B` checks only Lean certificates and never starts docker. `--docker-limit=--memory=6g --docker-limit=--cpus=2` caps each KEVM container (only `--memory` and `--cpus` are accepted). Exit status 0 means the verifier ran to completion, whatever the levels say; 2 means a usage or input error.

## 3. Read ladder.json
- **L0, identity and environment:** recomputed `root_hash`, the producer signature under *your* key, every child's bytes, and the artefact's keccak256 compared with the code the chain holds at the pinned address and block, all read by the verifier itself. Also the chain id, the fork (derived from the block), and each external contract's code hash.
- **L1, proof:** one result per claim: `accept`, `refute`, `unknown`, `not_accept`, `checker_hash_mismatch`, `checker_unavailable`, `malformed` or `not_checked`. `refused` is the status when the bundle's assumption ledger is empty or does not cover its annotations. A KEVM `refute` is a symbolic stuck state, not a concrete counterexample. KEVM claims are re-discharged by an external pinned prover, so `self_contained` is `false`.
- **L2, evidence about φ, reported and not judged:** coverage of requirements by claims in both directions; each requirement is `covered`, `partial` (claimed, but the producer declares what is not proved) or `blind` (no claim), and `total` is true only if every requirement is covered; back-translation, mutant witnesses (`refute`, `concrete_trace_violation` and `not_accept` are kept distinct; `no_witness` lists claims no mutant tests), and the pre-state witness.
- **L3, approval:** whether the oracle key, and not the producer key, signed `sha256(phi.json) ‖ sha256(requirements.md)` for exactly the φ that was proven. The approved and proven hashes are both shown.
- **L4, provenance:** whether the ledger chain is intact, plus `counts` of deterministic events: replayed and matched, replayed with a mismatch, not replayable because they touch a path outside the bundle (each listed with its paths, never a pass or a mismatch), skipped by you (`--l4-skip-provers` skips recorded prover/container runs, which can take hours), and not replayed for another reason. Any non-replayed event makes L4 `partial`. An outside input recorded with a hash that a bundle file matches byte for byte is replayed from that file (`replayed_with_stand_ins`).
- **`outside_bundle`:** everything the result depended on that the bundle does not contain: the chain source, the docker image, the Lean toolchain and its dependencies, `sh`, and the replayed tools. Trust in those is yours to judge.

The manifest's `not_claimed` sentences hold no matter what the ladder says. In particular, the bundle does not claim that the artefact is secure, or that φ is complete.
