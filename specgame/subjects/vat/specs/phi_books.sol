// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_books: global books-balance consequences over two keys (intent 12); expected Unknown under CHC.
contract Spec is Vat {
    constructor() {}

    /// Global (books balance, two keys): the stablecoin of two distinct addresses together is at most the total issued.
    function check_two_dai_within_debt(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        assert(dai[a] + dai[b] <= debt);
    }

    /// Global (books balance, two keys): the sin of two distinct addresses together is at most the total unbacked debt.
    function check_two_sin_within_vice(address a, address b, uint256 x, uint256 y) external {
        require(a != b);
        assert(sin[a] + sin[b] <= vice);
    }

    /// Global (books balance): the total unbacked debt is at most the total issued.
    function check_vice_within_debt(address a, address b, uint256 x, uint256 y) external {
        assert(vice <= debt);
    }
}
