# Spec harness format (frozen for Wave 1)

A specification φ is one Solidity file. This document fixes what that file may
contain, how it is compiled over an artifact, how a run of it is judged, and
what the artifact (b or a mutant) must look like for that to work. Every rule
here is mechanical: `tools/speclint.py` checks the file rules,
`tools/specgame_core.py` implements compilation, execution, the outcome rule
and Check. Parameters such as the solver timeout live in `../protocol.md`.

## 0. Subjects (protocol v3)

Everything below is written for the capped token, the first subject. Since
protocol v3 the subject is a parameter: `subjects/<name>/profile.json`
(`schemas/profile.schema.json`, sha256 pinned in protocol.json) fixes, per
subject, the contract file and name (`import "./<file>";`,
`contract Spec is <Name>`), the exact spec constructor, the allowed check
signatures, the value pools and the observation. Read "CappedToken" below as
the subject's contract. For Vat (`subjects/vat/`): `import "./Vat.sol";`,
`contract Spec is Vat`, `constructor() {}`, and two probe signatures,
`(address a, address b, uint256 x, uint256 y)` and
`(bytes32 i, address u, int256 dx, int256 dy)`; a σ carries the arguments of
both, so it scores against any check of either signature.

## 1. The harness

```solidity
// SPDX-License-Identifier: MIT
pragma solidity 0.8.35;

import "./CappedToken.sol";

contract Spec is CappedToken {
    constructor(uint256 cap_) CappedToken(cap_) {}

    function check_mint_adds(address a, address b, uint256 x, uint256 y) external {
        require(msg.sender == owner);                       // Pre
        require(x <= type(uint256).max - totalSupply);      // Pre
        uint256 before = totalSupply;
        mint(a, x);                                         // the token's own function
        assert(totalSupply == before + x);                  // Post
    }

    function check_cap(address a, address b, uint256 x, uint256 y) external {
        assert(totalSupply <= cap);                         // Post (state invariant)
    }
}
```

- `Spec` **inherits** the artifact. The deployed contract under test is
  `Spec` compiled over that artifact; it has the token's full public ABI plus
  the `check_*` probes. Prefix transactions of a configuration σ call the
  token functions on it; the final probe calls one `check_*`.
- Every probe has the **fixed signature**
  `check_<name>(address a, address b, uint256 x, uint256 y) external`
  (PLAN item 2). It is what makes one σ scorable against every spec, so the
  common pool W\* = ⋃ W_t is well defined. Parameters may go unused.
- A check calls the token **internally** (`mint(a, x)`, not `this.mint`), so
  `msg.sender` inside the token is the probe's sender. This is why the
  artifact's functions must be `public` (an `external` function cannot be
  called internally). See section 5.
- **Pre** = the maximal leading block of `require(...)` statements of a check.
  **Post/Trace** = its `assert(...)` statements. The spec φ is the conjunction
  over its checks of `Pre_i ⇒ Post_i`; each check carries its own Pre.

## 2. File rules (`tools/speclint.py spec`)

Comments and string literals are blanked before any rule runs.

| Rule | Requirement | Why |
|---|---|---|
| S1 | exactly one pragma, `pragma solidity 0.8.35;` | one compiler for Check and run |
| S2 | exactly one import, `import "./CappedToken.sol";` | the same text compiles over every artifact |
| S3 | the only top-level declaration is `contract Spec is CappedToken { ... }` | no helper contracts, interfaces, libraries, free functions |
| S4 | members of `Spec`: exactly the constructor `constructor(uint256 cap_) CappedToken(cap_) {}` and ≥1 `check_*` with the fixed signature; nothing else | no new state variables, no overrides of token functions, no helpers, no modifiers/events/errors |
| S5 | none of the tokens `assembly this super new delete selfdestruct payable storage memory calldata try catch revert emit event error modifier override virtual fallback receive for while do unchecked gasleft blockhash block tx interface library struct enum mapping using constant immutable public private internal view pure returns return` | no external calls, no environment outside σ, no storage aliasing, no loops, no `revert` that would blur the outcome rule |
| S6 | member access only `msg.sender`, `type(T).max` / `type(T).min`, and (v3) a struct field of the subject read after an index, e.g. `ilks[i].rate`, `urns[i][u].ink` | no `.call`, `.balance`, `.code`, `this.f()` |
| S7 | no write to an inherited state variable (`=`, `op=`, `++`, `--`), no tuple assignment, no local declaration that shadows a token name or a probe parameter | the spec observes the token, it never edits its state or keeps its own copy |
| S8 | calls only to public token functions, `require`, `assert`, `type(...)` and elementary type conversions | no inlined or internal token logic (`_mint`, modifiers), no hashing tricks |
| S9 | `require` only in the leading block; ≥1 `assert` per check; each `assert(` starts its own line, one per line; each check mentions a token state variable or calls a token function | Pre is a precondition, not a mid-body assumption; every target has a distinct line; a check that observes nothing about the token is not a spec of it |

