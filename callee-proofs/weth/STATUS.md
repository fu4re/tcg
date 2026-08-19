# STATUS — WETH9 token-leg callee summaries over REAL mainnet bytecode  (COMPLETE)

Deliverable D of the callee-proof problem (Finding 0005): the token-leg value-conservation
summaries GemJoin.join/exit will consume. Callee-side only; NO join/exit composition, NO
Vat.slip, NO kompiled-definition change.

Judge = kprove on the KEVM Haskell backend, lemma-equipped def at
`~/toolchains/kevm-1.0.678-lemmas` (main module LEMMAS-DRIVER), classified by the SHARED judge
`tcg.verdict.classify()` (exit 0 + `#Top` => Accept; "unifies with the destination" residual =>
Unknown(c); "cannot be rewritten further" => Refute). Every verdict below is an ACTUAL kprove
run; log paths given. The orchestrator independently re-verifies.

BOTTOM LINE: both summaries **Accept over the real WETH9 bytecode** and both discriminators
refuse — BUT only after adding, at SPEC time, the minimal subset of upstream `lemmas.k` that the
frozen driver OMITS (`specs/lemmas_min.k`: bool2Word + Map-reasoning, all pure `[simplification]`,
verbatim upstream). Against the FROZEN driver as-is the proofs Refute at a bool2Word wall — the
SAME wall Finding 0004's Vat.slip agent hit — plus a NEW Map-reasoning wall unique to the two-slot
token legs. This is a named trusted-base delta to be folded into the shared lemma-def rebuild (§5).

## 1. Subject bytecode — program-bound to the real WETH9 (SOUND ANCHOR)
- WETH9 = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 (canonical mainnet Wrapped Ether, ETH-A gem).
- Fetched deployed RUNTIME via 3 public RPCs (ETH_RPC_URL unset): publicnode / 1rpc / drpc.
- on-chain EXTCODEHASH == keccak256(fetched runtime) across ALL THREE RPCs AND the independent
  keccak, AND the fetched bytecode is byte-identical across all three (diff -q):
  `0xd0a06b12ac47863b5c7be4185c2deaad1c61557033f56c7d4ea74429cbb25e23`  (bytecode/codehash.txt)
- Runtime = 3124 bytes. Every proof `<program>` cell embeds this exact hex. CONFIRMED real WETH9.
- Storage layout: balanceOf = slot 3 (EMPIRICALLY confirmed vs the on-chain getter: getter
  balanceOf(GemJoin) == raw storage @ keccak(GemJoin.3) == 269609485538954355051071); allowance =
  slot 4 (standard layout; re-checked by the infinite-allowance branch gating in transferFrom_d).

## 2. The two summaries (PROVED), over the real WETH9 `<program>`
WETH9 (solc 0.4.19): transferFrom `require(bal[src]>=wad); if(src!=msg.sender && allow[src][snd]
!=uint(-1)){require(...); allow-=wad;} bal[src]-=wad; bal[dst]+=wad; emit Transfer; return true`.
transfer(dst,wad) = transferFrom(msg.sender,dst,wad). NO external CALL in either => the
reentrancy frame holds TRIVIALLY (surfaced, not assumed).

### transferFrom D — the GemJoin.join leg (adapter pulls wad from usr to itself)
- Parties: src=usr(0xaa), dst=adapter=msg.sender=ETH-A GemJoin(0x2F0b..042A). src != dst.
- Pre: callvalue 0; calldata 0x23b872dd ++ usr ++ adapter ++ wad; `0<=WAD<2^256`;
  `#rangeUInt(256, balanceOf[usr] -Int WAD)` (= the require `wad<=balanceOf[usr]`, stated in the
  form [chop-resolve] consumes); `#rangeUInt(256, balanceOf[adapter] +Int WAD)` (no overflow, raw
  ADD); **`allowance[usr][adapter] == 2^256-1`** (INFINITE-allowance precondition -> skips the
  allowance-decrement branch; this is the precondition I take. Finite-allowance is a documented
  extension: it adds one allowance-slot delta at keccak(adapter . keccak(usr . 4))).
- Post (PROVED Accept): `balanceOf[usr] -= WAD`, `balanceOf[adapter] += WAD`, EVMC_SUCCESS,
  output = 1 (return true), Transfer event emitted. Total supply conserved (−WAD/+WAD at two
  distinct slots; allowance unchanged).

### transfer D — the GemJoin.exit leg (adapter pushes wad to usr)
- Parties: msg.sender=src=adapter(GemJoin), dst=usr(0xaa). src==msg.sender => the allowance branch
  is SKIPPED entirely (NO allowance precondition). src != dst.
