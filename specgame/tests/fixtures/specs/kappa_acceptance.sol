// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

/// kappa acceptance table (protocol.md section 11): which conjuncts the havoc
/// test must count as tautological (T) and which not (N).
contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_kappa(address a, address b, uint256 x, uint256 y) external {
        require(totalSupply <= cap);
        uint256 t0 = totalSupply;
        uint256 b0 = balanceOf[b];
        assert(x == x);
        assert(totalSupply <= cap);
        bool r = transfer(a, x);
        assert(totalSupply == t0);
        assert(balanceOf[b] == b0);
        assert(r);
        assert(!r || r);
    }
}
