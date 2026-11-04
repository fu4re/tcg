// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_full: the union of phi_auth, phi_consent, phi_frob, phi_frob_guards, phi_fold, phi_move_flux, phi_grab_heal_suck and phi_books, each check textually identical to its source spec.
contract Spec is Vat {
    constructor() {}

    /// A non-ward cannot authorise anyone (must-revert).
    function check_rely_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        rely(a);
        assert(false);
    }

    /// A non-ward cannot deauthorise anyone (must-revert).
    function check_deny_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    /// A non-ward cannot register a collateral type (must-revert).
    function check_init_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    /// A non-ward cannot set a global parameter (must-revert).
    function check_file_global_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, uint256(dx));
        assert(false);
    }

    /// A non-ward cannot set a collateral-type parameter (must-revert).
    function check_file_ilk_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, i, uint256(dx));
        assert(false);
    }

    /// A non-ward cannot create or destroy free collateral (must-revert).
    function check_slip_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    /// A non-ward cannot confiscate a vault (must-revert).
    function check_grab_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    /// A non-ward cannot create unbacked stablecoin (must-revert).
    function check_suck_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    /// A non-ward cannot update a rate (must-revert).
    function check_fold_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    /// A non-ward cannot shut the system down (must-revert).
    function check_cage_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

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

    /// Global (books balance, two keys): the stablecoin of two distinct addresses together is at most the total issued.
    function check_two_dai_within_debt(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        assert(dai[a] + dai[b] <= debt);
    }

    /// Global (books balance, two keys): the sin of two distinct addresses together is at most the total unbacked debt.
    function check_two_sin_within_vice(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        assert(sin[a] + sin[b] <= vice);
    }

    /// Global (books balance): the total unbacked debt is at most the total issued.
    function check_vice_within_debt(address a, address b, uint256 x, uint256 y) external {
        assert(vice <= debt);
    }
}
