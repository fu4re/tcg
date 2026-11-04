// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------------------------------------------------------- Authority

    function check_rely_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        rely(a);
        assert(false);
    }

    function check_rely_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
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

    function check_deny_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        deny(a);
        assert(false);
    }

    function check_deny_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
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

    // ---------------------------------------------------------------- Consent

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

    // ---------------------------------------------------------------- Init

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 Art0 = ilks[i].Art;
        uint256 spot0 = ilks[i].spot;
        uint256 line0 = ilks[i].line;
        uint256 dust0 = ilks[i].dust;
        init(i);
        assert(ilks[i].rate == 10**27);
        assert(ilks[i].Art == Art0);
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
        require(wards[msg.sender] == 0);
        init(i);
        assert(false);
    }

    // ---------------------------------------------------------------- Parameters

    function check_file_line_effect(address a, address b, uint256 x, uint256 y) external {
        file("Line", x);
        assert(Line == x);
        assert(live == 1);
    }

    function check_file_line_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_line_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_unrecognised(address a, address b, uint256 x, uint256 y) external {
        require(bytes32(x) != "Line");
        file(bytes32(x), y);
        assert(false);
    }

    function check_file_spot_effect(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        uint256 Art0 = ilks[k].Art;
        uint256 rate0 = ilks[k].rate;
        uint256 line0 = ilks[k].line;
        uint256 dust0 = ilks[k].dust;
        uint256 Line0 = Line;
        file(k, "spot", x);
        assert(ilks[k].spot == x);
        assert(ilks[k].Art == Art0);
        assert(ilks[k].rate == rate0);
        assert(ilks[k].line == line0);
        assert(ilks[k].dust == dust0);
        assert(Line == Line0);
    }

    function check_file_line_ilk_effect(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        uint256 Art0 = ilks[k].Art;
        uint256 rate0 = ilks[k].rate;
        uint256 spot0 = ilks[k].spot;
        uint256 dust0 = ilks[k].dust;
        uint256 Line0 = Line;
        file(k, "line", x);
        assert(ilks[k].line == x);
        assert(ilks[k].Art == Art0);
        assert(ilks[k].rate == rate0);
        assert(ilks[k].spot == spot0);
        assert(ilks[k].dust == dust0);
        assert(Line == Line0);
    }

    function check_file_dust_effect(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        uint256 Art0 = ilks[k].Art;
        uint256 rate0 = ilks[k].rate;
        uint256 spot0 = ilks[k].spot;
        uint256 line0 = ilks[k].line;
        uint256 Line0 = Line;
        file(k, "dust", x);
        assert(ilks[k].dust == x);
        assert(ilks[k].Art == Art0);
        assert(ilks[k].rate == rate0);
        assert(ilks[k].spot == spot0);
        assert(ilks[k].line == line0);
        assert(Line == Line0);
    }

    function check_file_ilk_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        file(bytes32(y), "spot", x);
        assert(false);
    }

    function check_file_ilk_not_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file(bytes32(y), "line", x);
        assert(false);
    }

    function check_file_ilk_unrecognised(address a, address b, uint256 x, uint256 y) external {
        require(bytes32(x) != "spot");
        require(bytes32(x) != "line");
        require(bytes32(x) != "dust");
        file(bytes32(y), bytes32(x), x);
        assert(false);
    }

    // ---------------------------------------------------------------- Shutdown

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_cage_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        cage();
        assert(false);
    }

    function check_live_stays_down(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        suck(a, b, x);
        assert(live == 0);
    }

    // ---------------------------------------------------------------- slip

    function check_slip_credit(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(gem[i][u] >= g0);
        assert(gem[i][u] - g0 == uint256(dx));
    }

    function check_slip_debit(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx < 0 && dx > type(int256).min);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(g0 >= gem[i][u]);
        assert(g0 - gem[i][u] == uint256(-dx));
    }

    function check_slip_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
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
        require(dx < 0 && dx > type(int256).min);
        require(gem[i][u] < uint256(-dx));
        slip(i, u, dx);
        assert(false);
    }

    // ---------------------------------------------------------------- flux

    function check_flux_moves(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 ga0 = gem[k][a];
        uint256 gb0 = gem[k][b];
        flux(k, a, b, x);
        assert(ga0 >= gem[k][a]);
        assert(ga0 - gem[k][a] == x);
        assert(gem[k][b] >= gb0);
        assert(gem[k][b] - gb0 == x);
    }

    function check_flux_other_ilk(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        require(k != "GOLD");
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 ga0 = gem["GOLD"][a];
        uint256 gb0 = gem["GOLD"][b];
        flux(k, a, b, x);
        assert(gem["GOLD"][a] == ga0);
        assert(gem["GOLD"][b] == gb0);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 ga0 = gem[k][a];
        flux(k, a, a, x);
        assert(gem[k][a] == ga0);
    }

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        flux(bytes32(y), a, b, x);
        assert(false);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(gem[k][a] < x);
        flux(k, a, b, x);
        assert(false);
    }

    function check_flux_overflow(address a, address b, uint256 x, uint256 y) external {
        bytes32 k = bytes32(y);
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(gem[k][a] >= x);
        require(x > 0 && gem[k][b] > type(uint256).max - x);
        flux(k, a, b, x);
        assert(false);
    }

    // ---------------------------------------------------------------- move

    function check_move_moves(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 da0 = dai[a];
        uint256 db0 = dai[b];
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        move(a, b, x);
        assert(da0 >= dai[a]);
        assert(da0 - dai[a] == x);
        assert(dai[b] >= db0);
        assert(dai[b] - db0 == x);
        assert(debt == debt0);
        assert(vice == vice0);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender || can[a][msg.sender] == 1);
        uint256 da0 = dai[a];
        move(a, a, x);
        assert(dai[a] == da0);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        move(a, b, x);
        assert(false);
    }

    function check_move_underflow(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(dai[a] < x);
        move(a, b, x);
        assert(false);
    }

    function check_move_overflow(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(a == msg.sender || can[a][msg.sender] == 1);
        require(dai[a] >= x);
        require(x > 0 && dai[b] > type(uint256).max - x);
        move(a, b, x);
        assert(false);
    }

    // ---------------------------------------------------------------- frob

    function check_frob_collateral_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        require(u == msg.sender || can[u][msg.sender] == 1);
        uint256 ink0 = urns[i][u].ink;
        uint256 gem0 = gem[i][u];
        frob(i, u, u, u, dx, dy);
        if (dx >= 0) {
            assert(urns[i][u].ink == ink0 + uint256(dx));
            assert(gem[i][u] + uint256(dx) == gem0);
        } else {
            assert(urns[i][u].ink + uint256(-dx) == ink0);
            assert(gem[i][u] == gem0 + uint256(-dx));
        }
    }

    function check_frob_debt_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > type(int256).min);
        require(u == msg.sender || can[u][msg.sender] == 1);
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 rate0 = ilks[i].rate;
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        frob(i, u, u, u, dx, dy);
        if (dy >= 0) {
            assert(urns[i][u].art == art0 + uint256(dy));
            assert(ilks[i].Art == Art0 + uint256(dy));
            assert(dai[u] == dai0 + uint256(dy) * rate0);
            assert(debt == debt0 + uint256(dy) * rate0);
        } else {
            assert(urns[i][u].art + uint256(-dy) == art0);
            assert(ilks[i].Art + uint256(-dy) == Art0);
            assert(dai[u] + uint256(-dy) * rate0 == dai0);
            assert(debt + uint256(-dy) * rate0 == debt0);
        }
    }

    function check_frob_untouched(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u == msg.sender || can[u][msg.sender] == 1);
        uint256 rate0 = ilks[i].rate;
        uint256 spot0 = ilks[i].spot;
        uint256 line0 = ilks[i].line;
        uint256 dust0 = ilks[i].dust;
        uint256 Line0 = Line;
        uint256 vice0 = vice;
        uint256 sin0 = sin[u];
        frob(i, u, u, u, dx, dy);
        assert(ilks[i].rate == rate0);
        assert(ilks[i].spot == spot0);
        assert(ilks[i].line == line0);
        assert(ilks[i].dust == dust0);
        assert(Line == Line0);
        assert(vice == vice0);
        assert(sin[u] == sin0);
        assert(live == 1);
    }

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

    function check_frob_ilk_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].line == 0);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_global_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(debt >= Line);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_unsafe_draw(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].spot == 0);
        require(dy > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_unsafe_withdraw(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].spot == 0);
        require(dx < 0);
        require(dy >= 0);
        require(urns[i][u].art > 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dx != 0 || dy != 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_u(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        require(x > 0 && x <= uint256(type(int256).max));
        frob(bytes32(y), a, msg.sender, msg.sender, 0, int256(x));
        assert(false);
    }

    function check_frob_needs_consent_v(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        require(x > 0 && x <= uint256(type(int256).max));
        frob(bytes32(y), msg.sender, a, msg.sender, int256(x), 0);
        assert(false);
    }

    function check_frob_needs_consent_w(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        require(x > 0 && x <= uint256(type(int256).max));
        frob(bytes32(y), msg.sender, msg.sender, a, 0, -int256(x));
        assert(false);
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(urns[i][u].art == 0);
        require(dy > 0 && dy < 10**20);
        require(ilks[i].rate == 10**27);
        require(uint256(dy) * 10**27 < ilks[i].dust);
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

    function check_frob_total_art_overflow(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dy > 0);
        require(ilks[i].Art > type(uint256).max - uint256(dy));
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------------------------------------------------------- fork

    function check_fork_moves_forward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dy >= 0);
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 sink0 = urns[i][u].ink;
        uint256 sart0 = urns[i][u].art;
        uint256 dink0 = urns[i][msg.sender].ink;
        uint256 dart0 = urns[i][msg.sender].art;
        uint256 Art0 = ilks[i].Art;
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].ink + uint256(dx) == sink0);
        assert(urns[i][u].art + uint256(dy) == sart0);
        assert(urns[i][msg.sender].ink == dink0 + uint256(dx));
        assert(urns[i][msg.sender].art == dart0 + uint256(dy));
        assert(ilks[i].Art == Art0);
    }

    function check_fork_moves_backward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 sink0 = urns[i][u].ink;
        uint256 sart0 = urns[i][u].art;
        uint256 dink0 = urns[i][msg.sender].ink;
        uint256 dart0 = urns[i][msg.sender].art;
        uint256 Art0 = ilks[i].Art;
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].ink == sink0 + uint256(-dx));
        assert(urns[i][u].art == sart0 + uint256(-dy));
        assert(urns[i][msg.sender].ink + uint256(-dx) == dink0);
        assert(urns[i][msg.sender].art + uint256(-dy) == dart0);
        assert(ilks[i].Art == Art0);
    }

    function check_fork_untouched(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        uint256 rate0 = ilks[i].rate;
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        uint256 gem0 = gem[i][u];
        uint256 dai0 = dai[u];
        fork(i, u, msg.sender, dx, dy);
        assert(ilks[i].rate == rate0);
        assert(debt == debt0);
        assert(vice == vice0);
        assert(gem[i][u] == gem0);
        assert(dai[u] == dai0);
    }

    function check_fork_src_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_dst_consent(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        fork(i, msg.sender, u, dx, dy);
        assert(false);
    }

    function check_fork_unsafe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 1);
        require(ilks[i].spot == 0);
        require(ilks[i].rate > 0);
        require(dy != 0);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    // ---------------------------------------------------------------- grab

    function check_grab_nonpositive(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx <= 0 && dy <= 0);
        require(dx > type(int256).min && dy > type(int256).min);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 rate0 = ilks[i].rate;
        uint256 gem0 = gem[i][msg.sender];
        uint256 sin0 = sin[u];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 dai0 = dai[u];
        grab(i, u, msg.sender, u, dx, dy);
        assert(urns[i][u].ink == ink0 + uint256(-dx));
        assert(urns[i][u].art == art0 + uint256(-dy));
        assert(ilks[i].Art == Art0 + uint256(-dy));
        assert(gem[i][msg.sender] == gem0 + uint256(-dx));
        assert(sin[u] == sin0 + uint256(-dy) * rate0);
        assert(vice == vice0 + uint256(-dy) * rate0);
        assert(debt == debt0);
        assert(dai[u] == dai0);
        assert(ilks[i].rate == rate0);
    }

    function check_grab_nonnegative(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx >= 0 && dy >= 0);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 Art0 = ilks[i].Art;
        uint256 rate0 = ilks[i].rate;
        uint256 gem0 = gem[i][msg.sender];
        uint256 sin0 = sin[u];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        grab(i, u, msg.sender, u, dx, dy);
        assert(urns[i][u].ink == ink0 + uint256(dx));
        assert(urns[i][u].art == art0 + uint256(dy));
        assert(ilks[i].Art == Art0 + uint256(dy));
        assert(gem[i][msg.sender] + uint256(dx) == gem0);
        assert(sin[u] + uint256(dy) * rate0 == sin0);
        assert(vice + uint256(dy) * rate0 == vice0);
        assert(debt == debt0);
    }

    function check_grab_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------------------------------------------------------- heal

    function check_heal_effects(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = sin[msg.sender];
        uint256 d0 = dai[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 sa0 = sin[a];
        uint256 da0 = dai[a];
        heal(x);
        assert(s0 >= sin[msg.sender]);
        assert(s0 - sin[msg.sender] == x);
        assert(d0 >= dai[msg.sender]);
        assert(d0 - dai[msg.sender] == x);
        assert(vice0 >= vice);
        assert(vice0 - vice == x);
        assert(debt0 >= debt);
        assert(debt0 - debt == x);
        assert(sin[a] == sa0);
        assert(dai[a] == da0);
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

    // ---------------------------------------------------------------- suck

    function check_suck_effects(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = sin[a];
        uint256 d0 = dai[b];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        suck(a, b, x);
        assert(sin[a] >= s0);
        assert(sin[a] - s0 == x);
        assert(dai[b] >= d0);
        assert(dai[b] - d0 == x);
        assert(vice >= vice0);
        assert(vice - vice0 == x);
        assert(debt >= debt0);
        assert(debt - debt0 == x);
    }

    function check_suck_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_sin_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > 0 && sin[a] > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_dai_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > 0 && dai[b] > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_debt_overflow(address a, address b, uint256 x, uint256 y) external {
        require(x > 0 && debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------------------------------------------------------------- fold

    function check_fold_effects(bytes32 i, address u, int256 dx, int256 dy) external {
        require(dx > type(int256).min);
        uint256 rate0 = ilks[i].rate;
        uint256 Art0 = ilks[i].Art;
        uint256 dai0 = dai[u];
        uint256 debt0 = debt;
        fold(i, u, dx);
        assert(ilks[i].Art == Art0);
        if (dx >= 0) {
            assert(ilks[i].rate == rate0 + uint256(dx));
            assert(dai[u] >= dai0);
            assert(dai[u] - dai0 == Art0 * uint256(dx));
            assert(debt >= debt0);
            assert(debt - debt0 == Art0 * uint256(dx));
        } else {
            assert(ilks[i].rate + uint256(-dx) == rate0);
            assert(dai0 >= dai[u]);
            assert(dai0 - dai[u] == Art0 * uint256(-dx));
            assert(debt0 >= debt);
            assert(debt0 - debt == Art0 * uint256(-dx));
        }
    }

    function check_fold_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_not_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }
}
