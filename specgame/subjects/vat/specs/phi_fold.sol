// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_fold: rate update accounting (intent 10).
contract Spec is Vat {
    constructor() {}

    /// fold changes the type's rate by exactly dx and leaves its total normalised debt unchanged.
    function check_fold_rate_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 rate0 = ilks[i].rate;
        uint256 Art0 = ilks[i].Art;
        fold(i, u, dx);
        assert(int256(ilks[i].rate) == int256(rate0) + dx);
        assert(ilks[i].Art == Art0);
    }

    /// fold credits u and the total issued by exactly Art * dx.
    function check_fold_dai_debt_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        uint256 Art0 = ilks[i].Art;
        fold(i, u, dx);
        assert(int256(dai[u]) == int256(dai0) + int256(Art0) * dx);
        assert(int256(debt) == int256(debt0) + int256(Art0) * dx);
    }

    /// No fold while the system is not live (must-revert).
    function check_fold_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        fold(i, u, dx);
        assert(false);
    }
}
