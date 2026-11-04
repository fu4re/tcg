// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./Vat.sol";

/// phi_auth: every authorised operation reverts for a non-ward (intent 1).
contract Spec is Vat {
    constructor() {}

    /// A non-ward cannot authorise anyone (must-revert).
    function check_rely_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        rely(a);
        assert(false);
    }

    /// A non-ward cannot deauthorise anyone (must-revert).
    function check_deny_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        deny(a);
        assert(false);
    }

    /// A non-ward cannot register a collateral type (must-revert).
    function check_init_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        init(i);
        assert(false);
    }

    /// A non-ward cannot set a global parameter (must-revert).
    function check_file_global_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, uint256(dx));
        assert(false);
    }

    /// A non-ward cannot set a collateral-type parameter (must-revert).
    function check_file_ilk_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        file(i, i, uint256(dx));
        assert(false);
    }

    /// A non-ward cannot create or destroy free collateral (must-revert).
    function check_slip_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        slip(i, u, dx);
        assert(false);
    }

    /// A non-ward cannot confiscate a vault (must-revert).
    function check_grab_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        grab(i, u, u, u, dx, dy);
        assert(false);
    }

    /// A non-ward cannot create unbacked stablecoin (must-revert).
    function check_suck_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        suck(a, b, x);
        assert(false);
    }

    /// A non-ward cannot update a rate (must-revert).
    function check_fold_needs_auth(bytes32 i, address u, int256 dx, int256 dy) external {
        require(wards[msg.sender] != 1);
        fold(i, u, dx);
        assert(false);
    }

    /// A non-ward cannot shut the system down (must-revert).
    function check_cage_needs_auth(address a, address b, uint256 x, uint256 y) external {
        require(wards[msg.sender] != 1);
        cage();
        assert(false);
    }
}
