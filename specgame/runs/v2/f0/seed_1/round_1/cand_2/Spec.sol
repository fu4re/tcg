// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Guarantee 2: the cap invariant holds in every reachable state.
    function check_supply_within_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // Guarantee 1: a non-owner mint must revert (no effect).
    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // Guarantee 2: a mint past the cap must revert.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply + x > cap);
        mint(a, x);
        assert(false);
    }

    // Guarantee 3: mint is exact and touches no other balance.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba0 + x);
        assert(balanceOf[b] == bb0);
        assert(totalSupply <= cap);
    }

    // Guarantee 4: transfer to a distinct address is exact.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(b != msg.sender);
        require(a != b);
        uint256 s0 = totalSupply;
        uint256 bs0 = balanceOf[msg.sender];
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs0 - x);
        assert(balanceOf[a] == ba0 + x);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == s0);
    }

    // Guarantee 4: self transfer leaves balances unchanged.
    function check_transfer_self(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 s0 = totalSupply;
        uint256 bs0 = balanceOf[msg.sender];
        uint256 bb0 = balanceOf[b];
        bool ok = transfer(msg.sender, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs0);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == s0);
    }

    // Guarantee 5: overdraft must revert.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // Guarantee 6: owner and cap are fixed by mint.
    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Guarantee 6: owner and cap are fixed by transfer.
    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
