// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// phi_top: the trivially true specification (Pre true, every conclusion a
/// tautology). Kill set is empty by construction. kappa = 0: reflexive
/// equality holds in every state and for every token behaviour, so the assert
/// proves over the havoc base H (protocol.md section 11).
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    /// Reflexive equality on token state: true in every state.
    function check_top(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply == totalSupply);
    }
}
