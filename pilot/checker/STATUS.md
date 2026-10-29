# WS-C checker image -- STATUS

Last updated: 2026-10-29 ~13:55 UTC (session ws-c). Nothing committed or pushed.

## State: DONE (image built and pinned; smoke 9/9 as expected)

| Step | State |
|---|---|
| 1. docker on VM | installed by the user: Docker 29.1.3 (Ubuntu `docker.io 29.1.3-0ubuntu3~24.04.2`), server linux/x86_64, containerd image store (`io.containerd.snapshotter.v1`), no buildx (classic builder). vladimir is in group `docker` |
| 2. route | upstream RV K image pinned by digest + in-image kompile (below) |
| 3. build + pin | `pilot/checker/build.sh`: exit 0, **356 s** wall (4 vCPU VM, 2026-10-29 13:03 UTC) |
| 4. smoke | `pilot/checker/smoke.sh` on the 8 vCPU / 32 GB VM: **6/6 Accept, 3/3 wrong-slot NOT Accept** |
| 5. README + run-claim.sh | done; `run-claim.sh` passes `--network none --memory=6g --cpus=2` |

## Pins (checker identity)

| | value |
|---|---|
| **image Id** | **`sha256:7d4a35bc05dfdad97b244da3c75bb3c3e710be73713cac3ca1c5bb6226cdc465`** (`pilot/checker/IMAGE_ID`) |
| RepoDigests | `["tcg-kevm-checker@sha256:7d4a35bc…c465"]`: with the containerd store, the Id **is** the OCI manifest digest. Local only, not pushed to any registry |
| local tag | `tcg-kevm-checker:lemmas2` (convenience only, never an identity) |
| platform / size | linux/amd64, 1 320 740 476 bytes |
| `docker save` sha256 | `4fda05f85c32c470479ad24ba7605d6d209b34eeaa22e0ef51a60b4b01c6b772` (`~/pilot-checker/tcg-kevm-checker.tar`, 1 320 760 832 bytes) |
| `/opt/kevm/haskell/definition.kore` sha256 | `041aa516ccac29585bc5028fa2908dc2d4f0fae1fe27eceb04eb1c97e7e9a7ba` |
| `/opt/kevm/MANIFEST.sha256` sha256 | `388c1276e8d7a00fa85ef66e68f453248ed5e4cc6176bf1b98f7aab45d959e08` |
| `kprove --version` (in image) | `K version:    v7.1.337` |
| `z3 --version` (in image) | `Z3 version 4.12.1 - 64 bit` |
| base image | `runtimeverificationinc/kframework-k:ubuntu-jammy-7.1.337@sha256:a63698c015f2b349bb9807d486bf2a48a764237a018fd207c23ac7571519b12b` |
| full record | `~/pilot-checker/pins.json`, `~/pilot-checker/build.log`, `~/pilot-checker/context.sha256` |

