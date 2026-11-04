// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// phi_owner: total supply changes only through mint by the owner.
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
}
