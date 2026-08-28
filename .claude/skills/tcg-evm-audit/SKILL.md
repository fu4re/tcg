---
name: tcg-evm-audit
description: Audit or formally verify a deployed EVM contract with the tcg proof-carrying-bundle CLI. Use whenever the task is to formally establish machine-checked properties of EVM runtime bytecode using tcg — writing KEVM claim interfaces, proving with kprove, probing vacuity, composing across external calls (RECURSE / REUSE / STUB), decomposing the work onto subagents, and freezing bundles that re-verify offline, with an honest proved / refuted / assumed / wall map as the deliverable.
---

# Auditing an EVM contract with tcg

## What tcg is

tcg builds and verifies **proof-carrying bundles**: self-contained, content-addressed
certificates that a specific DEPLOYED runtime bytecode satisfies a set of formally
proved **root claims** in KEVM (reachability logic over the EVM semantics). The judge
is the K prover — `kprove`, kore-exec underneath — never your prose. A bundle
re-verifies offline, from the bundle alone, with `tcg verify <bundle>`; that replay is
what your deliverable rests on, not your session.

Uniform exit codes across every command:
`0` ok · `1` usage / internal error · `2` Unknown — could not verify (a REFUSAL, never
a pass) · `3` refused — refutation witness or failed check. "Could not verify" (2)
never shares a code with "found a defect" (3); keep them separate in your notes too.

## Honesty discipline (non-negotiable)

- **The judge is the solver.** Never report a property as established from reasoning,
  reading code, or a promising log. "Established" means exactly: the claim Accepts
  inside a bundle that passes `tcg verify` from the bundle alone.
- **Four verdicts, never blurred:** proved ≠ refuted(+witness) ≠ unknown ≠
  unreachable/vacuous. Unknown is a budget/incompleteness refusal — it is evidence of
  nothing about the property, in either direction.
- **Vacuity before belief.** Run `tcg vacuity <loop>` after every Accept. An Accept
  over an infeasible antecedent proves nothing; `freeze` requires the vacuity record
  for every root and `verify` re-derives it, so an unprobed Accept cannot ship anyway.
- **Claims bind to the real bytecode.** Roots must prove over the installed
  `subject/runtime.bin` (verify checks the claim's `<program>` cell byte-for-byte).
  The residual left to the reader is keccak(runtime.bin) vs the on-chain code hash.
- **Stubs are declared, never silent.** Every assumed callee frame appears in the
  trust ledger, in `verify`'s warning section, and MUST appear in your final report
  as an assumption. Smuggling an assumption is a soundness lie.
- **Walls are first-class results.** "Could not prove X because Y (Unknown class,
  what was tried)" is a deliverable, not a failure to hide. A false green is worse
  than no result.
- **Backend caveat:** a claim whose execution reaches the target but whose
  postcondition is wrong can surface as Unknown (residual implication), not Refute —
  the backend's output for it is identical to a true-but-under-specified claim. So
  treat Unknown strictly as "undecided"; only a structural non-unification gives a
  reliable Refute.

## The pipeline, operationally

Run `tcg --help` and `tcg <command> --help` for full flags; `tcg status` at any point
prints the workspace state and the next-step hint. The flow, in order:

```
tcg init --definition <kompiled-def-dir> -I <include-dir> [-I ...]
                                  # pins the toolchain into .tcg/toolchain.lock;
                                  # also honors $TCG_DEFINITION at init time (flag wins)
tcg subject set --runtime <file> [--environment <env.json>]
                                  # <file>: raw bytes, or 0x-prefixed / plain hex text.
                                  # Omitting --environment writes a null-field skeleton:
                                  # chainid, fork, fee_schedule, constructor_args,
                                  # immutables, external_code — fill these in.
tcg loop new <name>               # one loop per external-call-free execution segment;
                                  # scaffolds .tcg/loops/<name>/iface.json to edit
tcg iface set <name> --file <iface.json>
tcg compile-claims <name>         # canonicalize + content-address (round-trip checked)
tcg prove <name>                  # kprove per claim: Accept / Refute / Unknown
tcg vacuity <name>                # falsify each Accept's post and re-prove; if it
                                  # STILL proves, the antecedent is infeasible: vacuous
tcg junction <i> <j>              # (as needed) consequence claim Post_i => Pre_j;
tcg compat <i> <j>                # (as needed) interference: Guar_j => Rely_i.
                                  # Both scaffold a workspace named <role>-<i>-<j>;
                                  # then iface set / compile-claims / prove it like a loop
tcg graph check                   # structural checks on the claim DAG
tcg approve --reviewer <name>     # sign-off over the CURRENT root hashes — do this
                                  # last, right before freeze: root drift after
                                  # approval makes verify refuse the bundle
tcg freeze                        # assembles bundle/ : hash tree + MANIFEST
tcg verify bundle [--strict]      # full replay from the bundle alone; the verdict
tcg roots bundle                  # render the root claims (and any assumptions)
```

`prove`, `vacuity`, `verify` also accept `--definition <dir>` / `-I <dir>` to override
the lock. Re-compiling a loop invalidates its proofs and marks loops that trusted its
claims Stale — re-prove in dependency order.

## Writing interfaces and claims

The interface is a six-part contract per loop (`tcg iface set --help` shows the keys):

- `pre`, `post`, `exit` — K predicates, as strings (entry condition, result, exit code).
- `footprint` — `{"reads": [...], "writes": [...]}` state slices touched.
- `rely`, `guar` — what the environment may do to you / what you guarantee it.
- `requires`, `imports` — K module plumbing (defaults: `["evm.md"]`, `["EVM"]`).
- `trusted` — `[{"loop": L, "label": l}, ...]` already-compiled claims injected as
  trusted lemmas into this loop's prove run (this is how a callee summary reaches its
  caller's proof).
