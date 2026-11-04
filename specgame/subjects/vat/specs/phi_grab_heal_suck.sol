// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_grab_heal_suck: confiscation, settlement and unbacked-debt accounting (intent 8, 9).
contract Spec is Vat {
    constructor() {}

    /// grab changes u's vault by (dx, dy) and the type's total normalised debt by dy.
    function check_grab_urn_ilk_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        grab(i, u, u, msg.sender, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) + dx);
        assert(int256(urns[i][u].art) == int256(art0) + dy);
        assert(int256(ilks[i].Art) == int256(Art0) + dy);
    }

    /// grab moves exactly dx of collateral between the vault and the named address (u).
    function check_grab_gem_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 gem0 = gem[i][u];
        grab(i, u, u, msg.sender, dx, dy);
        assert(int256(gem[i][u]) == int256(gem0) - dx);
    }

    /// grab moves the debt, valued at the rate, to the named address's (msg.sender's) sin and to vice; debt unchanged.
    function check_grab_sin_vice_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 sin0 = sin[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 rate0 = ilks[i].rate;
        grab(i, u, u, msg.sender, dx, dy);
        assert(int256(sin[msg.sender]) == int256(sin0) - int256(rate0) * dy);
        assert(int256(vice) == int256(vice0) - int256(rate0) * dy);
        assert(debt == debt0);
    }

    /// heal cancels exactly x of the caller's stablecoin and sin and lowers vice and debt by x.
    function check_heal_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 sin0 = sin[msg.sender];
        uint256 dai0 = dai[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        heal(x);
        assert(sin[msg.sender] + x == sin0);
        assert(dai[msg.sender] + x == dai0);
        assert(vice + x == vice0);
        assert(debt + x == debt0);
    }

    /// suck raises sin[a], dai[b], vice and debt by exactly x.
    function check_suck_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 sin0 = sin[a];
        uint256 dai0 = dai[b];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        suck(a, b, x);
        assert(sin[a] == sin0 + x);
        assert(dai[b] == dai0 + x);
        assert(vice == vice0 + x);
        assert(debt == debt0 + x);
    }
}
