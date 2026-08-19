// Control spec: the Finding-0003 wall, removed.
//
// A symbolic ABI-decode: calldata = 4-byte selector ++ #buf(32, USR) ++
// #buf(32, WAD); the guard reads the second argument as
//   #asWord(#range(sel +Bytes #buf(32, USR) +Bytes #buf(32, WAD), 36, 32))
// which is exactly WAD. Under the lemma-LESS EDSL definition this term is
// opaque (Finding 0003: symbolic ABI-decode never binds -> the guard branch
// stays unpruned -> Unknown). Under the lemma-EQUIPPED definition the
// bytes/int simplification lemmas reduce it to WAD and the claim closes.
//
// The reduction path uses ONLY the four vendored simplification submodules:
//   #range(sel ++ #buf(32,USR) ++ #buf(32,WAD), 36, 32) => #range(#buf(32,WAD), 0, 32)  [range-outside-cHead, bytes]
//   #range(#buf(32,WAD), 0, 32)                          => #buf(32, WAD)                [range-buf-value,      bytes]
//   #asWord(#buf(32, WAD))                               => WAD                          [asWord-buf-inversion, evm-int]
// (lengthBytes(sel ++ #buf(32,USR)) = 36 comes from lengthBytes-concat/-buf, bytes).
//
// Expressed as a bare functional claim <k> EXPR:Int => WAD:Int </k>: the LHS is
// a stuck Int term with no rewrite rule, so the all-path obligation reduces to
// "the simplified LHS equals the RHS". No #execute / #halt / precompile dispatch
// is involved, so the substrate-§5 ECRECOVER crash cannot arise. sel is the
// concrete 4-byte buffer #buf(4, 3735928559) (= 0xDEADBEEF); USR, WAD are free
// symbolic 256-bit words.
//
// Run directly (SAME spec, two definitions):
//   OLD (lemma-less, expect Unknown):
//     kprove tests/control/lemmas/reduce-abi-decode.k \
//       --definition ~/toolchains/kevm-1.0.678/haskell \
//       --spec-module REDUCE-ABI-DECODE-SPEC \
//       -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
//       -I ~/toolchains/kevm-1.0.678/plugin
//   NEW (lemma-equipped, expect Accept / #Top):
//     kprove tests/control/lemmas/reduce-abi-decode.k \
//       --definition ~/toolchains/kevm-1.0.678-lemmas/haskell \
//       --spec-module REDUCE-ABI-DECODE-SPEC \
//       -I ~/toolchains/kevm-1.0.678-lemmas/evm-semantics-source \
//       -I ~/toolchains/kevm-1.0.678-lemmas/plugin

requires "edsl.md"

module REDUCE-ABI-DECODE-SPEC
    imports EDSL

    claim [decode]:
        <k> #asWord ( #range ( #buf(4, 3735928559) +Bytes #buf(32, USR) +Bytes #buf(32, WAD) , 36 , 32 ) )
         => WAD </k>
      requires #rangeUInt(256, USR)
       andBool #rangeUInt(256, WAD)
     [label(decode), all-path]

endmodule
