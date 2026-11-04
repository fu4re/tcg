// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // 2. The cap holds in every reachable state.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // 1. A non-owner mint must have no effect (it must revert).
    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // 2. A mint past the cap must have no effect (it must revert).
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // 2. The cap still holds after any mint.
    function check_cap_after_mint(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // 3. A mint is exact: totalSupply and the recipient grow by x, other balances are unchanged.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        mint(a, x);
        assert(totalSupply - s0 == x);
        assert(balanceOf[a] - ba0 == x);
        assert(balanceOf[b] == bb0);
    }

    // 6. Mint never changes owner or cap.
    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // 4. A transfer to another address is exact.
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
        assert(bs0 - balanceOf[msg.sender] == x);
        assert(balanceOf[a] - ba0 == x);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == s0);
    }

    // 4. A transfer to oneself leaves the balance unchanged.
    function check_transfer_self(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        require(b != msg.sender);
        uint256 s0 = totalSupply;
        uint256 bs0 = balanceOf[msg.sender];
        uint256 bb0 = balanceOf[b];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs0);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == s0);
    }

    // 5. An overdraft must have no effect (it must revert).
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // 6. Transfer never changes owner or cap.
    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
