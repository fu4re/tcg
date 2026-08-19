requires "evm.md"

module CALLER-DRAIN-SPEC
  imports EVM

  // Drain control: a leading STOP (byte 00) halts the caller at pc 0 BEFORE the
  // CALL. The callee never runs, A2.storage[0] stays 100, wordStack stays empty
  // -- yet R-drain asserts the +5 effect (105) and success (1). Structural
  // non-unification => Refute. The analogue of D3's drain.
  claim [rdrain]:
    <k> #execute => #halt </k>
    <mode> NORMAL </mode>
    <schedule> DEFAULT </schedule>
    <useGas> false </useGas>
    <output> _ => .Bytes </output>
    <statusCode> _ => EVMC_SUCCESS </statusCode>
    <program> #parseByteStack("006000600060006000600060C86000F100") </program>
    <jumpDests> #computeValidJumpDests(#parseByteStack("006000600060006000600060C86000F100")) </jumpDests>
    <id> 100 </id>
    <caller> 999999999999 </caller>
    <callData> .Bytes </callData>
    <callValue> 0 </callValue>
    <wordStack> .WordStack => 1 : .WordStack </wordStack>
    <localMem> .Bytes </localMem>
    <pc> 0 => ?_ </pc>
    <gas> 100000 => ?_ </gas>
    <memoryUsed> 0 => ?_ </memoryUsed>
    <callGas> _ => ?_ </callGas>
    <static> false </static>
    <callDepth> 0 </callDepth>
    <codeAddr> 100 </codeAddr>
    <touchedAccounts> _ => ?_ </touchedAccounts>
    <accessedAccounts> _ => ?_ </accessedAccounts>
    <account>
      <acctID> 100 </acctID>
      <balance> 0 </balance>
      <storage> .Map </storage>
      ...
    </account>
    <account>
      <acctID> 200 </acctID>
      <balance> 0 </balance>
      <code> #parseByteStack("60005460050160005500") </code>
      <storage> 0 |-> 100 => 0 |-> 105 </storage>
      ...
    </account>
 [label(rdrain), all-path]

endmodule
