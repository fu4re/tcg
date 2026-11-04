You write formal specifications for a Solidity token contract. A specification
is one Solidity file in a fixed harness format. It is checked by the Solidity
SMTChecker (CHC engine, z3) against the token, and it is also run, as a test
probe, against faulty variants of the token. Follow the format exactly: a file
that breaks a format rule is rejected without being checked.

# The harness format

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_<name>(address a, address b, uint256 x, uint256 y) external {
        require(...);    // Pre: zero or more leading require statements
        ...              // read token state, call token functions
        assert(...);     // Post: one or more asserts
    }
}
```

- `Spec` inherits the token. A check calls the token's functions internally
  (`mint(a, x)`, `transfer(a, x)`, never `this.mint(...)`), so inside the token
  `msg.sender` is the address that called the check.
- Every check has exactly the signature
  `check_<name>(address a, address b, uint256 x, uint256 y) external`.
  The four parameters are free inputs; any of them may go unused.
- Pre is the leading block of `require(...)` statements of a check; the
  asserts are its conclusion. The specification is the conjunction, over its
  checks, of "Pre implies the asserts".

# How a check is judged

- The checker proves each assert for every reachable state of the token
  (any deployment, any sequence of earlier calls by any senders) and every
  value of the check's parameters and `msg.sender`. The specification is
  accepted only if every assert is proved; an assert that can fail, or that
  the checker cannot decide within its time budget, means not accepted.
- When the check is run on a token variant, a failed assert is a violation.
  A revert anywhere in the check, including a `require` inside a token
  function the check calls, means the Pre was not met: not a violation.
- Consequences:
  - An assert placed after a token call is only reached if that call
    succeeded. "This call must revert" can therefore be stated: put an assert
    after the call that fails whenever the call had an effect. Example (no
    overdraft):

    ```solidity
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);   // unreachable if transfer reverts as it should
    }
    ```

  - "This call must succeed" cannot be stated: a revert is never a violation.
  - An assert after `require(false)`, or after a Pre that can never hold, is
    trivially proved and says nothing.

# Format rules (a file that breaks one is rejected)

S1. Exactly one pragma: `pragma solidity 0.8.35;`.
S2. Exactly one import: `import "./CappedToken.sol";`.
S3. The only top-level declaration is `contract Spec is CappedToken { ... }`
    (no other contracts, interfaces, libraries or free functions).
S4. Members of `Spec`: exactly the constructor
    `constructor(uint256 cap_) CappedToken(cap_) {}` and one or more
    `check_*` functions with the fixed signature. Nothing else: no state
    variables, no helper functions, no modifiers, events or errors, no
    overrides of token functions.
S5. None of these words may appear (outside comments and strings):
    assembly this super new delete selfdestruct payable storage memory
    calldata try catch revert emit event error modifier override virtual
    fallback receive for while do unchecked gasleft blockhash block tx
    interface library struct enum mapping using constant immutable public
    private internal view pure returns return
S6. Member access only as `msg.sender` and `type(T).max` / `type(T).min`.
S7. Never write to token state (`=`, `+=`, `++`, `delete`, ...), no tuple
    assignment, and no local variable that shadows a token name or one of
    `a`, `b`, `x`, `y`.
S8. Calls only to the token's public functions, `require`, `assert`,
    `type(...)` and elementary type conversions such as `uint256(...)`.
S9. `require` only in the leading block of a check; at least one `assert`
    per check; each `assert(` starts its own line, one per line; every check
    reads token state or calls a token function.

Local variables (`uint256 s0 = totalSupply;`, `bool ok = transfer(a, x);`)
and `if` statements are allowed.

# Examples

The trivially true specification (accepted, but it says nothing):

```solidity
    function check_trivially_true(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply == totalSupply);
    }
```

A check with content (minting never changes the owner):

```solidity
    function check_mint_keeps_owner(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        mint(a, x);
        assert(owner == o0);
    }
```

# Your reply

Reply with the complete specification file in exactly one fenced code block
marked `solidity`. Any text outside that block is ignored. A reply with no
such block, or with more than one, is rejected.
