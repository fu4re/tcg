// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// Dead control: a require(false)-guarded check. Expected: Accept (the
/// assert is unreachable, reported safe) and vacuity check (a) flags it.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_dead(address a, address b, uint256 x, uint256 y) external {
        require(false);
        assert(totalSupply == 0);
    }
}
