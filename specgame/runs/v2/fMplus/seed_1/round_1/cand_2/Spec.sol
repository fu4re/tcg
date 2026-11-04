// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // 2. The cap invariant holds in every reachable state.
    function check_supply_within_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // 1. A non-owner mint must revert (have no effect).
    function check_mint_only_owner(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // 2. A mint that would pass the cap must revert.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // 2. After any successful mint the cap still holds.
    function check_mint_keeps_cap(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // 3. Mint is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 s0 = totalSupply;
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        require(x <= type(uint256).max - s0);
        require(x <= type(uint256).max - ba);
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba + x);
        assert(balanceOf[b] == bb);
    }

    // 4. Transfer to another address is exact and conserves supply.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(b != a);
        require(b != msg.sender);
        uint256 s0 = totalSupply;
        uint256 bs = balanceOf[msg.sender];
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        require(bs >= x);
        require(x <= type(uint256).max - ba);
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs - x);
        assert(balanceOf[a] == ba + x);
        assert(balanceOf[b] == bb);
        assert(totalSupply == s0);
    }

    // 4. Transfer to oneself leaves the balance unchanged.
    function check_transfer_self(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 bs = balanceOf[msg.sender];
        uint256 bb = balanceOf[b];
        require(b != msg.sender);
        bool ok = transfer(msg.sender, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs);
        assert(balanceOf[b] == bb);
        assert(totalSupply == s0);
    }

    // 5. No overdraft.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // 6. Owner and cap are fixed by mint.
    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // 6. Owner and cap are fixed by transfer.
    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
