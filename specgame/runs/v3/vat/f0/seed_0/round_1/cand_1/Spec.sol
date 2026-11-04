// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

contract Spec is Vat {
    constructor() {}

    // ---------------- Authority ----------------

    function check_rely_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        rely(a);
        assert(wards[a] == 1);
        assert(wards[b] == w0);
    }

    function check_rely_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        rely(a);
        assert(false);
    }

    function check_rely_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        rely(a);
        assert(false);
    }

    function check_deny_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 w0 = wards[b];
        deny(a);
        assert(wards[a] == 0);
        assert(wards[b] == w0);
    }

    function check_deny_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        deny(a);
        assert(false);
    }

    function check_deny_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        deny(a);
        assert(false);
    }

    function check_init_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        uint256 art0 = ilks[i].Art;
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        init(i);
        assert(ilks[i].rate == 10 ** 27);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
    }

    function check_init_twice(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate != 0);
        init(i);
        assert(false);
    }

    function check_init_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        init(i);
        assert(false);
    }

    function check_cage_effect(address a, address b, uint256 x, uint256 y) external {
        cage();
        assert(live == 0);
    }

    function check_cage_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        cage();
        assert(false);
    }

    function check_cage_stays(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        cage();
        assert(live == 0);
    }

    // ---------------- Consent ----------------

    function check_hope_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(b != msg.sender);
        uint256 c0 = can[msg.sender][b];
        uint256 c1 = can[b][a];
        hope(a);
        assert(can[msg.sender][a] == 1);
        assert(can[msg.sender][b] == c0);
        assert(can[b][a] == c1);
    }

    function check_nope_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(b != msg.sender);
        uint256 c0 = can[msg.sender][b];
        uint256 c1 = can[b][a];
        nope(a);
        assert(can[msg.sender][a] == 0);
        assert(can[msg.sender][b] == c0);
        assert(can[b][a] == c1);
    }

    // ---------------- Parameters ----------------

    function check_file_line_effect(address a, address b, uint256 x, uint256 y) external {
        uint256 debt0 = debt;
        file("Line", x);
        assert(Line == x);
        assert(debt == debt0);
    }

    function check_file_line_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_line_needs_live(address a, address b, uint256 x, uint256 y) external {
        require(live == 0);
        file("Line", x);
        assert(false);
    }

    function check_file_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        require(i != "Line");
        file(i, uint256(dx));
        assert(false);
    }

    function check_file_spot_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 r0 = ilks[i].rate;
        uint256 art0 = ilks[i].Art;
        uint256 l0 = ilks[i].line;
        uint256 d0 = ilks[i].dust;
        uint256 g0 = Line;
        file(i, "spot", uint256(dx));
        assert(ilks[i].spot == uint256(dx));
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == art0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == d0);
        assert(Line == g0);
    }

    function check_file_line_ilk_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 r0 = ilks[i].rate;
        uint256 art0 = ilks[i].Art;
        uint256 s0 = ilks[i].spot;
        uint256 d0 = ilks[i].dust;
        uint256 g0 = Line;
        file(i, "line", uint256(dx));
        assert(ilks[i].line == uint256(dx));
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == s0);
        assert(ilks[i].dust == d0);
        assert(Line == g0);
    }

    function check_file_dust_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        uint256 r0 = ilks[i].rate;
        uint256 art0 = ilks[i].Art;
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 g0 = Line;
        file(i, "dust", uint256(dx));
        assert(ilks[i].dust == uint256(dx));
        assert(ilks[i].rate == r0);
        assert(ilks[i].Art == art0);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(Line == g0);
    }

    function check_file_ilk_unknown(bytes32 i, address u, int256 dx, int256 dy) external {
        file(i, "rate", uint256(dx));
        assert(false);
    }

    function check_file_ilk_unknown_art(bytes32 i, address u, int256 dx, int256 dy) external {
        file(i, "Art", uint256(dx));
        assert(false);
    }

    function check_file_ilk_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        file(i, "spot", uint256(dx));
        assert(false);
    }

    function check_file_ilk_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        file(i, "line", uint256(dx));
        assert(false);
    }

    // ---------------- Fungibility ----------------

    function check_slip_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(gem[i][u] < 2 ** 64);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        uint256 g0 = gem[i][u];
        slip(i, u, dx);
        assert(int256(gem[i][u]) == int256(g0) + dx);
    }

    function check_slip_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
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
        require(dx < 0 && dx > -2 ** 100);
        require(gem[i][u] < uint256(-dx));
        slip(i, u, dx);
        assert(false);
    }

    function check_flux_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(gem["GOLD"][a] < 2 ** 200);
        require(gem["GOLD"][b] < 2 ** 200);
        require(x < 2 ** 200);
        uint256 ga = gem["GOLD"][a];
        uint256 gb = gem["GOLD"][b];
        uint256 go = gem["SILVER"][a];
        uint256 gp = gem["SILVER"][b];
        uint256 d0 = dai[a];
        flux("GOLD", a, b, x);
        assert(gem["GOLD"][a] + x == ga);
        assert(gem["GOLD"][b] == gb + x);
        assert(gem["SILVER"][a] == go);
        assert(gem["SILVER"][b] == gp);
        assert(dai[a] == d0);
    }

    function check_flux_self(address a, address b, uint256 x, uint256 y) external {
        uint256 ga = gem["GOLD"][a];
        flux("GOLD", a, a, x);
        assert(gem["GOLD"][a] == ga);
    }

    function check_flux_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_flux_underflow(address a, address b, uint256 x, uint256 y) external {
        require(gem["GOLD"][a] < x);
        flux("GOLD", a, b, x);
        assert(false);
    }

    function check_move_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        require(dai[a] < 2 ** 200);
        require(dai[b] < 2 ** 200);
        require(x < 2 ** 200);
        uint256 da = dai[a];
        uint256 db = dai[b];
        uint256 debt0 = debt;
        uint256 vice0 = vice;
        uint256 sa = sin[a];
        move(a, b, x);
        assert(dai[a] + x == da);
        assert(dai[b] == db + x);
        assert(debt == debt0);
        assert(vice == vice0);
        assert(sin[a] == sa);
    }

    function check_move_self(address a, address b, uint256 x, uint256 y) external {
        uint256 da = dai[a];
        move(a, a, x);
        assert(dai[a] == da);
    }

    function check_move_needs_consent(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(can[a][msg.sender] == 0);
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
        require(dai[b] > type(uint256).max - x);
        move(a, b, x);
        assert(false);
    }

    // ---------------- Vault operations ----------------

    function check_frob_effect_self(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(gem[i][u] < 2 ** 64);
        require(dai[u] < 2 ** 200);
        require(debt < 2 ** 200);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 d0 = dai[u];
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        uint256 du0 = ilks[i].dust;
        frob(i, u, u, u, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) + dx);
        assert(int256(urns[i][u].art) == int256(art0) + dy);
        assert(int256(ilks[i].Art) == int256(tot0) + dy);
        assert(int256(gem[i][u]) == int256(g0) - dx);
        assert(int256(dai[u]) == int256(d0) + int256(r0) * dy);
        assert(int256(debt) == int256(debt0) + int256(r0) * dy);
        assert(ilks[i].rate == r0);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
        assert(ilks[i].dust == du0);
    }

    function check_frob_effect_w(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(gem[i][u] < 2 ** 64);
        require(gem[i][msg.sender] < 2 ** 64);
        require(dai[u] < 2 ** 200);
        require(dai[msg.sender] < 2 ** 200);
        require(debt < 2 ** 200);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 gm0 = gem[i][msg.sender];
        uint256 d0 = dai[u];
        uint256 dm0 = dai[msg.sender];
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        frob(i, u, u, msg.sender, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) + dx);
        assert(int256(urns[i][u].art) == int256(art0) + dy);
        assert(int256(ilks[i].Art) == int256(tot0) + dy);
        assert(int256(gem[i][u]) == int256(g0) - dx);
        assert(gem[i][msg.sender] == gm0);
        assert(dai[u] == d0);
        assert(int256(dai[msg.sender]) == int256(dm0) + int256(r0) * dy);
        assert(int256(debt) == int256(debt0) + int256(r0) * dy);
    }

    function check_frob_effect_v(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(gem[i][u] < 2 ** 64);
        require(gem[i][msg.sender] < 2 ** 64);
        require(dai[u] < 2 ** 200);
        require(dai[msg.sender] < 2 ** 200);
        require(debt < 2 ** 200);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 gm0 = gem[i][msg.sender];
        uint256 d0 = dai[u];
        uint256 dm0 = dai[msg.sender];
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        frob(i, u, msg.sender, u, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) + dx);
        assert(int256(urns[i][u].art) == int256(art0) + dy);
        assert(int256(ilks[i].Art) == int256(tot0) + dy);
        assert(gem[i][u] == g0);
        assert(int256(gem[i][msg.sender]) == int256(gm0) - dx);
        assert(int256(dai[u]) == int256(d0) + int256(r0) * dy);
        assert(dai[msg.sender] == dm0);
        assert(int256(debt) == int256(debt0) + int256(r0) * dy);
    }

    function check_frob_ceiling(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        frob(i, u, u, u, dx, dy);
        if (dy > 0) {
            assert(ilks[i].Art * ilks[i].rate <= ilks[i].line);
            assert(debt <= Line);
        }
    }

    function check_frob_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].spot < 2 ** 100);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        frob(i, u, u, u, dx, dy);
        if (dy > 0 || dx < 0) {
            assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        }
    }

    function check_frob_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate < 2 ** 100);
        require(urns[i][u].art < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        frob(i, u, u, u, dx, dy);
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    function check_frob_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_init(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate == 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_u(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dy > 0 || dx < 0);
        frob(i, u, u, u, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_v(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dx > 0);
        frob(i, u, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_frob_needs_consent_w(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        require(dx >= 0);
        require(dy < 0);
        frob(i, u, msg.sender, u, dx, dy);
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

    // ---------------- Fork ----------------

    function check_fork_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(urns[i][msg.sender].ink < 2 ** 64);
        require(urns[i][msg.sender].art < 2 ** 64);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 ink1 = urns[i][msg.sender].ink;
        uint256 art1 = urns[i][msg.sender].art;
        uint256 tot0 = ilks[i].Art;
        uint256 debt0 = debt;
        fork(i, u, msg.sender, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) - dx);
        assert(int256(urns[i][u].art) == int256(art0) - dy);
        assert(int256(urns[i][msg.sender].ink) == int256(ink1) + dx);
        assert(int256(urns[i][msg.sender].art) == int256(art1) + dy);
        assert(ilks[i].Art == tot0);
        assert(debt == debt0);
    }

    function check_fork_safe(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].spot < 2 ** 100);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(urns[i][msg.sender].ink < 2 ** 64);
        require(urns[i][msg.sender].art < 2 ** 64);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        fork(i, u, msg.sender, dx, dy);
        assert(urns[i][u].art * ilks[i].rate <= urns[i][u].ink * ilks[i].spot);
        assert(urns[i][msg.sender].art * ilks[i].rate <= urns[i][msg.sender].ink * ilks[i].spot);
    }

    function check_fork_dust(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(ilks[i].rate < 2 ** 100);
        require(urns[i][u].art < 2 ** 64);
        require(urns[i][msg.sender].art < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        fork(i, u, msg.sender, dx, dy);
        if (urns[i][u].art != 0) {
            assert(urns[i][u].art * ilks[i].rate >= ilks[i].dust);
        }
        if (urns[i][msg.sender].art != 0) {
            assert(urns[i][msg.sender].art * ilks[i].rate >= ilks[i].dust);
        }
    }

    function check_fork_needs_consent_src(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(can[u][msg.sender] == 0);
        fork(i, u, msg.sender, dx, dy);
        assert(false);
    }

    function check_fork_needs_consent_dst(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        require(can[b][msg.sender] == 0);
        fork("GOLD", msg.sender, b, int256(x), int256(y));
        assert(false);
    }

    // ---------------- Confiscation ----------------

    function check_grab_effect_w(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(gem[i][u] < 2 ** 64);
        require(sin[msg.sender] < 2 ** 200);
        require(vice < 2 ** 200);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        uint256 ink0 = urns[i][u].ink;
        uint256 art0 = urns[i][u].art;
        uint256 tot0 = ilks[i].Art;
        uint256 g0 = gem[i][u];
        uint256 s0 = sin[msg.sender];
        uint256 vice0 = vice;
        uint256 debt0 = debt;
        uint256 r0 = ilks[i].rate;
        grab(i, u, u, msg.sender, dx, dy);
        assert(int256(urns[i][u].ink) == int256(ink0) + dx);
        assert(int256(urns[i][u].art) == int256(art0) + dy);
        assert(int256(ilks[i].Art) == int256(tot0) + dy);
        assert(int256(gem[i][u]) == int256(g0) - dx);
        assert(int256(sin[msg.sender]) == int256(s0) - int256(r0) * dy);
        assert(int256(vice) == int256(vice0) - int256(r0) * dy);
        assert(debt == debt0);
    }

    function check_grab_effect_v(bytes32 i, address u, int256 dx, int256 dy) external {
        require(u != msg.sender);
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(urns[i][u].ink < 2 ** 64);
        require(urns[i][u].art < 2 ** 64);
        require(gem[i][msg.sender] < 2 ** 64);
        require(gem[i][u] < 2 ** 64);
        require(sin[u] < 2 ** 200);
        require(sin[msg.sender] < 2 ** 200);
        require(vice < 2 ** 200);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        require(dy > -2 ** 64 && dy < 2 ** 64);
        uint256 g0 = gem[i][msg.sender];
        uint256 g1 = gem[i][u];
        uint256 s0 = sin[u];
        uint256 s1 = sin[msg.sender];
        uint256 vice0 = vice;
        uint256 r0 = ilks[i].rate;
        grab(i, u, msg.sender, u, dx, dy);
        assert(int256(gem[i][msg.sender]) == int256(g0) - dx);
        assert(gem[i][u] == g1);
        assert(int256(sin[u]) == int256(s0) - int256(r0) * dy);
        assert(sin[msg.sender] == s1);
        assert(int256(vice) == int256(vice0) - int256(r0) * dy);
    }

    function check_grab_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    // ---------------- Settlement ----------------

    function check_heal_effect(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < 2 ** 200);
        require(dai[msg.sender] < 2 ** 200);
        require(vice < 2 ** 200);
        require(debt < 2 ** 200);
        require(x < 2 ** 200);
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

    function check_heal_sin_underflow(address a, address b, uint256 x, uint256 y) external {
        require(sin[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_heal_dai_underflow(address a, address b, uint256 x, uint256 y) external {
        require(dai[msg.sender] < x);
        heal(x);
        assert(false);
    }

    function check_suck_effect(address a, address b, uint256 x, uint256 y) external {
        require(sin[a] < 2 ** 200);
        require(dai[b] < 2 ** 200);
        require(vice < 2 ** 200);
        require(debt < 2 ** 200);
        require(x < 2 ** 200);
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

    function check_suck_needs_ward(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] == 0);
        suck(a, b, x);
        assert(false);
    }

    function check_suck_debt_overflow(address a, address b, uint256 x, uint256 y) external {
        require(debt > type(uint256).max - x);
        suck(a, b, x);
        assert(false);
    }

    // ---------------- Rates ----------------

    function check_fold_effect(bytes32 i, address u, int256 dx, int256 dy) external {
        require(ilks[i].rate < 2 ** 100);
        require(ilks[i].Art < 2 ** 64);
        require(dai[u] < 2 ** 200);
        require(debt < 2 ** 200);
        require(dx > -2 ** 64 && dx < 2 ** 64);
        uint256 r0 = ilks[i].rate;
        uint256 tot0 = ilks[i].Art;
        uint256 d0 = dai[u];
        uint256 debt0 = debt;
        uint256 s0 = ilks[i].spot;
        uint256 l0 = ilks[i].line;
        fold(i, u, dx);
        assert(int256(ilks[i].rate) == int256(r0) + dx);
        assert(ilks[i].Art == tot0);
        assert(int256(dai[u]) == int256(d0) + int256(tot0) * dx);
        assert(int256(debt) == int256(debt0) + int256(tot0) * dx);
        assert(ilks[i].spot == s0);
        assert(ilks[i].line == l0);
    }

    function check_fold_needs_live(bytes32 i, address u, int256 dx, int256 dy) external {
        require(live == 0);
        fold(i, u, dx);
        assert(false);
    }

    function check_fold_needs_ward(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] == 0);
        fold(i, u, dx);
        assert(false);
    }
}
