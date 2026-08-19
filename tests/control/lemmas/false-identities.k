// Mandatory soundness control (Finding 0004, task 4): KNOWN-FALSE identities
// that the lemma set must NOT be able to prove. Adding simplification lemmas
// grows the trusted base, and NEITHER the vacuity probe NOR program-binding
// catches a false lemma: a wrong simplification rule would let the prover
// Accept a false postcondition. So we attempt to prove false identities and
// require the prover to REFUSE every one of them (verdict != Accept: no #Top,
// non-zero exit). If ANY of these proves, the lemma set is UNSOUND and must not
// be shipped.
//
// Each probe is a bare functional claim <k> LHS:Int => WRONG:Int </k> whose LHS
// is reduced by a REAL simplification rule in one of the four vendored
// submodules to its CORRECT value, after which the residual obligation is the
// false equality <correct value> ==Int <wrong value>. The probe would wrongly
// Accept only if the corresponding lemma reduced LHS to the wrong thing (or the
// set were arithmetically inconsistent). One probe per submodule.
//
// Run each (scripts/lemma-consistency.sh does this against the NEW def):
//   kprove tests/control/lemmas/false-identities.k \
//     --definition ~/toolchains/kevm-1.0.678-lemmas/haskell \
//     --spec-module <MODULE> \
//     -I ~/toolchains/kevm-1.0.678-lemmas/evm-semantics-source \
//     -I ~/toolchains/kevm-1.0.678-lemmas/plugin
// Expected for every module: NOT Accept (exit != 0, no #Top).

requires "edsl.md"

// P1 — evm-int-simplification (asWord-buf-inversion). Correct: #asWord(#buf(32,X)) => X.
//      FALSE target X +Int 1.
module PROBE-ASWORD-SPEC
    imports EDSL
    claim [asword-off-by-one]:
        <k> #asWord ( #buf ( 32 , X ) ) => X +Int 1 </k>
      requires #rangeUInt(256, X)
     [label(asword-off-by-one), all-path]
endmodule

// P2 — bytes-simplification (#range extraction). The guard must decode the
//      SECOND argument (WAD), not the first (USR). Correct reduction: WAD.
//      FALSE target USR.
module PROBE-RANGE-SPEC
    imports EDSL
    claim [range-wrong-arg]:
        <k> #asWord ( #range ( #buf(4, 3735928559) +Bytes #buf(32, USR) +Bytes #buf(32, WAD) , 36 , 32 ) )
         => USR </k>
      requires #rangeUInt(256, USR)
       andBool #rangeUInt(256, WAD)
     [label(range-wrong-arg), all-path]
endmodule

// P3 — int-simplification (additive cancellation). Correct: (A +Int B) -Int B => A.
//      FALSE target A +Int 1.
module PROBE-INT-SPEC
    imports EDSL
    claim [int-cancel-off-by-one]:
        <k> ( A +Int B ) -Int B => A +Int 1 </k>
      requires #rangeUInt(256, A)
       andBool #rangeUInt(256, B)
     [label(int-cancel-off-by-one), all-path]
endmodule

// P4 — bitwise-simplification (idempotence of &Int). Correct: X &Int X => X.
//      FALSE target X +Int 1.
module PROBE-BITWISE-SPEC
    imports EDSL
    claim [band-idem-off-by-one]:
        <k> X &Int X => X +Int 1 </k>
      requires #rangeUInt(256, X)
     [label(band-idem-off-by-one), all-path]
endmodule
