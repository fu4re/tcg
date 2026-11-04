# Specification Games prototype: protocol (pre-registered)

Status: **protocol v3, 2026-11-02** (sections "Protocol v3: subjects" and
"Protocol v2" below; v1, frozen earlier the same day, is kept in sections 1–16
for the record). Drafted in WP-I. Mechanical definitions for every
quantity the prototype reports.

**`protocol.json` is authoritative for every value** that affects a verdict
or reproduction (compiler and executor settings, address pool, outcome rule
version, Check timeouts, adversary parameters and id, generator parameters,
prompt hashes); `tools/specgame_core.py` and `generator/loop.py` read their
constants from it. This file is the narrative (definitions, measurements,
sharpened definitions); where a table here repeats a value, protocol.json
wins. Bundles record `protocol_json_sha256` (compared by the verifier,
refused on mismatch) and `protocol_md_sha256` (recorded only), so a prose
edit here never invalidates a bundle. Implemented by `tools/specgame_core.py` (the
judge path), `tools/speclint.py` (spec and artifact rules) and the schemas in
`schemas/`; the harness format is `specs/SPEC_FORMAT.md`. The note is
"Specification Games" (Stoliarov, 2026-10-29), cited by definition number.

**Freeze rule.** Values marked `TBD-before-WP7` are set after the ladder is
measured (WP6) and are written into this file before the first WP7 run. From
the first WP7 run on, no value in this file may change; a change means a new
protocol version and a new run set, not an edit. Values marked *provisional*
are what Wave 1–2 use until then.

Judge rule: every verdict is produced by SMTChecker or by deterministic
execution in `specgame_core`; no LLM is on the judge path.

---

## 1. Semantics version

| Item | Value |
|---|---|
| Compiler | solc 0.8.35+commit.47b9dedd, official static Linux binary, sha256 `fa8ac9a3…a617f4` (TOOLCHAIN.md) |
| Compiler settings | standard JSON, `evmVersion: cancun`, `optimizer.enabled: false`, `metadata.bytecodeHash: none`; sources passed by content under the unit names `Spec.sol` and `CappedToken.sol` |
| SMT solver | z3 4.16.0 (external process; PATH restricted to the pinned binary) |
| Executor | pyrevm 0.3.7 (hash-pinned wheel), `spec_id = "CANCUN"` |
| Block env | number 1, timestamp 1, gas_limit 30 000 000, basefee 0, coinbase 0x0, prevrandao 0x00…00; chain_id 1 |
| Gas per call | 10 000 000 (every transaction, the probe, every getter read; core v1 also the deploy) |
| Deploy (core v2) | gas 30 000 000 (= the block gas limit); code size limit 1 048 576 bytes (pyrevm `CfgEnv.limit_contract_code_size`), initcode limit 2 097 152 (revm derives 2 x); b and every mutant must still have runtime ≤ 24 576 bytes (EIP-170), enforced by the core (sharpened definition 16) |
| Python | 3.12 (stdlib + pyrevm only on the judge path) |

`toolchain_fingerprint()` records all of these plus the sha256 of the core
itself; the bundle's provenance layer carries it and verifier step (1) hashes
it.

## 2. Artifacts

b = `contracts/CappedToken.sol` (owned by WP1). Mutants: `mutants/*.sol`. Both
must pass `speclint.py artifact` (SPEC_FORMAT.md section 5): one contract
`CappedToken`, `constructor(uint256 cap_)`, all functions `public` (never
`external`), no `assert`, no custom errors, no immutables, no external calls;
getters `owner()`, `cap()`, `totalSupply()`, `balanceOf(address)`; every
mutant has b's public ABI.

## 3. Spec format and probe signature

See `specs/SPEC_FORMAT.md`. Summary: `contract Spec is CappedToken`, probes
`check_<name>(address a, address b, uint256 x, uint256 y) external`, Pre =
leading `require`s, Post = `assert`s, the token called internally. φ is the
conjunction over its checks of `Pre_i ⇒ Post_i`.

## 4. Configuration σ (PLAN item 1)

```json
{
  "version": 1,
  "deployer": "alice",
  "ctor": {"cap": "100"},
  "txs": [
    {"sender": "alice", "fn": "mint(address,uint256)", "args": ["bob", "60"]},
    {"sender": "carol", "fn": "mint(address,uint256)", "args": ["carol", "50"]}
  ],
  "probe": {"sender": "carol", "a": "carol", "b": "zero", "x": "1", "y": "0",
            "check": "check_owner_only"}
}
```

- `deployer`, every `sender`: one of `alice`, `bob`, `carol`. The token's owner
  is whoever deploys it.
- `fn`: a canonical signature in the artifact's ABI whose parameter types are
  only `address` and `uint256`; never a `check_*`.
- `args`: `address` → a pool name (section 5); `uint256` → a decimal string
  without leading zeros, ≤ 2^256 − 1.
- `probe`: required for a witness, absent for a properness pair. `check` is
  provenance only (section 8).
- Schema: `schemas/sigma.schema.json`; the arity/type agreement and the
  uint256 bound are checked by `validate_sigma`.

Every σ is constructor-reachable by construction (it starts from a deploy),
matching what CHC quantifies over (constructor + arbitrary transactions).

## 5. Address pool and environment

| Name | Address | Role |
|---|---|---|
| alice | `0x1111111111111111111111111111111111111111` | sender / deployer / argument |
| bob | `0x2222222222222222222222222222222222222222` | sender / deployer / argument |
| carol | `0x3333333333333333333333333333333333333333` | sender / deployer / argument |
| zero | `0x0000000000000000000000000000000000000000` | argument only (the zero / unused address) |

No ETH value is ever sent. Block and chain context are fixed (section 1); no
spec or artifact may read them (S5, A3).

## 6. run(b, σ), observation, properness (Def. 4.2, PLAN item 6)

`run_sequence(entry, σ)` (no probe) on bare `CappedToken` gives an
observation:

- `deploy`: outcome class of the deployment;
- `txs[i]`: outcome class (section 7) and, on success, the return data;
- `state`: after the sequence, the return of `owner()`, `cap()`,
  `totalSupply()`, and `balanceOf(p)` for p ∈ {alice, bob, carol, zero}, each
  read as a static call from `zero`.

Revert payloads (the bytes behind `pre_unmet`/`other`), gas used and event
logs are **not** part of the observation. Two observations are equal iff
their canonical JSON is byte-equal (`observation_equal`).

A **properness pair** for mutant m is a σ (no probe) with
`run(b, σ) ≠ run(m, σ)`. It is found by differential fuzzing (WP2), re-checked
by replay before it is stored in `mutants.json`, and re-checked by the
verifier (step 3). A mutant with no pair within the search budget is
excluded (`exclusion_reason: no_properness_pair`) and logged; it is never
counted as killed or as surviving.

## 7. Outcome rule (Condition D, PLAN item 3)

`classify_outcome(revert_data)`: success → `success`; exactly
`Panic(0x01)` → `violation`; strict `Error(string)` or empty revert →
`pre_unmet`; any other panic, custom error, malformed data → `other`. Halts
(out of gas, invalid opcode) → `other`. Only `violation` of a probe is a
witness.

