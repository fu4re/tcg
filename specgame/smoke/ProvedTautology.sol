// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// WP0 smoke harness (b), in the spec format of specs/SPEC_FORMAT.md:
/// a tautological assert on a reachable path. Expected Check verdict: Accept.
/// The path is the same as in ReachableFalse.sol, whose counterexample shows
/// that it is reachable, so this proof is not vacuous.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_tautology(address a, address b, uint256 x, uint256 y) external {
        require(x > 5);
        assert(totalSupply == totalSupply);
    }
}
