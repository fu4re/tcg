// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Guarantee 1: a non-owner mint always reverts (has no effect).
    function check_mint_only_owner(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // Guarantee 2: the cap invariant holds in every reachable state.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // Guarantee 2: a mint that would pass the cap reverts.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // Guarantee 2: after a successful mint the supply is still within the cap.
    function check_mint_respects_cap(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // Guarantee 3: minting is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(msg.sender == o0);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba0 + x);
        assert(balanceOf[b] == bb0);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Guarantee 4: transfer to another address is exact.
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

    // Guarantee 4: transfer to oneself leaves balances unchanged.
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

    // Guarantee 5: no overdraft.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // Guarantee 6: transfer does not change owner or cap.
    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
