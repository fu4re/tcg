// SPDX-License-Identifier: MIT
// mutant: m04_mint_no_supply
// operator: remove-statement
// fault_class: accounting
// fault: `totalSupply += amount` removed from `mint`: balances grow, total supply does not.
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
