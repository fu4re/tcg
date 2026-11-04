// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        rely(a);
        assert(false);
    }

    function check_deny_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_init_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    function check_file_line_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_cage_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

    function check_slip_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    function check_grab_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_suck_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    function check_fold_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    function check_rely_sets(address a, address b, uint256 x, uint256 y) external {
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        if (b != a)
            assert(wards[b] == w0);
    }

    function check_deny_sets(address a, address b, uint256 x, uint256 y) external {
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        if (b != a)
            assert(wards[b] == w0);
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

    // ---------------- Consent ----------------

    function check_hope_sets(address a, address b, uint256 x, uint256 y) external {
        uint256 c0 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        if (b != msg.sender)
            assert(can[b][a] == c0);
    }

    function check_nope_sets(address a, address b, uint256 x, uint256 y) external {
        uint256 c0 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        if (b != msg.sender)
            assert(can[b][a] == c0);
    }

    // ---------------- Collateral types ----------------

    function check_init_sets(bytes32 i, address u, int256 dx, int256 dy) external {
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

    function check_file_sets_line(address a, address b, uint256 x, uint256 y) external {
        uint256 d0 = debt;
        file("Line", x);
        assert(Line == x);
        assert(debt == d0);
        assert(live == 1);
    }

    function check_file_line_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_unknown_param(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_sets_spot(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = ilks[i].Art;
        uint256 ra0 = ilks[i].rate;
        uint256 li0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 L0 = Line;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].Art == art0);
        assert(ilks[i].rate == ra0);
        assert(ilks[i].line == li0);
        assert(ilks[i].dust == du0);
        assert(Line == L0);
    }

    function check_file_sets_ilk_line(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = ilks[i].Art;
        uint256 ra0 = ilks[i].rate;
        uint256 sp0 = ilks[i].spot;
        uint256 du0 = ilks[i].dust;
        uint256 L0 = Line;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].Art == art0);
        assert(ilks[i].rate == ra0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].dust == du0);
        assert(Line == L0);
    }

    function check_file_sets_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = ilks[i].Art;
        uint256 ra0 = ilks[i].rate;
        uint256 sp0 = ilks[i].spot;
        uint256 li0 = ilks[i].line;
        uint256 L0 = Line;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].Art == art0);
        assert(ilks[i].rate == ra0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].line == li0);
        assert(Line == L0);
    }

    function check_file_ilk_unknown_param(bytes32 i, address u, int256 dx, int256 dy) external {
        file(i, "unknown", uint256(dx));
        assert(false);
    }

    function check_file_ilk_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    // ---------------- Shutdown ----------------

    function check_cage_sets(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_cage_stays_dead_frob(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_cage_stays_dead_fold(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }

    // ---------------- Free collateral ----------------

    function check_slip_pos(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 g0 = gem[i][u];
        uint256 s0 = gem[i][msg.sender];
        uint256 d0 = debt;
        slip(i, u, dx);
        assert(gem[i][u] == g0 + uint256(dx));
        assert(debt == d0);
        if (u != msg.sender)
            assert(gem[i][msg.sender] == s0);
    }

    function check_slip_neg(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        uint256 g0 = gem[i][u];
        uint256 s0 = gem[i][msg.sender];
        slip(i, u, dx);
        assert(gem[i][u] + uint256(-dx) == g0);
        if (u != msg.sender)
            assert(gem[i][msg.sender] == s0);
    }

    function check_flux_moves(address a, address b, uint256 x, uint256 y) external {
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 gs = gem["GOLD"][msg.sender];
        uint256 go = gem["SILVER"][a];
        uint256 da = dai[a];
        uint256 d0 = debt;
        flux("GOLD", a, b, x);
        if (a != b) {
            assert(gem["GOLD"][a] + x == ga);
            assert(gem["GOLD"][b] == gb + x);
        } else {
            assert(gem["GOLD"][a] == ga);
        }
        if (msg.sender != a && msg.sender != b)
            assert(gem["GOLD"][msg.sender] == gs);
        assert(gem["SILVER"][a] == go);
        assert(dai[a] == da);
        assert(debt == d0);
    }

    function check_flux_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        flux(i, u, msg.sender, uint256(dx));
        assert(false);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(gem["GOLD"][a] < x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(gem["GOLD"][b] > type(uint256).max - x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    // ---------------- Free dai ----------------

    function check_move_moves(address a, address b, uint256 x, uint256 y) external {
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 ds = dai[msg.sender];
        uint256 sa = sin[a];
        uint256 ga = gem["GOLD"][a];
        uint256 d0 = debt;
        uint256 v0 = vice;
        move(a, b, x);
        if (a != b) {
            assert(dai[a] + x == da);
            assert(dai[b] == db + x);
        } else {
            assert(dai[a] == da);
        }
        if (msg.sender != a && msg.sender != b)
            assert(dai[msg.sender] == ds);
        assert(sin[a] == sa);
        assert(gem["GOLD"][a] == ga);
        assert(debt == d0);
        assert(vice == v0);
    }

    function check_move_unauth(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        move(a, b, x);
        assert(false);
    }

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[a] < x);
        move(a, b, x);
        assert(false);
    }

    function check_move_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(dai[b] > type(uint256).max - x);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vaults: effects ----------------

    function check_frob_effects_src_self(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 ink1s = urns[i][msg.sender].ink;
        uint256 art1s = urns[i][msg.sender].art;
        uint256 Art0 = ilks[i].Art;
        uint256 ra0 = ilks[i].rate;
        uint256 sp0 = ilks[i].spot;
        uint256 li0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 g0 = gem[i][u];
        uint256 gs0 = gem[i][msg.sender];
        uint256 dai0 = dai[msg.sender];
        uint256 dau0 = dai[u];
        uint256 de0 = debt;
        uint256 vi0 = vice;
        uint256 L0 = Line;
        frob(i, u, u, msg.sender, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][u] + uint256(dx) == g0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][u] == g0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
        }
        assert(debt + dai0 == de0 + dai[msg.sender]);
        assert(dai[u] == dau0);
        assert(gem[i][msg.sender] == gs0);
        assert(urns[i][msg.sender].ink == ink1s);
        assert(urns[i][msg.sender].art == art1s);
        assert(ilks[i].rate == ra0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].line == li0);
        assert(ilks[i].dust == du0);
        assert(vice == vi0);
        assert(Line == L0);
        assert(live == 1);
    }

    function check_frob_effects_dst_self(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 gs0 = gem[i][msg.sender];
        uint256 dai0 = dai[msg.sender];
        uint256 dau0 = dai[u];
        uint256 de0 = debt;
        uint256 vi0 = vice;
        frob(i, u, msg.sender, u, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][msg.sender] + uint256(dx) == gs0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][msg.sender] == gs0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
        }
        assert(debt + dau0 == de0 + dai[u]);
        assert(dai[msg.sender] == dai0);
        assert(gem[i][u] == g0);
        assert(vice == vi0);
    }

    function check_frob_rate_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy == 1);
        uint256 dai0 = dai[msg.sender];
        uint256 de0 = debt;
        frob(i, u, u, msg.sender, dx, dy);
        assert(dai[msg.sender] == dai0 + ilks[i].rate);
        assert(debt == de0 + ilks[i].rate);
    }

    function check_frob_rate_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy == -1);
        uint256 dai0 = dai[msg.sender];
        uint256 de0 = debt;
        frob(i, u, u, msg.sender, dx, dy);
        assert(dai[msg.sender] + ilks[i].rate == dai0);
        assert(debt + ilks[i].rate == de0);
    }

    function check_frob_rate_up_dst(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy == 1);
        require(u != msg.sender);
        uint256 dai0 = dai[u];
        frob(i, msg.sender, msg.sender, u, dx, dy);
        assert(dai[u] == dai0 + ilks[i].rate);
    }

    // ---------------- Vaults: refusals ----------------

    function check_frob_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ilk_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].line == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_global_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(ilks[i].rate == 10 ** 27);
        require(Line == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_unsafe_borrow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].spot == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_unsafe_withdraw(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy == 0);
        require(dx < 0);
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].spot == 0);
        require(urns[i][u].art > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_u(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dy > 0);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_u_withdraw(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dx < 0);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_v(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dx > 0);
        require(dy <= 0);
        frob(i, u, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_w(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dx >= 0);
        require(dy < 0);
        frob(i, msg.sender, msg.sender, u, dx, dy);
        assert(false);
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(dy < int256(2 ** 100));
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].dust >= 2 ** 200);
        require(urns[i][u].art == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ink_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(urns[i][u].ink > type(uint256).max - uint256(dx));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_art_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(urns[i][u].art > type(uint256).max - uint256(dy));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_gem_underflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(gem[i][u] < uint256(dx));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Fork ----------------

    function check_fork_moves(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 uink0 = urns[i][u].ink;
        uint256 uart0 = urns[i][u].art;
        uint256 vink0 = urns[i][msg.sender].ink;
        uint256 vart0 = urns[i][msg.sender].art;
        uint256 Art0 = ilks[i].Art;
        uint256 ra0 = ilks[i].rate;
        uint256 g0 = gem[i][u];
        uint256 de0 = debt;
        fork(i, u, msg.sender, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink + uint256(dx) == uink0);
            assert(urns[i][msg.sender].ink == vink0 + uint256(dx));
        } else {
            assert(urns[i][u].ink == uink0 + uint256(-dx));
            assert(urns[i][msg.sender].ink + uint256(-dx) == vink0);
        }
        if (dy >= 0) {
            assert(urns[i][u].art + uint256(dy) == uart0);
            assert(urns[i][msg.sender].art == vart0 + uint256(dy));
        } else {
            assert(urns[i][u].art == uart0 + uint256(-dy));
            assert(urns[i][msg.sender].art + uint256(-dy) == vart0);
        }
        assert(ilks[i].Art == Art0);
        assert(ilks[i].rate == ra0);
        assert(gem[i][u] == g0);
        assert(debt == de0);
    }

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

    function check_fork_unsafe_src(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].spot == 0);
        require(urns[i][msg.sender].art > 0);
        fork(i, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_unsafe_dst(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].spot == 0);
        require(urns[i][u].art > 0);
        fork(i, msg.sender, u, 0, 0);
        assert(false);
    }

    function check_fork_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(ilks[i].dust >= 2 ** 200);
        require(urns[i][msg.sender].art > 0);
        require(urns[i][msg.sender].art < 2 ** 100);
        fork(i, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    // ---------------- Grab ----------------

    function check_grab_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 s0 = sin[msg.sender];
        uint256 su0 = sin[u];
        uint256 vi0 = vice;
        uint256 de0 = debt;
        uint256 dai0 = dai[msg.sender];
        uint256 ra0 = ilks[i].rate;
        grab(i, u, u, msg.sender, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][u] + uint256(dx) == g0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][u] == g0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
        }
        assert(vice + s0 == vi0 + sin[msg.sender]);
        assert(sin[u] == su0);
        assert(debt == de0);
        assert(dai[msg.sender] == dai0);
        assert(ilks[i].rate == ra0);
    }

    function check_grab_dst_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 g0 = gem[i][msg.sender];
        uint256 gu0 = gem[i][u];
        grab(i, u, msg.sender, u, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][msg.sender] + uint256(dx) == g0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][msg.sender] == g0 + uint256(-dx));
        }
        assert(gem[i][u] == gu0);
    }

    function check_grab_sin_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy == 1);
        require(u != msg.sender);
        uint256 s0 = sin[msg.sender];
        uint256 vi0 = vice;
        grab(i, u, u, msg.sender, dx, dy);
        assert(sin[msg.sender] + ilks[i].rate == s0);
        assert(vice + ilks[i].rate == vi0);
    }

    function check_grab_sin_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy == -1);
        require(u != msg.sender);
        uint256 s0 = sin[msg.sender];
        uint256 vi0 = vice;
        grab(i, u, u, msg.sender, dx, dy);
        assert(sin[msg.sender] == s0 + ilks[i].rate);
        assert(vice == vi0 + ilks[i].rate);
    }

    // ---------------- Settlement ----------------

    function check_heal_effects(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 v0 = vice;
        uint256 de0 = debt;
        uint256 sa0 = sin[a];
        uint256 da0 = dai[a];
        heal(x);
        assert(sin[msg.sender] + x == s0);
        assert(dai[msg.sender] + x == d0);
        assert(vice + x == v0);
        assert(debt + x == de0);
        if (a != msg.sender) {
            assert(sin[a] == sa0);
            assert(dai[a] == da0);
        }
    }

    function check_heal_sin_underflow(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_dai_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_vice_underflow(address a, address b, uint256 x, uint256 y) external {
        require(vice < x);
        heal(x);
        assert(false);
    }

    function check_heal_debt_underflow(address a, address b, uint256 x, uint256 y) external {
        require(debt < x);
        heal(x);
        assert(false);
    }

    function check_suck_effects(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[a];
        uint256 d0 = dai[b];
        uint256 v0 = vice;
        uint256 de0 = debt;
        uint256 db0 = dai[a];
        uint256 sb0 = sin[b];
        suck(a, b, x);
        assert(sin[a] == s0 + x);
        assert(dai[b] == d0 + x);
        assert(vice == v0 + x);
        assert(debt == de0 + x);
        if (a != b) {
            assert(dai[a] == db0);
            assert(sin[b] == sb0);
        }
    }

    function check_suck_debt_overflow(address a, address b, uint256 x, uint256 y) external {
        require(debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_vice_overflow(address a, address b, uint256 x, uint256 y) external {
        require(vice > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_sin_overflow(address a, address b, uint256 x, uint256 y) external {
        require(sin[a] > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_dai_overflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[b] > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].Art == 1);
        require(dx > type(int256).min);
        uint256 r0 = ilks[i].rate;
        uint256 da0 = dai[u];
        uint256 de0 = debt;
        uint256 sp0 = ilks[i].spot;
        fold(i, u, dx);
        if (dx >= 0) {
            assert(ilks[i].rate == r0 + uint256(dx));
            assert(dai[u] == da0 + uint256(dx));
            assert(debt == de0 + uint256(dx));
        } else {
            assert(ilks[i].rate + uint256(-dx) == r0);
            assert(dai[u] + uint256(-dx) == da0);
            assert(debt + uint256(-dx) == de0);
        }
        assert(ilks[i].Art == 1);
        assert(ilks[i].spot == sp0);
    }

    function check_fold_link(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 da0 = dai[u];
        uint256 de0 = debt;
        uint256 Art0 = ilks[i].Art;
        uint256 vi0 = vice;
        fold(i, u, dx);
        assert(debt + da0 == de0 + dai[u]);
        assert(ilks[i].Art == Art0);
        assert(vice == vi0);
    }

    function check_fold_no_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].Art == 0);
        uint256 da0 = dai[u];
        uint256 de0 = debt;
        fold(i, u, dx);
        assert(dai[u] == da0);
        assert(debt == de0);
    }

    function check_fold_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }
}
