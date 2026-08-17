// Control spec (a): PROVABLE.
//
// Claim: executing a 1-byte program consisting of a single STOP opcode
// reaches <k> #halt ... </k> with <output> b"" and <statusCode> EVMC_SUCCESS.
// This is true, and this exact claim is what `tcg prove` iterated on against
// the real Haskell-backend kprove parser to find the minimal form that
// closes (see docs/substrate.md, "Iterating the provable claim").
//
// Every non-transitioning cell is given a *concrete* value (not left
// symbolic) — leaving cells like <codeAddr> or <static> unconstrained was
// found empirically to make the Haskell backend explore precompiled-contract
// dispatch branches (ECRECOVER) during implication-checking, which crashes a
// native Krypto builtin on symbolic/empty-Bytes input (see docs/substrate.md,
// "Backend crash on underspecified state"). Fully concretizing the call
// frame avoids that branch entirely for this claim.
//
// Run directly:
//   kprove tests/control/provable.k \
//     --definition ~/toolchains/kevm-1.0.678/haskell \
//     --spec-module STOP-EVM-SPEC \
//     -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
//     -I ~/toolchains/kevm-1.0.678/plugin
//
// Expected: exit 0, stdout "#Top". See tests/control/logs/provable.log.

requires "evm.md"

module STOP-EVM-SPEC
    imports EVM

    claim [stop]:
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
        <pc> 0 </pc>
        <gas> 100000 </gas>
        <memoryUsed> 0 </memoryUsed>
        <callGas> 0 </callGas>
        <static> false </static>
        <callDepth> 0 </callDepth>
        <codeAddr> 1234567890 </codeAddr>
     [label(stop), all-path]

endmodule