`patch` was already in the base image (the Dockerfile's conditional apt step did nothing), so the build used no unpinned package fetch. All four inputs passed `sha256sum -c`, and both patches were dry-run before being applied. The `MAP-REASONING-SIMPLIFICATION` assertion passed.

## Smoke results

Command per claim (from `smoke.sh`, recorded in `~/pilot-checker/smoke/logs/<MODULE>.log.cmd`):

```
~/pilot-locks/with-slot.sh prover -- pilot/checker/run-claim.sh ~/pilot-checker/smoke/specs/<spec> --spec-module <MODULE>
  # inside: docker run --rm --platform linux/amd64 --network none --memory=6g --cpus=2 ... sha256:7d4a35bc…c465 \
  #   kprove /claim/<spec> --definition /opt/kevm/haskell -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin --spec-module <MODULE>
```

Verdict = `tcg/verdict.py` `classify()` (copied to `~/pilot-checker/smoke/verdict.py`, sha256 in `inputs.sha256`). Run 2026-10-29 on the 8 vCPU / 32 GB VM, sequential, one prover slot.

| spec | module | expected | exit | verdict | wall (s) |
|---|---|---|---|---|---|
| vat-vat-prove.k | VAT-VAT-PROVE | Accept | 0 | **Accept** (`#Top`) | 143.5 |
| vat-vat_g-prove.k | VAT-VAT-G-PROVE | Accept | 0 | **Accept** (`#Top`) | 127.6 |
| ilk-ilk-prove.k | ILK-ILK-PROVE | Accept | 0 | **Accept** (`#Top`) | 121.3 |
| ilk-ilk_g-prove.k | ILK-ILK-G-PROVE | Accept | 0 | **Accept** (`#Top`) | 121.7 |
| gem-gem-prove.k | GEM-GEM-PROVE | Accept | 0 | **Accept** (`#Top`) | 168.9 |
| gem-gem_g-prove.k | GEM-GEM-G-PROVE | Accept | 0 | **Accept** (`#Top`) | 168.5 |
| wrong-slot.k | WRONG-SLOT-VAT-SPEC | NOT Accept | 1 | **Unknown(c)** | 149.4 |
| wrong-slot.k | WRONG-SLOT-ILK-SPEC | NOT Accept | 1 | **Unknown(c)** | 127.3 |
| wrong-slot.k | WRONG-SLOT-GEM-SPEC | NOT Accept | 1 | **Unknown(c)** | 163.3 |

Raw table: `~/pilot-checker/smoke/results.tsv`. Logs: `~/pilot-checker/smoke/logs/`.

- The **getters Accept under lemmas2.** They do **not** need the older `-lemmas` definition, even though `scripts/build-getters-full.sh` defaults to it.
- **The discriminator holds.** All three wrong-slot modules end in `WarnStuckClaimState: … unifies with the destination's term, but the implication check between the conditions has failed`. The residual is exactly the wrong-slot equality, e.g. for VAT: `maxUInt160 &Int #lookup(STORAGE, 1)` vs `maxUInt160 &Int #lookup(STORAGE, 2)`. That is `Unknown(c)` in tcg's taxonomy, not Refute, which matches Finding 0003b's expectation ("NOT Accept (Unknown(c) or Refute), never #Top"). The lemma extension does not collapse distinct symbolic lookups.
- **Wall time.** 121–169 s per claim under `--cpus=2 --memory=6g`, versus about 28 s per claim on the laptop (task 08's figure, not re-measured here). The cause has not been investigated: it could be the CPU cap, an x86 VM vs Apple silicon, z3 4.12.1 vs 4.13.4, or kprove startup (definition load). This affects the L1 time estimate in `variants.md`, not soundness.
- **Earlier partial run.** It ran on the 4 vCPU VM before the hang, with no resource caps and other load present. It recorded VAT, VAT_G, ILK and ILK_G as Accept (158.0 / 210.5 / 207.5 / 282.0 s), then died with the VM during GEM. It is kept as `~/pilot-checker/smoke/results.pre-hang-4vcpu.tsv` + `logs.pre-hang-4vcpu/` and is superseded by the table above.

## Image vs laptop lemmas2 definition (structural, not a proof)

Same K source (see provenance). Compared `allRules.txt` of the image and the laptop's `~/toolchains/kevm-1.0.678-lemmas2/haskell/` (copies in `~/pilot-checker/{image,laptop-lemmas2}-allRules.txt`):

- module count 108 = 108; the simplification modules are identical (BITWISE, BOOL2WORD, BYTES, EVM-INT, GAS, INT, MAP-REASONING)
- 2939 = 2939 rules, 347 = 347 `simplification` rules, identical multiset of source locations
- 2928 / 2939 rule hashes identical. The **11 that differ** all sit on rules containing `#let … #in` (`evm.md:3083–3087` BLS12 gas rules; `lemmas/bytes-simplification.k:199–208` `range-memUpdate-*`), whose desugaring produces generated per-kompile names. This is the known `definition.kore` nondeterminism, and it is why the image Id, not a rebuild, is the identity.

## Checker note for A3: z3 differs from the producer

- image: z3 **4.12.1** (bundled with RV's K v7.1.337 Ubuntu image)
- laptop nix kprove (`k-7.1.337-4a46d123`): `kprove`/`kore-exec` wrappers point at `/nix/store/761igaxf…-z3-4.13.4` (z3 **4.13.4**)
- `CLAUDE.md` pins z3 4.16.0, which is the SMTChecker toolchain, not kprove's

T̂'s A3 entry must name K v7.1.337 (commit 4a46d123) + z3 4.12.1 as the checker. The 6/6 smoke shows the getter claims are insensitive to this difference. Other claims (WS-H's revert roots) are not yet tested under 4.12.1.

## Route: upstream RV K image + in-image kompile (not nix-in-docker)

Checked 2026-10-29 against Docker Hub:

- `runtimeverificationinc/kevm`: newest tag is `ubuntu-jammy-1.0.292`. There is **no KEVM image** for the KEVM this repo uses. Neither `runtimeverification-evm-semantics` nor `kframework-evm-semantics` has a matching tag.
- `runtimeverificationinc/kframework-k:ubuntu-jammy-7.1.337` exists, amd64 only, digest `sha256:a63698c0…b12b`. K tag `v7.1.337` = commit `4a46d1231473b599c699160132fd6e76a5c46406`, **the same K commit** as the laptop's nix kprove.
- `runtimeverificationinc/kontrol:ubuntu-jammy-1.0.255` (digest `sha256:858f0041…`, 2.07 GB) is the kontrol release the laptop's nix kontrol was built from (flake rev `0ac55eda`). It was not chosen because tcg calls `kprove` directly. It stays a fallback base.
- Nix-in-docker was rejected. The laptop's aarch64-darwin K store path is not in `k-framework.cachix.org` / `k-framework-binary.cachix.org` (narinfo 404), so the build could fall back to compiling K from source (hours), with no pin-strength gain.

Caveat: the image's K is RV's Ubuntu build of commit 4a46d123 and the laptop's is RV's nix build. The source is the same, the builds differ, and the z3 versions differ (above).

## What "KEVM 1.0.678" actually is (provenance finding)

- The laptop's kontrol flake (`0ac55eda`) locks `kevm` = `runtimeverification/evm-semantics` @ **`d4bf484a5dfe1e38d729a30434cd6f41e3590fb2`** = tag **`v1.0.921`**. There, `kevm-pyk/pyproject.toml` says `1.0.921`, but `kevm_pyk/__init__.py` has a stale `VERSION: Final = '1.0.678'`. `kevm version` prints that constant, and the nix package is named after it. tcg's `TOOLCHAIN["kevm"] = "1.0.678"` is that stale constant. T̂ names the commit.
- `diff -rq` of `kevm-pyk/src/kevm_pyk/kproj/evm-semantics` @ d4bf484a (tarball sha256 `5f8e3bcd…3275`) against laptop `~/toolchains/kevm-1.0.678/evm-semantics-source`: **identical**.
- The plugin submodule @ d4bf484a → `blockchain-k-plugin` @ `207ae5121e5178a09742ed746f2d15e34b1750cc` (tarball sha256 `1921eea0…8846`). Its `plugin/` is **identical** to the laptop's `kevm-1.0.678{,-lemmas2}/plugin/plugin`.
- d4bf484a + `ghost.diff` (`e300f622…68d1`) + `git show p1-b-vat-slip:theory/patches/lemmas.diff` (p1-b-vat-slip @ `5b3f9db9`, `dcc8789d…9c`; identical on p1-korerpc-probe) is **identical** (`diff -rq`) to the laptop's `kevm-1.0.678-lemmas2/evm-semantics-source`. The laptop's `-lemmas2/provenance.json` records the same patch hashes, and its definition.kore sha256 is `fcbb7fee…cc3`, which differs from the image's as expected.

## Kompile (inside the image)

Mirrors `scripts/build-kevm.sh` `build_lemmas()`. The script is unmodified:

```
kompile --backend haskell evm-semantics-source/lemmas-driver.k \
  --main-module LEMMAS-DRIVER --syntax-module LEMMAS-DRIVER \
  -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin \
  --md-selector "k & ! concrete" --hook-namespaces "JSON KRYPTO" --emit-json \
  -o /opt/kevm/haskell
```

## kprove argv (reproduced by run-claim.sh)

Recorded by running tcg's own pipeline (`init → loop new → iface set → compile-claims → prove`) on `tests/reference/getters-full/` with an argv-logging stub `kprove`:

```
kprove <ws>/.tcg/build/vat-vat-prove.k --definition <KEVM>/haskell --spec-module VAT-VAT-PROVE \
  -I <KEVM>/evm-semantics-source -I <KEVM>/plugin          (cwd = <ws>/.tcg/build)
```

`run-claim.sh` runs this argv with `<KEVM>` = `/opt/kevm`, with a scratch cwd.

## Open problems

1. **Distribution.** The image is not pushed anywhere (no-push rule). A consumer receives `tcg-kevm-checker.tar` out of band, `docker load`s it and compares the Id. Whether `docker save` output is byte-stable across docker versions or image stores is **untested**, so the Id is the primary identity and the tar sha256 is secondary.
2. **z3 4.12.1 vs the producer's 4.13.4** (above). Any claim that is not Accept in the image but was Accept on the laptop gets this suspect first.
3. **L1 wall time** is about 4–6× the laptop figure under the 2-CPU cap. The cause is not investigated.
4. The structural equivalence with the laptop definition is evidence, not proof. The trust statement is "this image Id re-discharges", not "same as the laptop".
