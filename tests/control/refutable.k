// Control spec (b): REFUTABLE.
//
// Identical to provable.k (same STOP program, same concrete call frame)
// except the claim asserts the final <pc> is 999, which is false for any
// execution of a 1-byte program starting at pc=0. The prover must reach a
// state that does not unify/imply the claimed destination and report a
// residual goal.
//
// Run directly:
//   kprove tests/control/refutable.k \
//     --definition ~/toolchains/kevm-1.0.678/haskell \
//     --spec-module REFUTE-EVM-SPEC \
//     -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
//     -I ~/toolchains/kevm-1.0.678/plugin
//
// Expected: exit 1, log ends with the standard
//   "[Error] Prover: backend terminated because the configuration cannot be
//    rewritten further."
// which is exactly the phrase tcg.commands.prove.classify() matches for
// Refute. See tests/control/logs/refutable.log.
//
// NOTE (real backend crash, not caused by this claim's content): before
// reaching that final verdict line, the log contains an internal Haskell
// backend crash —
//   "kore-exec: [...] Error (ErrorException): Assertion failed ...
//    called at src/Kore/Builtin/Krypto.hs:313:5 ..."
// — from the prover speculatively exploring an ECRECOVER-precompile
// hypothesis (via the trailing "..." match variable in #halt's continuation)
// with symbolic/empty-Bytes arguments, which trips a native assertion in the
// Krypto builtin. This reproduces identically for *any* claim on this
// definition whose destination does not unify trivially (confirmed with two
// independently-false claims: wrong <statusCode> and wrong <pc>; see
// docs/substrate.md, "Backend crash on any non-trivial residual goal").
// classify() still lands on the correct verdict here because its match is a
// plain substring search over the whole log and the terminal message survives
// the crash noise — but this is a real infrastructure wall worth knowing
// about, not an artifact of how this control spec was written.

requires "evm.md"

module REFUTE-EVM-SPEC
    imports EVM

    claim [refute]:
        <k> #execute => #halt ... </k>
        <mode> NORMAL </mode>
        <schedule> DEFAULT </schedule>
        <useGas> false </useGas>
        <output> _ => .Bytes </output>
        <statusCode> _ => EVMC_SUCCESS </statusCode>
        <program> #parseByteStack("00") </program>
        <jumpDests> #computeValidJumpDests(#parseByteStack("00")) </jumpDests>
        <id> 1234567890 </id>
        <caller> 999999999999 </caller>
        <callData> .Bytes </callData>
        <callValue> 0 </callValue>
        <wordStack> .WordStack </wordStack>
        <localMem> .Bytes </localMem>
        <pc> 0 => 999 </pc>
        <gas> 100000 </gas>
        <memoryUsed> 0 </memoryUsed>
        <callGas> 0 </callGas>
        <static> false </static>
        <callDepth> 0 </callDepth>
        <codeAddr> 1234567890 </codeAddr>
     [label(refute), all-path]

endmodule
