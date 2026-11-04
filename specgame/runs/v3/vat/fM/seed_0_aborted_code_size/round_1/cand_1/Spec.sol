// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        rely(a);
        assert(false);
    }

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == w0);
        assert(live == 1);
    }

    function check_rely_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        rely(a);
        assert(false);
    }

    function check_deny_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == w0);
    }

    function check_deny_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        deny(a);
        assert(false);
    }

    function check_init_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 t0 = ilks[i].Art;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == du0);
        assert(ilks[i].Art == t0);
    }

    function check_init_once(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_file_Line_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_Line_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_Line_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 d0 = debt;
        uint256 v0 = vice;
        file("Line", x);
        assert(Line == x);
        assert(debt == d0);
        assert(vice == v0);
        assert(live == 1);
    }

    function check_file_Line_unrecognized(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_ilk_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_file_ilk_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        file(i, "line", uint256(dx));
        assert(false);
    }

    function check_file_spot_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 l0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        uint256 t0 = ilks[i].Art;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == du0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == t0);
    }

    function check_file_line_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 du0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        uint256 t0 = ilks[i].Art;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == du0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == t0);
    }

    function check_file_dust_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 r0 = ilks[i].rate;
        uint256 t0 = ilks[i].Art;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == t0);
    }

    function check_file_ilk_unrecognized(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "spot");
        require(i != "line");
        require(i != "dust");
        file("GOLD", i, uint256(dx));
        assert(false);
    }

    function check_cage_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_dead_stays_dead(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        heal(x);
        assert(live == 0);
    }

    function check_dead_no_rely(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    // ---------------- Consent ----------------

    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 c0 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[b][a] == c0);
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 c0 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[b][a] == c0);
    }

    // ---------------- Free collateral ----------------

    function check_slip_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    function check_slip_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        require(i != "GOLD");
        uint256 g0 = gem[i][u];
        uint256 o0 = gem["GOLD"][u];
        slip(i, u, dx);
        assert(gem[i][u] - g0 == uint256(dx));
        assert(gem["GOLD"][u] == o0);
    }

    function check_slip_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(g0 - gem[i][u] == uint256(-dx));
    }

    function check_slip_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(gem[i][u] > type(uint256).max - uint256(dx));
        slip(i, u, dx);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(address(uint160(y)) != a);
        require(address(uint160(y)) != b);
        address c = address(uint160(y));
        uint256 ga0 = gem["GOLD"][a];
        uint256 gb0 = gem["GOLD"][b];
        uint256 gc0 = gem["GOLD"][c];
        uint256 so0 = gem["SILVER"][a];
        flux("GOLD", a, b, x);
        assert(ga0 - gem["GOLD"][a] == x);
        assert(gem["GOLD"][b] - gb0 == x);
        assert(gem["GOLD"][c] == gc0);
        assert(gem["SILVER"][a] == so0);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 g0 = gem["GOLD"][a];
        flux("GOLD", a, a, x);
        assert(gem["GOLD"][a] == g0);
    }

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(gem["GOLD"][a] < x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    // ---------------- Stablecoin ----------------

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(address(uint160(y)) != a);
        require(address(uint160(y)) != b);
        address c = address(uint160(y));
        uint256 da0 = dai[a];
        uint256 db0 = dai[b];
        uint256 dc0 = dai[c];
        uint256 d0 = debt;
        move(a, b, x);
        assert(da0 - dai[a] == x);
        assert(dai[b] - db0 == x);
        assert(dai[c] == dc0);
        assert(debt == d0);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 da0 = dai[a];
        move(a, a, x);
        assert(dai[a] == da0);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        move(a, b, x);
        assert(false);
    }

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[a] < x);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vaults: frob ----------------

    function check_frob_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_effect_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        require(dy >= 0);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 ta0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 g0 = gem[i][u];
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        frob(i, u, u, u, dx, dy);
        assert(urns[i][u].ink - ink0 == uint256(dx));
        assert(urns[i][u].art - art0 == uint256(dy));
        assert(ilks[i].Art - ta0 == uint256(dy));
        assert(ilks[i].rate == r0);
        assert(g0 - gem[i][u] == uint256(dx));
        assert(dai[u] - dai0 == debt - d0);
    }

    function check_frob_effect_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0);
        require(dy <= 0);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 ta0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 g0 = gem[i][u];
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        frob(i, u, u, u, dx, dy);
        assert(ink0 - urns[i][u].ink == uint256(-dx));
        assert(art0 - urns[i][u].art == uint256(-dy));
        assert(ta0 - ilks[i].Art == uint256(-dy));
        assert(ilks[i].rate == r0);
        assert(gem[i][u] - g0 == uint256(-dx));
        assert(dai0 - dai[u] == d0 - debt);
    }

    function check_frob_rate_factor(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(dy > 0);
        require(dy < 10 ** 30);
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        frob(i, u, u, u, dx, dy);
        assert(dai[u] - dai0 == uint256(dy) * 10 ** 27);
        assert(debt - d0 == uint256(dy) * 10 ** 27);
    }

    function check_frob_not_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].spot == 0);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ilk_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].line == 0);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_global_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(Line == 0);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(dy > 0);
        require(dy < 10 ** 30);
        require(urns[i][u].art < 10 ** 30);
        require(ilks[i].dust >= 10 ** 58);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_u_consent_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_u_consent_collateral(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        require(dx < 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_v_consent(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        require(b != msg.sender);
        require(can[b][msg.sender] != 1);
        require(x > 0 && x < 2 ** 200);
        frob("GOLD", a, b, a, -int256(x), 0);
        assert(false);
    }

    function check_frob_w_consent(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        require(b != msg.sender);
        require(can[b][msg.sender] != 1);
        require(x > 0 && x < 2 ** 200);
        frob("GOLD", a, a, b, 0, int256(x));
        assert(false);
    }

    function check_frob_ink_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(urns[i][u].ink > type(uint256).max - uint256(dx));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Vaults: fork ----------------

    function check_fork_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(b == msg.sender || can[b][msg.sender] == 1);
        uint256 ia0 = urns["GOLD"][a].ink;
        uint256 ib0 = urns["GOLD"][b].ink;
        uint256 aa0 = urns["GOLD"][a].art;
        uint256 ab0 = urns["GOLD"][b].art;
        uint256 ta0 = ilks["GOLD"].Art;
        uint256 r0 = ilks["GOLD"].rate;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(ia0 - urns["GOLD"][a].ink == x);
        assert(urns["GOLD"][b].ink - ib0 == x);
        assert(aa0 - urns["GOLD"][a].art == y);
        assert(urns["GOLD"][b].art - ab0 == y);
        assert(ilks["GOLD"].Art == ta0);
        assert(ilks["GOLD"].rate == r0);
    }

    function check_fork_src_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_dst_consent(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        require(can[b][msg.sender] != 1);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_dst_unsafe(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(ilks["GOLD"].spot == 0);
        require(ilks["GOLD"].rate != 0);
        require(y > 0 && y <= uint256(type(int256).max));
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_src_unsafe(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(ilks["GOLD"].spot == 0);
        require(ilks["GOLD"].rate != 0);
        require(y > uint256(type(int256).max));
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    // ---------------- Confiscation ----------------

    function check_grab_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_grab_effect_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0);
        require(dy <= 0);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 ta0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 s0 = sin[u];
        uint256 v0 = vice;
        uint256 d0 = debt;
        grab(i, u, u, u, dx, dy);
        assert(ink0 - urns[i][u].ink == uint256(-dx));
        assert(art0 - urns[i][u].art == uint256(-dy));
        assert(ta0 - ilks[i].Art == uint256(-dy));
        assert(gem[i][u] - g0 == uint256(-dx));
        assert(sin[u] - s0 == vice - v0);
        assert(debt == d0);
    }

    function check_grab_effect_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        require(dy >= 0);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 ta0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 s0 = sin[u];
        uint256 v0 = vice;
        uint256 d0 = debt;
        grab(i, u, u, u, dx, dy);
        assert(urns[i][u].ink - ink0 == uint256(dx));
        assert(urns[i][u].art - art0 == uint256(dy));
        assert(ilks[i].Art - ta0 == uint256(dy));
        assert(g0 - gem[i][u] == uint256(dx));
        assert(s0 - sin[u] == v0 - vice);
        assert(debt == d0);
    }

    function check_grab_rate_factor(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(dy < 0);
        require(dy > -(10 ** 30));
        uint256 s0 = sin[u];
        uint256 v0 = vice;
        grab(i, u, u, u, dx, dy);
        assert(sin[u] - s0 == uint256(-dy) * 10 ** 27);
        assert(vice - v0 == uint256(-dy) * 10 ** 27);
    }

    // ---------------- Settlement ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = sin[msg.sender];
        uint256 da0 = dai[msg.sender];
        uint256 v0 = vice;
        uint256 d0 = debt;
        uint256 sa0 = sin[a];
        uint256 daa0 = dai[a];
        heal(x);
        assert(s0 - sin[msg.sender] == x);
        assert(da0 - dai[msg.sender] == x);
        assert(v0 - vice == x);
        assert(d0 - debt == x);
        assert(sin[a] == sa0);
        assert(dai[a] == daa0);
    }

    function check_heal_dai_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_sin_underflow(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_suck_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[a];
        uint256 da0 = dai[b];
        uint256 v0 = vice;
        uint256 d0 = debt;
        suck(a, b, x);
        assert(sin[a] - s0 == x);
        assert(dai[b] - da0 == x);
        assert(vice - v0 == x);
        assert(debt - d0 == x);
    }

    function check_suck_overflow(address a, address b, uint256 x, uint256 y) external {
        require(debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 ta0 = ilks[i].Art;
        uint256 s0 = ilks[i].spot;
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        fold(i, u, dx);
        assert(ilks[i].rate - r0 == uint256(dx));
        assert(ilks[i].Art == ta0);
        assert(ilks[i].spot == s0);
        assert(dai[u] - dai0 == debt - d0);
    }

    function check_fold_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        uint256 r0 = ilks[i].rate;
        uint256 ta0 = ilks[i].Art;
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        fold(i, u, dx);
        assert(r0 - ilks[i].rate == uint256(-dx));
        assert(ilks[i].Art == ta0);
        assert(dai0 - dai[u] == d0 - debt);
    }

    function check_fold_factor(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].Art == 10 ** 18);
        require(dx >= 0);
        require(dx < 10 ** 30);
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        fold(i, u, dx);
        assert(dai[u] - dai0 == uint256(dx) * 10 ** 18);
        assert(debt - d0 == uint256(dx) * 10 ** 18);
    }

    function check_fold_no_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].Art == 0);
        uint256 dai0 = dai[u];
        uint256 d0 = debt;
        fold(i, u, dx);
        assert(dai[u] == dai0);
        assert(debt == d0);
    }

    function check_fold_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(ilks[i].rate > type(uint256).max - uint256(dx));
        fold(i, u, dx);
        assert(false);
    }
}
