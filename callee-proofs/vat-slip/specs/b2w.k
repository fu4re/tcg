// b2w.k — the TWO canonical KEVM bool2Word [simplification] lemmas that the
// frozen lemmas-driver omitted. VERBATIM from upstream evm-semantics
// lemmas/lemmas.k:71-72 (module LEMMAS-WITHOUT-SLOT-UPDATES). Both are pure
// [simplification] rules (bool2Word(B) is 0 or 1), sound and upstream-vetted.
//
// Needed because signed `add`'s `require(y >= 0 || z <= x)` compiles to a revert
// branch guarded by `bool2Word(bool2Word(WAD <Int 0) ==Int 0) ==Int 0`; without
// b2w-eq-zero that infeasible branch cannot be pruned against `0 <=Int WAD`.
requires "edsl.md"

module SLIP-B2W-LEMMAS
    imports EDSL

    rule [b2w-eq-zero]: bool2Word(B) ==Int 0 => notBool B [simplification(30), comm]
    rule [b2w-eq-one]:  bool2Word(B) ==Int 1 => B         [simplification(30), comm]
endmodule
