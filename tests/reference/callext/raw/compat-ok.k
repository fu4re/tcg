requires "evm.md"

module COMPAT-OK-SPEC
  imports EVM

  claim [compat]:
    <k> #execute => #halt </k>
    <mode> NORMAL </mode>
    <schedule> DEFAULT </schedule>
    <useGas> false </useGas>
    <output> _ => .Bytes </output>
    <statusCode> _ => EVMC_SUCCESS </statusCode>
    <program> #parseByteStack("60005460050160005500") </program>
    <jumpDests> #computeValidJumpDests(#parseByteStack("60005460050160005500")) </jumpDests>
    <id> 200 </id>
    <caller> 100 </caller>
    <callData> .Bytes </callData>
    <callValue> 0 </callValue>
    <wordStack> .WordStack </wordStack>
    <localMem> .Bytes </localMem>
    <pc> 0 => 9 </pc>
    <gas> 100000 </gas>
    <memoryUsed> 0 </memoryUsed>
    <callGas> 0 </callGas>
    <static> false </static>
    <callDepth> 0 </callDepth>
    <codeAddr> 200 </codeAddr>
    <account>
      <acctID> 100 </acctID>
      <storage> 1 |-> 42 </storage>
      ...
    </account>
    <account>
      <acctID> 200 </acctID>
      <storage> 0 |-> 100 => 0 |-> 105 </storage>
      ...
    </account>
 [label(compat), all-path]

endmodule
