// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Invariant: the cap is never exceeded.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // Only the owner mints: a non-owner mint must revert.
    function check_non_owner_cannot_mint(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // A mint that would pass the cap must revert.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply <= cap);
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // Minting is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        require(b != a);
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba0 + x);
        assert(balanceOf[b] == bb0);
    }

    // Minting up to exactly the cap is allowed and lands on the cap.
    function check_mint_to_cap_exact(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        require(totalSupply <= cap);
        require(x == cap - totalSupply);
        mint(a, x);
        assert(totalSupply == cap);
    }

    // Mint keeps owner and cap.
    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Transfer to a third party is exact.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(b != a);
        require(b != msg.sender);
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

    // Self transfer leaves balances unchanged.
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
