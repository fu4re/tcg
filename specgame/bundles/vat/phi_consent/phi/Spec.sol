// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_consent: moving value or adding risk needs the owner's consent; hope/nope act on the caller only (intent 2).
contract Spec is Vat {
    constructor() {}

    /// Making u's vault riskier (more debt) needs u's consent (must-revert).
    function check_frob_needs_u_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    /// Taking collateral from v into a vault needs v's consent (must-revert).
    function check_frob_needs_v_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, msg.sender, u, msg.sender, dx, dy);
        assert(false);
    }

    /// Repaying debt out of w's stablecoin needs w's consent (must-revert).
    function check_frob_needs_w_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy < 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, msg.sender, msg.sender, u, dx, dy);
        assert(false);
    }

    /// Moving collateral and debt out of u's vault needs u's consent (must-revert).
    function check_fork_needs_src_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    /// Moving collateral and debt into u's vault needs u's consent (must-revert).
    function check_fork_needs_dst_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        fork(i, msg.sender, u, dx, dy);
        assert(false);
    }

    /// Moving u's free collateral needs u's consent (must-revert).
    function check_flux_needs_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        flux(i, u, msg.sender, uint256(dx));
        assert(false);
    }

    /// Moving a's stablecoin needs a's consent (must-revert).
    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        move(a, b, x);
        assert(false);
    }

    /// hope changes only the caller's own permission: msg.sender allows a, b's permissions stay.
    function check_hope_own_only(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 c0 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[b][a] == c0);
    }

    /// nope changes only the caller's own permission: msg.sender disallows a, b's permissions stay.
    function check_nope_own_only(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 c0 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[b][a] == c0);
    }
}