- Pre: callvalue 0; calldata 0xa9059cbb ++ usr ++ wad; `0<=WAD<2^256`;
  `#rangeUInt(256, balanceOf[adapter] -Int WAD)`; `#rangeUInt(256, balanceOf[usr] +Int WAD)`.
- Post (PROVED Accept): `balanceOf[adapter] -= WAD`, `balanceOf[usr] += WAD`, EVMC_SUCCESS,
  output = 1, Transfer event emitted.

## 3. SCOPE (honest — concrete-pinned schema, NOT universal over addresses)
- `wad`: UNIVERSAL over uint256 (`0<=WAD<2^256`) and over pre-state `STORAGE` (symbolic Map).
- `src,dst,msg.sender`: CONCRETE-PINNED (usr=0xaa, adapter=GemJoin). Concrete so keccak is a
  concrete CONSTANT in BOTH cast AND KEVM — NO keccak axiom is invoked; the ±WAD delta is proved
  at the opaque slot CONSTANTS. The delta is independent of the concrete key VALUES => a SCHEMA
  instantiable at any concrete (src,dst) with src != dst (klab uses this same concrete-key
  discipline). Universal-over-address is the blocked keccak widening, NOT a soundness gap.
- src==dst aliasing (balance nets to zero): EXCLUDED by construction — usr != adapter, so the two
  balanceOf slots are distinct concrete constants; the +WAD/−WAD land on different slots.