## 8. Witnesses, kill sets, score (Def. 5.1, 5.3)

σ is a **witness against (m, φ)** iff deploying Spec-over-m from σ succeeds
and some `check_*` of φ, called with σ.probe after a fresh replay of σ's
prefix, ends in `violation` (`evaluate_witness`). The pair (m, σ) does not
depend on φ, so it can be scored against any spec (PLAN item 2).

For a presented witness set W ⊆ M × Σ:
`K_cert_W(φ) = { m ∈ M : ∃ (m, σ) ∈ W, σ is a witness against (m, φ) }`,
`ms_cert = |K_cert| / |M|`, reported as the exact pair
`{"killed": |K_cert|, "total": |M|}`, never as a float. M is the set of
**included** mutants (section 10). A pair that does not evaluate to a
violation is discarded and logged with its outcome, never counted.

Certified adequacy (Def. 5.4) = Check(b, φ) = Accept and K_cert = M.

## 9. Check(b, φ) and Unknown (PLAN item 5)

SMTChecker CHC + z3, targets `assert`, contracts restricted to `Spec`, with
`showProvedSafe` and `showUnproved`; strict classification as in
SPEC_FORMAT.md section 6. **Unknown counts as non-Accept** everywhere (scores,
feedback, certified adequacy).

| Parameter | Value |
|---|---|
| `timeout_ms` (solc `modelChecker.timeout`, per solver query) | **120 000** (frozen 2026-11-02; was `TBD-before-WP7`, provisional 20 000) |
| `wall_timeout_s` (whole solc process per harness) | **1500** (frozen 2026-11-02; was `TBD-before-WP7`, provisional 300) |

**Measured durations (WP3, 2026-11-02; input to the TBDs above, not a
setting).** Placeholder b, solc 0.8.35 + z3 4.16.0, `tcg` VM (4 cores), one
`tools/specreport.py` run per timeout, specs run sequentially, nothing else
running. Seconds of solc wall time per run; "κ" = Check of the spec over the
havoc base, "vac (a)" = Check of the Pre-probed spec over b.

| Spec | asserts | 20 000 ms: verdict / Check / κ / vac (a) | 120 000 ms: verdict / Check / κ / vac (a) |
|---|---|---|---|
| phi_top | 1 | Accept / 0.12 / 0.5 / 0.95 | Accept / 0.13 / 0.6 / 0.9 |
| phi_owner | 3 | Accept / 0.71 / 56.6 / 4.9 | Accept / 0.67 / 92.3 / 4.8 |
| phi_cap | 2 | Accept / 0.43 / 10.8 / 2.4 | Accept / 0.45 / 11.3 / 2.4 |
| phi_both | 5 | Accept / 5.3 / 79.2 / 25.4 | Accept / 5.3 / 122.6 / 27.3 |
| phi_transfer | 7 | Accept / 4.3 / 80.5 / 14.3 | Accept / 4.3 / 289.0 / 13.7 |
| phi_full | 11 | **Unknown** (unproved) / 221.0 / 162.1 / 243.6 | Accept / 630.6 / 370.7 / 1363.3 |
| controls/phi_false | 1 | Refute / 9.2 / 2.0 / 16.2 | Refute / 9.0 / 2.1 / 15.5 |
| controls/phi_dead | 1 | Accept / 0.12 / 1.0 / 0.21 | Accept / 0.12 / 1.0 / 0.22 |

Additional phi_full Check runs: 60 000 ms → Unknown (9/11 safe;
`mint_owner_adds_amount` and `transfer_keeps_supply` unproved), 548.7 s;
120 000 ms → Accept, 601.6 s (both while another solc run shared the CPU).
The pairwise unions phi_cap ∪ phi_transfer and phi_owner ∪ phi_transfer
Accept at 20 000 ms (56.3 s, 33.7 s, also under contention). Observations for
the freeze:

- phi_full needs ≥ 120 000 ms per query at this machine speed; the verdict
  at a given per-query timeout depends on how fast the machine answers each
  query, so a spec near the cliff can flip Accept ↔ Unknown between the build
  machine and the E1 verifier machine. The frozen timeout should keep a
  margin above the slowest ladder spec, and the verifier should treat a
  verdict flip as "could not verify", not as a refusal of the score.
- The wall timeout must cover the slowest of Check, κ and vacuity (a) on the
  largest spec: 1363 s for vacuity (a) of phi_full at 120 000 ms; the
  provisional 300 s is too small for phi_full under any setting tried.
- κ over the havoc base is the slowest step for every other spec (the
  unknown external call makes CHC work harder), up to 289 s.

## 10. Mutation class M and mutant identity (Def. 4.1, PLAN item 7)

- Mutant id = sha256 of the runtime bytecode of bare `CappedToken` compiled
  from the mutant source (section 1 settings). Equal ids = one mutant: a
  mutant whose id equals another's, or b's, is rejected at library build.
- A mutant that does not compile, does not deploy (with σ's `cap` used by its
  properness pair), fails the artifact lint, or changes the public ABI is
  excluded before any experiment (note §9, "Policies").
- **Behavioural duplicates** (note open question 10): m and m' are flagged
  duplicates iff `run(m, σ) = run(m', σ)` for every σ in the union of their
  properness pairs. Flagged in `behavioural_duplicate_of`, not merged; both
  stay in M.
- `operator` and `fault_class` are T\* labels and affect no verdict.
- Schema: `schemas/mutants.schema.json`.

## 11. κ: non-tautological conjunct count (PLAN item 4)

A conjunct is one `assert(e)` of a check, read under that check's Pre.
It is **tautological** iff Check proves it (status `safe`) when the spec is
compiled over the **havoc base** H instead of b. κ(φ) = number of asserts of φ
that are not tautological. `unproved` over H counts as non-tautological
(conservative: it can only raise κ) and the number of such asserts is
reported next to κ.

The havoc base H is a contract named `CappedToken` with:

1. the same state variables as b (same names, types and visibility), plus
   one private storage variable `__ret_<fn>_<k>` of the return type per
   return value of a token function;
2. a public setter per state variable, `havoc_<var>(T v)`, and for each
   mapping `havoc_<var>(K k, V v)`, plus a setter per `__ret_*`;
3. b's constructor signature with an empty body;
4. every public token function of b with b's signature and a body that makes
   one external call to a fixed unknown address
   (`IFree(address(0xF4EE)).next()`) and then returns its `__ret_*` value
   (or nothing).

Under SMTChecker's default (untrusted) external-call model, the unknown call
may re-enter any public function of the contract, so after it every state
variable, every mapping entry and every return value is unconstrained; before
any call the state is any value the setters can produce. Proving `assert(e)`
over H thus means e holds for every state and every token behaviour that
satisfies Pre: a tautology in the intended sense. Proving over b is not a
tautology test (every true property of b proves over b).

