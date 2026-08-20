// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

/// @title OpaqueNotify — the smallest opaque callee for the STUB composition fixture.
///
/// A caller invokes `hook()` at an external address it does NOT own and does NOT
/// prove. The single external entry point mutates the callee's OWN storage (a
/// counter) — enough that its effect is not trivially empty, so a caller cannot
/// cheaply prove "this call changed nothing." In the composition E2E the caller
/// discharges this call via a *typed stub* (Mechanism B): a named, conservative
/// assumption recorded in the trust ledger, never a silent pass.
///
/// This is a FIXTURE, not a realistic contract. It exists only to give the STUB
/// branch a concrete, pinned runtime bytecode and a human-language typed frame.
contract OpaqueNotify {
    uint256 private pings;

    /// The opaque external effect the caller stubs instead of proving.
    function hook() external {
        pings += 1;
    }
}
