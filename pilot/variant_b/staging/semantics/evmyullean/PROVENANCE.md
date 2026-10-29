# EVMYulLean: vendored semantics for variant B

| | |
|---|---|
| Upstream | `https://github.com/leonardoalt/EVMYulLean` |
| Commit | `56253eb468bb39355ed522440502e3480c0139f0` (2026-05-02, "FRAME_LIBRARY: refresh after relational-invariant closure moved consumer-side"), contained in `origin/main` |
| Export | `git archive 56253eb468bb39355ed522440502e3480c0139f0` from the laptop clone `~/evm-smith/EVMYulLean` (the evm-smith submodule), unpacked into `upstream/`. Not modified. |
| Size | 121 files, 1.7 MB |
| Licence | Apache-2.0 (`upstream/license.txt`) |
| Toolchain | `leanprover/lean4:v4.22.0` (`upstream/lean-toolchain`); Mathlib `v4.22.0`, rev `79e94a093aff4a60fb1b1f92d9681e407124c2ca` |
| Tree hash | `TREE_SHA256.txt` = `sha256sum` of every file under `upstream/`, paths sorted; sha256 of that listing = `57ed86e0a58e0936d9f3aaf092db6d3409411300088f1f7b81be673b5e768e99` |

Not vendored: the `EthereumTests` submodule (conformance tests only) and the
two C hash libraries the upstream lakefile clones at build time (`sha-2`,
`SHA3IUF`). They are linked only into executables; the variant B proofs
neither build nor call them.

## Patches

Applied on top of `upstream/`, never edited into it.
`pilot/variant_b/tools/prepare_semantics.sh` checks `upstream/` against
`TREE_SHA256.txt`, copies it to `pilot/variant_b/semantics/evmyullean/`
(gitignored), and applies the patches in order. All five exist only to make
definitions on the `ilk()` path reducible by the Lean kernel; none changes
an opcode's semantics.

| Patch | sha256 | Upstream definition | Change | Faithfulness |
|---|---|---|---|---|
| `0001-dj-aux-fuel.patch` | `d5d73e8f…bd2933` | `D_J_aux` (valid jump destinations): `partial def`, an opaque constant to the kernel | same body, recursion bounded by fuel `c.size + 1` | Argued, not proved (a `partial def` has no equations to prove against): every recursive call needs `i < c.size` and advances `i` by at most 33, so the fuel is never exhausted while `c.size + 33 < 2^256`. For the GemJoin runtime the 59-entry result equals an independent Python scan. |
| `0002-zeroes-transparent.patch` | `385b680e…fc28` | `ffi.ByteArray.zeroes : USize → ByteArray`: `opaque`, implemented by C `memset_zero` | `def zeroes (n : Nat) := ⟨Array.replicate n 0⟩`; the 11 call sites pass the `Nat` length instead of `⟨k⟩ : USize` | Argued, not proved (opaque): same `n` zero bytes for `n < 2^64`. Upstream's compiled code would hand C `n mod 2^64` for larger `n`. A `USize`-typed body would still not reduce, because `USize` literals go through the opaque `System.Platform.numBits`. |
| `0003-frombytearray-structural.patch` | `cbe24e88…7cd0a` | `fromByteArrayBigEndian` reads `b.toList` (Lean core, well-founded loop) | reads `b.data.toList` | **Proved**: `GemJoin.ByteArray_toList_eq : b.toList = b.data.toList` (`pilot/variant_b/GemJoin/Bytes.lean`). |
| `0004-tobytes-structural.patch` | `774ddee6…a197` | `toBytesBigEndian = List.reverse ∘ toBytes'`, `toBytes'` private, well-founded | `toBytesBigEndian n = (toBytesFuel n n).reverse`, `toBytesFuel` structural with the same equations | **Proved**: `GemJoin.toBytesFuel_eq : n ≤ fuel → toBytesFuel fuel n = toBytes' n`. |
| `0005-tobytearray-32.patch` | `fbb2e02e…bd428` | `UInt256.toByteArray v = zeroes (32 - b.size) ++ b` (`b := BE v.toNat`): its length depends on `v`, so with a symbolic word the kernel cannot see it is 32 at the next memory read | the 32 big-endian bytes written elementwise | **Proved**: `GemJoin.toByteArray_eq` (upstream expression = patched definition). |

Patches 0001 and 0002 add to the trusted base: a consumer who accepts a
variant B certificate accepts these two definitions as faithful to upstream.
Patches 0003, 0004 and 0005 are equal to upstream by a kernel-checked lemma, so they
add nothing beyond the lemma statements.

Credentials: the laptop clone's `origin` URL embeds a GitHub personal access
token. It is not reproduced here; the owner may want to revoke it.
