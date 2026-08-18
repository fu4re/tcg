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
// docs/substrate.md §5). The crash aborts the search before kore-exec can
// print a WarnStuckClaimState preamble at all -- this log has NEITHER
// variant of that warning, just the crash followed by the generic trailer --
// so it is kept as its own fixture, distinct from
// tests/control/refutable-structural.k (same false-claim shape, but closed
// so as to avoid the crash and show the actual "doesn't unify" warning
// text). classify() lands on the correct verdict for both, for different
// textual reasons; a crash is never itself a classification signal (see
// tcg/commands/prove.py).

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
