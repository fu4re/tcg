// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

/// Subject b of the Specification Games prototype (WP1).
/// Intent: intent.md. Mutation class: mutants/ (each mutant is this file with
/// one named fault). Artifact rules A1-A5 (specs/SPEC_FORMAT.md section 5):
/// every function public, no assert, no custom errors, no immutables, so the
/// runtime bytecode (the artifact id) does not depend on constructor arguments.
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
        balanceOf[to] += amount;
        return true;
    }
}
