// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        rely(a);
        assert(false);
    }

    function check_deny_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        deny(a);
        assert(false);
    }

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 wb = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == wb);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 wb = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == wb);
    }

    function check_rely_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    function check_deny_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        deny(a);
        assert(false);
    }

    function check_init_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        init(i);
        assert(false);
    }

    function check_file_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        file("GOLD", "spot", x);
        assert(false);
    }

    function check_cage_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        cage();
        assert(false);
    }

    function check_slip_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        slip(i, u, dx);
        assert(false);
    }

    function check_grab_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_suck_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        suck(a, b, x);
        assert(false);
    }

    function check_fold_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        fold(i, u, dy);
        assert(false);
    }

    // ---------------- Consent ----------------

    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 cb = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[b][a] == cb);
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 cb = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[b][a] == cb);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        move(a, b, x);
        assert(false);
    }

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_frob_u_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender && can[u][msg.sender] == 0);
        require(dy > 0 || dx < 0);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_v_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        require(x > 0 && x <= uint256(type(int256).max));
        frob("GOLD", msg.sender, a, msg.sender, int256(x), 0);
        assert(false);
    }

    function check_frob_w_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        require(x > 0 && x <= uint256(type(int256).max));
        frob("GOLD", msg.sender, msg.sender, a, 0, -int256(x));
        assert(false);
    }

    function check_fork_src_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender && can[u][msg.sender] == 0);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_dst_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender && can[u][msg.sender] == 0);
        fork(i, msg.sender, u, dx, dy);
        assert(false);
    }

    // ---------------- Collateral types ----------------

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 art0 = ilks[i].Art;
        init(i);
        assert(ilks[i].rate == 1000000000000000000000000000);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].Art == art0);
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
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        uint256 live0 = live;
        file("Line", x);
        assert(Line == x);
        assert(debt == debt0);
        assert(vice == vice0);
        assert(live == live0);
    }

    function check_file_spot_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 l0 = ilks["GOLD"].line;
        uint256 d0 = ilks["GOLD"].dust;
        uint256 r0 = ilks["GOLD"].rate;
        uint256 art0 = ilks["GOLD"].Art;
        uint256 gl0 = Line;
        file("GOLD", "spot", x);
        assert(ilks["GOLD"].spot == x);
        assert(ilks["GOLD"].line == l0);
        assert(ilks["GOLD"].dust == d0);
        assert(ilks["GOLD"].rate == r0);
        assert(ilks["GOLD"].Art == art0);
        assert(Line == gl0);
    }

    function check_file_line_ilk_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = ilks["GOLD"].spot;
        uint256 d0 = ilks["GOLD"].dust;
        uint256 r0 = ilks["GOLD"].rate;
        uint256 art0 = ilks["GOLD"].Art;
        uint256 gl0 = Line;
        file("GOLD", "line", x);
        assert(ilks["GOLD"].line == x);
        assert(ilks["GOLD"].spot == s0);
        assert(ilks["GOLD"].dust == d0);
        assert(ilks["GOLD"].rate == r0);
        assert(ilks["GOLD"].Art == art0);
        assert(Line == gl0);
    }

    function check_file_dust_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = ilks["GOLD"].spot;
        uint256 l0 = ilks["GOLD"].line;
        uint256 r0 = ilks["GOLD"].rate;
        uint256 art0 = ilks["GOLD"].Art;
        uint256 gl0 = Line;
        file("GOLD", "dust", x);
        assert(ilks["GOLD"].dust == x);
        assert(ilks["GOLD"].spot == s0);
        assert(ilks["GOLD"].line == l0);
        assert(ilks["GOLD"].rate == r0);
        assert(ilks["GOLD"].Art == art0);
        assert(Line == gl0);
    }

    function check_file_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("GOLD", "spot", x);
        assert(false);
    }

    function check_file_unrecognized(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        require(dx >= 0);
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_ilk_unrecognized(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "spot" && i != "line" && i != "dust");
        require(dx >= 0);
        file("GOLD", i, uint256(dx));
        assert(false);
    }

    // ---------------- Moving value ----------------

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da0 = dai[a];
        uint256 db0 = dai[b];
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        move(a, b, x);
        assert(dai[a] + x == da0);
        assert(dai[b] == db0 + x);
        assert(debt == debt0);
        assert(vice == vice0);
    }

    function check_move_other_unchanged(address a, address b, uint256 x, uint256 y) external {
        address c = address(uint160(y));
        require(c != a && c != b);
        uint256 dc0 = dai[c];
        uint256 sc0 = sin[c];
        move(a, b, x);
        assert(dai[c] == dc0);
        assert(sin[c] == sc0);
    }

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[a] < x);
        move(a, b, x);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 ga0 = gem["GOLD"][a];
        uint256 gb0 = gem["GOLD"][b];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga0);
        assert(gem["GOLD"][b] == gb0 + x);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(gem["GOLD"][a] < x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_slip_pos(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] == g0 + uint256(dx));
    }

    function check_slip_neg(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] + uint256(-dx) == g0);
    }

    // ---------------- Vaults: frob ----------------

    function check_frob_effect_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dy >= 0);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tart0 = ilks[i].Art;
        uint256 g0 = gem[i][msg.sender];
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        frob(i, u, msg.sender, u, dx, dy);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == tart0 + uint256(dy));
        assert(gem[i][msg.sender] + uint256(dx) == g0);
        assert(dai[u] == dai0 + r0 * uint256(dy));
        assert(debt == debt0 + r0 * uint256(dy));
        assert(ilks[i].rate == r0);
    }

    function check_frob_effect_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tart0 = ilks[i].Art;
        uint256 g0 = gem[i][msg.sender];
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        frob(i, u, msg.sender, u, dx, dy);
        assert(urns[i][u].ink + uint256(-dx) == ink0);
        assert(urns[i][u].art + uint256(-dy) == art0);
        assert(ilks[i].Art + uint256(-dy) == tart0);
        assert(gem[i][msg.sender] == g0 + uint256(-dx));
        assert(dai[u] + r0 * uint256(-dy) == dai0);
        assert(debt + r0 * uint256(-dy) == debt0);
    }

    function check_frob_isolated(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(i != "OTHER");
        uint256 oink = urns[i][msg.sender].ink;
        uint256 oart = urns[i][msg.sender].art;
        uint256 odai = dai[msg.sender];
        uint256 oArt = ilks["OTHER"].Art;
        uint256 orate = ilks["OTHER"].rate;
        uint256 vice0 = vice;
        frob(i, u, msg.sender, u, dx, dy);
        assert(urns[i][msg.sender].ink == oink);
        assert(urns[i][msg.sender].art == oart);
        assert(dai[msg.sender] == odai);
        assert(ilks["OTHER"].Art == oArt);
        assert(ilks["OTHER"].rate == orate);
        assert(vice == vice0);
    }

    function check_frob_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(debt <= Line);
        assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
    }

    function check_frob_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 || dx < 0);
        frob(i, u, u, u, dx, dy);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
    }

    function check_frob_ink_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0 && urns[i][u].ink > type(uint256).max - uint256(dx));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_art_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && urns[i][u].art > type(uint256).max - uint256(dy));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_gem_underflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0 && gem[i][u] < uint256(dx));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Vaults: fork ----------------

    function check_fork_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx >= 0 && dy >= 0);
        uint256 inku = urns[i][u].ink;
        uint256 artu = urns[i][u].art;
        uint256 inkm = urns[i][msg.sender].ink;
        uint256 artm = urns[i][msg.sender].art;
        uint256 tart0 = ilks[i].Art;
        uint256 debt0 = debt;
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].ink + uint256(dx) == inku);
        assert(urns[i][u].art + uint256(dy) == artu);
        assert(urns[i][msg.sender].ink == inkm + uint256(dx));
        assert(urns[i][msg.sender].art == artm + uint256(dy));
        assert(ilks[i].Art == tart0);
        assert(debt == debt0);
    }

    function check_fork_effect_neg(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        uint256 inku = urns[i][u].ink;
        uint256 artu = urns[i][u].art;
        uint256 inkm = urns[i][msg.sender].ink;
        uint256 artm = urns[i][msg.sender].art;
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].ink == inku + uint256(-dx));
        assert(urns[i][u].art == artu + uint256(-dy));
        assert(urns[i][msg.sender].ink + uint256(-dx) == inkm);
        assert(urns[i][msg.sender].art + uint256(-dy) == artm);
    }

    function check_fork_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);
    }

    function check_fork_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        assert(urns[i][msg.sender].art == 0 || urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);
    }

    // ---------------- Confiscation ----------------

    function check_grab_effect_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tart0 = ilks[i].Art;
        uint256 g0 = gem[i][msg.sender];
        uint256 sin0 = sin[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 dai0 = dai[msg.sender];
        uint256 r0 = ilks[i].rate;
        grab(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].ink + uint256(-dx) == ink0);
        assert(urns[i][u].art + uint256(-dy) == art0);
        assert(ilks[i].Art + uint256(-dy) == tart0);
        assert(gem[i][msg.sender] == g0 + uint256(-dx));
        assert(sin[msg.sender] == sin0 + r0 * uint256(-dy));
        assert(vice == vice0 + r0 * uint256(-dy));
        assert(debt == debt0);
        assert(dai[msg.sender] == dai0);
    }

    function check_grab_effect_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dy >= 0);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tart0 = ilks[i].Art;
        uint256 g0 = gem[i][msg.sender];
        uint256 sin0 = sin[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        grab(i, u, msg.sender, msg.sender, dx, dy);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == tart0 + uint256(dy));
        assert(gem[i][msg.sender] + uint256(dx) == g0);
        assert(sin[msg.sender] + r0 * uint256(dy) == sin0);
        assert(vice + r0 * uint256(dy) == vice0);
        assert(debt == debt0);
    }

    // ---------------- Settlement ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
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

    function check_heal_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_sin_underflow(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
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

    function check_suck_overflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[b] > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_debt_overflow(address a, address b, uint256 x, uint256 y) external {
        require(debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold_effect_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 tart0 = ilks[i].Art;
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        fold(i, u, dy);
        assert(ilks[i].rate == r0 + uint256(dy));
        assert(ilks[i].Art == tart0);
        assert(dai[u] == dai0 + tart0 * uint256(dy));
        assert(debt == debt0 + tart0 * uint256(dy));
    }

    function check_fold_effect_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy <= 0 && dy > type(int256).min);
        uint256 r0 = ilks[i].rate;
        uint256 tart0 = ilks[i].Art;
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        fold(i, u, dy);
        assert(ilks[i].rate + uint256(-dy) == r0);
        assert(ilks[i].Art == tart0);
        assert(dai[u] + tart0 * uint256(-dy) == dai0);
        assert(debt + tart0 * uint256(-dy) == debt0);
    }

    function check_fold_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dy);
        assert(false);
    }

    // ---------------- Shutdown ----------------

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_live_stays_suck(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        suck(a, b, x);
        assert(live == 0);
    }

    function check_live_stays_heal(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        heal(x);
        assert(live == 0);
    }

    function check_live_stays_move(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        move(a, b, x);
        assert(live == 0);
    }

    function check_live_stays_grab(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        grab(i, u, u, u, dx, dy);
        assert(live == 0);
    }

    function check_live_stays_slip(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        slip(i, u, dx);
        assert(live == 0);
    }

    function check_live_stays_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        init(i);
        assert(live == 0);
    }

    function check_live_stays_cage(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        cage();
        assert(live == 0);
    }

    function check_live_stays_fork(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fork(i, u, msg.sender, dx, dy);
        assert(live == 0);
    }
}
