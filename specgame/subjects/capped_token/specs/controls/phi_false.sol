// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// Negative control: an assert b violates (an owner mint can reach the cap
/// exactly). Expected: Refute with a parsed counterexample.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_below_cap_after_mint(address a, address b, uint256 x, uint256 y) external {
        require(x > 0);
        mint(a, x);
        assert(totalSupply < cap);
    }
}
