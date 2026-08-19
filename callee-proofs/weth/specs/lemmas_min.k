// lemmas_min.k -- the MINIMAL subset of upstream evm-semantics `lemmas/lemmas.k`
// (module LEMMAS-WITHOUT-SLOT-UPDATES) that WETH9's transferFrom/transfer summaries
// need and that the FROZEN lemmas-driver (theory/patches/lemmas.diff) OMITS. The
// driver imports only the four pure submodules (bitwise/bytes/evm-int/int); it does
// NOT import lemmas.k, so BOTH families below are absent from the compiled judge.
//
// All rules are VERBATIM from lemmas/lemmas.k (line cites), all pure [simplification],
// all sound and upstream-vetted. This is a SPEC-TIME import (NO kompiled-definition
// change, NO competing def) -- the rules ride into kprove's simplification set via
// the spec module. It is a NAMED trusted-base delta to be folded into the shared
// lemma def by the ongoing rebuild.
//
// Two omitted families, each pinned to a concrete WETH wall:
//  (A) bool2Word: WETH's `require(bal >= wad)` compiles to `LT ISZERO ISZERO ISZERO
//      ... JUMPI`; the revert branch guard bool2Word(bool2Word(bool2Word(bool2Word(
//      bal < wad)==0)==0)==0) needs [b2w-eq-zero] to prune against `wad <= bal`.
//      (This is exactly the Finding-0004 Vat.slip wall.)
//  (B) Map reasoning: transferFrom/transfer write TWO balanceOf slots; the second
//      read `#lookup(STORAGE[K_src <- _], K_dst)` (distinct concrete keys) needs the
//      lookup-over-update rule to reduce to `#lookup(STORAGE, K_dst)` so the outer
//      `chop(_ +Int wad)` can strip against the no-overflow precondition. Vat.slip
//      (one slot, one SSTORE) never hit this -- it is NEW to the two-slot token legs.
requires "edsl.md"

module WETH-CALLEE-LEMMAS
    imports EDSL

    // (A) bool2Word reasoning -- lemmas.k:71-72
    rule [b2w-eq-zero]: bool2Word(B) ==Int 0 => notBool B [simplification(30), comm]
    rule [b2w-eq-one]:  bool2Word(B) ==Int 1 => B         [simplification(30), comm]

    // (B) Map reasoning -- lemmas.k:125-130
    rule 0 <=Int #lookup( _M:Map , _ )             => true [simplification, smt-lemma]
    rule         #lookup( _M:Map , _ ) <Int pow256 => true [simplification, smt-lemma]

    rule #lookup ( _M:Map [ K1 <- V1 ] , K2 )    => #lookup ( K1 |-> V1 , K1 ) requires K1 ==Int  K2 [simplification]
    rule #lookup (  M:Map [ K1 <- _  ] , K2 )    => #lookup ( M         , K2 ) requires notBool ( K1 ==Int K2 ) [simplification]
    rule #lookup ( (K1:Int |-> _) M:Map, K2:Int) => #lookup ( M         , K2 ) requires notBool ( K1 ==Int K2 ) [simplification]
endmodule
