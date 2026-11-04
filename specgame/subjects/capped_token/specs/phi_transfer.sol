// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// phi_transfer: transfer preserves total supply and moves exactly the
/// amount from the sender to the recipient (recipient != sender), leaves the
/// balance unchanged on a self-transfer, and touches no third address.
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    /// transfer never changes total supply (supply changes only through mint).
    function check_transfer_keeps_supply(address a, address b, uint256 x, uint256 y) external {
        uint256 s0 = totalSupply;
        transfer(a, x);
        assert(totalSupply == s0);
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
