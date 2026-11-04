// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------- Authority ----------
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

    function check_file_unauth(address a, address b, uint256 x, uint256 y) external {
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

    function check_slip_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        slip("GOLD", a, int256(x));
        assert(false);
    }

    function check_grab_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        grab("GOLD", a, b, a, int256(x), int256(y));
        assert(false);
    }

    function check_suck_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    function check_fold_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        fold("GOLD", a, int256(x));
        assert(false);
    }

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        if (b != a) {
            assert(wards[b] == w0);
        }
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        if (b != a) {
            assert(wards[b] == w0);
        }
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

    // ---------- Consent ----------
    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 c0 = can[b][a];
        uint256 c1 = can[msg.sender][b];
        hope(a);
        assert(can[msg.sender][a] == 1);
        if (b != msg.sender) {
            assert(can[b][a] == c0);
        }
        if (b != a) {
            assert(can[msg.sender][b] == c1);
        }
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 c0 = can[b][a];
        uint256 c1 = can[msg.sender][b];
        nope(a);
        assert(can[msg.sender][a] == 0);
        if (b != msg.sender) {
            assert(can[b][a] == c0);
        }
        if (b != a) {
            assert(can[msg.sender][b] == c1);
        }
    }

    function check_move_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        move(a, b, x);
        assert(false);
    }

    function check_flux_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        flux("GOLD", a, b, x);
        assert(false);
    }

    // ---------- Collateral types ----------
    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        init(i);
        assert(ilks[i].rate == 10 ** 27);
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

    // ---------- Parameters ----------
    function check_file_sets_line(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
    }

    function check_file_spot(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].rate == r0);
    }

    function check_file_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 d0 = ilks[i].dust;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == d0);
    }

    function check_file_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
    }

    function check_file_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_ilk_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "spot" && i != "line" && i != "dust");
        file("GOLD", i, uint256(dy));
        assert(false);
    }

    function check_file_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    // ---------- Shutdown ----------
    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_live_flag(address a, address b, uint256 x, uint256 y) external {
        assert(live == 0 || live == 1);
    }

    function check_stays_caged(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        hope(a);
        nope(b);
        assert(live == 0);
    }

    // ---------- Moving value ----------
    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 d0 = debt;
        uint256 v0 = vice;
        move(a, b, x);
        assert(dai[a] + x == da);
        assert(dai[b] == db + x);
        assert(debt == d0);
        assert(vice == v0);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        uint256 da = dai[a];
        move(a, a, x);
        assert(dai[a] == da);
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

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 gc = gem["SILVER"][a];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb + x);
        assert(gem["SILVER"][a] == gc);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        uint256 ga = gem["GOLD"][a];
        flux("GOLD", a, a, x);
        assert(gem["GOLD"][a] == ga);
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

    // ---------- Vaults ----------
    function check_frob_ink_gem(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 g0 = gem[i][u];
        frob(i, u, u, u, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][u] + uint256(dx) == g0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][u] == g0 + uint256(-dx));
        }
    }

    function check_frob_art(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > type(int256).min);
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        frob(i, u, u, u, dx, dy);
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
        }
    }

    function check_frob_dai_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > type(int256).min);
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        uint256 r0 = ilks[i].rate;
        frob(i, u, u, u, dx, dy);
        assert(ilks[i].rate == r0);
        if (dy >= 0) {
            assert(dai[u] == d0 + r0 * uint256(dy));
            assert(debt == t0 + r0 * uint256(dy));
        } else {
            assert(dai[u] + r0 * uint256(-dy) == d0);
            assert(debt + r0 * uint256(-dy) == t0);
        }
    }

    function check_frob_guards(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        assert(live == 1);
        assert(ilks[i].rate != 0);
        if (dy > 0) {
            assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
            assert(debt <= Line);
        }
        if (dy > 0 || dx < 0) {
            assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
            assert(u == msg.sender || can[u][msg.sender] == 1);
        }
        assert(urns[i][u].art == 0 || urns[i][u].art * ilks[i].rate >= ilks[i].dust);
    }

    function check_frob_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_distinct_pos(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 Art0 = ilks["GOLD"].Art;
        uint256 g0 = gem["GOLD"][b];
        uint256 d0 = dai[msg.sender];
        uint256 t0 = debt;
        uint256 r0 = ilks["GOLD"].rate;
        frob("GOLD", a, b, msg.sender, int256(x), int256(y));
        assert(urns["GOLD"][a].ink == ink0 + x);
        assert(urns["GOLD"][a].art == art0 + y);
        assert(ilks["GOLD"].Art == Art0 + y);
        assert(gem["GOLD"][b] + x == g0);
        assert(dai[msg.sender] == d0 + r0 * y);
        assert(debt == t0 + r0 * y);
        if (y > 0) {
            assert(a == msg.sender || can[a][msg.sender] == 1);
        }
        if (x > 0) {
            assert(b == msg.sender || can[b][msg.sender] == 1);
        }
    }

    function check_frob_distinct_neg(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 Art0 = ilks["GOLD"].Art;
        uint256 g0 = gem["GOLD"][b];
        uint256 d0 = dai[msg.sender];
        uint256 t0 = debt;
        uint256 r0 = ilks["GOLD"].rate;
        frob("GOLD", a, b, msg.sender, -int256(x), -int256(y));
        assert(urns["GOLD"][a].ink + x == ink0);
        assert(urns["GOLD"][a].art + y == art0);
        assert(ilks["GOLD"].Art + y == Art0);
        assert(gem["GOLD"][b] == g0 + x);
        assert(dai[msg.sender] + r0 * y == d0);
        assert(debt + r0 * y == t0);
        if (x > 0) {
            assert(a == msg.sender || can[a][msg.sender] == 1);
        }
    }

    // ---------- Fork ----------
    function check_fork_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        uint256 inka = urns["GOLD"][a].ink;
        uint256 inkb = urns["GOLD"][b].ink;
        uint256 arta = urns["GOLD"][a].art;
        uint256 artb = urns["GOLD"][b].art;
        uint256 Art0 = ilks["GOLD"].Art;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].ink + x == inka);
        assert(urns["GOLD"][b].ink == inkb + x);
        assert(urns["GOLD"][a].art + y == arta);
        assert(urns["GOLD"][b].art == artb + y);
        assert(ilks["GOLD"].Art == Art0);
        assert(a == msg.sender || can[a][msg.sender] == 1);
        assert(b == msg.sender || can[b][msg.sender] == 1);
    }

    function check_fork_safe(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].art * ilks["GOLD"].rate <= urns["GOLD"][a].ink * ilks["GOLD"].spot);
        assert(urns["GOLD"][b].art * ilks["GOLD"].rate <= urns["GOLD"][b].ink * ilks["GOLD"].spot);
        assert(urns["GOLD"][a].art == 0 || urns["GOLD"][a].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);
        assert(urns["GOLD"][b].art == 0 || urns["GOLD"][b].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);
    }

    function check_fork_self(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        fork(i, u, u, dx, dy);
        assert(urns[i][u].ink == ink0);
        assert(urns[i][u].art == art0);
    }

    // ---------- Confiscation ----------
    function check_grab_neg(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 Art0 = ilks["GOLD"].Art;
        uint256 g0 = gem["GOLD"][b];
        uint256 s0 = sin[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        uint256 r0 = ilks["GOLD"].rate;
        grab("GOLD", a, b, msg.sender, -int256(x), -int256(y));
        assert(urns["GOLD"][a].ink + x == ink0);
        assert(urns["GOLD"][a].art + y == art0);
        assert(ilks["GOLD"].Art + y == Art0);
        assert(gem["GOLD"][b] == g0 + x);
        assert(sin[msg.sender] == s0 + r0 * y);
        assert(vice == v0 + r0 * y);
        assert(debt == t0);
    }

    function check_grab_pos(address a, address b, uint256 x, uint256 y) external {
        require(x <= uint256(type(int256).max));
        require(y <= uint256(type(int256).max));
        uint256 ink0 = urns["GOLD"][a].ink;
        uint256 art0 = urns["GOLD"][a].art;
        uint256 Art0 = ilks["GOLD"].Art;
        uint256 g0 = gem["GOLD"][b];
        uint256 s0 = sin[msg.sender];
        uint256 v0 = vice;
        uint256 t0 = debt;
        uint256 r0 = ilks["GOLD"].rate;
        grab("GOLD", a, b, msg.sender, int256(x), int256(y));
        assert(urns["GOLD"][a].ink == ink0 + x);
        assert(urns["GOLD"][a].art == art0 + y);
        assert(ilks["GOLD"].Art == Art0 + y);
        assert(gem["GOLD"][b] + x == g0);
        assert(sin[msg.sender] + r0 * y == s0);
        assert(vice + r0 * y == v0);
        assert(debt == t0);
    }

    // ---------- Settlement ----------
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

    function check_heal_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_underflow_sin(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < x);
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
        require(debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------- Rates ----------
    function check_fold_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 r0 = ilks[i].rate;
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        uint256 Art0 = ilks[i].Art;
        fold(i, u, dx);
        assert(ilks[i].Art == Art0);
        if (dx >= 0) {
            assert(ilks[i].rate == r0 + uint256(dx));
            assert(dai[u] == d0 + Art0 * uint256(dx));
            assert(debt == t0 + Art0 * uint256(dx));
        } else {
            assert(ilks[i].rate + uint256(-dx) == r0);
            assert(dai[u] + Art0 * uint256(-dx) == d0);
            assert(debt + Art0 * uint256(-dx) == t0);
        }
    }

    function check_fold_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }
}
