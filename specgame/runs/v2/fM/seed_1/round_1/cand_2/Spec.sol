// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    function check_cap_not_exceeded(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply <= cap);
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    function check_cap_respected_after_mint(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply <= type(uint256).max - x);
        require(balanceOf[a] <= type(uint256).max - x);
        uint256 s0 = totalSupply;
        uint256 ba = balanceOf[a];
        uint256 bb = balanceOf[b];
        mint(a, x);
        assert(totalSupply == s0 + x);
        assert(balanceOf[a] == ba + x);
        if (a != b) {
            assert(balanceOf[b] == bb);
        }
    }

    function check_mint_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(balanceOf[msg.sender] >= x);
        require(a == msg.sender || balanceOf[a] <= type(uint256).max - x);
        uint256 s0 = totalSupply;
        uint256 sb = balanceOf[msg.sender];
        uint256 ab = balanceOf[a];
        uint256 bb = balanceOf[b];
        bool ok = transfer(a, x);
        assert(ok);
        assert(totalSupply == s0);
        if (a != msg.sender) {
            assert(balanceOf[msg.sender] == sb - x);
            assert(balanceOf[a] == ab + x);
        } else {
            assert(balanceOf[a] == ab);
        }
        if (b != a && b != msg.sender) {
            assert(balanceOf[b] == bb);
        }
    }

    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    function check_transfer_keeps_owner_cap(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
