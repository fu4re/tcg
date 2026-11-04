// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// phi_full = phi_owner, phi_cap and phi_transfer: the set union of their
/// checks (check_transfer_keeps_supply, shared by phi_owner and phi_transfer,
/// appears once), each textually identical to its source spec.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    /// A non-owner mint must revert (must-revert pattern): if the call goes
    /// through, total supply must not have moved. Unreachable assert on b.
    function check_mint_nonowner_no_supply_change(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender != owner);
        uint256 s0 = totalSupply;
        mint(a, x);
        assert(totalSupply == s0);
    }

    /// The owner mint changes total supply by exactly the minted amount.
    function check_mint_owner_adds_amount(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);
        uint256 s0 = totalSupply;
        mint(a, x);
        assert(totalSupply == s0 + x);
    }

    /// transfer never changes total supply (supply changes only through mint).
    function check_transfer_keeps_supply(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        transfer(a, x);
        assert(totalSupply == s0);
    }

    /// totalSupply <= cap holds in every reachable state.
    function check_cap_invariant(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);
    }

    /// totalSupply <= cap holds after any successful mint.
    function check_cap_after_mint(address a, address b, uint256 x, uint256 y) external {
        mint(a, x);
        assert(totalSupply <= cap);
    }

    /// transfer to another address moves exactly x from the sender to the
    /// recipient and returns true.
    function check_transfer_moves_amount(address a, address b, uint256 x, uint256 y) external {
        require(a != msg.sender);
        uint256 from0 = balanceOf[msg.sender];
        uint256 to0 = balanceOf[a];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[msg.sender] == from0 - x);
        assert(balanceOf[a] == to0 + x);
    }

    /// A self-transfer leaves the balance unchanged and returns true.
    function check_transfer_self_unchanged(address a, address b, uint256 x, uint256 y) external {
        require(a == msg.sender);
        uint256 bal0 = balanceOf[a];
        bool ok = transfer(a, x);
        assert(ok);
        assert(balanceOf[a] == bal0);
    }

    /// transfer does not touch a third address (neither sender nor recipient).
    function check_transfer_others_untouched(address a, address b, uint256 x, uint256 y) external {
        require(b != msg.sender);
        require(b != a);
        uint256 other0 = balanceOf[b];
        transfer(a, x);
        assert(balanceOf[b] == other0);
    }
}
