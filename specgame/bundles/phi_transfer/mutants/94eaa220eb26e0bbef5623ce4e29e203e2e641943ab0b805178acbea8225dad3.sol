// SPDX-License-Identifier: MIT
// mutant: m05_transfer_no_debit
// operator: remove-statement
// fault_class: accounting
// fault: the debit `balanceOf[msg.sender] -= amount` removed from `transfer`: the recipient is credited, the sender keeps the amount (the balance check stays).
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
        require(totalSupply + amount <= cap, "cap exceeded");
        totalSupply += amount;
        balanceOf[to] += amount;
    }

    /// Moves `amount` from the caller to `to`; reverts on insufficient balance.
    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[to] += amount;
        return true;
    }
}
