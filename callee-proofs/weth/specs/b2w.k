// b2w.k -- the TWO canonical KEVM bool2Word [simplification] lemmas that the
// frozen lemmas-driver (theory/patches/lemmas.diff) OMITS. VERBATIM from upstream
// evm-semantics lemmas/lemmas.k:71-72 (module LEMMAS-WITHOUT-SLOT-UPDATES). Both
// are pure [simplification] rules (bool2Word(B) is definitionally 0 or 1), sound
// and upstream-vetted; they are WITHIN the driver's own stated "[simplification]-only"
// intent -- the driver's four submodules simply do not transitively import them.
//
// Needed here because WETH9's `require(balanceOf[src] >= wad)` compiles to
// `LT ISZERO ISZERO ISZERO ... JUMPI`, whose revert branch is guarded by
//   bool2Word(bool2Word(bool2Word(bool2Word(balanceOf[src] <Int wad) ==Int 0) ==Int 0) ==Int 0)
// Without [b2w-eq-zero] that nested bool2Word never reduces, so the infeasible
// revert branch cannot be pruned against `wad <= balanceOf[src]` and kprove halts
// at EVMC_REVERT (Refute). This is the SAME wall Finding-0004's Vat.slip agent hit.
//
// This is a spec-time import (NO kompiled-definition change): the rules ride into
// kprove's simplification set via the spec module. It is a NAMED trusted-base delta
// beyond the frozen driver -- to be folded into the shared lemma def by the rebuild.
requires "edsl.md"

module WETH-B2W-LEMMAS
    imports EDSL

    rule [b2w-eq-zero]: bool2Word(B) ==Int 0 => notBool B [simplification(30), comm]
    rule [b2w-eq-one]:  bool2Word(B) ==Int 1 => B         [simplification(30), comm]
endmodule
