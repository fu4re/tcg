// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// phi_cap: total supply never exceeds the cap.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    /// totalSupply <= cap holds in every reachable state.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    /// totalSupply <= cap holds after any successful mint.
    function check_cap_after_mint(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }
}
