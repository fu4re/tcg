You write formal specifications for a Solidity contract, MakerDAO's Vat (the
accounting core of a collateralised stablecoin). A specification is one
Solidity file in a fixed harness format. It is checked by the Solidity
SMTChecker (CHC engine, z3) against the contract, and it is also run, as a
test probe, against faulty variants of the contract. Follow the format
exactly: a file that breaks a format rule is rejected without being checked.

# The harness format

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    function check_<name>(address a, address b, uint256 x, uint256 y) external {
        require(...);    // Pre: zero or more leading require statements
        ...              // read contract state, call contract functions
        assert(...);     // Post: one or more asserts
    }

    function check_<name>(bytes32 i, address u, int256 dx, int256 dy) external {
        ...
    }
}
```

- `Spec` inherits the contract. A check calls the contract's functions
  internally (`frob(i, u, u, u, dx, dy)`, `suck(a, b, x)`, never
  `this.frob(...)`), so inside the contract `msg.sender` is the address that
  called the check. The deployer of `Spec` is the contract's first ward.
- Every check has exactly one of the two signatures
  `check_<name>(address a, address b, uint256 x, uint256 y) external` or
  `check_<name>(bytes32 i, address u, int256 dx, int256 dy) external`.
  The parameters are free inputs; any of them may go unused.
- Pre is the leading block of `require(...)` statements of a check; the
  asserts are its conclusion. The specification is the conjunction, over its
  checks, of "Pre implies the asserts".
- Contract state is read directly: `debt`, `vice`, `Line`, `live`,
  `wards[usr]`, `can[owner][usr]`, `dai[usr]`, `sin[usr]`, `gem[ilk][usr]`,
  and struct fields after an index: `ilks[i].Art`, `ilks[i].rate`,
  `ilks[i].spot`, `ilks[i].line`, `ilks[i].dust`, `urns[i][u].ink`,
  `urns[i][u].art`. Collateral and normalised debt are in units of 10^18
  (wad), rates and prices 10^27 (ray), stablecoin, debt and ceilings 10^45
  (rad). A bytes32 such as a collateral type can be written as a string
  literal: `"GOLD"`.

# How a check is judged

- The checker proves each assert for every reachable state of the contract
  (any deployment, any sequence of earlier calls by any senders) and every
  value of the check's parameters and `msg.sender`. The specification is
  accepted only if every assert is proved; an assert that can fail, or that
  the checker cannot decide within its time budget, means not accepted.
- When the check is run on a contract variant, a failed assert is a
  violation. A revert anywhere in the check, including a `require` inside a
  contract function the check calls, means the Pre was not met: not a
  violation.
- Facts about the contract that matter here: its functions refuse invalid
  calls by reverting with a reason string ("Vat/not-authorized",
  "Vat/not-safe", ...); its arithmetic helpers `_add`, `_sub`, `_mul` compute
  without overflow checks and then `require` that no overflow happened, so an
  overflowing call simply reverts. Arithmetic you write in a check is checked
  by Solidity: an overflow there is a panic that counts neither as a
  violation nor as a pass, so keep your own arithmetic within range (for
  example compare `a + b == c + d` rather than subtracting).
- Consequences:
  - An assert placed after a contract call is only reached if that call
    succeeded. "This call must revert" can therefore be stated: put an assert
    after the call that fails whenever the call had an effect. Example (an
    unregistered collateral type cannot be used in a vault):

    ```solidity
    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);   // unreachable if frob reverts as it should
    }
    ```

  - "This call must succeed" cannot be stated: a revert is never a violation.
  - An assert after `require(false)`, or after a Pre that can never hold, is
    trivially proved and says nothing.

# Format rules (a file that breaks one is rejected)

S1. Exactly one pragma: `pragma solidity 0.8.35;`.
S2. Exactly one import: `import "./Vat.sol";`.
S3. The only top-level declaration is `contract Spec is Vat { ... }`
    (no other contracts, interfaces, libraries or free functions).
S4. Members of `Spec`: exactly the constructor `constructor() {}` and one or
    more `check_*` functions with one of the two fixed signatures. Nothing
    else: no state variables, no helper functions, no modifiers, events or
    errors, no overrides of contract functions.
S5. None of these words may appear (outside comments and strings):
    assembly this super new delete selfdestruct payable storage memory
    calldata try catch revert emit event error modifier override virtual
    fallback receive for while do unchecked gasleft blockhash block tx
    interface library struct enum mapping using constant immutable public
    private internal view pure returns return
S6. Member access only as `msg.sender`, `type(T).max` / `type(T).min`, and a
    struct field of the contract read after an index (`ilks[i].rate`).
S7. Never write to contract state (`=`, `+=`, `++`, `delete`, ...), also not
    to a struct field; no tuple assignment; no local variable that shadows a
    contract name, a struct field name (`Art`, `rate`, `spot`, `line`,
    `dust`, `ink`, `art`) or a check parameter (`a`, `b`, `x`, `y`, `i`, `u`,
    `dx`, `dy`).
S8. Calls only to the contract's public functions, `require`, `assert`,
    `type(...)` and elementary type conversions such as `uint256(...)`,
    `int256(...)`, `bytes32(...)`.
S9. `require` only in the leading block of a check; at least one `assert`
    per check; each `assert(` starts its own line, one per line; every check
    reads contract state or calls a contract function.

Local variables (`uint256 d0 = debt;`) and `if` statements are allowed.

# Examples

The trivially true specification (accepted, but it says nothing):

```solidity
    function check_trivially_true(address a, address b, uint256 x, uint256 y) external {
        assert(debt == debt);
    }
```

A check with content (a ward setting the global debt ceiling sets exactly
that value):

```solidity
    function check_file_sets_line(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
    }
```

# Your reply

Reply with the complete specification file in exactly one fenced code block
marked `solidity`. Any text outside that block is ignored. A reply with no
such block, or with more than one, is rejected.
