// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // 1. Only the owner mints.
    function check_non_owner_mint_reverts(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // 2. Cap invariant.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // 2. A mint past the cap has no effect.
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // 2. Cap still holds after a mint.
    function check_mint_respects_cap(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // 2. Minting exactly up to the cap is exact when it goes through.
    function check_mint_to_cap(address a, address b, uint256 x, uint256 y) external {
        require(x == cap - totalSupply);
        uint256 ba0 = balanceOf[a];
        mint(a, x);
        assert(totalSupply == cap);
        assert(balanceOf[a] >= ba0);
        assert(balanceOf[a] - ba0 == x);
    }

    // 3. Minting is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(b != a);
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(totalSupply >= s0);
        assert(totalSupply - s0 == x);
        assert(balanceOf[a] >= ba0);
        assert(balanceOf[a] - ba0 == x);
        assert(balanceOf[b] == bb0);
        assert(owner == o0);
        assert(cap == c0);
    }

    // 4. Transfer to another address is exact.
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
        assert(balanceOf[msg.sender] <= bs0);
        assert(bs0 - balanceOf[msg.sender] == x);
        assert(balanceOf[a] >= ba0);
        assert(balanceOf[a] - ba0 == x);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == s0);
    }

    // 4. Self transfer leaves balances unchanged.
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

    // 6. Owner and cap fixed under transfer.
    function check_owner_cap_fixed_transfer(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
