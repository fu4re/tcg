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

    function check_deny_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_init_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    function check_file_line_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_ilk_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_cage_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
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

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 1);
        require(b != a);
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == w0);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 1);
        require(b != a);
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
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

    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 c0 = can[msg.sender][b];
        uint256 c1 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[msg.sender][b] == c0);
        assert(can[b][a] == c1);
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 c0 = can[msg.sender][b];
        uint256 c1 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[msg.sender][b] == c0);
        assert(can[b][a] == c1);
    }

    // ---------------- Collateral types / parameters ----------------

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        init(i);
        assert(ilks[i].rate == 10 ** 27);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_file_line_effect(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
    }

    function check_file_unknown_global(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_global_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_spot_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].rate == r0);
    }

    function check_file_line_ilk_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 d0 = ilks[i].dust;
        uint256 r0 = ilks[i].rate;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == d0);
        assert(ilks[i].rate == r0);
    }

    function check_file_dust_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 r0 = ilks[i].rate;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].rate == r0);
    }

    function check_file_unknown_ilk_param(bytes32 i, address u, int256 dx, int256 dy) external {
        require(bytes32(uint256(dx)) != "spot");
        require(bytes32(uint256(dx)) != "line");
        require(bytes32(uint256(dx)) != "dust");
        file(i, bytes32(uint256(dx)), uint256(dy));
        assert(false);
    }

    function check_file_ilk_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    // ---------------- Shutdown ----------------

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    // ---------------- Free collateral ----------------

    function check_slip_add(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 k0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] == k0 + uint256(dx));
    }

    function check_slip_sub(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > type(int256).min);
        uint256 k0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] + uint256(-dx) == k0);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 gs = gem["SILVER"][a];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb + x);
        assert(gem["SILVER"][a] == gs);
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

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 d0 = debt;
        move(a, b, x);
        assert(dai[a] + x == da);
        assert(dai[b] == db + x);
        assert(debt == d0);
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

    // ---------------- frob ----------------

    function check_frob_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_urn_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        require(dy > -(2 ** 100) && dy < 2 ** 100);
        uint256 k0 = urns[i][u].ink;
        uint256 t0 = urns[i][u].art;
        uint256 a0 = ilks[i].Art;
        require(k0 < 2 ** 200 && t0 < 2 ** 200 && a0 < 2 ** 200);
        frob(i, u, u, u, dx, dy);
        assert(int256(urns[i][u].ink) == int256(k0) + dx);
        assert(int256(urns[i][u].art) == int256(t0) + dy);
        assert(int256(ilks[i].Art) == int256(a0) + dy);
    }

    function check_frob_gem_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        require(dy > -(2 ** 100) && dy < 2 ** 100);
        uint256 g0 = gem[i][u];
        require(g0 < 2 ** 200);
        frob(i, u, u, u, dx, dy);
        assert(int256(gem[i][u]) == int256(g0) - dx);
    }

    function check_frob_dai_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        require(dy > -(2 ** 100) && dy < 2 ** 100);
        uint256 r0 = ilks[i].rate;
        uint256 d0 = dai[u];
        uint256 b0 = debt;
        require(r0 < 2 ** 100 && d0 < 2 ** 200 && b0 < 2 ** 200);
        frob(i, u, u, u, dx, dy);
        assert(int256(dai[u]) == int256(d0) + int256(r0) * dy);
        assert(int256(debt) == int256(b0) + int256(r0) * dy);
        assert(ilks[i].rate == r0);
    }

    function check_frob_distinct_gem(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 gb = gem["GOLD"][b];
        uint256 ga = gem["GOLD"][a];
        frob("GOLD", a, b, b, int256(x), int256(y));
        assert(gem["GOLD"][b] + x == gb);
        assert(gem["GOLD"][a] == ga);
    }

    function check_frob_distinct_dai(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 db = dai[b];
        uint256 da = dai[a];
        require(db < 2 ** 200);
        require(ilks["GOLD"].rate < 2 ** 100);
        frob("GOLD", a, b, b, int256(x), int256(y));
        assert(dai[b] == db + ilks["GOLD"].rate * y);
        assert(dai[a] == da);
    }

    function check_frob_distinct_urn(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 kb = urns["GOLD"][b].ink;
        uint256 tb = urns["GOLD"][b].art;
        uint256 s0 = ilks["SILVER"].Art;
        frob("GOLD", a, b, b, int256(x), int256(y));
        assert(urns["GOLD"][b].ink == kb);
        assert(urns["GOLD"][b].art == tb);
        assert(ilks["SILVER"].Art == s0);
    }

    function check_frob_ilk_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(ilks[i].Art < 2 ** 100 && ilks[i].rate < 2 ** 100);
        require((ilks[i].Art + uint256(dy)) * ilks[i].rate > ilks[i].line);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_global_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(debt < 2 ** 200 && ilks[i].rate < 2 ** 100);
        require(debt + ilks[i].rate * uint256(dy) > Line);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_not_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(dx >= 0 && dx < 2 ** 100);
        require(urns[i][u].art < 2 ** 100 && urns[i][u].ink < 2 ** 100);
        require(ilks[i].rate < 2 ** 100 && ilks[i].spot < 2 ** 100);
        require((urns[i][u].art + uint256(dy)) * ilks[i].rate > (urns[i][u].ink + uint256(dx)) * ilks[i].spot);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_not_safe_withdraw(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > -(2 ** 100));
        require(dy >= 0 && dy < 2 ** 100);
        require(urns[i][u].art < 2 ** 100 && urns[i][u].ink < 2 ** 100);
        require(ilks[i].rate < 2 ** 100 && ilks[i].spot < 2 ** 100);
        require(urns[i][u].ink >= uint256(-dx));
        require((urns[i][u].art + uint256(dy)) * ilks[i].rate > (urns[i][u].ink - uint256(-dx)) * ilks[i].spot);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_urn_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 || dx < 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_gem_consent(address a, address b, uint256 x, uint256 y) external {
        require(x > 0 && x < 2 ** 100);
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        frob("GOLD", msg.sender, a, msg.sender, int256(x), 0);
        assert(false);
    }

    function check_frob_needs_dai_consent(address a, address b, uint256 x, uint256 y) external {
        require(y > 0 && y < 2 ** 100);
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        frob("GOLD", msg.sender, msg.sender, a, 0, int256(y));
        assert(false);
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 && dy < 2 ** 100);
        require(urns[i][u].art < 2 ** 100 && ilks[i].rate < 2 ** 100);
        require((urns[i][u].art + uint256(dy)) * ilks[i].rate < ilks[i].dust);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- fork ----------------

    function check_fork_ink(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ka = urns["GOLD"][a].ink;
        uint256 kb = urns["GOLD"][b].ink;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].ink + x == ka);
        assert(urns["GOLD"][b].ink == kb + x);
    }

    function check_fork_art(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ta = urns["GOLD"][a].art;
        uint256 tb = urns["GOLD"][b].art;
        uint256 a0 = ilks["GOLD"].Art;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(urns["GOLD"][a].art + y == ta);
        assert(urns["GOLD"][b].art == tb + y);
        assert(ilks["GOLD"].Art == a0);
    }

    function check_fork_no_other_change(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ga = gem["GOLD"][a];
        uint256 da = dai[a];
        uint256 d0 = debt;
        fork("GOLD", a, b, int256(x), int256(y));
        assert(gem["GOLD"][a] == ga);
        assert(dai[a] == da);
        assert(debt == d0);
    }

    function check_fork_needs_src_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_needs_dst_consent(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        require(can[b][msg.sender] != 1);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_src_unsafe(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        require(urns["GOLD"][a].ink < 2 ** 100 && urns["GOLD"][a].art < 2 ** 100);
        require(urns["GOLD"][a].ink >= x && urns["GOLD"][a].art >= y);
        require(ilks["GOLD"].rate < 2 ** 100 && ilks["GOLD"].spot < 2 ** 100);
        require((urns["GOLD"][a].art - y) * ilks["GOLD"].rate > (urns["GOLD"][a].ink - x) * ilks["GOLD"].spot);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_dst_unsafe(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        require(urns["GOLD"][b].ink < 2 ** 100 && urns["GOLD"][b].art < 2 ** 100);
        require(ilks["GOLD"].rate < 2 ** 100 && ilks["GOLD"].spot < 2 ** 100);
        require((urns["GOLD"][b].art + y) * ilks["GOLD"].rate > (urns["GOLD"][b].ink + x) * ilks["GOLD"].spot);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_src_dust(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        require(urns["GOLD"][a].art < 2 ** 100 && urns["GOLD"][a].art > y);
        require(ilks["GOLD"].rate < 2 ** 100);
        require((urns["GOLD"][a].art - y) * ilks["GOLD"].rate < ilks["GOLD"].dust);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    function check_fork_dst_dust(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y > 0 && y < 2 ** 100);
        require(urns["GOLD"][b].art < 2 ** 100);
        require(ilks["GOLD"].rate < 2 ** 100);
        require((urns["GOLD"][b].art + y) * ilks["GOLD"].rate < ilks["GOLD"].dust);
        fork("GOLD", a, b, int256(x), int256(y));
        assert(false);
    }

    // ---------------- grab ----------------

    function check_grab_urn_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        require(dy > -(2 ** 100) && dy < 2 ** 100);
        uint256 k0 = urns[i][u].ink;
        uint256 t0 = urns[i][u].art;
        uint256 a0 = ilks[i].Art;
        require(k0 < 2 ** 200 && t0 < 2 ** 200 && a0 < 2 ** 200);
        grab(i, u, u, u, dx, dy);
        assert(int256(urns[i][u].ink) == int256(k0) + dx);
        assert(int256(urns[i][u].art) == int256(t0) + dy);
        assert(int256(ilks[i].Art) == int256(a0) + dy);
    }

    function check_grab_gem_sin_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        require(dy > -(2 ** 100) && dy < 2 ** 100);
        uint256 g0 = gem[i][u];
        uint256 s0 = sin[u];
        uint256 r0 = ilks[i].rate;
        require(g0 < 2 ** 200 && s0 < 2 ** 200 && r0 < 2 ** 100);
        grab(i, u, u, u, dx, dy);
        assert(int256(gem[i][u]) == int256(g0) - dx);
        assert(int256(sin[u]) == int256(s0) - int256(r0) * dy);
    }

    function check_grab_totals(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > -(2 ** 100) && dy < 2 ** 100);
        uint256 v0 = vice;
        uint256 b0 = debt;
        uint256 d0 = dai[u];
        uint256 r0 = ilks[i].rate;
        require(v0 < 2 ** 200 && r0 < 2 ** 100);
        grab(i, u, u, u, dx, dy);
        assert(int256(vice) == int256(v0) - int256(r0) * dy);
        assert(debt == b0);
        assert(dai[u] == d0);
    }

    function check_grab_distinct(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(x < 2 ** 100 && y < 2 ** 100);
        uint256 ga = gem["GOLD"][a];
        uint256 sa = sin[a];
        uint256 sb = sin[b];
        uint256 r0 = ilks["GOLD"].rate;
        require(r0 < 2 ** 100);
        grab("GOLD", a, a, b, int256(x), int256(y));
        assert(gem["GOLD"][a] + x == ga);
        assert(sin[b] + r0 * y == sb);
        assert(sin[a] == sa);
    }

    // ---------------- heal / suck ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 v0 = vice;
        uint256 b0 = debt;
        heal(x);
        assert(sin[msg.sender] + x == s0);
        assert(dai[msg.sender] + x == d0);
        assert(vice + x == v0);
        assert(debt + x == b0);
    }

    function check_heal_others(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = sin[a];
        uint256 d0 = dai[a];
        heal(x);
        assert(sin[a] == s0);
        assert(dai[a] == d0);
    }

    function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 sa = sin[a];
        uint256 db = dai[b];
        uint256 v0 = vice;
        uint256 b0 = debt;
        suck(a, b, x);
        assert(sin[a] == sa + x);
        assert(dai[b] == db + x);
        assert(vice == v0 + x);
        assert(debt == b0 + x);
    }

    function check_suck_others(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 da = dai[a];
        uint256 sb = sin[b];
        suck(a, b, x);
        assert(dai[a] == da);
        assert(sin[b] == sb);
    }

    // ---------------- fold ----------------

    function check_fold_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_rate(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        uint256 r0 = ilks[i].rate;
        uint256 a0 = ilks[i].Art;
        uint256 s0 = ilks[i].spot;
        require(r0 < 2 ** 100);
        fold(i, u, dx);
        assert(int256(ilks[i].rate) == int256(r0) + dx);
        assert(ilks[i].Art == a0);
        assert(ilks[i].spot == s0);
    }

    function check_fold_dai_debt(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > -(2 ** 100) && dx < 2 ** 100);
        uint256 a0 = ilks[i].Art;
        uint256 d0 = dai[u];
        uint256 b0 = debt;
        require(a0 < 2 ** 100 && d0 < 2 ** 200 && b0 < 2 ** 200);
        fold(i, u, dx);
        assert(int256(dai[u]) == int256(d0) + int256(a0) * dx);
        assert(int256(debt) == int256(b0) + int256(a0) * dx);
    }
}