Measured on solc 0.8.35 + z3 4.16.0 (WP-I, scratch run): with token functions
as plain no-ops, the frame conditions `totalSupply == t0` and
`balanceOf[b] == b0` after a `transfer` call are proved, i.e. wrongly counted
as tautologies; with the external-call construction above they are refuted /
unproved, while `x == x`, `totalSupply <= cap` under the Pre
`require(totalSupply <= cap)`, and `!r || r` are still proved. H is generated
by `tools/kappa.py` from the artifact's AST on every run (so subject or
mutant changes propagate); `specs/havoc/CappedToken.sol` is the reviewed
snapshot for the placeholder b (`make havoc` regenerates it, a unit test
fails if it is stale). The table above is its acceptance test
(`tests/fixtures/specs/kappa_acceptance.sol`, `tests/test_wp3.py`), and it
reproduces.

An assert is read at its program point: over H it is proved under the
check's Pre **and the asserts before it on the same path** (a failed assert
reverts). So `assert(e); assert(e);` counts e once, which is the intended
"adds nothing given the earlier conjuncts". Over H solc sometimes reports a
bare "happens here." without a counterexample (the violating path goes
through the unknown external call); the classifier counts that as violated
(SPEC_FORMAT.md section 6).

Alternative recorded, **not used**: the M-relative test (a conjunct is
"tautological" iff removing it leaves K_cert unchanged).

## 12. Three vacuity checks, kept apart (PLAN item 9, note §5)

Per spec, the bundle reports all three; none replaces another.

(a) **Pre satisfiable**, per check: Check on `pre_probe_source(φ, check)`
(an `assert(false)` right after the leading requires). Inserted target
`violated` ⇒ satisfiable; `safe` ⇒ unsatisfiable, flagged (this is what an
Accept of a `require(false)` check looks like from the inside); `unproved` ⇒
Unknown, reported. Check (a) tests **Pre satisfiability only, deliberately
not reachability of the assert points on b**: the probe sits before any token
call, because a must-revert check (Sharpened definitions, item 3) has an
unreachable assert point on b by design, and a Probe-R style reachability
test at the assert would flag every must-revert property as vacuous.

(b) **Conclusion non-trivial**: κ(φ) > 0 (section 11), with the per-assert
table.

(c) **M-vacuity** (Def. 5.4): K_cert_W(φ) = ∅ at budget B_A.

## 13. Events on W\* (PLAN item 8, note §9 "Weakening event")

Within one trajectory (condition × seed) with rounds t = 0..R−1:
W\* = ⋃_t W_t (all pairs any round's adversary found, deduplicated by
canonical JSON). K_t = K_cert_{W\*}(φ_t), computed for every round,
including rounds whose φ_t was not Accepted (`acc_t` recorded next to it).
For consecutive rounds:

| Relation | Event |
|---|---|
| K_{t+1} ⊊ K_t | weakening |
| K_{t+1} ⊋ K_t | strengthening |
| incomparable | shift (reported separately, never folded into the other two) |
| equal | unchanged |

`lost = K_t \ K_{t+1}`, `gained = K_{t+1} \ K_t`; |K_t| is reported as the
scalar view. A round whose φ_t failed the lint has `acc = lint_rejected` and
K_t = ∅ (it is not a spec). Schema: `schemas/events.schema.json`.

## 14. Bundle layout and trust classes (PLAN item 11, note §10, Table 2)

`schemas/manifest.schema.json`:

| Layer | Content | Trust |
|---|---|---|
| `files` | sha256 of every file in the bundle | step (1) |
| `hard` | b (source, runtime sha256); φ (source, sha256 of Spec over b, checks); c = the exact solc standard-JSON input, its sha256, raw output, verdict, timeouts | T after the verifier re-runs Check |
| `evidence` | M (id, source, properness σ list); W (witnesses); adversary id, source sha256, seed, B_A; discarded pairs with reasons | U until checked |
| `metadata` | operator, fault_class per mutant | T\*, no verdict |
| `provenance` | toolchain fingerprint (semantics version), core and verifier sha256, `protocol_json_sha256` (compared, refused on mismatch), `protocol_md_sha256` (recorded only), feedback condition / round / seed / model / temperature / prompts sha256 (null for hand-written specs) | read, hashed in step (1) |
| `claimed` | `ms_cert` as {killed, total}, `kill_set` (sorted ids) | recomputed; a disagreeing claim is refused |
| `not_claimed` | must contain `"V-completeness"` | — |

## 15. Pre-registered parameters

Frozen 2026-11-02, before the first WP7 run. The freeze rule at the top of
this file applies to every row.

| Parameter | Before the freeze | Frozen 2026-11-02 |
|---|---|---|
| Probe signature | fixed | `(address a, address b, uint256 x, uint256 y)` |
| Address pool | fixed | section 5 |
| Gas per call, block env | fixed | section 1 |
| Outcome rule | fixed | section 7 |
| Observation for properness | fixed | section 6 |
| κ test | fixed | havoc base, section 11 |
| Check `timeout_ms` | TBD (provisional 20 000) | **120 000** (WP3/WP6: phi_full needs it, section 9) |
| Check `wall_timeout_s` | TBD (provisional 300) | **1500** |
| Adversary budget B_A (sequences per (mutant, φ)) | TBD | **2000** |
| Adversary seed seed_A | TBD | **0** |
| Adversary max sequence length (max_txs) | TBD | **6** |
| Witnesses kept per (mutant, φ) | TBD | **1** |
| Adversary id (adversary.py + seqgen.py sources + the four values above + seqgen's distribution id) | — | `c16d1dd5a4a4…` (= the ladder's; byte-identical sources) |
| Rounds R | TBD (PLAN: 3) | **3** |
| Best-of-k | TBD (PLAN: 2) | **2** |
| Generator seeds | TBD (PLAN: ≥ 2) | **{0, 1}** |
| Feedback conditions | f∅, fM, fM+ | **f0, fM, fMplus** (3; section 16.4) |
| Generator model id (requested) | TBD | **`claude-sonnet-5-5`**; the id the API returns is recorded per call and per run |
| Temperature | TBD | **not sent**: "API default; non-default values rejected by this model" (section 16.1; probe: `temperature: 0.7` → HTTP 400) |
| max_tokens | — | **16 000** (section 16.1) |
| Effort | — | **`output_config: {"effort": "high"}`**, sent explicitly (= the model default, pinned in the body) |
| Thinking | — | model default (adaptive, always on); not sent; thinking tokens recorded per call |
| SDK / API version | — | `anthropic` 2.3.0, header `anthropic-version: 2026-10-21` (recorded per run) |
| Server-side fallbacks | — | **none** (a refusal is a failed candidate, never a different model) |
| Prompts | TBD | `generator/prompts/`, sha256 per file in section 16.7 |
| Selection rule (best-of-k) | — | section 16.3 |
| Per-round cost rule | — | section 16.2 |

## 16. Generator loop (WP7; gates E3, E5)

Implemented by `generator/loop.py` (not on the judge path: no module in
`tools/` imports it; it reads model output only as a candidate spec file).
One trajectory = one (condition, seed): R rounds, k candidates per round.

### 16.1 The request

