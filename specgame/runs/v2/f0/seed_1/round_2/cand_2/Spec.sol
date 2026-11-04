// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    // Guarantee 1: a non-owner mint has no effect (it must revert).
    function check_only_owner_mints(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        mint(a, x);
        assert(false);
    }

    // Guarantee 2: the cap holds in every reachable state.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    // Guarantee 2: the cap still holds after a successful mint.
    function check_cap_after_mint(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    // Guarantee 2: a mint past the cap has no effect (it must revert).
    function check_mint_over_cap_reverts(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply <= cap);
        require(x > cap - totalSupply);
        mint(a, x);
        assert(false);
    }

    // Guarantee 3: minting is exact.
    function check_mint_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        uint256 ts0 = totalSupply;
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        mint(a, x);
        assert(totalSupply == ts0 + x);
        assert(balanceOf[a] == ba0 + x);
        assert(balanceOf[b] == bb0);
    }

    // Guarantee 4: transfer is exact and conserves supply (distinct parties).
    function check_transfer_exact(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        require(b != msg.sender);
        require(b != a);
        uint256 ts0 = totalSupply;
        uint256 bs0 = balanceOf[msg.sender];
        uint256 ba0 = balanceOf[a];
        uint256 bb0 = balanceOf[b];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs0 - x);
        assert(balanceOf[a] == ba0 + x);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == ts0);
    }

    // Guarantee 4: a self-transfer leaves the balance unchanged.
    function check_transfer_self(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        uint256 ts0 = totalSupply;
        uint256 bs0 = balanceOf[msg.sender];
        uint256 bb0 = balanceOf[b];
        bool ok = transfer(msg.sender, x);
        assert(ok);
        assert(balanceOf[msg.sender] == bs0);
        assert(balanceOf[b] == bb0);
        assert(totalSupply == ts0);
    }

    // Guarantee 5: no overdraft.
    function check_no_overdraft(address a, address b, uint256 x, uint256 y) external {
        require(x > balanceOf[msg.sender]);
        transfer(a, x);
        assert(false);
    }

    // Guarantee 6: owner and cap are fixed by mint.
    function check_owner_cap_fixed_mint(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        mint(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }

    // Guarantee 6: owner and cap are fixed by transfer.
    function check_owner_cap_fixed_transfer(address a, address b, uint256 x, uint256 y) external {
        address o0 = owner;
        uint256 c0 = cap;
        transfer(a, x);
        assert(owner == o0);
        assert(cap == c0);
    }
}
