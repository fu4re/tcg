// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Invariant: the cap is never exceeded in any reachable state.
    function check_supply_within_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // 1. Only the owner mints.
    function check_non_owner_mint_reverts(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // 2. A mint past the cap has no effect.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // The cap still holds after a successful mint.
    function check_mint_respects_cap(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // 3. Minting is exact.
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

    // 4. Transfer to another address is exact and conserves supply.
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

    // 4. Transfer to oneself leaves the balance unchanged.
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

    // 5. No overdraft.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // 6. Owner and cap are fixed.
    function check_mint_keeps_owner_and_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    function check_transfer_keeps_owner_and_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
