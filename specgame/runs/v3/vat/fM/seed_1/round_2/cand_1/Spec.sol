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
        require(a != b);
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == w0);
        assert(live == 1);
    }

    function check_rely_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    function check_deny_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == w0);
    }

    function check_deny_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        deny(a);
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

    // ---------------- Collateral types ----------------

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 A0 = ilks[i].Art;
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].Art == A0);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == du0);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_init_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
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
        file("Line", x);
        assert(Line == x);
    }

    function check_file_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_unknown(address a, address b, uint256 x, uint256 y) external {
        require(bytes32(x) != "Line");
        file(bytes32(x), y);
        assert(false);
    }

    function check_file_spot(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 l0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == du0);
        assert(ilks[i].rate == r0);
    }

    function check_file_line(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 du0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == du0);
        assert(ilks[i].rate == r0);
    }

    function check_file_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 r0 = ilks[i].rate;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].rate == r0);
    }

    function check_file_ilk_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_file_ilk_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        file(i, "line", uint256(dx));
        assert(false);
    }

    function check_file_ilk_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "spot");
        require(i != "line");
        require(i != "dust");
        file("GOLD", i, uint256(dx));
        assert(false);
    }

    // ---------------- Shutdown ----------------

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_cage_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

    function check_dead_stays_dead_frob(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_dead_stays_dead_cage(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        cage();
        assert(live == 0);
    }

    // ---------------- Fungibility: slip / flux / move ----------------

    function check_slip_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        if (dx >= 0) {
            assert(gem[i][u] == g0 + uint256(dx));
        } else {
            assert(gem[i][u] + uint256(-dx) == g0);
        }
    }

    function check_slip_frame_ilk(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "GOLD");
        uint256 g0 = gem["GOLD"][u];
        slip(i, u, dx);
        assert(gem["GOLD"][u] == g0);
    }

    function check_slip_frame_addr(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x <= uint256(type(int256).max));
        uint256 g0 = gem["GOLD"][b];
        slip("GOLD", a, int256(x));
        assert(gem["GOLD"][b] == g0);
    }

    function check_slip_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    function check_slip_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(uint256(dx) > type(uint256).max - gem[i][u]);
        slip(i, u, dx);
        assert(false);
    }

    function check_slip_underflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        require(gem[i][u] < uint256(-dx));
        slip(i, u, dx);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 gb = gem["GOLD"][b];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][b] == gb + x);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        uint256 ga = gem["GOLD"][a];
        flux("GOLD", a, a, x);
        assert(gem["GOLD"][a] == ga);
    }

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_ilk(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(i != "GOLD");
        require(dx >= 0);
        uint256 gm = gem[i][msg.sender];
        uint256 go = gem["GOLD"][u];
        flux(i, u, msg.sender, uint256(dx));
        assert(gem[i][msg.sender] == gm + uint256(dx));
        assert(gem["GOLD"][u] == go);
    }

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 db = dai[b];
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        move(a, b, x);
        assert(dai[b] == db + x);
        assert(debt == debt0);
        assert(vice == vice0);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        uint256 da = dai[a];
        move(a, a, x);
        assert(dai[a] == da);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vaults: frob ----------------

    function check_frob_collateral(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 g0 = gem[i][u];
        frob(i, u, u, u, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][u] + uint256(dx) == g0);
        } else {
            assert(gem[i][u] == g0 + uint256(-dx));
        }
    }

    function check_frob_debt_units(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = urns[i][u].art;
        uint256 A0 = ilks[i].Art;
        frob(i, u, u, u, dx, dy);
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == A0 + uint256(dy));
        }
    }

    function check_frob_dai_unit_rate(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(dy >= 0);
        require(dy <= 1000000);
        uint256 d0 = dai[u];
        uint256 debt0 = debt;
        frob(i, u, u, u, dx, dy);
        assert(dai[u] == d0 + 10 ** 27 * uint256(dy));
        assert(debt == debt0 + 10 ** 27 * uint256(dy));
    }

    function check_frob_frame(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 r0 = ilks[i].rate;
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 vice0 = vice;
        uint256 L0 = Line;
        uint256 sn0 = sin[u];
        frob(i, u, u, u, dx, dy);
        assert(ilks[i].rate == r0);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == du0);
        assert(vice == vice0);
        assert(Line == L0);
        assert(sin[u] == sn0);
        assert(live == 1);
    }

    function check_frob_roles_up(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        require(a != b);
        require(a != msg.sender);
        require(b != msg.sender);
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 g0 = gem["GOLD"][b];
        frob("GOLD", a, b, msg.sender, int256(x), int256(y));
        assert(urns["GOLD"][a].ink == ink0 + x);
        assert(urns["GOLD"][a].art == art0 + y);
        assert(gem["GOLD"][b] + x == g0);
    }

    function check_frob_roles_down(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        require(a != b);
        require(a != msg.sender);
        require(b != msg.sender);
        uint256 g0 = gem["GOLD"][b];
        frob("GOLD", a, b, msg.sender, -int256(x), -int256(y));
        assert(gem["GOLD"][b] == g0 + x);
    }

    function check_frob_safe_after(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0 || dx < 0) {
            assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        }
    }

    function check_frob_ceiling_after(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0) {
            assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
            assert(debt <= Line);
        }
    }

    function check_frob_dust_after(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
    }

    function check_frob_ilk_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(ilks[i].line == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_unsafe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(ilks[i].spot == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_u(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 || dx < 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_v(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, msg.sender, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_w(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy < 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, msg.sender, msg.sender, u, dx, dy);
        assert(false);
    }

    // ---------------- Vaults: fork ----------------

    function check_fork_frame(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        uint256 A0 = ilks[i].Art;
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        uint256 g0 = gem[i][u];
        uint256 d0 = dai[u];
        fork(i, u, msg.sender, dx, dy);
        assert(ilks[i].Art == A0);
        assert(debt == debt0);
        assert(vice == vice0);
        assert(gem[i][u] == g0);
        assert(dai[u] == d0);
    }

    function check_fork_needs_consent_src(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_needs_consent_dst(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        fork(i, msg.sender, u, dx, dy);
        assert(false);
    }

    // ---------------- Confiscation: grab ----------------

    function check_grab_units(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        require(dy >= 0);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 A0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        grab(i, u, u, u, dx, dy);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == A0 + uint256(dy));
        assert(gem[i][u] + uint256(dx) == g0);
    }

    function check_grab_frame(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 debt0 = debt;
        uint256 d0 = dai[u];
        uint256 r0 = ilks[i].rate;
        grab(i, u, u, u, dx, dy);
        assert(debt == debt0);
        assert(dai[u] == d0);
        assert(ilks[i].rate == r0);
    }

    function check_grab_sin_unit_rate(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 10 ** 27);
        require(dy >= 0);
        require(dy <= 1000000);
        uint256 s0 = sin[u];
        uint256 vice0 = vice;
        grab(i, u, u, u, dx, dy);
        assert(sin[u] + 10 ** 27 * uint256(dy) == s0);
        assert(vice + 10 ** 27 * uint256(dy) == vice0);
    }

    function check_grab_roles(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        require(a != b);
        uint256 gb = gem["GOLD"][b];
        uint256 ga = gem["GOLD"][a];
        uint256 sb = sin[b];
        grab("GOLD", a, b, a, int256(x), int256(y));
        assert(gem["GOLD"][b] + x == gb);
        assert(gem["GOLD"][a] == ga);
        assert(sin[b] == sb);
    }

    function check_grab_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Settlement: heal / suck ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        heal(x);
        assert(sin[msg.sender] + x == s0);
        assert(dai[msg.sender] + x == d0);
        assert(vice + x == vice0);
        assert(debt + x == debt0);
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
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        suck(a, b, x);
        assert(sin[a] == s0 + x);
        assert(dai[b] == d0 + x);
        assert(vice == vice0 + x);
        assert(debt == debt0 + x);
    }

    function check_suck_roles(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 d0 = dai[a];
        uint256 s0 = sin[b];
        suck(a, b, x);
        assert(dai[a] == d0);
        assert(sin[b] == s0);
    }

    function check_suck_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates: fold ----------------

    function check_fold_unit_art(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].Art == 1);
        require(dy >= 0);
        require(dy <= 1000000);
        uint256 r0 = ilks[i].rate;
        uint256 d0 = dai[u];
        uint256 debt0 = debt;
        fold(i, u, dy);
        assert(ilks[i].rate == r0 + uint256(dy));
        assert(dai[u] == d0 + uint256(dy));
        assert(debt == debt0 + uint256(dy));
    }

    function check_fold_frame(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 vice0 = vice;
        uint256 sn0 = sin[u];
        fold(i, u, dy);
        assert(vice == vice0);
        assert(sin[u] == sn0);
    }

    function check_fold_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dy);
        assert(false);
    }

    function check_fold_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dy);
        assert(false);
    }
}
