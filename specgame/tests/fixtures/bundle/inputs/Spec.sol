// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// WP5 fixture spec: an owner mint adds exactly x to totalSupply, and the
/// supply never exceeds the cap. Kills "mint does not increase totalSupply"
/// and "cap check removed"; does not constrain transfer.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_mint_adds(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        uint256 s0 = totalSupply;
        mint(a, x);
        assert(totalSupply == s0 + x);
    }

    function check_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }
}
