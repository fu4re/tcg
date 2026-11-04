// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// WP0 smoke harness (c), in the spec format of specs/SPEC_FORMAT.md:
/// assert(false) after a satisfiable require. Expected Check verdict: Refute
/// with some x > 5, which `make check` replays on pyrevm as a witness.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_reachable(address a, address b, uint256 x, uint256 y) external {
        require(x > 5);
        assert(false);
    }
}