The lint is text-level and strict on purpose: it rejects some harmless
programs (e.g. a helper `pure` function) rather than accept a harmful one. A
file it rejects is not a spec; Check, the adversary and the scorer never run on
it (the generator loop records such a round as `lint_rejected`).

φ⊤ (the trivially true spec) must still satisfy S9, e.g.
`assert(totalSupply == totalSupply);`.

## 3. Compilation over an artifact

`compile_spec_over(spec, artifact)` builds one solc standard-JSON input with
two source units given **by content**: `Spec.sol` (the harness text) and
`CappedToken.sol` (the artifact text: b or a mutant). solc runs in an empty
temporary directory and reads nothing from disk, so the harness text compiles
unchanged over every artifact and no file path can reach the bytecode.

Settings, identical for every compilation: `evmVersion: cancun`,
`optimizer.enabled: false`, `metadata.bytecodeHash: none`, solc
0.8.35+commit.47b9dedd.

Identities (PLAN item 7):

- **artifact** id = sha256 of the runtime bytecode (`evm.deployedBytecode`)
  of bare `CappedToken` compiled from the artifact source;
- **pair (φ, artifact)** id = sha256 of the runtime bytecode of `Spec`
  compiled over that artifact.

Always the compiled runtime, never `get_code()` from the executor (pyrevm pads
deployed code with zeros; TOOLCHAIN.md finding 3). Source sha256 values are
recorded next to these ids but are not identities.

## 4. Running and judging a probe

`run_sequence(entry, σ, probe_check)`: a fresh pyrevm EVM (spec_id CANCUN,
fixed block env, 10 000 000 gas per call; core v2 deploys with 30 000 000 gas
and a 1 MiB code size limit, since the Spec is never deployed on a chain,
protocol.md sharpened definition 16), deploy `entry` with `σ.ctor.cap`
from `σ.deployer`, execute `σ.txs` in order (a reverting prefix transaction is
recorded and the sequence continues), then call `probe_check(σ.probe.a,
σ.probe.b, σ.probe.x, σ.probe.y)` from `σ.probe.sender`.

**Outcome rule** (Condition D, PLAN item 3), `classify_outcome(revert_data)`:

| Probe ends in | Outcome | Witness? |
|---|---|---|
| normal return | `success` (satisfied) | no |
| `Panic(0x01)` (exactly 36 bytes) | `violation` | **yes** |
| `Error(string)` (strict ABI encoding) or empty revert data | `pre_unmet` | no |
| any other panic code (e.g. `0x11` overflow), custom error, malformed data, or a halt (out of gas, invalid opcode) | `other` | no |

The same function is used by the adversary, the scorer and the verifier.

**σ violates φ on artifact m** iff deploying `Spec` over m succeeds and, for
some `check_*` of φ, a fresh replay of σ's prefix followed by that check with
σ's probe arguments ends in `violation` (`evaluate_witness`). Every check gets
its own replay; `σ.probe.check` is provenance only. A violation implies the
check's Pre held, so this is exactly Def. 5.1's `Pre(σ) ∧ run violates φ`.

Consequence to keep in mind: a revert anywhere inside a check, including a
`require` inside a token function the check calls, is `pre_unmet`. Two cases
follow (protocol.md, "Sharpened definitions", item 3):

- **"This call must revert" is expressible** (must-revert pattern): put an
  assert after the call that fails whenever the call had an effect, e.g.

  ```solidity
  require(msg.sender != owner);
  uint256 s0 = totalSupply;
  mint(a, x);
  assert(totalSupply == s0);   // or assert(false)
  ```

  On b the call reverts, the assert point is unreachable, and Check Accepts
  (section 6, unreachable asserts are reported safe). On a mutant that drops
  the guard the call succeeds and the assert ends in `Panic(0x01)`: a witness.
- **"This call must succeed" (liveness) is not expressible**: a revert of the
  call is `pre_unmet` whatever the spec says after it. A mutant whose only
  difference is extra reverts (e.g. `mint` always reverts) is proper but no
  spec in this format kills it.

## 5. Constraints on the artifact (b and every mutant; `speclint.py artifact`)