Messages API, Python SDK `anthropic` 2.3.0 (hash-pinned closure in
`generator/requirements.lock`; it sends `anthropic-version: 2026-10-21`).
Body: `model`, `max_tokens` 16 000, `output_config: {"effort": "high"}`,
`system` (= `prompts/system.md`), `messages`; nothing else. No sampling
parameters: `claude-sonnet-5-5` rejects them (probe on 2026-11-02:
`temperature: 0.7` → HTTP 400 "temperature: Extra inputs are not
permitted"; the same request without it → 200), so the temperature is the
API default, recorded as "API default; non-default values rejected by this
model"; diversity between the k candidates comes from independent calls on
the same prefix. Bundle provenance needs a number there: it records 1.0, the
Messages API's default temperature, with this note. `effort` is sent although `high` is the model default, so
the body pins it. The model always thinks
(adaptive thinking is its default and cannot be turned off; thinking tokens
count toward `max_tokens`), hence `max_tokens` 16 000 rather than 4096; a
reply cut at `max_tokens` is recorded with its `stop_reason` and judged like
any other reply. Recorded per call: returned model id, `stop_reason`,
`stop_details`, input / output / thinking tokens
(`usage.output_tokens_details.thinking_tokens`, part of the output). The
Messages API has no `seed` parameter: the trajectory seed
is recorded only (`trajectory.json: seed_param`). No server-side fallbacks:
a refusal (`stop_reason: refusal`) is a failed candidate (no spec,
`lint_rejected`), recorded with its `stop_reason` and `stop_details`.

Conversation, append-only: round 1 = `[user: round_1.md]`; round t+1 =
round t's messages + `[assistant: the selected candidate's content blocks,
verbatim (text and thinking blocks), user: the feedback]`. The k candidates of
a round share one request body. Every request body (no key) and response is
stored per candidate. API key: `ANTHROPIC_API_KEY`, else `~/.specgame_env`;
never printed, never written; every trajectory directory is scanned for the
key after the run.

### 16.2 Per-candidate cost rule

Every candidate: extract the single `solidity` block (0 or ≥ 2 blocks → no
spec, `acc = lint_rejected`) → `speclint` (fail → `lint_rejected`, no Check)
→ Check(b, φ) at the frozen timeouts → adversary A (frozen id) → its own
W_t and ms_cert on W_t. A spec that does not compile gets `acc = Unknown`
(`compile_error`), no adversary. "Compile" means the whole Spec over b to
bytecode with the pinned settings, done before Check (2026-11-03): the
SMTChecker run skips code generation, so a codegen error ("Stack too deep")
passes lint and Check and surfaced only when the adversary compiled the
Spec, aborting the trajectory (`runs/v3/vat/fM/seed_0_aborted_stack_too_deep`). κ and vacuity (a) are computed **once per
trajectory, for the final selected spec only** (they are too slow per round:
370 s and 1363 s on phi_full in WP3) and are **never fed back**.

### 16.3 Selection rule (best-of-k)

Uses only what the condition reveals. Under **f0**: an Accepted candidate
before a non-Accepted one; ties → fewer lint/compile errors (number of
reported lint violations, plus extraction failure, plus compile errors); then
the first (lower j). Under **fM** and **fMplus**: Accept first; then higher
ms_cert on the candidate's own W_t; then the first. The selected candidate's
reply continues the conversation; the others are scored and kept but never
shown to the model.

### 16.4 Feedback (`prompts/feedback_<condition>.md`)

All conditions: the checker verdict as a bit ("Accept" / "not accepted"),
plus the error text — lint violations, compile errors, or, for a non-Accept,
each assert that was not proved (line, source text, "can fail" or "could not
be decided within the checker's budget"); never counterexample values.
**fM** adds ms_cert as `killed/total` on the selected candidate's own W_t.
**fMplus** adds the surviving mutants as 12-hex id prefixes with their
`fault_class` label; never mutant sources, operators or names. In no
condition does the generator see mutant sources or the ladder specs.

### 16.5 Two scores per round

- **own ms_cert**: on the candidate's own W_t (what fM / fMplus show and
  what the selection rule uses);
- **K_t on W\***: post hoc, for the selected φ_t of every round, on
  W\* = ⋃ over all candidates of all rounds of the trajectory of their W_t,
  ∪ the ladder's W\* (the W of `bundles/phi_*`), so every round of the
  trajectory is scored on the same pool (section 13). Events are decided
  from K_t only.

Both are recorded (`round_t/cand_j/score.json`, `events.json`); they are
different numbers by construction and must not be compared as if they were
one. A selected φ_t that was lint-rejected or does not compile has K_t = ∅.

### 16.6 Per trajectory

`runs/<condition>/seed_<N>/`: per round and candidate `request.json`,
`response.json`, `Spec.sol`, `lint.json`, `check.json` (v3 runs:
`check.json.gz` + `check_summary.json`, 16.10), `witnesses.json`,
`adversary_log.json`, `score.json`; per round `selected.json`, `feedback.md`;
then `kappa.json`, `vacuity_a.json`, `bundle/` (tools/bundle.py on the final
spec with its own W_R and the feedback provenance) and `verify.json`
(tools/verify.py exit 0 HOLDS = `bundle_holds`; exit 2, e.g. NOT_CERTIFIED
for a final spec whose Check is Unknown and reproduces as Unknown, =
`bundle_not_certified`, ms_cert still reported; exit 3 or no bundle =
`bundle_refused`; the reason is recorded),
`W_star.json`, `events.json` (`schemas/events.schema.json`), `trajectory.md`
(per-round table, spec diffs, event kinds) and `trajectory.json` (requested
and returned model, tokens per call and total, timings, errors).
Trajectories run one at a time.

### 16.7 Prompt files (sha256)

| File | sha256 |
|---|---|
| `generator/prompts/system.md` | `e10abee05c69410a9bc538ad0c8d2f4acda224e054ff66b6aa5f13ba61596cdf` |
| `generator/prompts/round_1.md` | `0d5460ff48fbe85a60d454d3369e42e594f15de4ad9195c66fb589a342eea65c` |
| `generator/prompts/feedback_f0.md` | `0044d327cc58966ada3797c50835ad058cec94540f164e15dd9297a13e542700` |
| `generator/prompts/feedback_fM.md` | `3e22dc0e896d07e8d89f272fddfe8e96e2c5f2236ca1beaf0cadb16dd4d468dd` |
| `generator/prompts/feedback_fMplus.md` | `21b6574b733ebbf918384b0a7f0e398806ac198fad8563f90a584a401b820dde` |
| all five (canonical JSON of the table above; bundle provenance `prompts_sha256`) | `ef5622219a5de745cdec1d0dea26b19f34b3a099d7309b0aff04a21ed4e73f32` |

`intent.md` is read from `specgame/intent.md` (not duplicated) and
`contracts/CappedToken.sol` is inlined verbatim into round 1.

### 16.8 Cost estimate (before any live call)

From the `--dry-run` sizes: round-1 request 9 171 characters (system 5 155,
user 4 016), identical under the three conditions; feedback on the example
score 277 (f0), 388 (fM), 623 (fMplus) characters. Estimated at 3 characters per token (conservative for the
current tokenizer): round-1 input ≈ 3 050 tokens. Per trajectory (R = 3,
k = 2, 6 calls), assuming ≤ 6 000 tokens of replayed assistant content per
earlier round: input ≈ 2 × (3 050 + 9 300 + 15 500) ≈ 56 000 tokens; output
6 × 6 000 ≈ 36 000 tokens expected, 6 × 16 000 = 96 000 at the `max_tokens`
cap. At `claude-sonnet-5-5` prices ($2 / $10 per MTok): ≈ $0.47 per
trajectory expected, ≤ $1.08 at the cap; six trajectories ≈ $2.8 expected,
≤ $6.5 at the cap. Actual tokens are recorded per call.

### 16.9 Bundles and the protocol files

Bundles record `protocol_json_sha256` (compared by verifier step 1; a bundle
produced under other frozen values is refused) and `protocol_md_sha256`
(informational, never compared). After a change that leaves every
verdict-relevant input unchanged (prose here, the verifier's or the core's
source text), `python tools/bundle.py --restamp <bundle>...` rewrites only the
provenance, the core audit copy and the `files` table, in seconds, and
refuses if b, φ, M, the solc input of c or the semantics version would
change. The full verification stays the expensive path and is run once, at
the end (E1). History: at the freeze, before the split, the ladder bundles
were rebuilt in full (`make ladder`, 23 min, every bundle HOLDS, only the
protocol hash changed); after the split they were restamped.

### 16.10 Storage note: raw Check records in runs/ (2026-11-03)

Not a protocol change; no verdict, score or bundle depends on it. A
candidate's raw Check record (`check.json` in 16.6: the full Check result,
including every check's raw solc output, about 360 KB per check on Vat, 20 to
25 MB per Vat candidate) is stored in protocol v3 runs as `check.json.gz`
(gzip of the same bytes, `mtime` 0, `tools/runstore.py`) next to
`check_summary.json`: the sha256 and size of the uncompressed bytes, the
combined verdict and reason, the timeouts and walls, and per check its
verdict, reason, wall and solc input sha256. Readers accept both forms
(`runstore.read_check_json`; `bundle.py --check-json` takes either). Applied
retroactively to every v3 run (`runs/v3/vat/fM/seed_0` and the three aborted
attempts) in one commit, with each summary's sha256 equal to the committed
`check.json`; no history rewrite. runs/v2 keeps plain `check.json`. Bundles
are unchanged: their hard layer keeps the per-check certificates as they are.
The measurement bundles were not restamped for this prose (their
`protocol_md_sha256` is informational); only the test fixture
`tests/fixtures/bundle/good`, whose freshness test pins it, was.

### 16.11 Planned (WP8): cross-condition rescoring on the union of pools

Not a change to what runs now. W* is per trajectory: the ladder's pool plus
that trajectory's own witnesses (|W*| = 25 for Vat fM seed 0, 17 for f0 seed
0), so kill sets on W* are not comparable across trajectories as they stand.
The final cross-condition comparison will rescore every trajectory's final
spec (and, for events, every selected spec) on the union of all pools of the
subject, with the same executor, and report both the per-trajectory and the
union-pool kill sets. A side probe already shows a pool gap: a hand σ with a
sin-creating setup kills m08 for the f0 seed 0 round-3 spec although no σ in
any W* does (`runs/v3/vat/f0/seed_0/probes/m08_sin_setup/`).

## Protocol v3: subjects (2026-11-02)

**What changed.** The subject b is a protocol dimension. A subject is
`subjects/<name>/` with its contract, `profile.json`
(`schemas/profile.schema.json`), intent, mutants and specs; protocol.json
(`protocol_version` 3) lists the subjects with the sha256 of each profile and
the per-subject frozen values, and the core refuses a profile whose sha256 is
not the pinned one. What moved out of protocol.json into the profile: the
address pool, the senders, the constructor parameters, the probe signature(s)
and the observation getters (protocol.json v2 `configuration`, `observation`);
the adversary parameters and id and the generator configuration moved under
`subjects.<name>`. Shared, unchanged: compiler and executor settings, the
outcome rule, Check v2 and its timeouts. Every tool takes `--subject`
(default `capped_token`).

| Per subject (protocol.json `subjects.<name>`) | capped_token | vat |
|---|---|---|
| profile sha256 | `04b386f2213754b7…` | `66e8b6203a073d7e…` |
| contract | `CappedToken.sol` / `CappedToken`, constructor `(uint256)` | `Vat.sol` / `Vat`, constructor `()` |
| probe signatures | `(address a, address b, uint256 x, uint256 y)` | that one and `(bytes32 i, address u, int256 dx, int256 dy)` |
| generator | `capped-v1` (the v2 distribution) | `typed-v2` (per-call kinds; distribution sha256 `c7813478e227…`) |
| setup | none | init GOLD, SILVER; Line; spot/line per ilk; slip 1000 wad of both ilks to every sender; alice hopes bob, bob hopes carol; every sender opens a 100/50 wad urn in both ilks |
| adversary B_A / seed_A / max_txs / per mutant | 2000 / 0 / 6 / 1 | 2000 / 0 / 6 / 1 |
| adversary id | `229abfec314c…` (v2: `c16d1dd5a4a4…`) | `da221ec5557e…` |
| generator (LLM loop) | as frozen in v1/v2 | same R, k, seeds, model, effort; `max_tokens` **64 000** (below); own system and round-1 prompts (below) |

New mechanics: typed σ arguments (address and bytes32 as pool names, uint256
and int256 as decimal strings, int256 signed); σ.probe carries the arguments
of every probe signature, so one σ scores against any check of any signature;
a fixed `setup` (the profile's, sent by the deployer right after deployment)
is part of every σ's canonical form and hash as `σ.setup`, validated to equal
the profile's, so witnesses and properness pairs in a bundle carry it and the
verifier replays it; the typed generator's value kinds include `repeat` and
`negate` of a numeric value already in the σ (setup arguments first), so a σ
can unwind a step (frob(+d) then frob(-d)) or reuse an exact value, and they
are part of the distribution id (`tools/seqgen.py` docstring); `sigma.schema.json`
is subject-neutral (the profile-specific checks are in `validate_sigma`); the
observation is the profile's getters over the profile's key spaces (keys
`sig`, `sig[k]`, `sig[k1,k2]`); lint S6 also admits struct-field reads of the
subject (`ilks[i].rate`), S7 also catches struct-field writes; the artifact
rules are relaxed for real contracts (SPEC_FORMAT.md section 5: pragma
ranges, structs, modifiers, `unchecked`, helpers; still no external calls,
`assert`, custom errors, immutables, assembly, `external`). Verify step 2 now
also refuses a bundle whose Check timeouts are not protocol.json's.

**Capped token under v3.** σ streams (2000 σ, with and without probe), solc
inputs, runtime ids and observations are byte-identical to v2
(`tests/test_subjects.py`, and all eight mutants' recorded properness
observation hashes reproduce). The adversary id changes only because it
hashes `adversary.py` and `seqgen.py`, which became profile-driven; both ids
are recorded. All 13 capped-token bundles (ladder, fixture, six v2 runs) were
**restamped**, not rebuilt: three verifier checks broke, none for a
verdict-relevant reason: step 0 (the manifest schema now requires
`provenance.subject`), step 1 could-not-verify (core and verifier sources
changed) and step 1 refusal (`protocol_json_sha256` changed with v3).
Restamp re-derives every solc input and id with the v3 core and refuses on
any difference; none differed.

**Generator loop for Vat (prepared, not yet run).** `generator/loop.py
--subject vat` uses `subjects/vat/prompts/system.md` and `round_1.md` (the
spec format for `contract Spec is Vat`, the two check signatures, the units,
the struct-field reads, and the contract facts the model needs: reason-string
reverts, the unchecked-with-require `_add/_sub/_mul` helpers, and that its
own checked arithmetic may panic without that counting as a violation;
round 1 embeds `Vat.sol`, the Vat intent and the two signatures) and the
shared, unchanged feedback templates. The examples in the system prompt (a
trivially true check, `file("Line", x)` sets `Line`, and frob on an
unregistered collateral type must revert) lint clean and are Accepted
(`tests/test_generator.py`). R, k, seeds, conditions, model and effort
equal the capped token's (protocol.json `subjects.vat.generator`).
`max_tokens` is 64 000 for vat (capped token: 16 000, unchanged): in the
first fM seed 0 attempt both round-1 replies spent all 16 000 output tokens
on thinking (`thinking_tokens` 16 000, a single thinking block, no text) on
an 8 745-token prompt and were lint-rejected; the attempt is kept as
`runs/v3/vat/fM/seed_0_aborted_max_tokens`. Effort stays `high`, so the
generator's reasoning regime is the capped token's; only the budget
changes. Requests are sent with `messages.stream(...).get_final_message()`
(the SDK requires streaming at this `max_tokens`); the body is unchanged,
and the capped token's body stays byte-identical. A live run is refused
while `subjects/vat/mutants/mutants.json` or the ladder W*
(`bundles/vat/phi_*/manifest.json`) is missing.

| Vat prompt file | sha256 |
|---|---|
| `subjects/vat/prompts/system.md` | `8afcd74c44fcc2558575f072dc385146ad1a6e358ffe9ba3c81943be0d4b17ac` |
| `subjects/vat/prompts/round_1.md` | `4a875318c1a8d8a4ac88ab58be1c419798b62a2819336daf6bfc7ad62d691f3b` |
| `generator/prompts/feedback_f0.md` | `0044d327cc58966ada3797c50835ad058cec94540f164e15dd9297a13e542700` |
| `generator/prompts/feedback_fM.md` | `3e22dc0e896d07e8d89f272fddfe8e96e2c5f2236ca1beaf0cadb16dd4d468dd` |
| `generator/prompts/feedback_fMplus.md` | `21b6574b733ebbf918384b0a7f0e398806ac198fad8563f90a584a401b820dde` |
| all five (bundle provenance `prompts_sha256`) | `fbd52777f1a512821d7964339f9b931c42c62b92c48b4739df0995e3c6adc74c` |

Cost estimate (before any live call): the round-1 request is 22 561
characters (system 6 781, user 15 780), identical under the three
conditions; feedback 277 / 388 / 602 characters (f0 / fM / fMplus, on the
dry-run's example score). At 3 characters per token: round 1 ≈ 7 500 input
tokens; with up to 6 000 tokens of replayed reply per earlier round, input
per trajectory ≈ 2 x (7 500 + 13 700 + 19 900) ≈ 82 000 tokens; output
6 x 6 000 ≈ 36 000 expected, 96 000 at the original 16 000 cap. At
`claude-sonnet-5-5` prices ($2 / $10 per MTok): ≈ $0.52 per trajectory
expected, ≤ $1.12 at that cap; six trajectories ≈ $3.1 expected, ≤ $6.7 at
that cap. (The aborted first attempt showed round 1 alone uses the full
16 000; at the 64 000 cap the output bound is 6 x 64 000 = 384 000 tokens,
≤ $3.84 + input per trajectory, ≤ $25 for six) (the capped-token estimate was $2.8, the measured cost $1.34). The
judge side is slower than for the capped token: a frob-related check can
take 1–2 minutes of Check (60 s per query, Unknown at that budget), and the
adversary replays every check per σ against every mutant (2000 σ x checks x
mutants at ~2.3 ms per σ run), so a trajectory is expected to take on the
order of an hour, not minutes.

**Vat (`subjects/vat/`).** Source: the sheaf repo's equivalence-verified 0.8
port of MakerDAO DSS Vat with `external` → `public` only (PROVENANCE.md).
`tools/portdiff.py`: the sheaf port compiled as-is and `subjects/vat/Vat.sol`
have identical runtime bytecode, and 5000 seeded σ give equal observations;
the σ exercise real behaviour (successful frob 399/846, fork 470/845, grab
430/911; `subjects/vat/portdiff_log.json`).

**Adversary coverage on Vat (gate).** The first typed generator (kind
typed-v1: one pool per type) reached Vat's core almost never, so a Vat kill
set would have been a search artifact (Thm 8.4: a low certified score is
ambiguous between weak spec and weak search). The Vat generator is now
`typed-v2`: per-call sender kinds (auth functions biased to the deployer),
per-parameter kinds (ilks from the registered ones, `bogus` rarely; urn,
source and destination biased to the sender itself and to addresses that
`hope`d it; amounts bounded by what the setup made available, `dart` a
fraction of `dink`, plus repeat/negate), and a richer setup (both ilks for
every sender, an open urn per sender and ilk, two consent pairs only, so
consent faults stay observable). Successful / total calls over 2000 σ, seed
0 (`python tools/seqgen.py --coverage --subject vat`), with the acceptance
floors enforced by `tests/test_subjects.py`:

| function | typed-v1 | typed-v2 | floor |
|---|---|---|---|
| frob | 2/326 (0.6 %) | 168/340 (49.4 %) | 25 % |
| fork | 1/347 (0.3 %) | 179/338 (53.0 %) | 10 % |
| grab | 8/373 (2.1 %) | 168/339 (49.6 %) | 10 % |
| move | 9/335 (2.7 %) | 302/332 (91.0 %) | 20 % |
| fold | 78/364 (21.4 %) | 228/310 (73.6 %) | 20 % |
| slip | 63/330 (19.1 %) | 231/345 (67.0 %) | 20 % |
| flux | 13/359 (3.6 %) | 289/380 (76.0 %) | 20 % |
| heal | 48/360 (13.3 %) | 10/361 (2.8 %) | — (needs the caller's own sin) |

**κ on Vat.** The havoc base now supports struct-valued mappings (one setter
per mapping taking the keys and every field), so κ is determined on Vat:
κ = 4 of 4 asserts on the measurement spec (`subjects/vat/specs/measurement/`).

**Check v2 on Vat (measurement for step 2; `subjects/vat/specs/measurement/vat_measure.sol`,
4 workers, no cache):**

| Check | kind | 60 000 ms / 600 s | 300 000 ms / 1500 s |
|---|---|---|---|
| `check_suck_needs_auth` | must-revert auth | **Accept**, 3.5 s | Accept, 3.9 s |
| `check_frob_conserves_collateral` (2 asserts) | linear per-transition on frob | **Unknown (unproved)**, 123.3 s | Unknown (unproved), 603.4 s |
| `check_two_dai_balances_within_debt` | global invariant, two-key sum ≤ debt | **Unknown (unproved)**, 61.8 s | Unknown (unproved), 302.1 s |

The Unknown durations are 1× and 2× the per-query timeout in both settings:
every query of those checks exhausts its budget, and 5× more budget does not
help. Even a linear per-transition property of frob (one call, no invariant
needed) is not proved by CHC, presumably because frob's path condition
carries the non-linear rate·art and ink·spot products; a sum-style global
invariant over mappings is out of reach as expected. Authorisation
(must-revert) properties are cheap. Consequences for step 2: under
Unknown-as-non-Accept, most non-trivial Vat specs will not be Accepted at
these budgets; the κ havoc base does not yet support struct-valued mappings
(`HavocError: unsupported mapping value type Ilk`); and the adversary needs
the setup (or a richer one) to reach frob states.

---

## Protocol v2 (2026-11-02)

**What changed.** Check(b, φ) is no longer one SMTChecker run over the whole
spec. For a spec with checks c_1..c_n, Check v2 builds n **isolated
harnesses**: harness_i = the fixed header (pragma, import,
`contract Spec is CappedToken`, the constructor) followed by c_i's function
text verbatim; every other check is left out (`core.isolate_check`, using
the same parser as speclint; for a lint-clean spec this is exactly "the spec
with every check except c_i removed", since S1–S4 fix the header). Each
harness is checked over the artifact with the strict classifier, up to
`workers` = 4 solc processes at once. Spec verdict: **Accept iff every check
is Accept; Refute(w) if any check is Refute** (all counterexamples kept);
else Unknown, reason `compile_error` / `solver_unavailable` / `unparsed` /
`no_targets`, then `budget` (some check hit its wall timeout), then
`missing_target`, else `unproved`. κ (one havoc-base Check per check) and
vacuity (a) (one probed isolated harness per check) use the same isolation
and pool. The whole-harness Check stays available (`check.py --mode whole`)
for comparison only.

| Value (protocol.json) | v1 | v2 |
|---|---|---|
| `protocol_version` | — | **2** |
| `check.mode` | whole harness | **isolated** |
| `check.workers` | 1 | **4** |
| `check.timeout_ms` (per solver query) | 120 000 | **60 000** |
| `check.wall_timeout_s` | 1500 per spec | **600 per check harness** |

Everything else in sections 1–16 (σ, observation, outcome rule, adversary
id and parameters, generator parameters, prompts, selection, feedback,
events) is unchanged. v2 trajectories are written to `runs/v2/`.

**Why.** Measured on the placeholder-era ladder and on the aborted v1 run
(4 cores, no cache):

| Spec | asserts | v1 whole-harness Check (120 000 ms) | v2 isolated, wall / solc total (120 000 ms) | v2 at 60 000 ms | slowest check (v2) |
|---|---|---|---|---|---|
| phi_top | 1 | Accept, 0.12 s | Accept, 0.14 / 0.12 s | Accept, 0.13 s | 0.12 s |
| phi_owner | 3 | Accept, 0.70 s | Accept, 0.23 / 0.58 s | Accept, 0.21 s | 0.22 s |
| phi_cap | 2 | Accept, 0.41 s | Accept, 0.17 / 0.31 s | Accept, 0.17 s | 0.16 s |
| phi_both | 5 | Accept, 5.3 s | Accept, 0.38 / 1.09 s | Accept, 0.41 s | 0.25 s |
| phi_transfer | 7 | Accept, 4.2 s | Accept, 0.54 / 1.40 s | Accept, 0.58 s | 0.53 s |
| phi_full | 11 | Accept, 597–632 s (Unknown at 20 000 and 60 000 ms) | Accept, 0.79 / 2.38 s | Accept, 0.84 s | 0.56 s |
| controls/phi_false | 1 | Refute, 9.0 s | Refute, 9.6 / 9.6 s | Refute, 10.2 s | 9.6 s |
| controls/phi_dead | 1 | Accept, 0.12 s | Accept, 0.12 / 0.12 s | Accept, 0.13 s | 0.12 s |
| v1 run, fM seed 0, round 1 cand 1 (LLM, 11 checks) | 22 | **Unknown (wall_timeout), 1500 s** | **Accept, 1.61 / 5.46 s** | Accept, 1.56 s | 1.34 s |
| v1 attempt 2, cand 1 (LLM) | 21 | not run (stopped) | Accept, 1.59 / 5.20 s | Accept, 1.55 s | 1.32 s |

The whole-harness cost is not in any single check: every check of a
combined spec is also a transaction of `Spec`, so CHC must find one
inductive invariant for all of them together; isolated, each check needs
only the token's invariant plus its own body. Under v1 the generator's first
real spec ran into the 1500 s wall, and a wall-timeout non-Accept fed back
to the generator is indistinguishable, for the generator, from "your spec is
wrong", which fakes exactly the weakening signal the experiment measures
(H1). Under v2 the same spec is Accepted in under 2 s.

**Timeouts.** The slowest isolated check measured is the phi_false Refute
(9.6–10.2 s, a counterexample search); the slowest Accept is 1.34 s. All
verdicts are identical at 60 000 and 120 000 ms. 60 000 ms per query keeps
a margin of ~6× over the slowest check and ~45× over the slowest Accept
while halving the worst case of a genuinely hard check; the wall timeout of
600 s **per check harness** (10 query timeouts) bounds a pathological check
without bounding the number of checks. A check that exhausts its budget is
`Unknown (budget)`; solc prints the same "might happen" for a per-query
solver timeout as for incompleteness (TOOLCHAIN.md finding 2), so a
per-query timeout without a wall timeout is reported as `unproved`; the two
cannot be separated from solc's output.

**Soundness of the isolation (Sharpened definitions, item 15; E4).** A check
changes state only through public token functions called with the probe
sender (speclint S5–S8: no own state, no writes to token state, no other
calls), so a call to another check is, as a state transition, equivalent to
a sequence of token calls by the same sender; adding or removing checks adds
or removes no reachable token state. Hence Accept(Spec with all checks) ⟺ ∧_i
Accept(harness_i) semantically, and a Refute of harness_i is a Refute of the
spec. Verified empirically: on phi_top … phi_transfer and both controls the
per-assert statuses of the isolated runs equal those of the whole-harness
run (`tests/test_check_v2.py`), and phi_full Accepts under both.

**Verdict cache.** `build/cache/<key>.json` holds the full per-check
CheckResult; key = sha256 of {the exact solc input's sha256, the wall
timeout, the solc and z3 binary sha256, the core source sha256}. check.py,
specreport, kappa, vacuity, the ladder and the generator loop consult it
first; it is a pure optimization. A bundle always carries the real solc
input and raw output of every check; `verify.py` never reads the cache
(it re-runs every certificate).

**Bundles.** Hard layer `c` is a list of per-check certificates (check name,
solc input path and sha256, raw output path, verdict, reason) plus the
combined verdict; verify step (2) re-derives every input from the bundled b
and φ, re-runs all of them in the pool and requires Accept on each. Bundles
record `protocol_json_sha256` (compared, refused on mismatch) and
`protocol_md_sha256` (informational); `bundle.py --restamp` updates
provenance only. The ladder and fixture bundles are rebuilt under v2.

**v1 record.** Sections 1–16 describe v1 as frozen; where they give Check
values or the whole-harness procedure, this section supersedes them. The two
aborted v1 attempts of fM seed 0 are kept in `runs/fM/seed_0/` and
`runs/fM/seed_0_attempt2/` with READMEs.

---

## Sharpened definitions

Places where the note or PLAN.md was not mechanical, and what this protocol
fixes them to. Candidates for the E4 list.

1. **Σ is the constructor-reachable, pool-restricted configuration space.**
   The note's configurations are abstract; here σ = (deployer, cap, sequence
   of token calls, probe) over a 4-address pool. K_sem is therefore relative
   to this Σ, while CHC quantifies over all addresses: a Check Accept is
   stronger than the Σ the adversary searches.

2. **φ is a conjunction of per-check implications, and a witness is scored by
   "some check panics".** The note's Pre is one predicate per spec; here each
   check carries its own Pre, σ violates φ iff ∃ check i with Pre_i(σ) and
   Post_i violated, and every check is evaluated on its own replay. Under this
   reading Prop. 6.3 (kill of a conjunction = union of kills) holds for any
   two specs, without the note's "share Pre" side condition, provided the
   conjunction is formed as the union of their checks.

3. **Pre absorbs token-call reverts.** Any revert inside a probe, including a
   `require` inside a token function the check calls, is `pre_unmet`.
   "Must revert" is still expressible: an assert after the call that fails
   whenever the call had an effect (e.g. `require(msg.sender != owner);
   s0 = totalSupply; mint(a, x); assert(totalSupply == s0);`) is unreachable
   on b, hence Accepted, and becomes a `Panic(0x01)` witness on a mutant that
   lets the call through (SPEC_FORMAT.md section 4). What the format cannot
   express is liveness ("this call must succeed"): a revert is `pre_unmet`
   whatever follows it. A mutant that only adds reverts (e.g. mint always
   reverts) is therefore proper (the observation sees the outcome class) but
   no spec in this format can kill it: a concrete instance of the note's open
   question 7 (unkillable proper mutants) caused by the outcome rule, not by
   the observable. WP1/WP2 should expect a score ceiling < 1 if such mutants
   are included.

4. **Observable = outcome class + success return data + getter state on the
   pool.** Revert payloads, gas and event logs are excluded, so mutants that
   differ only in a revert message, gas or events are *not proper* by this
   definition and are excluded. This removes the note's gas example from M by
   definition rather than solving open question 7.

5. **κ's havoc base must havoc behaviour, not only state.** PLAN item 4's
   "functions return free values" with otherwise no-op functions makes frame
   conditions after a call (e.g. `totalSupply` unchanged by `transfer`)
   provable, i.e. counted as tautologies; measured, section 11. Fixed: token
   functions in H make an unknown external call, so state and return values
   after any token call are free. `unproved` over H counts as
   non-tautological.

6. **Unknown has two sources solc does not distinguish.** A per-query solver
   timeout and an over-approximation both print "might happen"
   (TOOLCHAIN.md finding 2). The protocol keeps two timeouts (per query,
   per harness wall) and treats both kinds of Unknown as non-Accept.

7. **Accept requires a positive result for every assert.** "No violation
   reported" is not Accept: solc 0.8.35 with no reachable z3 skips CHC and
   exits 0 (TOOLCHAIN.md finding 1). Accept = every assert target has a
   "safe" line; a target with no line is Unknown (`missing_target`).

8. **An unreachable assert is Accepted.** solc reports an assert after
   `require(false)` as safe. That is the intended φ⊤ behaviour (PLAN WP3) and
   is why vacuity check (a) exists as a separate, per-check test.

9. **Two identities.** The note identifies mutants by hash; here the mutant
   id is the runtime sha256 of bare `CappedToken`, and the pair (φ, artifact)
   has its own id, the runtime sha256 of `Spec` over the artifact. Source
   hashes are recorded but are not identities (a comment change is not a new
   mutant).

10. **ms_cert is an exact rational** {killed, total} over the included
    mutants only; excluded mutants are not in the denominator.

11. **Behavioural duplicates** are decided on the union of the two mutants'
    properness σ (a finite, recorded set), flagged and kept, answering the
    note's question 10 operationally without merging.

12. **CHC reachability vs σ reachability.** CHC analyses `Spec`, whose
    `check_*` functions are themselves transactions. The lint (S5–S8) ensures
    a check changes state only through public token functions called with the
    probe sender, so the states CHC explores are the token-reachable states σ
    can reach. CHC counterexamples are not certified witnesses: they may use
    arbitrary addresses and call checks as transactions; only replayed σ
    count.

13. **The probe's `check` field is provenance.** A witness found against one
    check of φ_t is scored against φ' by trying every check of φ'; the field
    records where the adversary found it and affects no verdict.

14. **Vacuity check (a) is Pre satisfiability, not assert reachability.**
    The note's "Pre is satisfiable" (§5) and the sheaf Probe R convention
    (`assert(false)` proved ⇒ unreachable ⇒ flag) diverge here: placed after
    Pre, the probe tests the note's notion; placed at an assert point, it
    would test reachability of the conclusion on b, which is false by design
    for every must-revert property (item 3). The protocol uses the former
    (section 12) and leaves conclusion vacuity to κ (check (b)) and
    library-relative vacuity to check (c).

15. **Check is per check, not per spec (protocol v2).** The note's
    Check(b, φ, c) is one call on φ as a whole. Here Check(b, φ) = ∧_i
    Check(b, φ_i) over isolated one-check harnesses, sound because a check
    adds no reachable token state (lint S5–S8; Protocol v2, "Soundness of
    the isolation"), and orders of magnitude cheaper (phi_full 632 s → 0.8 s).
    Without it, the solver budget, not the specification, decides Accept
    for large specs, and Unknown-as-non-Accept feeds that budget back to the
    generator as if it were a property of the spec.

16. **The Spec is a measurement harness, never deployed (core v2,
    2026-11-03).** EIP-170 (24 576-byte runtime) and EIP-3860 (49 152-byte
    initcode) are deployment rules for contracts on a chain; the Spec
    (φ over b, or over a mutant) only carries the checks into the executor,
    so they do not apply to it. Core v2 deploys with a 1 MiB runtime limit,
    the 2 MiB initcode limit revm derives from it, and the block gas limit
    (30 000 000) as deploy gas; at 200 gas per deposited byte that admits
    about 145 KB of Spec runtime, above which the deploy runs out of gas and
    every check is `not_run`. Calls keep 10 000 000. The subject side is
    unchanged: b and every mutant must be deployable contracts (runtime ≤
    24 576 bytes); `check_deployable` refuses any other in `run_sequence`
    and `properness.build`, so the lift can change no observation of b or a
    mutant. Found by the Vat generator: a 73-check spec of 37 530 runtime
    bytes (`runs/v3/vat/fM/seed_0_aborted_code_size`) could not deploy under
    core v1, every check was `not_run` and its ms_cert 0/8 was an executor
    artifact; the hand-written `phi_full` (42 checks, 23 899 bytes) was
    just under. The committed bundles were restamped with
    `bundle.py --restamp --migrate-executor-limits`, which replays every
    properness σ and witness σ (every check) of a bundle under core v1 and
    v2 and refuses unless all observations are identical (1 296 observations
    over the 24 bundles, all identical).

Left to later work packages: whether Prop. 6.2's counterexample reproduces
(PLAN item 10; WP6 measures, the ladder is not bent to the note).
