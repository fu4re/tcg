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

    function check_rely_sets(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == w0);
    }

    function check_rely_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        rely(a);
        assert(false);
    }

    function check_deny_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_deny_sets(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == w0);
    }

    function check_deny_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        deny(a);
        assert(false);
    }

    function check_init_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    function check_init_once(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_init_sets_rate(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 a0 = ilks[i].Art;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].Art == a0);
    }

    function check_cage_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

    function check_cage_sets_not_live(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_dead_stays_dead_rely(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    function check_dead_no_frob(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_dead_no_fold(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_dead_no_file(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_slip_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    function check_grab_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_suck_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    function check_fold_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    function check_file_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    // ---------------- Parameters ----------------

    function check_file_sets_line(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
    }

    function check_file_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_ilk_spot(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        uint256 a0 = ilks[i].Art;
        uint256 g0 = Line;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == a0);
        assert(Line == g0);
    }

    function check_file_ilk_line(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 d0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        uint256 a0 = ilks[i].Art;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == a0);
    }

    function check_file_ilk_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 r0 = ilks[i].rate;
        uint256 a0 = ilks[i].Art;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == a0);
    }

    function check_file_ilk_unknown(address a, address b, uint256 x, uint256 y) external {
        require(bytes32(x) != "spot");
        require(bytes32(x) != "line");
        require(bytes32(x) != "dust");
        file("GOLD", bytes32(x), y);
        assert(false);
    }

    function check_file_ilk_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    // ---------------- Consent ----------------

    function check_hope(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 c0 = can[msg.sender][b];
        uint256 c1 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[msg.sender][b] == c0);
        assert(can[b][a] == c1 || b == msg.sender);
    }

    function check_nope(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 c0 = can[msg.sender][b];
        uint256 c1 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[msg.sender][b] == c0);
        assert(can[b][a] == c1 || b == msg.sender);
    }

    // ---------------- Moving value ----------------

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 sa = gem["GOLD"][a];
        uint256 sb = gem["GOLD"][b];
        uint256 o0 = gem["COAL"][a];
        uint256 d0 = dai[a];
        uint256 t0 = debt;
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == sa);
        assert(gem["GOLD"][b] == sb + x);
        assert(gem["COAL"][a] == o0);
        assert(dai[a] == d0);
        assert(debt == t0);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        uint256 sa = gem["GOLD"][a];
        flux("GOLD", a, a, x);
        assert(gem["GOLD"][a] == sa);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        move(a, b, x);
        assert(false);
    }

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 sa = dai[a];
        uint256 sb = dai[b];
        uint256 g0 = gem["GOLD"][a];
        uint256 t0 = debt;
        uint256 v0 = vice;
        move(a, b, x);
        assert(dai[a] + x == sa);
        assert(dai[b] == sb + x);
        assert(gem["GOLD"][a] == g0);
        assert(debt == t0);
        assert(vice == v0);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        uint256 sa = dai[a];
        move(a, a, x);
        assert(dai[a] == sa);
    }

    // ---------------- Slip ----------------

    function check_slip_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 g0 = gem[i][u];
        uint256 t0 = debt;
        slip(i, u, dx);
        assert(gem[i][u] == g0 + uint256(dx));
        assert(debt == t0);
    }

    function check_slip_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] + uint256(-dx) == g0);
    }

    // ---------------- Vaults: frob ----------------

    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ceilings(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, u, u, u, dx, dy);
        if (dy > 0) {
            assert(debt <= Line);
            assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
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
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    function check_frob_needs_owner_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        require(dy > 0 || dx < 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_collateral_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        require(x > 0);
        require(x <= 10 ** 30);
        require(y <= 10 ** 30);
        frob("GOLD", msg.sender, a, msg.sender, int256(x), int256(y));
        assert(false);
    }

    function check_frob_needs_debt_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        require(y > 0);
        require(y <= 10 ** 30);
        require(x <= 10 ** 30);
        frob("GOLD", msg.sender, msg.sender, a, int256(x), -int256(y));
        assert(false);
    }

    function check_frob_collateral_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 k0 = urns[i][u].ink;
        uint256 a0 = urns[i][u].art;
        uint256 g0 = gem[i][u];
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        uint256 b0 = ilks[i].Art;
        frob(i, u, u, u, dx, 0);
        assert(urns[i][u].ink == k0 + uint256(dx));
        assert(gem[i][u] + uint256(dx) == g0);
        assert(urns[i][u].art == a0);
        assert(ilks[i].Art == b0);
        assert(dai[u] == d0);
        assert(debt == t0);
    }

    function check_frob_collateral_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        uint256 k0 = urns[i][u].ink;
        uint256 a0 = urns[i][u].art;
        uint256 g0 = gem[i][u];
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        frob(i, u, u, u, dx, 0);
        assert(urns[i][u].ink + uint256(-dx) == k0);
        assert(gem[i][u] == g0 + uint256(-dx));
        assert(urns[i][u].art == a0);
        assert(dai[u] == d0);
        assert(debt == t0);
    }

    function check_frob_debt_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        uint256 k0 = urns[i][u].ink;
        uint256 a0 = urns[i][u].art;
        uint256 g0 = gem[i][u];
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        uint256 b0 = ilks[i].Art;
        uint256 r0 = ilks[i].rate;
        frob(i, u, u, u, 0, dy);
        assert(urns[i][u].art == a0 + uint256(dy));
        assert(ilks[i].Art == b0 + uint256(dy));
        assert(ilks[i].rate == r0);
        assert(dai[u] == d0 + r0 * uint256(dy));
        assert(debt == t0 + r0 * uint256(dy));
        assert(urns[i][u].ink == k0);
        assert(gem[i][u] == g0);
    }

    function check_frob_full(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x <= 10 ** 30);
        require(y <= 10 ** 30);
        uint256 k0 = urns["GOLD"][a].ink;
        uint256 a0 = urns["GOLD"][a].art;
        uint256 b0 = ilks["GOLD"].Art;
        uint256 r0 = ilks["GOLD"].rate;
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 t0 = debt;
        frob("GOLD", a, a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].ink == k0 + x);
        assert(urns["GOLD"][a].art == a0 + y);
        assert(ilks["GOLD"].Art == b0 + y);
        assert(ilks["GOLD"].rate == r0);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb);
        assert(dai[a] == da);
        assert(dai[b] == db + r0 * y);
        assert(debt == t0 + r0 * y);
    }

    function check_frob_close(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x <= 10 ** 30);
        require(y <= 10 ** 30);
        uint256 k0 = urns["GOLD"][a].ink;
        uint256 a0 = urns["GOLD"][a].art;
        uint256 b0 = ilks["GOLD"].Art;
        uint256 r0 = ilks["GOLD"].rate;
        uint256 ga = gem["GOLD"][b];
        uint256 gc = gem["GOLD"][a];
        uint256 da = dai[b];
        uint256 t0 = debt;
        frob("GOLD", a, b, b, -int256(x), -int256(y));
        assert(urns["GOLD"][a].ink + x == k0);
        assert(urns["GOLD"][a].art + y == a0);
        assert(ilks["GOLD"].Art + y == b0);
        assert(gem["GOLD"][b] == ga + x);
        assert(gem["GOLD"][a] == gc);
        assert(dai[b] + r0 * y == da);
        assert(debt + r0 * y == t0);
    }

    // ---------------- Vaults: fork ----------------

    function check_fork_needs_src_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        fork("GOLD", a, b, 0, 0);
        assert(false);
    }

    function check_fork_needs_dst_consent(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        require(can[b][msg.sender] != 1);
        fork("GOLD", a, b, 0, 0);
        assert(false);
    }

    function check_fork_safe_dust(address a, address b, uint256 x, uint256 y) external {
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].art * ilks["GOLD"].rate <= urns["GOLD"][a].ink * ilks["GOLD"].spot);
        assert(urns["GOLD"][b].art * ilks["GOLD"].rate <= urns["GOLD"][b].ink * ilks["GOLD"].spot);
        assert(urns["GOLD"][a].art == 0 || urns["GOLD"][a].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);
        assert(urns["GOLD"][b].art == 0 || urns["GOLD"][b].art * ilks["GOLD"].rate >= ilks["GOLD"].dust);
    }

    function check_fork_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x <= 10 ** 30);
        require(y <= 10 ** 30);
        uint256 ka = urns["GOLD"][a].ink;
        uint256 kb = urns["GOLD"][b].ink;
        uint256 aa = urns["GOLD"][a].art;
        uint256 ab = urns["GOLD"][b].art;
        uint256 b0 = ilks["GOLD"].Art;
        uint256 t0 = debt;
        uint256 ga = gem["GOLD"][a];
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].ink + x == ka);
        assert(urns["GOLD"][b].ink == kb + x);
        assert(urns["GOLD"][a].art + y == aa);
        assert(urns["GOLD"][b].art == ab + y);
        assert(ilks["GOLD"].Art == b0);
        assert(debt == t0);
        assert(gem["GOLD"][a] == ga);
    }

    // ---------------- Confiscation ----------------

    function check_grab_effect(address a, address b, uint256 x, uint256 y) external {
        require(x <= 10 ** 30);
        require(y <= 10 ** 30);
        uint256 k0 = urns["GOLD"][a].ink;
        uint256 a0 = urns["GOLD"][a].art;
        uint256 b0 = ilks["GOLD"].Art;
        uint256 r0 = ilks["GOLD"].rate;
        uint256 g0 = gem["GOLD"][a];
        uint256 s0 = sin[b];
        uint256 v0 = vice;
        uint256 t0 = debt;
        uint256 d0 = dai[b];
        grab("GOLD", a, a, b, -int256(x), -int256(y));
        assert(urns["GOLD"][a].ink + x == k0);
        assert(urns["GOLD"][a].art + y == a0);
        assert(ilks["GOLD"].Art + y == b0);
        assert(ilks["GOLD"].rate == r0);
        assert(gem["GOLD"][a] == g0 + x);
        assert(sin[b] == s0 + r0 * y);
        assert(vice == v0 + r0 * y);
        assert(debt == t0);
        assert(dai[b] == d0);
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

    // ---------------- Rates ----------------

    function check_fold_up(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 r0 = ilks[i].rate;
        uint256 a0 = ilks[i].Art;
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        fold(i, u, dx);
        assert(ilks[i].rate == r0 + uint256(dx));
        assert(ilks[i].Art == a0);
        assert(dai[u] == d0 + a0 * uint256(dx));
        assert(debt == t0 + a0 * uint256(dx));
    }

    function check_fold_down(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0);
        require(dx > type(int256).min);
        uint256 r0 = ilks[i].rate;
        uint256 a0 = ilks[i].Art;
        uint256 d0 = dai[u];
        uint256 t0 = debt;
        fold(i, u, dx);
        assert(ilks[i].rate + uint256(-dx) == r0);
        assert(ilks[i].Art == a0);
        assert(dai[u] + a0 * uint256(-dx) == d0);
        assert(debt + a0 * uint256(-dx) == t0);
    }
}
