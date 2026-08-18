claim [drain]:
    <k> #execute => #halt </k>
    <mode> NORMAL </mode>
    <schedule> DEFAULT </schedule>
    <useGas> false </useGas>
    <output> _ => .Bytes </output>
    <statusCode> _ => EVMC_SUCCESS </statusCode>
    <program> #parseByteStack("006046600055") </program>
    <jumpDests> #computeValidJumpDests(#parseByteStack("006046600055")) </jumpDests>
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
    <account>
      <acctID> 1234567890 </acctID>
      <storage> 0 |-> 100 => 0 |-> 70 </storage>
      ...
    </account>
 [label(drain), all-path]
