claim [r2a]:
    <k> #execute => #halt </k>
    <mode> NORMAL </mode>
    <schedule> DEFAULT </schedule>
    <useGas> false </useGas>
    <output> _ => .Bytes </output>
    <statusCode> _ => EVMC_SUCCESS </statusCode>
    <program> #parseByteStack("6000600060006000600060C86000F100") </program>
    <jumpDests> #computeValidJumpDests(#parseByteStack("6000600060006000600060C86000F100")) </jumpDests>
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
      <code> CODE </code>
      <storage> 0 |-> 100 => 0 |-> 105 </storage>
      ...
    </account>
 [label(r2a), all-path]
