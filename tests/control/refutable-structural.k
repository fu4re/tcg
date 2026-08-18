// Control spec (b'): REFUTABLE, structural non-unification, no backend crash.
//
// refutable.k (the original false claim, wrong <pc>) reaches its verdict
// only after a Krypto/ECRECOVER backend crash (docs/substrate.md §5) — the
// crash aborts the search before kore-exec prints any WarnStuckClaimState
// preamble at all, so that log alone cannot demonstrate the "doesn't unify"
// variant of the warning, only the bare generic trailer.
//
// This spec avoids the crash by closing the <k> cell's RHS (no trailing
// "..."): claiming the fully-executed state's <k> cell is literally the
// bare, unexecuted STOP opcode -- never true, since STOP always steps to
// #end/#halt. With no open trailing match-variable to invite the backend's
// speculative ECRECOVER-hypothesis exploration (docs/substrate.md §5), the
// search terminates cleanly and kore-exec explicitly reports the destination
// term does NOT unify -- the other half of WarnStuckClaimState, and the one
// classify() must still route to Refute (see docs/substrate.md §4a and
// tcg/commands/prove.py).
//
// Run directly:
//   kprove tests/control/refutable-structural.k \
//     --definition ~/toolchains/kevm-1.0.678/haskell \
//     --spec-module REFUTE-CLOSED2-SPEC \
//     -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
//     -I ~/toolchains/kevm-1.0.678/plugin
//
// Expected: exit 1, no crash trace, log contains:
//   kore-exec: [...] Warning (WarnStuckClaimState):
//       The configuration's term doesn't unify with the destination's term
//       and the configuration cannot be rewritten further.
// See tests/control/logs/refutable-structural.log.

requires "evm.md"

module REFUTE-CLOSED2-SPEC
    imports EVM

    claim [refute]:
        <k> #execute => STOP </k>
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
        <pc> 0 </pc>
        <gas> 100000 </gas>
        <memoryUsed> 0 </memoryUsed>
        <callGas> 0 </callGas>
        <static> false </static>
        <callDepth> 0 </callDepth>
        <codeAddr> 1234567890 </codeAddr>
     [label(refute), all-path]

endmodule
