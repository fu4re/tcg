// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_frob: per-transition accounting of frob (intent 6, the exact-amount part).
contract Spec is Vat {
    constructor() {}

    /// frob changes u's vault by exactly (dx, dy); collateral source and stablecoin destination = msg.sender.
    function check_frob_urn_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) + dx);
        assert(int256(urns[i][u].art) == int256(art0) + dy);
    }

    /// frob changes the type's total normalised debt by exactly dy and leaves its rate unchanged.
    function check_frob_ilk_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 Art0 = ilks[i].Art;
        uint256 rate0 = ilks[i].rate;
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(int256(ilks[i].Art) == int256(Art0) + dy);
        assert(ilks[i].rate == rate0);
    }

    /// frob takes exactly dx of free collateral from the source (msg.sender).
    function check_frob_gem_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 gem0 = gem[i][msg.sender];
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(int256(gem[i][msg.sender]) == int256(gem0) - dx);
    }

    /// frob credits the destination (msg.sender) and the total issued by exactly rate * dy.
    function check_frob_dai_debt_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 dai0 = dai[msg.sender];
        uint256 debt0 = debt;
        uint256 rate0 = ilks[i].rate;
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(int256(dai[msg.sender]) == int256(dai0) + int256(rate0) * dy);
        assert(int256(debt) == int256(debt0) + int256(rate0) * dy);
    }
}
