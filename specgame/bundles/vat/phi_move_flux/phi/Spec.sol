// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_move_flux: exact movement and conservation of stablecoin and free collateral (intent 5).
contract Spec is Vat {
    constructor() {}

    /// move between two addresses changes exactly the two balances by exactly x.
    function check_move_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 a0 = dai[a];
        uint256 b0 = dai[b];
        move(a, b, x);
        assert(dai[a] + x == a0);
        assert(dai[b] == b0 + x);
    }

    /// move to oneself leaves the balance unchanged.
    function check_move_self_unchanged(address a, address b, uint256 x, uint256 y) external {
        require(a == b);
        uint256 a0 = dai[a];
        move(a, b, x);
        assert(dai[a] == a0);
    }

    /// move leaves a third balance (the caller's) and the total issued unchanged.
    function check_move_others_and_debt_unchanged(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != a);
        require(msg.sender != b);
        uint256 s0 = dai[msg.sender];
        uint256 debt0 = debt;
        move(a, b, x);
        assert(dai[msg.sender] == s0);
        assert(debt == debt0);
    }

    /// flux from the caller to another address changes exactly the two collateral balances by exactly dx.
    function check_flux_exact(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        require(u != msg.sender);
        uint256 s0 = gem[i][msg.sender];
        uint256 u0 = gem[i][u];
        flux(i, msg.sender, u, uint256(dx));
        assert(gem[i][msg.sender] + uint256(dx) == s0);
        assert(gem[i][u] == u0 + uint256(dx));
    }
}
