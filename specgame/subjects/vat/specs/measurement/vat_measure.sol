// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// Protocol v3 measurement specs for Vat (not a ladder spec): one check of each
/// kind, to measure Check v2 on the subject.
contract Spec is Vat {
    constructor() {}

    /// Linear per-transition law: when u frobs its own urn (u is also the
    /// collateral source and the dai destination), the collateral it locks
    /// leaves its gem balance one for one, and the urn's normalised debt change
    /// equals the ilk's total normalised debt change.
    function check_frob_conserves_collateral(bytes32 i, address u, int256 dx, int256 dy) external {
        require(msg.sender == u);
        uint256 ink0 = urns[i][u].ink;
        uint256 gem0 = gem[i][u];
        uint256 art0 = urns[i][u].art;
        uint256 total0 = ilks[i].Art;
        frob(i, u, u, u, dx, dy);
        assert(urns[i][u].ink + gem[i][u] == ink0 + gem0);
        assert(ilks[i].Art + art0 == total0 + urns[i][u].art);
    }

    /// Must-revert auth law: an address that is not a ward cannot create
    /// unbacked dai.
    function check_suck_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    /// Global invariant over a small key space: the dai of any two distinct
    /// addresses together never exceeds the total issued.
    function check_two_dai_balances_within_debt(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        assert(dai[a] + dai[b] <= debt);
    }
}
