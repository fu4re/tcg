// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_frob_guards: after a successful frob the ceilings, safety and dust conditions hold; no frob when not live (intent 6, the no-effect part).
contract Spec is Vat {
    constructor() {}

    /// After a frob that draws debt, the type's debt is within its ceiling and the total within the global ceiling.
    function check_frob_within_ceilings(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
        assert(debt <= Line);
    }

    /// After a frob that makes the vault riskier, its debt is within its collateral valued at the price.
    function check_frob_riskier_is_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 || dx < 0);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
    }

    /// After a frob, the vault has no debt or at least dust.
    function check_frob_not_dusty(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
    }

    /// No frob while the system is not live (must-revert).
    function check_frob_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }
}
