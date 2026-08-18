// Regression fixture: a claim that IS semantically true but is under-
// specified enough that kprove cannot discharge it -- this is the exact
// predecessor of provable.k before that claim's call frame was fully
// concretized (see docs/substrate.md §2). Kept verbatim (not "improved")
// because its value is entirely in being real, reproducible evidence for
// the classify() fix in docs/substrate.md §4a: before the fix, this log
// was reported as Refute (a false defect report on a valid claim).
//
// Run directly:
//   kprove tests/control/underspecified-true.k \
//     --definition ~/toolchains/kevm-1.0.678/haskell \
//     --spec-module UNDERSPECIFIED-TRUE-SPEC \
//     -I ~/toolchains/kevm-1.0.678/evm-semantics-source \
//     -I ~/toolchains/kevm-1.0.678/plugin
//
// Expected: exit 1. Log opens with:
//   kore-exec: [...] Warning (WarnStuckClaimState):
//       The configuration's term unifies with the destination's term, but
//       the implication check between the conditions has failed.
// and ends with the same generic "cannot be rewritten further" trailer used
// for genuine refutation (compare tests/control/refutable-structural.k,
// which shows the OTHER WarnStuckClaimState variant -- "doesn't unify" --
// for an actually-false claim). See tests/control/logs/underspecified-true.log
// and docs/substrate.md §4a for why these two must classify differently.

requires "evm.md"

module UNDERSPECIFIED-TRUE-SPEC
    imports EVM

    claim [underspecified]:
        <k> #execute => #halt ... </k>
        <mode> NORMAL </mode>
        <schedule> DEFAULT </schedule>
        <useGas> false </useGas>
        <program> #parseByteStack("00") </program>
        <pc> 0 </pc>
        <wordStack> .WordStack </wordStack>
     [label(underspecified), all-path]

endmodule
