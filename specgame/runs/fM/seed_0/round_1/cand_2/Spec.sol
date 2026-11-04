// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Cap invariant: holds in every reachable state.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // Only the owner mints: a non-owner mint must revert (no effect).
    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // A mint past the cap must revert.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply + x > cap);
        mint(a, x);
        assert(false);
    }

    // After any successful mint the cap still holds.
    function check_mint_respects_cap(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply <= cap);
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // Mint exactness: supply and recipient balance.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba0 + x);
    }

    // Mint changes no other balance.
    function check_mint_other_balance_unchanged(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 bb0 = balanceOf[b];
        mint(a, x);
        assert(balanceOf[b] == bb0);
    }

    // Mint keeps owner and cap.
    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Transfer to another address: exact amounts, supply unchanged, returns true.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = totalSupply;
        uint256 bs0 = balanceOf[msg.sender];
        uint256 ba0 = balanceOf[a];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs0 - x);
        assert(balanceOf[a] == ba0 + x);
        assert(totalSupply == s0);
    }

    // Transfer to self leaves the balance unchanged.
    function check_transfer_self(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        uint256 s0 = totalSupply;
        uint256 b0 = balanceOf[a];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[a] == b0);
        assert(totalSupply == s0);
    }

    // Transfer changes no third balance.
    function check_transfer_other_unchanged(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        require(b != msg.sender);
        uint256 bb0 = balanceOf[b];
        transfer(a, x);
        assert(balanceOf[b] == bb0);
    }

    // No overdraft.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // Transfer keeps owner and cap.
    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
