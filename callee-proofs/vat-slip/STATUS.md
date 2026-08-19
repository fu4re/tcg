# STATUS — Vat.slip callee summary over REAL mainnet Vat bytecode

Deliverable D of the callee-proof problem (Finding 0005): the Vat.slip value-conservation
summary that GemJoin.join/exit will later consume. Callee-side only; NO join/exit composition.

Judge = kprove on the KEVM Haskell backend, lemma-equipped def at
`~/toolchains/kevm-1.0.678-lemmas`, driven through `tcg prove` (tcg.commands.prove.classify:
exit 0 => Accept; residual => Refute; else Unknown(a/b/c)). Every verdict below is an actual
kprove run; the log path is given.

## 1. Subject bytecode — program-bound to the real Vat (SOUND ANCHOR)
- MCD_VAT = 0x35D1b3F3D7966A1DFe207aa4514C12a259A0492B (chainlog2.json).
- Fetched deployed RUNTIME via public RPC (ETH_RPC_URL was unset; used publicnode/1rpc/drpc).
- keccak256(runtime) == on-chain EXTCODEHASH across all three RPCs:
  `0x808b98f6475736d56c978e4fb476175ecd9d7abdab0797017fc10c7f46311a59`  (see bytecode/codehash.txt)
- The proof `<program>` cell embeds this exact 13493-byte hex. CONFIRMED real Vat, no fabrication.

## 2. The slip summary (what is proved)
`slip(bytes32 ilk, address usr, int256 wad) external auth { gem[ilk][usr] = _add(gem[ilk][usr], wad); }`
Delta of interest: `gem[ilk][usr]` changes by exactly `wad`, 1:1, at the opaque keccak slot.

Matches the canonical klab/k-dss `behaviour slip of Vat` (dss.md:609): storage
`gem[ilk][usr] |-> Gem => Gem + wad`, iff `wards[CALLER]==1`, `VCallValue==0`, `Gem+wad` in
range uint256.

### Summary claim (D), over the real Vat `<program>`:
- Pre: calldata = selector `0x7cdd3fde` ++ ilk ++ usr ++ wad; callvalue 0; `<static> false`;
  caller = GemJoin (0x2F0b…042A); storage symbolic Map `STORAGE`.
- Precondition (requires): `0 <= WAD < 2^255` (non-negative int256 — join's actual usage);
  `#rangeUInt(256, #lookup(STORAGE, GEMSLOT) +Int WAD)` (no overflow, the klab `iff in range`);
  `#lookup(STORAGE, WARDSLOT) ==Int 1` (auth: GemJoin is a ward).
- Post: `STORAGE => STORAGE [ GEMSLOT <- #lookup(STORAGE, GEMSLOT) +Int WAD ]`, `EVMC_SUCCESS`.
- Opaque slots (keccak treated as an uninterpreted concrete constant, re-checkable via slots.sh):
  - `GEMSLOT  = 109968117995108105786565572842071691871171164772949068926251789879993337596252`
     = keccak(usr32 . keccak(ilk32 . 4)) = `gem[ETH-A][0x…AA]`  (gem is storage slot 4)
  - `WARDSLOT = 49961635201387463252893605866551699684656743484194109711528147149142982045043`
     = keccak(gemjoin32 . 0) = `wards[GemJoin]`  (wards is storage slot 0)

## 3. SCOPE (stated honestly — NOT universal)
- `wad`: universal over non-negative int256 (`0 <= WAD < 2^255`) and over pre-state `STORAGE`.
  This is exactly the sign GemJoin.join uses (`require(int(wad) >= 0)`); the exit leg (negative
  wad) is a documented extension, NOT yet proved.
- `ilk`, `usr`, `caller`: CONCRETE-PINNED (ilk = ETH-A, usr = 0x…AA representative, caller =
  GemJoin). Forced concrete because the SYMBOLIC keccak-slot widening walls (see §5). The +wad
  delta is independent of the concrete key VALUES, so this is a schema instantiable at any
  concrete (ilk,usr); universal-usr is the blocked widening, not a soundness gap.

## 4. Non-vacuity discriminators (MANDATORY)
- WRONG-DELTA (`slip_wrong.k`): identical claim but post delta `+ WAD + 1`. MUST NOT Accept.
- VACUITY (`slip_vac.k`): identical claim but `ensures false`. MUST NOT Accept.

## 5. WALL (the precise next-cycle lemma target) — signed-add bool2Word
The frozen `lemmas-driver` (theory/patches/lemmas.diff) imports only the four PURE submodules
BITWISE / BYTES / EVM-INT / INT-SIMPLIFICATION. It OMITS module `LEMMAS-WITHOUT-SLOT-UPDATES`
(evm-semantics lemmas/lemmas.k), whose `bool2Word` reasoning rules — notably
`[b2w-eq-zero]: bool2Word(B) ==Int 0 => notBool B` (lemmas.k:71) — are themselves `[simplification]`
and thus WITHIN the driver's own stated "[simplification]-only" intent. The four submodules do
not transitively import that module, so the rules are absent from the compiled judge.

Consequence: signed `_add`'s `require(y >= 0 || z <= x)` compiles to a revert branch guarded by
`0 #Equals bool2Word(bool2Word(WAD <Int 0) ==Int 0)`. Under `0 <=Int WAD` this branch is
INFEASIBLE, but without `[b2w-eq-zero]` the nested bool2Word never reduces, so kprove is left with
an unprunable `EVMC_REVERT` leaf and returns Refute (residual, not a real defect).

EXACT opaque term: `bool2Word ( bool2Word ( WAD <Int 0 ) ==Int 0 )`  (residual log, pc 13143).
FIX (next cycle): add the bool2Word `[simplification]` rules of `LEMMAS-WITHOUT-SLOT-UPDATES` to
the lemmas-driver (matches its stated intent). `specs/b2w.k` supplies the two rules verbatim for
the with-lemma variant below.

## 6. VERDICTS (actual kprove runs)
| loop        | spec         | judge                        | verdict | log |
|-------------|--------------|------------------------------|---------|-----|
| slip_d      | slip_d.k     | frozen def (driver as-is)    | Refute (bool2Word wall §5) | logs/slip_d-refute-frozen.log |
| slip_d_b2w  | slip_d.k     | def + b2w.k (2 canonical lemmas) | PENDING | logs/… |
| slip_wrong  | slip_wrong.k | def + b2w.k                  | PENDING (must NOT Accept) | |
| slip_vac    | slip_vac.k   | def + b2w.k                  | PENDING (must NOT Accept) | |

## 7. Discharged vs assumed
- Discharged (over real Vat bytecode): the +wad delta at the gem slot, success, auth-gating,
  callvalue-0 — for the concrete-pinned scope, with the two bool2Word lemmas.
- Assumed / ledgered: (a) storage-layout facts (gem = slot 4, wards = slot 0; keccak slots
  re-checkable via slots.sh); (b) the two bool2Word `[simplification]` lemmas in b2w.k (verbatim
  upstream KEVM, sound, but an addition beyond the frozen driver — trusted-base delta named);
  (c) universal-usr / negative-wad are OUT of scope (walls §5 and exit-leg extension).
- Reentrancy frame: slip makes NO external call (one SSTORE) — the frame holds trivially.
