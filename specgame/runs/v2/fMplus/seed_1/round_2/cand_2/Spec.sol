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

    // 3. Minting is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba + x);
        if (b != a) {
            assert(balanceOf[b] == bb);
        }
        assert(totalSupply <= cap);
    }

    // 4. Transfers are exact and conserve supply.
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        uint256 bs = balanceOf[msg.sender];
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        bool ok = transfer(a, x);
        assert(ok);
        assert(totalSupply == s0);
        if (a != msg.sender) {
            assert(balanceOf[msg.sender] == bs - x);
            assert(balanceOf[a] == ba + x);
        } else {
            assert(balanceOf[a] == ba);
        }
        if (b != a && b != msg.sender) {
            assert(balanceOf[b] == bb);
        }
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
