// SPDX-License-Identifier: MIT
// mutant: m06_transfer_credits_sender
// operator: replace-variable
// fault_class: wrong-recipient
// fault: `transfer` credits `msg.sender` instead of `to`: the sender is debited and re-credited, `to` receives nothing.
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
        balanceOf[msg.sender] -= amount;
        balanceOf[msg.sender] += amount;
        return true;
    }
}
