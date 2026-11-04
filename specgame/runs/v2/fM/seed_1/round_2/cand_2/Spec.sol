// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // 1. Only the owner mints.
    function check_non_owner_cannot_mint(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    function check_non_owner_mint_zero_has_no_effect(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        require(x == 0);
        mint(a, x);
        assert(false);
    }

    // 2. Cap invariant.
    function check_supply_within_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    function check_mint_past_cap_has_no_effect(address a, address b, uint256 x, uint256 y) external {
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    function check_supply_within_cap_after_mint(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    function check_supply_within_cap_after_transfer(address a, address b, uint256 x, uint256 y) external {
        transfer(a, x);
        assert(totalSupply <= cap);
    }

    // 3. Minting is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(balanceOf[a] <= type(uint256).max - x);
        uint256 s0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(msg.sender == o0);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba0 + x);
        if (a != b) {
            assert(balanceOf[b] == bb0);
        }
        assert(owner == o0);
        assert(cap == c0);
    }

    function check_mint_balance_overflow_has_no_effect(address a, address b, uint256 x, uint256 y) external {
        require(balanceOf[a] > type(uint256).max - x);
        mint(a, x);
        assert(false);
    }

    // 4. Transfers are exact and conserve supply.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 s0 = balanceOf[msg.sender];
        uint256 r0 = balanceOf[a];
        uint256 c0 = balanceOf[b];
        uint256 t0 = totalSupply;
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == s0 - x);
        assert(balanceOf[a] == r0 + x);
        if (b != a && b != msg.sender) {
            assert(balanceOf[b] == c0);
        }
        assert(totalSupply == t0);
    }

    function check_transfer_to_self(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        uint256 s0 = balanceOf[msg.sender];
        uint256 c0 = balanceOf[b];
        uint256 t0 = totalSupply;
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == s0);
        if (b != msg.sender) {
            assert(balanceOf[b] == c0);
        }
        assert(totalSupply == t0);
    }

    function check_transfer_balance_overflow_has_no_effect(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(balanceOf[a] > type(uint256).max - x);
        transfer(a, x);
        assert(false);
    }

    // 5. No overdraft.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // 6. Owner and cap are fixed.
    function check_transfer_keeps_owner_and_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    function check_mint_keeps_owner_and_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
