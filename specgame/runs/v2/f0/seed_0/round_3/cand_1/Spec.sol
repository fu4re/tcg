// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Cap invariant: totalSupply never exceeds cap.
    function check_supply_within_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // After any successful mint the cap still holds.
    function check_mint_respects_cap(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // A mint that would pass the cap has no effect (must revert).
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // Non-owner cannot mint.
    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // Mint is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        mint(a, x);
        assert(msg.sender == owner);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba0 + x);
        if (b != a) {
            assert(balanceOf[b] == bb0);
        }
    }

    // Transfer returns true and conserves supply.
    function check_transfer_ok_and_supply(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        bool ok = transfer(a, x);
        assert(ok);
        assert(totalSupply == s0);
    }

    // Transfer to another address moves exactly x.
    function check_transfer_moves_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 bs0 = balanceOf[msg.sender];
        uint256 ba0 = balanceOf[a];
        transfer(a, x);
        assert(balanceOf[msg.sender] == bs0 - x);
        assert(balanceOf[a] == ba0 + x);
    }

    // Transfer to self leaves balance unchanged.
    function check_transfer_self(address a, address b, uint256 x, uint256 y) external {
        uint256 bs0 = balanceOf[msg.sender];
        transfer(msg.sender, x);
        assert(balanceOf[msg.sender] == bs0);
    }

    // Transfer changes no third balance.
    function check_transfer_others_unchanged(address a, address b, uint256 x, uint256 y) external {
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

    // Owner and cap fixed by mint.
    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Owner and cap fixed by transfer.
    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
