# pilot/checker -- the variant-A KEVM checker image

The pinned `Check'` for the bundle's KEVM claims (DECISIONS D6). It is a linux/amd64 docker image that contains `kprove` and a kompiled KEVM definition with the lemma patches baked in. The image is identified **by image Id**, never by tag. Current pin and results: [STATUS.md](STATUS.md).

## Naming: KEVM is identified by commit, not by "1.0.678"

The KEVM this repo calls "1.0.678" (`tcg/commands/init.py` `TOOLCHAIN["kevm"]`, `kevm version`, the nix package `kevm-pyk-1.0.678`) is **`runtimeverification/evm-semantics` @ `d4bf484a5dfe1e38d729a30434cd6f41e3590fb2`, tag `v1.0.921`**. At that commit, `kevm-pyk/pyproject.toml` says `1.0.921`, while `kevm_pyk/__init__.py` still carries a stale `VERSION = '1.0.678'`, which is what every tool prints. The laptop's kontrol flake (`0ac55eda`, kontrol 1.0.255) locks exactly this commit. The trusted base (T̂) and the image labels therefore name the **commit**, never the version string. Evidence (`diff -rq` against the laptop toolchains, tarball hashes) is in [STATUS.md](STATUS.md).

## What the image contains

| Path in image | What | Pinned by |
|---|---|---|
| base layers | RV's K image `runtimeverificationinc/kframework-k:ubuntu-jammy-7.1.337`: `kprove`, `kompile`, Haskell backend, z3 | base digest `sha256:a63698c0…b12b`; K commit `4a46d123…` (tag v7.1.337) |
| `/opt/kevm/evm-semantics-source/` | KEVM K sources from `evm-semantics` @ `d4bf484a…` (tag v1.0.921, self-reported as KEVM "1.0.678") + `ghost.diff` + `lemmas2.diff` | tarball sha256, patch sha256s (Dockerfile ARGs) |
| `/opt/kevm/plugin/plugin/krypto.md` | `blockchain-k-plugin` @ `207ae512…` `plugin/` | tarball sha256 |
| `/opt/kevm/haskell/` | the kompiled Haskell-backend definition, main module `LEMMAS-DRIVER` (EDSL + six simplification-lemma submodules, including lemmas2's `BOOL2WORD-` and `MAP-REASONING-SIMPLIFICATION`) | the image Id; `definition.kore` sha256 in `/opt/kevm/provenance.json` |
| `/opt/kevm/inputs/` | the downloaded tarballs and the two patches, as verified | sha256 |
| `/opt/kevm/provenance.json` | K/z3 versions, every rev and sha above, `definition.kore` sha256 | |
| `/opt/kevm/MANIFEST.sha256` | sha256 of every file under `haskell/`, `evm-semantics-source/`, `plugin/` | |

`definition.kore` is not byte-deterministic across kompiles. **Do not rebuild the image to check it.** A rebuild from this Dockerfile yields an equivalent checker under a different Id. Load the producer's exact image and compare its Id.

## Checker note for A3 (trusted base): z3 4.12.1, not 4.16.0

The image's SMT solver is **z3 4.12.1** (`z3 --version` inside the image, captured in `/opt/kevm/provenance.json`), shipped by RV's K v7.1.337 image. The repo toolchain pin in `CLAUDE.md` (z3 4.16.0) is for the Solidity/SMTChecker side of `cycle/`, not for kprove. The checker that re-discharges KEVM claims is therefore K v7.1.337 + Haskell backend + z3 4.12.1, and T̂'s A3 entry must name that, not 4.16.0. **The solver differs from the producer's.** The laptop's nix kprove (`k-7.1.337-4a46d123`) is wrapped to `/nix/store/761igaxf…-z3-4.13.4` (`grep` of the `kprove`/`kore-exec` wrappers; `z3 --version` → 4.13.4). The August/getters-full Accepts were produced under z3 4.13.4, and this image re-discharges under z3 4.12.1. The smoke results in STATUS.md are the empirical check that the getter claims still Accept under 4.12.1. For any claim that does not, the z3 difference is the first suspect, not the claim.

## Consumer: load, check identity, run one claim

```bash
docker load -i tcg-kevm-checker.tar
```

```bash
docker image inspect --format '{{.Id}}' <PINNED_IMAGE_ID>
```

The output must equal the pinned Id (`checker[kevm-prove].hash` in the bundle's trusted base, also in `IMAGE_ID`). Then run one claim with one command:

```bash
TCG_CHECKER_IMAGE_ID=<PINNED_IMAGE_ID> pilot/checker/run-claim.sh claims/vat-vat-prove.k --spec-module VAT-VAT-PROVE
```

`run-claim.sh` refuses to run unless the local image's Id equals the pin. It then runs, with `--network none --memory=6g --cpus=2`:

```
kprove <claim.k> --definition /opt/kevm/haskell --spec-module <MODULE> \
  -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin [extra args]
```

On the pilot VM, every call must hold a prover slot (3 VM-wide, shared with WS-H): `~/pilot-locks/with-slot.sh prover -- pilot/checker/run-claim.sh …`. `run-claim.sh` does not lock itself, because a nested lock under an outer wrapper would take two slots and can deadlock.

This is the argv `tcg prove` uses (`tcg/commands/prove.py`). Exit status and output are kprove's own. **Accept iff exit 0 and stdout contains `#Top`** (`tcg/verdict.py`). Anything else is not Accept: `Refute` if kprove reports a residual that "cannot be rewritten further", otherwise `Unknown`. The script judges nothing.

## Producer: build and pin (VM only, once)

```bash
pilot/checker/build.sh
```

This writes `~/pilot-checker/{context/,build.log,tcg-kevm-checker.tar,pins.json}` and `pilot/checker/IMAGE_ID`. Then:

```bash
pilot/checker/smoke.sh
```

This re-proves the six getters-full claims (expect Accept) and the three wrong-slot discriminators (expect not Accept) and writes `~/pilot-checker/smoke/results.tsv`.

## Files

- `Dockerfile`: the image recipe (every input checked by sha256).
- `patches/ghost.diff`: copy of `theory/patches/ghost.diff`.
- `patches/lemmas2.diff`: `git show p1-b-vat-slip:theory/patches/lemmas.diff`.
- `build.sh`: build + pin. `run-claim.sh`: the verifier's single entry point. `smoke.sh`: smoke test.
- `smoke/specs/`: the tcg-assembled getter prove specs + `tests/control/getters-full/wrong-slot.k`.
- `IMAGE_ID`: written by `build.sh`.
