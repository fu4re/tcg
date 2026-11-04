// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_top: the trivially true specification.
contract Spec is Vat {
    constructor() {}

    /// Trivially true (phi_top).
    function check_top(address a, address b, uint256 x, uint256 y) external {
        assert(debt == debt);
    }
}