| Rule | Requirement |
|---|---|
| A1 | exactly one pragma, `pragma solidity <range>;`, whose range admits the pinned solc 0.8.35 (v3: `^0.8.0` is fine; v1–v2 required `0.8.35` exactly) |
| A2 | the only top-level declaration is `contract <subject contract> { ... }` (no imports, interfaces, libraries) |
| A3 | none of `assert assembly import interface library immutable selfdestruct delegatecall staticcall this new external error`; no `.call/.send/.transfer/.code/.balance` |
| A4 | no custom errors (`revert E()`, or a `require` whose second argument is not a string literal); guards use `require(c)` / `require(c, "text")` / `revert("text")` |
| A5 | exactly one constructor, with the parameter types of the profile's `constructor.params` (capped token: `(uint256)`; Vat: `()`) |

Allowed (v3, for real contracts): structs, several mappings, modifiers such as
`auth`, `unchecked` blocks, internal pure/view helpers, any number of reason
strings.

Not lintable, checked by compile and by WP1's library build:

- the public ABI of every mutant equals b's (same function signatures);
- getters `owner()`, `cap()`, `totalSupply()`, `balanceOf(address)` exist
  (the observation reads them, protocol.md section 6);
- state variable and public function names used by specs exist in every
  mutant (otherwise a spec does not compile over it, and the pair is
  reported, not scored).

Why: no `assert` in the artifact, so `Panic(0x01)` can only come from the
spec; no custom errors, so a token guard maps to `pre_unmet` like a spec
`require`; no `external`, so checks can call every function internally; no
immutables, so the runtime bytecode is constructor-independent and equals the
deployed code (+ padding).

The κ havoc base (protocol.md section 11) is not an artifact and is exempt
from A3 (it uses an external call by design).

## 6. Check(b, φ)

`smtcheck(spec, artifact, timeout_ms, wall_timeout_s)`: the compilation input
of section 3 plus

```json
"modelChecker": {"engine": "chc", "solvers": ["z3"], "targets": ["assert"],
                 "timeout": <timeout_ms>, "contracts": {"Spec.sol": ["Spec"]},
                 "showProvedSafe": true, "showUnproved": true}
```

run as `solc --standard-json` with a PATH that resolves `z3` only to the
pinned z3 4.16.0. The exact input JSON, its sha256 and solc's raw output are
kept (bundle hard layer `c`).

Strict classification (`classify_smt_output`), in this order:

1. wall timeout → **Unknown** (`wall_timeout`)
2. any compiler error → **Unknown** (`compile_error`)
3. "Solver z3 ... not available" / "CHC analysis was not possible" →
   **Unknown** (`solver_unavailable`)
4. the targets are every `assert(...)` call in the AST. Every SMTChecker
   message must be exactly one of: `Info` "CHC: Assertion violation check is
   safe!" (→ safe), `Warning` "CHC: Assertion violation happens here." with a
   parsable counterexample and transaction trace, or exactly that message
   with no counterexample at all (→ violated; solc omits the counterexample
   when the violating path goes through an external call, e.g. over the κ
   havoc base), `Warning` "CHC:
   Assertion violation might happen here." (→ unproved); at the location of a
   target; at most one per target. Anything else → **Unknown** (`unparsed`).
5. no targets → **Unknown** (`no_targets`)
6. some target violated → **Refute(w)**, w = the parsed counterexample(s);
   reason `violation_without_counterexample` if solc gave none for some
   violated target (still Refute, w partial)
7. some target unproved → **Unknown** (`unproved`; includes solver-budget
   timeouts, which solc does not label)
8. some target without a result line → **Unknown** (`missing_target`)
9. every target safe → **Accept**

Accept therefore needs a positive per-target result for every assert: a run in
which the solver did not run cannot be an Accept, whatever solc prints (WP0
finding 1). Unknown is non-Accept everywhere. The counterexample of a Refute
is solver output, not a certified witness: its addresses are arbitrary and its
trace may call `check_*` functions as transactions. Only σ replayed under
section 4 count as witnesses.

Note on vacuity: solc reports an unreachable assert (e.g. after
`require(false)`) as "safe", so such a check is Accepted. That is intended
(the φ⊤ assumption) and is exactly what vacuity check (a) of protocol.md
section 12 detects.

## 7. Vacuity probe text (check (a))

`speclint.pre_probe_source(spec_text, check)` returns the spec with
`assert(false); // SPECGAME-PRE-PROBE` inserted on its own line right after
the leading requires of `check` (at the top of the body if there are none).
Check on that text: the inserted target `violated` ⇒ Pre satisfiable;
`safe` ⇒ Pre unsatisfiable, flag; `unproved` ⇒ Unknown, reported as such.

The probe sits right after Pre, before any token call, so it tests Pre
satisfiability only, **not** reachability of the check's assert points on b.
That is deliberate: a must-revert check (section 4) has an unreachable assert
point on b by design. A Probe-R style test that put `assert(false)` next to
each assert would flag every must-revert property as vacuous. Vacuity of the
conclusion is check (b) (κ), and library-relative vacuity is check (c).
