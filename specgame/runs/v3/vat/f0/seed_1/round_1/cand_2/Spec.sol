// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 wb = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == wb);
    }

    function check_rely_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        rely(a);
        assert(false);
    }

    function check_rely_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        rely(a);
        assert(false);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 wb = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == wb);
    }

    function check_deny_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_deny_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        deny(a);
        assert(false);
    }

    // ---------------- Consent ----------------

    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 c1 = can[msg.sender][b];
        uint256 c2 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[msg.sender][b] == c1);
        if (b != msg.sender) {
            assert(can[b][a] == c2);
        }
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 c1 = can[msg.sender][b];
        uint256 c2 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[msg.sender][b] == c1);
        if (b != msg.sender) {
            assert(can[b][a] == c2);
        }
    }

    // ---------------- Collateral types ----------------

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 art0 = ilks[i].Art;
        uint256 spot0 = ilks[i].spot;
        uint256 line0 = ilks[i].line;
        uint256 dust0 = ilks[i].dust;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == spot0);
        assert(ilks[i].line == line0);
        assert(ilks[i].dust == dust0);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_init_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
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

    function check_file_line_effect(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
    }

    function check_file_line_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_line_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_unrecognized(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dy));
        assert(false);
    }

    function check_file_spot_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 line0 = ilks[i].line;
        uint256 dust0 = ilks[i].dust;
        uint256 l0 = Line;
        file(i, "spot", uint256(dy));
        assert(ilks[i].spot == uint256(dy));
        assert(ilks[i].Art == art0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].line == line0);
        assert(ilks[i].dust == dust0);
        assert(Line == l0);
    }

    function check_file_line_ilk_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 spot0 = ilks[i].spot;
        uint256 dust0 = ilks[i].dust;
        uint256 l0 = Line;
        file(i, "line", uint256(dy));
        assert(ilks[i].line == uint256(dy));
        assert(ilks[i].Art == art0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].spot == spot0);
        assert(ilks[i].dust == dust0);
        assert(Line == l0);
    }

    function check_file_dust_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 art0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 spot0 = ilks[i].spot;
        uint256 line0 = ilks[i].line;
        uint256 l0 = Line;
        file(i, "dust", uint256(dy));
        assert(ilks[i].dust == uint256(dy));
        assert(ilks[i].Art == art0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].spot == spot0);
        assert(ilks[i].line == line0);
        assert(Line == l0);
    }

    function check_file_ilk_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dy));
        assert(false);
    }

    function check_file_ilk_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        file(i, "dust", uint256(dy));
        assert(false);
    }

    function check_file_ilk_unrecognized_rate(bytes32 i, address u, int256 dx, int256 dy) external {
        file(i, "rate", uint256(dy));
        assert(false);
    }

    function check_file_ilk_unrecognized_art(bytes32 i, address u, int256 dx, int256 dy) external {
        file(i, "Art", uint256(dy));
        assert(false);
    }

    // ---------------- Shutdown ----------------

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_cage_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

    function check_cage_stays(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        cage();
        assert(live == 0);
    }

    // ---------------- Free collateral ----------------

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

    function check_slip_frame(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(i != "OTHER");
        uint256 g1 = gem[i][msg.sender];
        uint256 g2 = gem["OTHER"][u];
        slip(i, u, dx);
        assert(gem[i][msg.sender] == g1);
        assert(gem["OTHER"][u] == g2);
    }

    function check_slip_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 go1 = gem["SILVER"][a];
        uint256 go2 = gem["SILVER"][b];
        uint256 gc = gem["GOLD"][msg.sender];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb + x);
        assert(gem["SILVER"][a] == go1);
        assert(gem["SILVER"][b] == go2);
        if (msg.sender != a && msg.sender != b) {
            assert(gem["GOLD"][msg.sender] == gc);
        }
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

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(gem["GOLD"][a] < x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x > type(uint256).max - gem["GOLD"][b]);
        flux("GOLD", a, b, x);
        assert(false);
    }

    // ---------------- Free stablecoin ----------------

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 dc = dai[msg.sender];
        uint256 d0 = debt;
        uint256 v0 = vice;
        move(a, b, x);
        assert(dai[a] + x == da);
        assert(dai[b] == db + x);
        assert(debt == d0);
        assert(vice == v0);
        if (msg.sender != a && msg.sender != b) {
            assert(dai[msg.sender] == dc);
        }
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

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[a] < x);
        move(a, b, x);
        assert(false);
    }

    function check_move_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x > type(uint256).max - dai[b]);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vaults: frob ----------------

    function check_frob_open(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dy >= 0);
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 gs0 = gem[i][msg.sender];
        uint256 gu0 = gem[i][u];
        uint256 du0 = dai[u];
        uint256 ds0 = dai[msg.sender];
        uint256 d0 = debt;
        frob(i, u, msg.sender, u, dx, dy);
        uint256 t = ilks[i].rate * uint256(dy);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == tot0 + uint256(dy));
        assert(ilks[i].rate == r0);
        assert(gem[i][msg.sender] + uint256(dx) == gs0);
        assert(gem[i][u] == gu0);
        assert(dai[u] == du0 + t);
        assert(dai[msg.sender] == ds0);
        assert(debt == d0 + t);
    }

    function check_frob_close(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        uint256 gs0 = gem[i][msg.sender];
        uint256 gu0 = gem[i][u];
        uint256 du0 = dai[u];
        uint256 ds0 = dai[msg.sender];
        uint256 d0 = debt;
        frob(i, u, msg.sender, u, dx, dy);
        uint256 t = ilks[i].rate * uint256(-dy);
        assert(urns[i][u].ink + uint256(-dx) == ink0);
        assert(urns[i][u].art + uint256(-dy) == art0);
        assert(ilks[i].Art + uint256(-dy) == tot0);
        assert(ilks[i].rate == r0);
        assert(gem[i][msg.sender] == gs0 + uint256(-dx));
        assert(gem[i][u] == gu0);
        assert(dai[u] + t == du0);
        assert(dai[msg.sender] == ds0);
        assert(debt + t == d0);
    }

    function check_frob_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ceilings(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0) {
            assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
            assert(debt <= Line);
        }
    }

    function check_frob_safety(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0 || dx < 0) {
            assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        }
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    function check_frob_needs_consent_u(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        require(dx < 0 || dy > 0);
        frob(i, u, msg.sender, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_v(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        require(dx > 0);
        frob(i, msg.sender, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_w(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        require(dy < 0);
        frob(i, msg.sender, msg.sender, u, dx, dy);
        assert(false);
    }

    // ---------------- Vaults: fork ----------------

    function check_fork_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dy >= 0);
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 inku0 = urns[i][u].ink;
        uint256 artu0 = urns[i][u].art;
        uint256 inks0 = urns[i][msg.sender].ink;
        uint256 arts0 = urns[i][msg.sender].art;
        uint256 tot0 = ilks[i].Art;
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].ink + uint256(dx) == inku0);
        assert(urns[i][u].art + uint256(dy) == artu0);
        assert(urns[i][msg.sender].ink == inks0 + uint256(dx));
        assert(urns[i][msg.sender].art == arts0 + uint256(dy));
        assert(ilks[i].Art == tot0);
    }

    function check_fork_effect_reverse(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 inku0 = urns[i][u].ink;
        uint256 artu0 = urns[i][u].art;
        uint256 inks0 = urns[i][msg.sender].ink;
        uint256 arts0 = urns[i][msg.sender].art;
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].ink == inku0 + uint256(-dx));
        assert(urns[i][u].art == artu0 + uint256(-dy));
        assert(urns[i][msg.sender].ink + uint256(-dx) == inks0);
        assert(urns[i][msg.sender].art + uint256(-dy) == arts0);
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

    function check_fork_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);
    }

    function check_fork_not_dusty(bytes32 i, address u, int256 dx, int256 dy) external {
        fork(i, u, msg.sender, dx, dy);
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
        if (urns[i][msg.sender].art != 0) {
            assert(urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    // ---------------- Confiscation ----------------

    function check_grab_confiscate(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 1);
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        require(u != msg.sender);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 gs0 = gem[i][msg.sender];
        uint256 gu0 = gem[i][u];
        uint256 su0 = sin[u];
        uint256 ss0 = sin[msg.sender];
        uint256 du0 = dai[u];
        uint256 v0 = vice;
        uint256 d0 = debt;
        grab(i, u, msg.sender, u, dx, dy);
        uint256 t = ilks[i].rate * uint256(-dy);
        assert(urns[i][u].ink + uint256(-dx) == ink0);
        assert(urns[i][u].art + uint256(-dy) == art0);
        assert(ilks[i].Art + uint256(-dy) == tot0);
        assert(gem[i][msg.sender] == gs0 + uint256(-dx));
        assert(gem[i][u] == gu0);
        assert(sin[u] == su0 + t);
        assert(sin[msg.sender] == ss0);
        assert(dai[u] == du0);
        assert(vice == v0 + t);
        assert(debt == d0);
    }

    function check_grab_reverse(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 1);
        require(dx >= 0 && dy >= 0);
        require(u != msg.sender);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 gs0 = gem[i][msg.sender];
        uint256 su0 = sin[u];
        uint256 v0 = vice;
        uint256 d0 = debt;
        grab(i, u, msg.sender, u, dx, dy);
        uint256 t = ilks[i].rate * uint256(dy);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == tot0 + uint256(dy));
        assert(gem[i][msg.sender] + uint256(dx) == gs0);
        assert(sin[u] + t == su0);
        assert(vice + t == v0);
        assert(debt == d0);
    }

    function check_grab_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, msg.sender, u, dx, dy);
        assert(false);
    }

    // ---------------- Settlement ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        uint256 sa = sin[a];
        uint256 da = dai[a];
        heal(x);
        assert(sin[msg.sender] + x == s0);
        assert(dai[msg.sender] + x == d0);
        assert(vice + x == v0);
        assert(debt + x == t0);
        if (a != msg.sender) {
            assert(sin[a] == sa);
            assert(dai[a] == da);
        }
    }

    function check_heal_needs_sin(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_needs_dai(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[a];
        uint256 d0 = dai[b];
        uint256 v0 = vice;
        uint256 t0 = debt;
        suck(a, b, x);
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

    function check_suck_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_debt_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > type(uint256).max - debt);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_sin_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > type(uint256).max - sin[a]);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_dai_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > type(uint256).max - dai[b]);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 tot0 = ilks[i].Art;
        uint256 du0 = dai[u];
        uint256 d0 = debt;
        fold(i, u, dx);
        uint256 t = ilks[i].Art * uint256(dx);
        assert(ilks[i].rate == r0 + uint256(dx));
        assert(ilks[i].Art == tot0);
        assert(dai[u] == du0 + t);
        assert(debt == d0 + t);
    }

    function check_fold_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dx > type(int256).min);
        uint256 r0 = ilks[i].rate;
        uint256 tot0 = ilks[i].Art;
        uint256 du0 = dai[u];
        uint256 d0 = debt;
        fold(i, u, dx);
        uint256 t = ilks[i].Art * uint256(-dx);
        assert(ilks[i].rate + uint256(-dx) == r0);
        assert(ilks[i].Art == tot0);
        assert(dai[u] + t == du0);
        assert(debt + t == d0);
    }

    function check_fold_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        fold(i, u, dx);
        assert(false);
    }
}