- `claims` — `[{"label": l, "file": f, "role": r, "root": bool}, ...]`; `file` is a
  `.k` file inside the loop's own directory; `root: true` marks a bundle root.

Claim body form (checked by `compile-claims`): one K claim per file — a single
`claim ...` ending in the trailing attribute list `[label(<l>), all-path]`, with `<l>`
matching the entry's label. No `module`/`endmodule`/`requires` lines (the wrapper is
emitted for you); `trusted` and `one-path` attributes are refused. Every claim carries
the explicit all-path quantifier in the artifact itself.

What the bundle guarantees is exactly its **roots** — typically one per external
function of the subject. Generic property families that make good roots: revert/guard
behavior (calls outside the guard leave state unchanged and revert), access control
(only authorized senders reach a state-changing path), getter side-effect-freedom
(view paths write nothing), accounting invariants (declared balance sums preserved
across a call). Start from the subject's dispatcher: enumerate selectors, then state
one root per selector you can specify.

## External calls — the three branches

A loop ends at an external CALL. The callee's effect enters the caller's proof as an
**abstract summary claim S** (its `<program>` cell is a free variable, so S itself can
never Accept and is never proved directly); S is injected into the caller via
`trusted` and must then be DISCHARGED one of three ways:

- **RECURSE — prove the callee in-graph.** Prove a concrete callee claim D over the
  callee's real code P, plus a bridge claim B (S re-proved with `<program> := P`), in
  this same workspace. Wire it in the iface: the summary's `claims[]` entry carries a
  `bridge` block:
  `{"callee_address": "0x...", "code_hash": "<keccak256-of-callee-runtime>",
    "concrete_proof": {"loop": ..., "label": ...},
    "at_program_proof": {"loop": ..., "label": ...}}`.
- **REUSE — link an already-frozen callee bundle.** Freeze and verify the callee as
  its OWN bundle first; copy that bundle into this workspace under
  `deps/<callee_root>/`, where `<callee_root>` = sha256 of the dep's `MANIFEST.json`;
  the `bridge` block instead carries
  `"concrete_proof": {"dep": "<callee_root>", "root": "<dep-root-claim-hash>"}` and NO
  `at_program_proof`. `freeze` vendors the dep; `verify` re-verifies it recursively
  (post-order) and checks code-identity + the anti-proxy binding. Prove once, link
  from every caller.
- **STUB — a named, typed assumption.** When the callee is opaque or out of scope, do
  not pretend. After `compile-claims`, edit the summary node in `spec/graph.json`:
  replace any `bridge` with an `assume` block (the two are mutually exclusive):
  `{"callee_address": "<addr>", "frame": "<what the callee MAY and MAY NOT do — MUST
  state the storage-frame (does it write caller storage?) and reentrancy (may it
  re-enter the caller?)>", "ledger_id": "A_callee_<addr>"}` — `ledger_id` exactly
  `A_callee_<callee_address>`. `freeze` writes the matching trust-ledger entry;
  `verify` exits 0 but prints a prominent warning section naming every load-bearing
  assumption, and `verify --strict` refuses (exit 3). The frame is never interpreted
  by the tool — it is an assumption you are choosing, so err toward the strongest
  frame: forbid caller-storage writes and re-entry unless you truly need less.

For RECURSE and REUSE, `environment.json`'s `external_code[<callee>]` must equal the
callee runtime byte-for-byte — code-identity is computed, not assumed.

**Decision order:** a frozen dep bundle for this callee already exists → REUSE.
Callee code available and tractable → prove it (as its own bundle then REUSE if any
other caller might need it; in-graph RECURSE for a one-off). Otherwise → STUB, and
carry the assumption into the report.

## Decomposition and parallel subagents

1. **Map the call graph first.** From the bytecode (and source if given as a hint):
   selectors, which paths make external CALLs, to which callee addresses. Write the
   map down before proving anything.
2. **Work post-order:** callee legs (leaves) before the callers that consume them —
   a caller's summary can only be discharged by REUSE/RECURSE once the callee leg is
   proved (or honestly stubbed).
3. **Parallelize what is independent:** separate callee bundles, and separate property
   families on the same subject, can each go to a subagent with its own workspace.
4. **A subagent's "proved" is untrusted prose.** The only thing that counts is its
   frozen bundle passing `tcg verify` — run by YOU, the coordinator, before linking
   it as a dep or reporting it. Re-verify everything you did not prove yourself.

## Budget and iteration hygiene

- Prover runs are expensive and Unknowns happen. On Unknown: narrow the claim (one
  selector, one branch), pin more of the entry state in `pre`, split a long path at a
  CALL boundary, or downgrade the composition branch (RECURSE → STUB) — rather than
  re-running the same claim hoping for a different verdict.
- Escalate specificity, not optimism: a smaller true claim that Accepts beats a broad
  claim stuck at Unknown.
- Keep a running written map as you go — per function / property: proved (bundle +
  root hash) · refuted (witness) · assumed (stub frame, verbatim) · wall (Unknown
  class, what was tried). This map becomes the final report; do not reconstruct it
  from memory at the end.

## The deliverable

- Frozen bundle(s), each shown passing `tcg verify` (quote the exit code and, if any
  stubs exist, the warning section; note that `--strict` would refuse a stubbed
  bundle — that is by design, not a defect).
- `tcg roots <bundle>` output — the human-readable statement of what is guaranteed.
- The honest map: proved / refuted / assumed-stub (each frame verbatim) / walls.
- Claim nothing beyond the roots. The bundle transfers the mechanical part; whether
  the roots say what the reader cares about is their own reading — help them by
  keeping root claims small and legible.
