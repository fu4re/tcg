# STATUS — Vat.slip callee summary over REAL mainnet Vat bytecode

Deliverable D of the callee-proof problem (Finding 0005): the Vat.slip value-conservation
summary that GemJoin.join/exit will later consume. Callee-side only; NO join/exit composition.

Judge = kprove on the KEVM Haskell backend. The bool2Word wall (§5) is fixed on a NEW
authoritative lemma-equipped def `~/toolchains/kevm-1.0.678-lemmas2` (base + ghost.diff + the
EXTENDED `theory/patches/lemmas.diff` that vendors TWO [simplification]-only submodules —
`BOOL2WORD-SIMPLIFICATION` (lemmas.k:58-111) and `MAP-REASONING-SIMPLIFICATION`
(#lookup map reasoning, lemmas.k:125-130); the older `~/toolchains/kevm-1.0.678-lemmas` is kept
intact for existing bundles). One authoritative def covers BOTH Vat.slip AND the WETH/GemJoin
two-slot token legs (coordinated with the parallel WETH agent; the map family is byte-identical
to that agent's independently-extracted subset). Verdicts classified by `tcg.verdict.classify`
(exit 0 + `#Top` => Accept;
residual => Refute; else Unknown(a/b/c)) — the same judge `tcg prove` uses. Slip specs run
with `requires "edsl.md"` / `imports EDSL` and NO `b2w.k` (the bool2Word rules now live in the
def; importing b2w.k too would duplicate the [b2w-eq-zero]/[b2w-eq-one] labels). Every verdict
below is an actual kprove run; the command is in each log header, the log path is given.

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

## 5. WALL — bool2Word REVERT wall FIXED; residual blocker is the §9 impl-check ceiling
### 5a. The bool2Word wall is REMOVED (this cycle's fix, verified)
Signed `_add`'s `require(y >= 0 || z <= x)` compiles to a revert branch guarded by
`0 #Equals bool2Word(bool2Word(WAD <Int 0) ==Int 0)`. On the OLD `-lemmas` def that nested
bool2Word never reduced, leaving an unprunable `EVMC_REVERT` leaf → Refute (residual, not a
defect; `logs/slip_d-refute-frozen.log`). The new `-lemmas2` def carries the bool2Word
`[simplification]` rules (`lemmas/bool2word-simplification.k`, verbatim from
lemmas.k:58-111, incl. `[b2w-eq-zero]: bool2Word(B) ==Int 0 => notBool B` at lemmas.k:71).
Effect, verified in EVERY new-def slip log: `bool2Word` count is 0 and the only reached leaf is
`EVMC_SUCCESS` — the infeasible revert branch is pruned and the success path reaches the target.

### 5b. NEW residual blocker (a DIFFERENT term — diagnosed, not forced)
slip_d now reaches the EXACT target config over the real Vat bytecode: `#halt`, `EVMC_SUCCESS`,
and `<storage> = STORAGE [ GEMSLOT <- #lookup(STORAGE, GEMSLOT) +Int WAD ]` (identical to the
destination — see `logs/slip_d-lemmas2.log:227`). kore-exec reports the configuration term
UNIFIES with the destination, but the implication check between the branch conditions is left
undischarged on the signed-`_add` sign split (`WAD <=Int 0`; and on the strictly-positive
variant `0 <Int WAD`). Verdict: Unknown(c).

This is the documented substrate limit (tcg/commands/prove.py §9 / docs/substrate.md §9): a
reached-but-under-closed TRUE target is indistinguishable, in kore-exec's own output, from a
false one — both surface as the `WarnStuckClaimState` "unifies ... implication check has failed"
variant → Unknown(c), never Refute. Lifting it needs kore-rpc `implies`/`get-model` or a pyk
APRProof, explicitly out of scope for this tool.

Isolation (it is NOT the lemma set and NOT the claim shape):
- NOT the lemmas: the config matches the destination exactly; `bool2Word` is fully gone.
- NOT the claim shape: three structures all Unknown(c) —
  `slip_d.k` (cell-rewrite, `0<=WAD`), `slip_dpos.k` (`0<WAD`, sign branch collapsed),
  `slip_de.k` (getters-style `<storage> STORAGE => ?FINAL:Map` + `ensures ?FINAL ==K ...`).
- Contrast: the getters roots (Findings 0003a/0003b) Accept to `#Top` because their path has NO
  signed arithmetic / branch split and leaves storage unchanged. slip's signed-add sign split is
  the structural difference kore-exec cannot close here.

Next lever (out of scope; substrate-fitting): kore-rpc/APRProof replay per §9, or concretize the
account/sign cells to collapse the branch (also visible: an `ACCTID in_keys(...)` set-membership
residual). Not attempted — a conservative-but-incomplete result beats over-fitting the claim.

## 6. VERDICTS (actual kprove runs)
Judge for the new rows: kprove on `~/toolchains/kevm-1.0.678-lemmas2/haskell`,
`requires "edsl.md"` / `imports EDSL`, classified by `tcg.verdict.classify`. Command in each
log header.

| loop        | spec           | judge                              | verdict | log |
|-------------|----------------|------------------------------------|---------|-----|
| slip_d      | slip_d.k       | OLD `-lemmas` (no bool2Word)       | Refute — bool2Word REVERT wall §5a | logs/slip_d-refute-frozen.log |
| slip_d      | slip_d.k       | NEW `-lemmas2` (+ BOOL2WORD-SIMPL) | **Unknown(c)** — wall GONE (bool2Word=0, only EVMC_SUCCESS), reaches EXACT +WAD target; §9 impl-check ceiling on sign split | logs/slip_d-lemmas2.log |
| slip_dpos   | slip_dpos.k (`0<WAD`) | NEW `-lemmas2`              | Unknown(c) — `WAD<=0` branch collapsed, single `0<WAD` branch still §9 | logs/slip_dpos-lemmas2.log |
| slip_de     | slip_de.k (existential `?FINAL`) | NEW `-lemmas2`  | Unknown(c) — getters-shape restructure, still §9 | logs/slip_de-lemmas2.log |
| slip_wrong  | slip_wrong.k (`+WAD+1`) | NEW `-lemmas2`            | Unknown(c) — **NOT Accept** ✓ (storage unify ⇒ false `WAD==WAD+1`) | logs/slip_wrong-lemmas2.log |
| slip_vac    | slip_vac.k (`ensures false`) | NEW `-lemmas2`      | Unknown(c) — **NOT Accept** ✓ (41s, `ensures false`) | logs/slip_vac-lemmas2.log |

HONEST BOTTOM LINE: slip_d does **NOT** reach Accept on this substrate. The bool2Word extension
delivered its intended effect (Refute → reaches the exact +WAD target; the wall term is gone),
but slip_d halts at the pre-existing §9 kore-exec implication-check ceiling. Because slip_d,
slip_wrong, and slip_vac ALL surface as Unknown(c), the discriminators refuse (good) but give NO
positive contrast — the slip value-conservation summary is **not positively discharged here**.
This is the task's anticipated "walls on a different term" outcome, reported as data (§5b).

## 7. Discharged vs assumed
- Discharged this cycle (NOT a slip Accept): (a) the lemma-def extension is CONSERVATIVE and
  CONSISTENT — consistency gate 5/5 on `-lemmas2` (the 4 prior false identities + the new
  `PROBE-B2W-SPEC` bool2Word wrong-direction control all refuse), and the full prior-proof
  regression is UNCHANGED (getters-full 6/6 Accept + self-verify; build-reference 3/3 +
  drain-Refute; conformance 6/6) — see `logs/regression/SUMMARY.txt`; (b) the bool2Word REVERT
  wall is removed — slip's success path now reaches the EXACT +WAD storage-delta config,
  EVMC_SUCCESS, over the real Vat bytecode (keccak(runtime)==0x808b98f6…1a59).
- NOT discharged: slip_d → Accept. Blocked at the §9 kore-exec implication-check ceiling on the
  signed-add sign split (§5b), verified across three claim structures. Unknown(c), not Accept.
- Assumed / ledgered: (a) storage-layout facts (gem = slot 4, wards = slot 0; keccak slots
  re-checkable via `slots.sh`); (b) the vendored `[simplification]` lemmas — now in the DEF, two
  submodules: `lemmas/bool2word-simplification.k` (verbatim lemmas.k:58-111) and
  `lemmas/map-simplification.k` (verbatim lemmas.k:125-130, byte-identical to the WETH agent's
  extract), provenance per-rule, NOT a spec-side `b2w.k`; a named trusted-base delta bounded by
  the **6/6** consistency gate (a bool2Word AND a map false-identity control both refuse — see
  `logs/regression/SUMMARY.txt`); (c) universal-usr / negative-wad exit-leg remain OUT of scope.
- Map family is INERT for slip: its rules fire only on `#lookup(M[K<-V], K2)` (updated-map reads),
  which slip's single SSTORE never produces (slip reads `#lookup(STORAGE, GEMSLOT)` on the
  ORIGINAL map). Verified: all slip verdicts are UNCHANGED between the bool2Word-only build and
  this two-family authoritative def. The map family is what the WETH/GemJoin two-slot legs need.
- Reentrancy frame: slip makes NO external call (one SSTORE) — the frame holds trivially.
- Note: `specs/b2w.k` is now SUPERSEDED (its two rules are a subset of the def-side submodule);
  kept only as the interim record. `specs/slip_dpos.k` and `specs/slip_de.k` are the §5b
  diagnostic variants (not summaries).