## 4. VERDICTS (actual kprove runs — the SHARED judge)
| spec                     | judge (spec-time imports)        | verdict            | log |
|--------------------------|----------------------------------|--------------------|-----|
| transferFrom_d_lem       | frozen def + lemmas_min.k        | **Accept (#Top)**  | logs/transferFrom_d_lem.log |
| transferFrom_wrong_lem   | frozen def + lemmas_min.k        | Unknown(c) NOT Accept | logs/transferFrom_wrong_lem.log |
| transferFrom_vac_lem     | frozen def + lemmas_min.k        | Unknown NOT Accept (RHSIsBottom) | logs/transferFrom_vac_lem.log |
| transfer_d_lem           | frozen def + lemmas_min.k        | **Accept (#Top)**  | logs/transfer_d_lem.log |
| transfer_wrong_lem       | frozen def + lemmas_min.k        | Unknown(c) NOT Accept | logs/transfer_wrong_lem.log |
| transfer_vac_lem         | frozen def + lemmas_min.k        | Unknown NOT Accept (RHSIsBottom) | logs/transfer_vac_lem.log |
| transferFrom_d (FROZEN)  | frozen def, NO lemmas.k          | **Refute** (wall)  | logs/transferFrom_d.log |
| transferFrom_d_b2w       | frozen def + b2w.k only          | Unknown(c) NOT Accept (2nd wall) | logs/transferFrom_d_b2w.log |

- Wrong-delta refuses BECAUSE of the +1: the reached storage carries the CORRECT `+Int WAD`; the
  claim demanded `+Int WAD +Int 1`, so the implication fails (a false summary does NOT Accept).
- Vacuity refuses with `WarnClaimRHSIsBottom` — the antecedent is FEASIBLE, so `ensures false` is
  not provable => the Accept is NON-VACUOUS (a vacuous claim's `ensures false` would Accept).
- (Substrate limit, docs/substrate.md §9 / prove.py: a false ARITHMETIC postcondition surfaces as
  Unknown(c), not Refute — the safe direction; "NOT Accept" is the discriminator that matters.)

Reproduce: `callee-proofs/weth/run.sh` (asserts every verdict). Slots: `slots.sh`.

## 5. THE WALLS (precise, reproducible) — a named trusted-base delta for the lemma-def rebuild
The frozen lemmas-driver (theory/patches/lemmas.diff) imports only the four PURE submodules
(bitwise/bytes/evm-int/int); it does NOT import `lemmas/lemmas.k` (module LEMMAS-WITHOUT-SLOT-
UPDATES). WETH's two token legs need two families from that omitted module — EACH pinned to a wall:

(A) **bool2Word wall** (== the Finding-0004 Vat.slip wall). transferFrom's `require(bal>=wad)`
    compiles to `LT ISZERO ISZERO ISZERO ... JUMPI`; the revert branch guard is
    `bool2Word(bool2Word(bool2Word(bool2Word(#lookup(STORAGE,BAL_USR) <Int WAD) ==Int 0) ==Int 0)
    ==Int 0)`. Frozen def => this never reduces, the revert branch cannot be pruned against
    `wad<=bal`, and kprove HALTS in EVMC_REVERT (Refute).
    EXACT term + pc: `bool2Word ( bool2Word ( bool2Word ( bool2Word ( #lookup(STORAGE, <BAL_USR>)
    <Int WAD ) ==Int 0 ) ==Int 0 ) ==Int 0 )` at pc **1755** (0x06db) — logs/transferFrom_d.log.
    FIX: `[b2w-eq-zero]` (lemmas.k:71), `[b2w-eq-one]` (l.72).

(B) **Map-reasoning wall** (NEW — the token legs write TWO balanceOf slots; Vat.slip's one-SSTORE
    slip never hit it). After (A) is cleared, the second-slot read is
    `#lookup ( STORAGE [ BAL_SRC <- ... ] , BAL_DST )` over the UPDATED map (distinct concrete
    keys); with only bool2Word it never reduces, so the outer `chop(_ +Int WAD)` cannot strip and
    the implication fails (Unknown). EXACT residual (logs/transferFrom_d_b2w.log):
    `chop ( #lookup ( STORAGE [ <BAL_USR> <- #lookup(STORAGE,<BAL_USR>) -Int WAD ] , <BAL_ADAPTER>
    ) +Int WAD )`. FIX: `#lookup(M[K1<-_],K2) => #lookup(M,K2) requires notBool(K1==Int K2)`
    (lemmas.k:129) + the `#lookup` range rules (l.125-126).

`specs/lemmas_min.k` (module WETH-CALLEE-LEMMAS) is the MINIMAL verbatim subset of the omitted
lemmas.k that closes both (A)+(B). It is a SPEC-TIME import — NO kompiled-def change, NO competing
def — the rules ride into kprove's simplification set via the spec module. `specs/b2w.k` is the
(A)-only subset, used for the isolation run transferFrom_d_b2w that pins wall (B).

Two further non-wall obligations resolved along the way (both sound, both in the spec, no new
lemmas): (i) the src `chop(bal -Int WAD)` strips only when the require is stated as
`#rangeUInt(256, bal -Int WAD)` (the form `[chop-resolve]: chop(I)=>I requires #rangeUInt(256,I)`
consumes) — equivalent to `wad<=bal`; (ii) the `<log>` cell must be freed (`<log> _ => ?_`) since
transferFrom emits Transfer(src,dst,wad) — otherwise the claim frames the log unchanged and the
event append fails the implication.

RECOMMENDATION for the lemma-def rebuild: fold module LEMMAS-WITHOUT-SLOT-UPDATES (lemmas.k) into
the driver — at minimum {b2w-eq-zero, b2w-eq-one (l.71-72), the #lookup map-reasoning rules
(l.125-130)}. Then these WETH summaries (and Vat.slip) Accept against the frozen def with NO
spec-time lemma import, and the orchestrator re-verifies with the def alone.

## 6. Discharged vs assumed
- Discharged (over the real WETH9 bytecode, for the concrete-pinned schema, WITH lemmas_min.k):
  balanceOf[src] −= wad, balanceOf[dst] += wad, EVMC_SUCCESS, output=1, callvalue-0 guard passed;
  for transferFrom, the infinite-allowance branch (allowance unchanged); non-vacuous; wrong-delta
  refused.
- Reentrancy frame: NO external CALL in transfer/transferFrom => holds trivially (surfaced).
- Assumed / ledgered: (a) storage-layout facts (balanceOf slot 3 empirically confirmed; allowance
  slot 4 standard + branch-checked; keccak slots re-checkable via slots.sh); (b) the omitted
  lemmas.k subset in lemmas_min.k — verbatim upstream, pure `[simplification]`, sound, but an
  addition BEYOND the frozen driver = a NAMED trusted-base delta (§5), to be folded into the
  shared def rebuild; (c) OUT of scope: universal-over-address (keccak widening), finite-allowance
  transferFrom (documented extension), and the exit-leg with negative/other framings.
- keccak wall: handled klab-style — concrete src/dst/msg.sender => keccak is a concrete constant,
  NO keccak axiom invoked; delta proved at the opaque slot CONSTANTS.

## Files
- bytecode/{runtime.hex, codehash.txt} — the 3-RPC + independent-keccak identity anchor.
- specs/{transferFrom,transfer}_{d,wrong,vac}.k         — frozen-def specs (D + discriminators).
- specs/{transferFrom,transfer}_{d,wrong,vac}_lem.k     — same, importing lemmas_min.k (the proofs).
- specs/transferFrom_d_b2w.k                            — b2w-only isolation (pins wall B).
- specs/{b2w.k, lemmas_min.k}                           — the omitted-lemma subsets (named delta).
- logs/*.log — every kprove run above.  run.sh — verdict-asserting reproduction.  slots.sh — slots.
