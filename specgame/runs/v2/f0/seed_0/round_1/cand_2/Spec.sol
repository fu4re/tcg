// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Guarantee 2: the cap holds in every reachable state.
    function check_supply_within_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // Guarantee 1: a non-owner mint has no effect (it must revert).
    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // Guarantee 2: a mint past the cap has no effect (it must revert).
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // Guarantees 2, 3, 6: a successful mint is exact, respects the cap, and keeps owner and cap.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba + x);
        if (b != a) {
            assert(balanceOf[b] == bb);
        }
        assert(totalSupply <= cap);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Minting exactly up to the cap is allowed.
    function check_mint_to_cap_exact(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        require(x == cap - totalSupply);
        mint(a, x);
        assert(totalSupply == cap);
    }

    // Guarantees 4, 6: transfers are exact and conserve supply.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 bs = balanceOf[msg.sender];
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        address o0 = owner;
        uint256 c0 = cap;
        bool ok = transfer(a, x);
        assert(ok);
        if (a != msg.sender) {
            assert(balanceOf[msg.sender] == bs - x);
            assert(balanceOf[a] == ba + x);
        } else {
            assert(balanceOf[a] == ba);
        }
        if (b != a && b != msg.sender) {
            assert(balanceOf[b] == bb);
        }
        assert(totalSupply == s0);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Guarantee 5: an overdraft has no effect (it must revert).
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }
}
