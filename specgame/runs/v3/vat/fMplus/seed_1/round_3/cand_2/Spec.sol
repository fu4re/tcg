// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 wb = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == wb);
        assert(live == 1);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 wb = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == wb);
        assert(live == 1);
    }

    function check_rely_not_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        rely(a);
        assert(false);
    }

    function check_deny_not_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        deny(a);
        assert(false);
    }

    function check_rely_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    function check_deny_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        deny(a);
        assert(false);
    }

    function check_init_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        init(i);
        assert(false);
    }

    function check_file_global_not_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        require(dx >= 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_file_ilk_line_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        require(dx >= 0);
        file(i, "line", uint256(dx));
        assert(false);
    }

    function check_file_ilk_dust_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        require(dx >= 0);
        file(i, "dust", uint256(dx));
        assert(false);
    }

    function check_cage_not_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        cage();
        assert(false);
    }

    function check_slip_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        slip(i, u, dx);
        assert(false);
    }

    function check_grab_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_suck_not_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        suck(a, b, x);
        assert(false);
    }

    function check_fold_not_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        fold(i, u, dx);
        assert(false);
    }

    // ---------------- Consent flags ----------------

    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 c0 = can[a][b];
        uint256 c1 = can[msg.sender][a];
        hope(b);
        assert(can[msg.sender][b] == 1);
        assert(can[a][b] == c0);
        if (a != b) {
            assert(can[msg.sender][a] == c1);
        }
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 c0 = can[a][b];
        uint256 c1 = can[msg.sender][a];
        nope(b);
        assert(can[msg.sender][b] == 0);
        assert(can[a][b] == c0);
        if (a != b) {
            assert(can[msg.sender][a] == c1);
        }
    }

    // ---------------- Collateral types ----------------

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 art0 = ilks[i].Art;
        uint256 sp0 = ilks[i].spot;
        uint256 li0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].line == li0);
        assert(ilks[i].dust == du0);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Parameters ----------------

    function check_file_line_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 d0 = debt;
        uint256 v0 = vice;
        file("Line", x);
        assert(Line == x);
        assert(debt == d0);
        assert(vice == v0);
        assert(live == 1);
    }

    function check_file_global_unknown(address a, address b, uint256 x, uint256 y) external {
        require(bytes32(x) != "Line");
        file(bytes32(x), y);
        assert(false);
    }

    function check_file_global_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_spot_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 art0 = ilks[i].Art;
        uint256 li0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 gl0 = Line;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == art0);
        assert(ilks[i].line == li0);
        assert(ilks[i].dust == du0);
        assert(Line == gl0);
    }

    function check_file_line_ilk_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 art0 = ilks[i].Art;
        uint256 sp0 = ilks[i].spot;
        uint256 du0 = ilks[i].dust;
        uint256 gl0 = Line;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].dust == du0);
        assert(Line == gl0);
    }

    function check_file_dust_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 art0 = ilks[i].Art;
        uint256 sp0 = ilks[i].spot;
        uint256 li0 = ilks[i].line;
        uint256 gl0 = Line;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].line == li0);
        assert(Line == gl0);
    }

    function check_file_ilk_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        require(dx >= 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    // ---------------- Shutdown ----------------

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_stays_caged_frob(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_stays_caged_fold(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_not_live_zero(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, 0);
        assert(false);
    }

    function check_frob_not_live_zero(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, 0, 0);
        assert(false);
    }

    // ---------------- Free collateral ----------------

    function check_slip_add(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 g0 = gem[i][u];
        uint256 d0 = debt;
        slip(i, u, dx);
        assert(gem[i][u] >= g0);
        assert(gem[i][u] == g0 + uint256(dx));
        assert(debt == d0);
    }

    function check_slip_sub(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] <= g0);
        assert(g0 - gem[i][u] == uint256(-dx));
    }

    function check_slip_frame(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        uint256 g0 = gem[i][msg.sender];
        uint256 s0 = dai[u];
        slip(i, u, dx);
        assert(gem[i][msg.sender] == g0);
        assert(dai[u] == s0);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        bytes32 k = bytes32(y);
        uint256 ga = gem[k][a];
        uint256 gb = gem[k][b];
        uint256 da = dai[a];
        uint256 d0 = debt;
        flux(k, a, b, x);
        assert(gem[k][a] <= ga);
        assert(gem[k][b] >= gb);
        assert(gem[k][b] == gb + x);
        assert(dai[a] == da);
        assert(debt == d0);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        require(a == b);
        bytes32 k = bytes32(y);
        uint256 ga = gem[k][a];
        flux(k, a, b, x);
        assert(gem[k][a] == ga);
    }

    function check_flux_other_ilk(address a, address b, uint256 x, uint256 y) external {
        require(bytes32(y) != "GOLD");
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        flux(bytes32(y), a, b, x);
        assert(gem["GOLD"][a] == ga);
        assert(gem["GOLD"][b] == gb);
    }

    function check_flux_no_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        flux(bytes32(y), a, b, x);
        assert(false);
    }

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 d0 = debt;
        uint256 v0 = vice;
        move(a, b, x);
        assert(dai[a] <= da);
        assert(dai[b] >= db);
        assert(dai[b] == db + x);
        assert(debt == d0);
        assert(vice == v0);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        require(a == b);
        uint256 da = dai[a];
        move(a, b, x);
        assert(dai[a] == da);
    }

    function check_move_no_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vault operations ----------------

    function check_frob_collateral_pos(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dx < 2 ** 120);
        require(dy > -(2 ** 120) && dy < 2 ** 120);
        require(ilks[i].rate < 2 ** 128);
        uint256 ink0 = urns[i][u].ink;
        uint256 g0 = gem[i][msg.sender];
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].ink >= ink0);
        assert(gem[i][msg.sender] <= g0);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(gem[i][msg.sender] + uint256(dx) == g0);
    }

    function check_frob_collateral_neg(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > -(2 ** 120));
        require(dy > -(2 ** 120) && dy < 2 ** 120);
        require(ilks[i].rate < 2 ** 128);
        uint256 ink0 = urns[i][u].ink;
        uint256 g0 = gem[i][msg.sender];
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].ink <= ink0);
        assert(gem[i][msg.sender] >= g0);
        assert(gem[i][msg.sender] - g0 == uint256(-dx));
    }

    function check_frob_debt_pos(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 120) && dx < 2 ** 120);
        require(dy >= 0 && dy < 2 ** 120);
        require(ilks[i].rate < 2 ** 128);
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 d0 = dai[msg.sender];
        uint256 debt0 = debt;
        uint256 v0 = vice;
        uint256 r0 = ilks[i].rate;
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].art >= art0);
        assert(ilks[i].Art >= tot0);
        assert(dai[msg.sender] >= d0);
        assert(debt >= debt0);
        assert(ilks[i].rate == r0);
        assert(vice == v0);
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == tot0 + uint256(dy));
        assert(dai[msg.sender] == d0 + r0 * uint256(dy));
        assert(debt == debt0 + r0 * uint256(dy));
    }

    function check_frob_debt_neg(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 120) && dx < 2 ** 120);
        require(dy < 0 && dy > -(2 ** 120));
        require(ilks[i].rate < 2 ** 128);
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 d0 = dai[msg.sender];
        uint256 debt0 = debt;
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].art <= art0);
        assert(ilks[i].Art <= tot0);
        assert(dai[msg.sender] <= d0);
        assert(debt <= debt0);
    }

    function check_frob_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ilk_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(ilks[i].rate < 2 ** 128 && ilks[i].Art < 2 ** 100);
        require((ilks[i].Art + uint256(dy)) * ilks[i].rate > ilks[i].line);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_global_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(ilks[i].rate < 2 ** 128 && debt < 2 ** 200);
        require(debt + ilks[i].rate * uint256(dy) > Line);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_unsafe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(dx >= 0 && dx < 2 ** 100);
        require(ilks[i].rate < 2 ** 128 && ilks[i].spot < 2 ** 128);
        require(urns[i][u].ink < 2 ** 100 && urns[i][u].art < 2 ** 100);
        require((urns[i][u].art + uint256(dy)) * ilks[i].rate > (urns[i][u].ink + uint256(dx)) * ilks[i].spot);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_u_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        frob(i, u, msg.sender, msg.sender, 0, dy);
        assert(false);
    }

    function check_frob_no_consent_u_ink(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        frob(i, u, msg.sender, msg.sender, dx, 0);
        assert(false);
    }

    function check_frob_no_consent_u_self(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        require(x > 0 && x < 2 ** 100);
        frob(bytes32(y), a, a, a, 0, int256(x));
        assert(false);
    }

    function check_frob_no_consent_v(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        require(x > 0 && x < 2 ** 100);
        frob(bytes32(y), msg.sender, a, msg.sender, int256(x), 0);
        assert(false);
    }

    function check_frob_no_consent_w(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        require(y > 0 && y < 2 ** 100);
        frob(bytes32(x), msg.sender, msg.sender, a, 0, -int256(y));
        assert(false);
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(ilks[i].rate < 2 ** 128 && urns[i][u].art < 2 ** 100);
        require((urns[i][u].art + uint256(dy)) * ilks[i].rate < ilks[i].dust);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    // ---------------- Fork (consent) ----------------

    function check_fork_no_consent_src(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_no_consent_dst(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        fork(i, msg.sender, u, dx, dy);
        assert(false);
    }

    function check_fork_no_consent_self(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        fork(bytes32(y), a, a, 0, 0);
        assert(false);
    }

    // ---------------- Confiscation ----------------

    function check_grab_collateral(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dx < 2 ** 120);
        uint256 g0 = gem[i][msg.sender];
        uint256 d0 = debt;
        grab(i, u, msg.sender, msg.sender, dx, 0);
        assert(gem[i][msg.sender] <= g0);
        assert(g0 - gem[i][msg.sender] == uint256(dx));
        assert(debt == d0);
    }

    function check_grab_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy >= 0 && dy < 2 ** 120);
        uint256 s0 = sin[msg.sender];
        uint256 v0 = vice;
        uint256 d0 = debt;
        grab(i, u, msg.sender, msg.sender, 0, dy);
        assert(sin[msg.sender] <= s0);
        assert(vice <= v0);
        assert(debt == d0);
    }

    // ---------------- Settlement and unbacked debt ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        heal(x);
        assert(sin[msg.sender] <= s0);
        assert(dai[msg.sender] <= d0);
        assert(vice <= v0);
        assert(debt <= t0);
        assert(s0 - sin[msg.sender] == x);
        assert(d0 - dai[msg.sender] == x);
        assert(v0 - vice == x);
        assert(t0 - debt == x);
    }

    function check_heal_frame(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = sin[a];
        uint256 d0 = dai[a];
        heal(x);
        assert(sin[a] == s0);
        assert(dai[a] == d0);
    }

    function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[a];
        uint256 d0 = dai[b];
        uint256 v0 = vice;
        uint256 t0 = debt;
        suck(a, b, x);
        assert(sin[a] >= s0);
        assert(dai[b] >= d0);
        assert(vice >= v0);
        assert(debt >= t0);
        assert(sin[a] == s0 + x);
        assert(dai[b] == d0 + x);
        assert(vice == v0 + x);
        assert(debt == t0 + x);
    }

    function check_suck_frame(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 s0 = sin[b];
        uint256 d0 = dai[a];
        suck(a, b, x);
        assert(sin[b] == s0);
        assert(dai[a] == d0);
    }

    // ---------------- Rates ----------------

    function check_fold_pos(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dx < 2 ** 120);
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        uint256 v0 = vice;
        fold(i, u, dx);
        assert(dai[u] >= d0);
        assert(debt >= t0);
        assert(vice == v0);
    }

    function check_fold_neg(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > -(2 ** 120));
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        fold(i, u, dx);
        assert(dai[u] <= d0);
        assert(debt <= t0);
    }
}
