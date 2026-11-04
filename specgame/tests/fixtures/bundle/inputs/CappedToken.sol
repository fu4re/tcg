// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

/// Placeholder capped token for the WP0 smoke check (`make check`).
/// WP1 owns the real contract; this version is only minimal and correct.
/// `owner` and `cap` are storage variables, not immutables, so the runtime
/// bytecode does not depend on constructor arguments.
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

    function mint(address to, uint256 amount) public onlyOwner {
        require(totalSupply + amount <= cap, "cap exceeded");
        totalSupply += amount;
        balanceOf[to] += amount;
    }

    function transfer(address to, uint256 amount) public returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        return true;
    }
}
