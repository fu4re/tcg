// SPDX-License-Identifier: MIT
// mutant: m08_mint_always_reverts
// operator: insert-revert
// fault_class: liveness
// fault: `revert("mint disabled")` inserted as the first statement of `mint`: every mint reverts.
// expected_unkillable: true; proper by Def. 4.2 (the observation sees the outcome class of a mint), but every successful execution of this mutant is an execution of b with the mint transactions removed, and a revert inside a check is pre_unmet (protocol.md, Sharpened definitions, item 3). So a witness against this mutant would be a witness against b on the same sigma without its mints: no spec that holds on b can kill it (note, open question 7)
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
        revert("mint disabled");
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
