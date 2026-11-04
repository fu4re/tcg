// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// Fixture spec for the "might happen" (Unknown) classifier case: nonlinear
/// arithmetic that CHC cannot settle within a 1 ms query timeout.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_nonlinear(address a, address b, uint256 x, uint256 y) external {
        require(x > 1 && y > 1 && x < 2**64 && y < 2**64 && totalSupply > 1 && totalSupply < 2**64);
        assert(x * x * x + y * y * y != totalSupply * totalSupply * totalSupply);
    }
}
