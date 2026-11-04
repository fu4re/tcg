// SPDX-License-Identifier: MIT
// mutant: m03_mint_cap_off_by_one
// operator: shift-bound-by-one
// fault_class: off-by-one
// fault: cap bound shifted by one (`<= cap + 1`): the owner can mint exactly one unit past `cap`. Side effect of the `+1` operator: with cap = 2^256-1, `cap + 1` overflows and every mint ends in Panic(0x11). The stricter shift (`< cap`) was not used: it only adds reverts, so no spec in this format can kill it (same argument as m08).
pragma solidity 0.8.35;

/// Mutant of contracts/CappedToken.sol with one named fault (header above).
contract CappedToken {
    address public owner;
    uint256 public cap;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;

    modifier onlyOwner() {
        require(msg.sender == owner, "not owner");
        _;
    }

    constructor(uint256 cap_) {
        owner = msg.sender;
        cap = cap_;
    }

    /// Only the owner mints, and never past the cap.
    function mint(address to, uint256 amount) public onlyOwner {
        require(totalSupply + amount <= cap + 1, "cap exceeded");
        totalSupply += amount;
        balanceOf[to] += amount;
    }

    /// Moves `amount` from the caller to `to`; reverts on insufficient balance.
    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
