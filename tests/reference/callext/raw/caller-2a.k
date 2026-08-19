requires "evm.md"

module CALLER-2A-SPEC
  imports EVM

  // Abstract callee summary S (TRUSTED). Pins the callee ENTRY state exactly as
  // KEVM's #mkCall/#initVM produces it (pc 0, empty stack/mem, caller 100, args
  // empty, value 0, static false) so S is the SOUND summary of D's precondition;
  // the ONLY abstracted cell is <program> _PGM (free), which unifies with the
  // stalled symbolic callee code. Binding _PGM to the concrete callee code P is
  // the bridge obligation S<==D, discharged by D (proved over concrete P) plus
  // the code-identity binding code(200)=P. S rewrites #execute => #halt with the
  // +5 delta and EVMC_SUCCESS.
  claim [s]:
    <k> #execute => #halt ... </k>
    <mode> NORMAL </mode>
    <schedule> DEFAULT </schedule>
    <useGas> false </useGas>
    <statusCode> _ => EVMC_SUCCESS </statusCode>
    <program> _PGM </program>
    <id> 200 </id>
    <caller> 100 </caller>
    <callData> .Bytes </callData>
    <callValue> 0 </callValue>
    <pc> 0 </pc>
    <wordStack> .WordStack </wordStack>
    <localMem> .Bytes </localMem>
    <static> false </static>
    <account>
      <acctID> 200 </acctID>
      <storage> 0 |-> 100 => 0 |-> 105 </storage>
      ...
    </account>
 [label(s), all-path, trusted]

  // Caller root R: A2 (200) code is SYMBOLIC (variable CODE). R asserts
  // A2.storage[0]==105 -- a fact the caller never computes; closable only by
  // consuming S as a circularity at the CALL into the symbolic-code frame.
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

endmodule
