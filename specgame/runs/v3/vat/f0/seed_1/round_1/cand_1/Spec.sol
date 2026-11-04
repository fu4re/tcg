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

    function check_grab_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        grab("GOLD", a, b, a, 0, 0);
        assert(false);
    }

    function check_suck_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        suck(a, b, x);
        assert(false);
    }

    function check_fold_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == w0);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == w0);
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

    // ---------------- Shutdown ----------------

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_not_live_rely(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    function check_not_live_deny(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        deny(a);
        assert(false);
    }

    function check_not_live_file(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_not_live_file_ilk(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_not_live_fold(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_not_live_frob(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Collateral types ----------------

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 t0 = ilks[i].Art;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].spot == s0);
        assert(ilks[i].Art == t0);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_frob_not_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Parameters ----------------

    function check_file_line(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
    }

    function check_file_unknown(address a, address b, uint256 x, uint256 y) external {
        file("debt", x);
        assert(false);
    }

    function check_file_spot(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].rate == r0);
    }

    function check_file_line_ilk(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 s0 = ilks[i].spot;
        uint256 d0 = ilks[i].dust;
        uint256 g0 = Line;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == d0);
        assert(Line == g0);
    }

    function check_file_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 r0 = ilks[i].rate;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].rate == r0);
    }

    function check_file_ilk_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        file(i, "rate", uint256(dx));
        assert(false);
    }

    // ---------------- Moving value ----------------

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 t0 = debt;
        move(a, b, x);
        assert(dai[a] + x == da);
        assert(dai[b] == db + x);
        assert(debt == t0);
    }

    function check_move_others(address a, address b, uint256 x, uint256 y) external {
        require(a != b && msg.sender != a && msg.sender != b);
        uint256 ds = dai[msg.sender];
        uint256 ss = sin[a];
        uint256 v0 = vice;
        move(a, b, x);
        assert(dai[msg.sender] == ds);
        assert(sin[a] == ss);
        assert(vice == v0);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        move(a, b, x);
        assert(false);
    }

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(x > dai[a]);
        move(a, b, x);
        assert(false);
    }

    function check_move_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b && x > type(uint256).max - dai[b]);
        move(a, b, x);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 go = gem["SILVER"][a];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb + x);
        assert(gem["SILVER"][a] == go);
    }

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(x > gem["GOLD"][a]);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b && x > type(uint256).max - gem["GOLD"][b]);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_slip_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        if (dx >= 0) {
            assert(gem[i][u] == g0 + uint256(dx));
        } else {
            assert(gem[i][u] + uint256(-(dx + 1)) + 1 == g0);
        }
    }

    // ---------------- Vaults: frob ----------------

    function check_frob_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0) {
            assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
            assert(debt <= Line);
        }
    }

    function check_frob_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0 || dx < 0) {
            assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        }
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
    }

    function check_frob_ink_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0 && uint256(dx) > type(uint256).max - urns[i][u].ink);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_at_all(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender && can[u][msg.sender] == 0);
        require(dx != 0 || dy != 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_v(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        require(x > 0 && x < 2 ** 100);
        frob("GOLD", msg.sender, a, msg.sender, int256(x), 0);
        assert(false);
    }

    function check_frob_needs_consent_w(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        require(x > 0 && x < 2 ** 100);
        frob("GOLD", msg.sender, msg.sender, a, 0, -int256(x));
        assert(false);
    }

    function check_frob_needs_consent_u_debt(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        require(x > 0 && x < 2 ** 100);
        frob("GOLD", a, msg.sender, msg.sender, 0, int256(x));
        assert(false);
    }

    function check_frob_needs_consent_u_collateral(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        require(x > 0 && x < 2 ** 100);
        frob("GOLD", a, msg.sender, msg.sender, -int256(x), 0);
        assert(false);
    }

    function check_frob_draw_urn(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ink0 = urns["GOLD"][msg.sender].ink;
        uint256 art0 = urns["GOLD"][msg.sender].art;
        uint256 tot0 = ilks["GOLD"].Art;
        frob("GOLD", msg.sender, a, b, int256(x), int256(y));
        assert(urns["GOLD"][msg.sender].ink == ink0 + x);
        assert(urns["GOLD"][msg.sender].art == art0 + y);
        assert(ilks["GOLD"].Art == tot0 + y);
    }

    function check_frob_draw_balances(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 g0 = gem["GOLD"][a];
        uint256 d0 = dai[b];
        uint256 t0 = debt;
        frob("GOLD", msg.sender, a, b, int256(x), int256(y));
        assert(gem["GOLD"][a] + x == g0);
        assert(dai[b] == d0 + ilks["GOLD"].rate * y);
        assert(debt == t0 + ilks["GOLD"].rate * y);
    }

    function check_frob_wipe_urn(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ink0 = urns["GOLD"][msg.sender].ink;
        uint256 art0 = urns["GOLD"][msg.sender].art;
        uint256 tot0 = ilks["GOLD"].Art;
        frob("GOLD", msg.sender, a, b, -int256(x), -int256(y));
        assert(urns["GOLD"][msg.sender].ink + x == ink0);
        assert(urns["GOLD"][msg.sender].art + y == art0);
        assert(ilks["GOLD"].Art + y == tot0);
    }

    function check_frob_wipe_balances(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 g0 = gem["GOLD"][a];
        uint256 d0 = dai[b];
        uint256 t0 = debt;
        frob("GOLD", msg.sender, a, b, -int256(x), -int256(y));
        assert(gem["GOLD"][a] == g0 + x);
        assert(dai[b] + ilks["GOLD"].rate * y == d0);
        assert(debt + ilks["GOLD"].rate * y == t0);
    }

    // ---------------- Vaults: fork ----------------

    function check_fork_needs_consent_src(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender && can[a][msg.sender] == 0);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_needs_consent_dst(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender && can[b][msg.sender] == 0);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_conserves_ink(address a, address b, uint256 x, uint256 y) external {
        require(a != b && x < 2 ** 100 && y < 2 ** 100);
        uint256 ia = urns["GOLD"][a].ink;
        uint256 ib = urns["GOLD"][b].ink;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].ink + x == ia);
        assert(urns["GOLD"][b].ink == ib + x);
    }

    function check_fork_conserves_art(address a, address b, uint256 x, uint256 y) external {
        require(a != b && x < 2 ** 100 && y < 2 ** 100);
        uint256 aa = urns["GOLD"][a].art;
        uint256 ab = urns["GOLD"][b].art;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].art + y == aa);
        assert(urns["GOLD"][b].art == ab + y);
    }

    function check_fork_totals(address a, address b, uint256 x, uint256 y) external {
        uint256 t0 = ilks["GOLD"].Art;
        uint256 d0 = debt;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(ilks["GOLD"].Art == t0);
        assert(debt == d0);
    }

    function check_fork_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        fork(i, msg.sender, u, dx, dy);
        assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
    }

    function check_fork_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        fork(i, msg.sender, u, dx, dy);
        assert(urns[i][msg.sender].art == 0 || urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
    }

    // ---------------- Confiscation ----------------

    function check_grab_up_urn(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 tot0 = ilks["GOLD"].Art;
        uint256 g0 = gem["GOLD"][b];
        grab("GOLD", a, b, msg.sender, int256(x), int256(y));
        assert(urns["GOLD"][a].ink == ink0 + x);
        assert(urns["GOLD"][a].art == art0 + y);
        assert(ilks["GOLD"].Art == tot0 + y);
        assert(gem["GOLD"][b] + x == g0);
    }

    function check_grab_up_debt(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 s0 = sin[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        grab("GOLD", a, b, msg.sender, int256(x), int256(y));
        assert(sin[msg.sender] + ilks["GOLD"].rate * y == s0);
        assert(vice + ilks["GOLD"].rate * y == v0);
        assert(debt == t0);
    }

    function check_grab_down_urn(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 tot0 = ilks["GOLD"].Art;
        uint256 g0 = gem["GOLD"][b];
        grab("GOLD", a, b, msg.sender, -int256(x), -int256(y));
        assert(urns["GOLD"][a].ink + x == ink0);
        assert(urns["GOLD"][a].art + y == art0);
        assert(ilks["GOLD"].Art + y == tot0);
        assert(gem["GOLD"][b] == g0 + x);
    }

    function check_grab_down_debt(address a, address b, uint256 x, uint256 y) external {
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 s0 = sin[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        grab("GOLD", a, b, msg.sender, -int256(x), -int256(y));
        assert(sin[msg.sender] == s0 + ilks["GOLD"].rate * y);
        assert(vice == v0 + ilks["GOLD"].rate * y);
        assert(debt == t0);
    }

    // ---------------- Settlement ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        heal(x);
        assert(sin[msg.sender] + x == s0);
        assert(dai[msg.sender] + x == d0);
        assert(vice + x == v0);
        assert(debt + x == t0);
    }

    function check_heal_underflow_dai(address a, address b, uint256 x, uint256 y) external {
        require(x > dai[msg.sender]);
        heal(x);
        assert(false);
    }

    function check_heal_underflow_sin(address a, address b, uint256 x, uint256 y) external {
        require(x > sin[msg.sender]);
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

    function check_suck_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > type(uint256).max - debt);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        fold(i, u, dx);
        assert(ilks[i].rate == r0 + uint256(dx));
        assert(dai[u] == d0 + ilks[i].Art * uint256(dx));
        assert(debt == t0 + ilks[i].Art * uint256(dx));
    }

    function check_fold_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        uint256 m = uint256(-(dx + 1)) + 1;
        uint256 r0 = ilks[i].rate;
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        fold(i, u, dx);
        assert(ilks[i].rate + m == r0);
        assert(dai[u] + ilks[i].Art * m == d0);
        assert(debt + ilks[i].Art * m == t0);
    }
}
