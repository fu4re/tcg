requires "evm.md"

module BRIDGE-S-AT-P-SPEC
  imports EVM

  claim [sbridge]:
    <k> #execute => #halt </k>
    <mode> NORMAL </mode>
    <schedule> DEFAULT </schedule>
    <useGas> false </useGas>
    <output> _ => ?_ </output>
    <statusCode> _ => EVMC_SUCCESS </statusCode>
    <program> #parseByteStack("60005460050160005500") </program>
    <id> 200 </id>
    <caller> 100 </caller>
    <callData> .Bytes </callData>
    <callValue> 0 </callValue>
    <pc> 0 => ?_ </pc>
    <wordStack> .WordStack </wordStack>
    <localMem> .Bytes </localMem>
    <gas> 100000 => ?_ </gas>
    <memoryUsed> 0 => ?_ </memoryUsed>
    <static> false </static>
    <account>
      <acctID> 200 </acctID>
      <storage> 0 |-> 100 => 0 |-> 105 </storage>
      ...
    </account>
 [label(sbridge), all-path]

endmodule
