// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely(address a, address b, uint256 x, uint256 y) external {
        uint256 wb = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(live == 1);
        if (a != b) {
            assert(wards[b] == wb);
        }
    }

    function check_rely_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        rely(a);
        assert(false);
    }

    function check_rely_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        rely(a);
        assert(false);
    }

    function check_deny(address a, address b, uint256 x, uint256 y) external {
        uint256 wb = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(live == 1);
        if (a != b) {
            assert(wards[b] == wb);
        }
    }

    function check_deny_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    function check_deny_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        deny(a);
        assert(false);
    }

    function check_cage(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_cage_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }

    // ---------------- Consent ----------------

    function check_hope(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 cb = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[b][a] == cb);
    }

    function check_nope(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 cb = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[b][a] == cb);
    }

    // ---------------- Collateral types and parameters ----------------

    function check_init(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 Art0 = ilks[i].Art;
        uint256 sp0 = ilks[i].spot;
        uint256 ln0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].Art == Art0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].line == ln0);
        assert(ilks[i].dust == du0);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_init_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    function check_file_Line(address a, address b, uint256 x, uint256 y) external {
        uint256 d0 = debt;
        file("Line", x);
        assert(Line == x);
        assert(live == 1);
        assert(debt == d0);
    }

    function check_file_Line_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_Line_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live != 1);
        file("Line", x);
        assert(false);
    }

    function check_file_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_ilk_spot(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 Art0 = ilks[i].Art;
        uint256 rt0 = ilks[i].rate;
        uint256 ln0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        uint256 L0 = Line;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].Art == Art0);
        assert(ilks[i].rate == rt0);
        assert(ilks[i].line == ln0);
        assert(ilks[i].dust == du0);
        assert(Line == L0);
        assert(live == 1);
    }

    function check_file_ilk_line(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 Art0 = ilks[i].Art;
        uint256 rt0 = ilks[i].rate;
        uint256 sp0 = ilks[i].spot;
        uint256 du0 = ilks[i].dust;
        uint256 L0 = Line;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].Art == Art0);
        assert(ilks[i].rate == rt0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].dust == du0);
        assert(Line == L0);
        assert(live == 1);
    }

    function check_file_ilk_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 Art0 = ilks[i].Art;
        uint256 rt0 = ilks[i].rate;
        uint256 sp0 = ilks[i].spot;
        uint256 ln0 = ilks[i].line;
        uint256 L0 = Line;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].Art == Art0);
        assert(ilks[i].rate == rt0);
        assert(ilks[i].spot == sp0);
        assert(ilks[i].line == ln0);
        assert(Line == L0);
        assert(live == 1);
    }

    function check_file_ilk_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "spot");
        require(i != "line");
        require(i != "dust");
        file("GOLD", i, uint256(dx));
        assert(false);
    }

    function check_file_ilk_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_file_ilk_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        file(i, "line", uint256(dx));
        assert(false);
    }

    // ---------------- Free collateral ----------------

    function check_slip(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        if (dx >= 0) {
            assert(gem[i][u] == g0 + uint256(dx));
        } else {
            assert(gem[i][u] + uint256(-dx) == g0);
        }
    }

    function check_slip_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    function check_slip_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(gem[i][u] > type(uint256).max - uint256(dx));
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

    function check_flux(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 gs = gem["SILVER"][a];
        uint256 gt = gem["SILVER"][b];
        uint256 gm = gem["GOLD"][msg.sender];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb + x);
        assert(gem["SILVER"][a] == gs);
        assert(gem["SILVER"][b] == gt);
        if (msg.sender != a && msg.sender != b) {
            assert(gem["GOLD"][msg.sender] == gm);
        }
    }

    function check_flux_no_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        require(gem["GOLD"][a] < x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    // ---------------- Stablecoin movement ----------------

    function check_move(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 dm = dai[msg.sender];
        uint256 dt = debt;
        uint256 vc = vice;
        move(a, b, x);
        assert(dai[a] + x == da);
        assert(dai[b] == db + x);
        assert(debt == dt);
        assert(vice == vc);
        if (msg.sender != a && msg.sender != b) {
            assert(dai[msg.sender] == dm);
        }
    }

    function check_move_no_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] != 1);
        move(a, b, x);
        assert(false);
    }

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        require(dai[a] < x);
        move(a, b, x);
        assert(false);
    }

    function check_move_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender);
        require(dai[b] > type(uint256).max - x);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vault operations ----------------

    function check_frob_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 rt = ilks[i].rate;
        uint256 gm0 = gem[i][u];
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        frob(i, u, u, u, dx, dy);
        assert(ilks[i].rate == rt);
        assert(vice == vice0);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][u] + uint256(dx) == gm0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][u] == gm0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
            assert(debt == debt0 + rt * uint256(dy));
            assert(dai[u] == dai0 + rt * uint256(dy));
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
            assert(debt + rt * uint256(-dy) == debt0);
            assert(dai[u] + rt * uint256(-dy) == dai0);
        }
    }

    function check_frob_collateral_source(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 gv0 = gem[i][msg.sender];
        uint256 gu0 = gem[i][u];
        uint256 dw0 = dai[u];
        uint256 dm0 = dai[msg.sender];
        uint256 rt = ilks[i].rate;
        frob(i, u, msg.sender, u, dx, dy);
        assert(gem[i][u] == gu0);
        assert(dai[msg.sender] == dm0);
        if (dx >= 0) {
            assert(gem[i][msg.sender] + uint256(dx) == gv0);
        } else {
            assert(gem[i][msg.sender] == gv0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(dai[u] == dw0 + rt * uint256(dy));
        } else {
            assert(dai[u] + rt * uint256(-dy) == dw0);
        }
    }

    function check_frob_debt_destination(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 gu0 = gem[i][u];
        uint256 gm0 = gem[i][msg.sender];
        uint256 du0 = dai[u];
        uint256 dw0 = dai[msg.sender];
        uint256 rt = ilks[i].rate;
        frob(i, u, u, msg.sender, dx, dy);
        assert(gem[i][msg.sender] == gm0);
        assert(dai[u] == du0);
        if (dx >= 0) {
            assert(gem[i][u] + uint256(dx) == gu0);
        } else {
            assert(gem[i][u] == gu0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(dai[msg.sender] == dw0 + rt * uint256(dy));
        } else {
            assert(dai[msg.sender] + rt * uint256(-dy) == dw0);
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
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    function check_frob_consent_v(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, msg.sender, u, msg.sender, dx, dy);
        if (dx > 0) {
            assert(u == msg.sender || can[u][msg.sender] == 1);
        }
    }

    function check_frob_consent_w(bytes32 i, address u, int256 dx, int256 dy) external {
        frob(i, msg.sender, msg.sender, u, dx, dy);
        if (dy < 0) {
            assert(u == msg.sender || can[u][msg.sender] == 1);
        }
    }

    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_no_consent_u(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0 || dx < 0);
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_ink_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > 0);
        require(urns[i][u].ink > type(uint256).max - uint256(dx));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Fork ----------------

    function check_fork_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 inkm = urns[i][msg.sender].ink;
        uint256 artm = urns[i][msg.sender].art;
        uint256 Art0 = ilks[i].Art;
        uint256 debt0 = debt;
        fork(i, u, msg.sender, dx, dy);
        assert(ilks[i].Art == Art0);
        assert(debt == debt0);
        assert(can[u][msg.sender] == 1);
        if (dx >= 0) {
            assert(urns[i][u].ink + uint256(dx) == ink0);
            assert(urns[i][msg.sender].ink == inkm + uint256(dx));
        } else {
            assert(urns[i][u].ink == ink0 + uint256(-dx));
            assert(urns[i][msg.sender].ink + uint256(-dx) == inkm);
        }
        if (dy >= 0) {
            assert(urns[i][u].art + uint256(dy) == art0);
            assert(urns[i][msg.sender].art == artm + uint256(dy));
        } else {
            assert(urns[i][u].art == art0 + uint256(-dy));
            assert(urns[i][msg.sender].art + uint256(-dy) == artm);
        }
    }

    function check_fork_safety(bytes32 i, address u, int256 dx, int256 dy) external {
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
        if (urns[i][msg.sender].art != 0) {
            assert(urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    function check_fork_consent_dst(bytes32 i, address u, int256 dx, int256 dy) external {
        fork(i, msg.sender, u, dx, dy);
        assert(u == msg.sender || can[u][msg.sender] == 1);
    }

    function check_fork_no_consent_src(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_no_consent_dst(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] != 1);
        fork(i, msg.sender, u, dx, dy);
        assert(false);
    }

    // ---------------- Confiscation ----------------

    function check_grab_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 rt = ilks[i].rate;
        uint256 gv0 = gem[i][msg.sender];
        uint256 gu0 = gem[i][u];
        uint256 s0 = sin[u];
        uint256 sm0 = sin[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 dai0 = dai[u];
        grab(i, u, msg.sender, u, dx, dy);
        assert(ilks[i].rate == rt);
        assert(debt == debt0);
        assert(dai[u] == dai0);
        assert(gem[i][u] == gu0);
        assert(sin[msg.sender] == sm0);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][msg.sender] + uint256(dx) == gv0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][msg.sender] == gv0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
            assert(sin[u] + rt * uint256(dy) == s0);
            assert(vice + rt * uint256(dy) == vice0);
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
            assert(sin[u] == s0 + rt * uint256(-dy));
            assert(vice == vice0 + rt * uint256(-dy));
        }
    }

    function check_grab_roles(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(dx > type(int256).min);
        require(dy > type(int256).min);
        uint256 gv0 = gem[i][u];
        uint256 gm0 = gem[i][msg.sender];
        uint256 s0 = sin[u];
        uint256 sm0 = sin[msg.sender];
        uint256 rt = ilks[i].rate;
        grab(i, msg.sender, u, msg.sender, dx, dy);
        assert(gem[i][msg.sender] == gm0);
        assert(sin[u] == s0);
        if (dx >= 0) {
            assert(gem[i][u] + uint256(dx) == gv0);
        } else {
            assert(gem[i][u] == gv0 + uint256(-dx));
        }
        if (dy >= 0) {
            assert(sin[msg.sender] + rt * uint256(dy) == sm0);
        } else {
            assert(sin[msg.sender] == sm0 + rt * uint256(-dy));
        }
    }

    function check_grab_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Settlement and unbacked debt ----------------

    function check_heal(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 sa = sin[a];
        uint256 da = dai[a];
        uint256 vc = vice;
        uint256 dt = debt;
        heal(x);
        assert(sin[msg.sender] + x == s0);
        assert(dai[msg.sender] + x == d0);
        assert(vice + x == vc);
        assert(debt + x == dt);
        assert(sin[a] == sa);
        assert(dai[a] == da);
    }

    function check_heal_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_suck(address a, address b, uint256 x, uint256 y) external {
        uint256 sa = sin[a];
        uint256 db = dai[b];
        uint256 da = dai[a];
        uint256 sb = sin[b];
        uint256 vc = vice;
        uint256 dt = debt;
        suck(a, b, x);
        assert(sin[a] == sa + x);
        assert(dai[b] == db + x);
        assert(vice == vc + x);
        assert(debt == dt + x);
        if (a != b) {
            assert(dai[a] == da);
            assert(sin[b] == sb);
        }
    }

    function check_suck_unauth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_overflow(address a, address b, uint256 x, uint256 y) external {
        require(debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 rt0 = ilks[i].rate;
        uint256 Art0 = ilks[i].Art;
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        fold(i, u, dx);
        assert(live == 1);
        assert(ilks[i].Art == Art0);
        assert(vice == vice0);
        if (dx >= 0) {
            assert(ilks[i].rate == rt0 + uint256(dx));
            assert(dai[u] == dai0 + Art0 * uint256(dx));
            assert(debt == debt0 + Art0 * uint256(dx));
        } else {
            assert(ilks[i].rate + uint256(-dx) == rt0);
            assert(dai[u] + Art0 * uint256(-dx) == dai0);
            assert(debt + Art0 * uint256(-dx) == debt0);
        }
    }

    function check_fold_unauth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live != 1);
        fold(i, u, dx);
        assert(false);
    }
}
