# TCG bundle format — spec v1

A bundle is a self-contained, content-addressed certificate that a specific
deployed EVM runtime bytecode satisfies a set of formally proved **root
claims**. It carries everything a third party needs to re-establish that
guarantee mechanically — bytecode, claims, composition graph, vendored
semantics, replay evidence, and an explicit ledger of what remains assumed —
with no trust in the bundle's author, the tooling that produced it, or the
session history behind it.

This document specifies the v1 format and the verifier protocol. Verdict
vocabulary used throughout:

- **proved** — the prover accepted the claim; evidence is replayable.
- **refuted** — the prover produced a concrete counterexample.
- **unknown** — the prover could not decide (budget, timeout, or solver
  incompleteness). Unknown is always a refusal, never a pass.

## 1. Format principles

1. **One trust root.** The certificate's identity is the hash of
   `MANIFEST.json`. Everything trust-relevant is reachable from it by hash
   links. Anything unreachable does not exist for the guarantee.
2. **Link direction encodes trust status.** Non-certified material (`nav/`)
   may reference the certificate; the certificate never references `nav/`.
   This makes the non-certified status mechanically checkable: the transitive
   closure of the trust root contains no links into `nav/`.
3. **Accept evidence only.** Refuter runs, iteration history, and session
   provenance live outside the certificate (in `nav/`). Soundness is carried
   only by proved claims.
4. **Vendoring, not pinning.** The bundle *contains* the theory sources —
   the semantics release, project lemmas, and the audited instrumentation
   patches — not just their hashes. A pinned remote repository is a dead link
   in five years; a vendored copy is not. Trust must transfer over time.
5. **Format cheaper than the tool.** Every structural check (hash tree, DAG
   discipline, topological order) is JSON + SHA-256 and re-implementable in an
   evening. The verifier trusts the prover and the semantics — not `tcg`.

## 2. Layout

```
bundle/
├── MANIFEST.json            # trust root: cert_version, hash tree, list of roots
│
├── subject/
│   ├── runtime.bin          # runtime bytecode, bit-exact
│   └── environment.json     # environment class: chainid, fork, fee schedule,
│                            #   constructor args / immutables, external code
├── spec/
│   ├── claims/<h>.k         # canonical claims, content-addressed by hash
│   ├── interfaces.json      # per loop: (Pre, Post, Eff, Exit) → claim refs
│   ├── graph.json           # claim DAG: typed nodes and edges, roots marked
│   └── root-assembly/<r>.json  # composite-root records (see §5)
│
├── theory/
│   ├── semantics/           # vendored semantics release (sources)
│   ├── patches/             # audited instrumentation diffs (ghost cells) +
│   │                        #   their transparency proof and audit notes
│   ├── lemmas/              # project lemmas: each proved or ledgered as assumed
│   └── toolchain.lock       # prover/solver versions, binary hashes, seeds,
│                            #   timeouts, replay retry policy
│
├── evidence/
│   ├── replay/<h>.json      # v1: exact prover invocation for claim h,
│   │                        #   children-as-trusted, expected Accept, resources
│   └── proofs/<h>.mm        # v2: proof objects, same key h
│
├── assumptions/
│   ├── trust-manifest.json  # named assumptions with per-entry status
│   ├── annotations.json     # facts ledger (storage layout etc.): each entry
│   │                        #   re-checkable or an explicit trusted input
│   └── oracle-record.json   # human sign-off over the current root hashes
│
└── nav/                     # NON-CERTIFIED: outside the MANIFEST hash tree
    ├── report.md            # human-readable narrative
    └── session/             # provenance: iterations, refutation history, prompts
```

## 3. Canonical claims

`spec/claims/<h>.k` is the trusted object; interface declarations are its
untrusted pre-form. The human oracle and the verifier validate claims, not the
intermediate representation — so the interface-to-claim compiler must support a
**round-trip print-back**, and approval is given against the printed claim.

Canonical form requirements:

- **Explicit all-path quantifier.** Every claim carries the all-path attribute
  in the artifact itself. Path semantics is pinned in the claim, never
  inherited from a toolchain default.
- **Ghost discipline.** Ghost variables are fresh and pairwise independent
  between Pre and Post. Pre carries the well-formedness constraints of ghost
  state (map well-formedness for per-selector maps, integer sorts otherwise);
  Post carries no ghost constraints.
- **Rely closure.** For interference (trace) claims, the invariant must be
  stated over a state slice stable under the loop's rely condition. This is a
  form requirement on the claim, checked structurally (or discharged by a
  dedicated rely-closure node, see §4).
- **Existentially bound outputs.** Any existentially bound variables in Post
  are explicitly marked; junctions bind them via substitution witnesses (§5).

Content addressing: `<h>` is the SHA-256 of the canonical claim text. A claim
with the same hash and the same set of trusted children never needs re-proving.

## 4. The claim graph

`spec/graph.json` is a directed graph over claim nodes with typed nodes and
typed edges.

**Node roles**

| Role | Meaning |
|---|---|
| `loop` | a proved reachability claim for one loop (one external-call segment) |
| `junction` | a consequence implication `Post_i ⟹ Pre_j` between sequenced loops |
| `subsumption` | a consequence implication used to weaken/strengthen at a boundary |
| `guar` | the guarantee claim of a loop (one per loop is mandatory) |
| `frame` | a frame obligation (state untouched outside the declared footprint) |
| `compat` | an interference obligation `Guar_j ⟹ Rely_i` |
| `env` | the environment-guarantee node, in decomposed form |
| `rely-closure` | optional: rely closure discharged as its own node rather than by claim form |

**Edge types**

| Type | Discipline |
|---|---|
| `trusted-lemma` | the source's proof uses the target as a trusted lemma. The target must itself be a proved, progress-carrying node — zero-step (consequence) nodes must never be the target of a trusted-lemma edge. The trusted-lemma subgraph must be **acyclic**. |
| `consequence` | the source uses the target's implication (junction / subsumption). Zero-step implications are valid here and only here. |
| `compat` | interference edges. **Cycles are allowed** on the compat subgraph; their soundness is carried by the interference theorem of the underlying discipline, not by acyclicity. |

**Roots.** The answer to "what does this bundle guarantee" is the set of root
claims — one root per external function of the subject. A verifier reads
exactly the roots, not the graph. Roots split into:

- `roots_R` — roots proved directly by a single prover run, and
- `roots_asm` — composite roots, declared by a root-assembly record (§5).

A junction node can never be a root.

## 5. Root-assembly records

A composite root that no single prover run proves is assembled from proved
sub-claims by a `spec/root-assembly/<r>.json` record: a **linear**, alternating
chain

```
[ (claim h0), (implication e1, σ1), (claim h1), … , (claim hm) ]
```

of proved loop claims and junction implications, where each `σi` is an explicit
**substitution witness** — the renaming that brings segment i's Post and
segment i+1's Pre to common free variables, such that after applying `σi` the
implication is literally the content of the junction node `ei`. Optional prefix
weakening and suffix strengthening implications are ordinary junction nodes.

v1 deliberately restricts assembly to linear chains; arbitrary graph-shaped
assemblies are outside the format.

## 6. Evidence

**v1 — replay records.** `evidence/replay/<h>.json` fixes the exact prover
invocation for claim `h`: command, module, options, the set of children
supplied as trusted lemmas, the expected verdict (Accept), and resource
budgets. Replay is deterministic up to solver behavior; the retry policy for
nondeterministic unknowns is pinned in `toolchain.lock`.

On a failed replay the verifier records the unknown class:

- `(a)` iteration bound exhausted — carries localization;
- `(b)` timeout;
- `(c)` solver returned unknown (nonlinear arithmetic / hashing theory).

All three refuse the certificate. Refusal on unknown is conservative: it can
reject a true claim, it can never accept a false one.

**v2 — proof objects.** `evidence/proofs/<h>.mm` replaces replay with
checkable proof objects under the same content key. The bundle skeleton does
not change between v1 and v2.

## 7. Assumptions

**`trust-manifest.json`** materializes every assumption as data with a status:

- `vendored` — e.g. the semantics: sources included, plus a reference to their
  conformance validation against the official execution test suite;
- `machine-checkable` — e.g. subject identity: instructions to compare
  `keccak(runtime.bin)` with the on-chain code hash;
- `verifier-action-required` — the irreducible semantic step: *read the roots*
  (§8 step 6).

Named entries the v1 manifest must carry:

- `A_keccak` — injectivity of keccak on the used preimages (storage slot
  disjointness rests on it);
- `A_access`, `A_precompile`, `A_gas_termination` — environment-model
  assumptions of the interference discipline;
- `A_gas` — gas decrease makes every maximal execution path finite (grounds
  the all-path quantifier);
- `A_adm` — no infinite internal stuttering of the semantics between
  observable steps;
- weak well-definedness of the vendored semantics;
- instrumentation transparency — the ghost-cell patches do not alter
  non-ghost behavior; proved once, shipped with the patches in
  `theory/patches/`, with any residual verification obligations listed as
  `residual, pending`;
- two reading-discipline lines: a prover Accept is read as a derivation in the
  prover's proof system; a checker Accept on an implication is read as
  validity of that implication.

**`annotations.json`** is the facts ledger: every compiler-derived fact the
proofs rely on (storage layout above all) is either re-checkable against
`runtime.bin` by the verifier (step 3) or declared as an explicit trusted
input. No silent inputs.

**`oracle-record.json`** dates and attributes the one non-formal act: a signed
statement by the approving human that the root-claim set `{h1..hn}` — by their
**current** hashes at freeze time — expresses the intended property. The
verifier does not trust it (their own reading of the roots replaces it); it
exists so that trust transfer over time is auditable.

## 8. Verifier protocol

Strictly ordered; failure of any step is **refusal of the certificate**.

| # | Step | Content | Cost |
|---|---|---|---|
| 1 | Integrity | recompute the hash tree from `MANIFEST.json` | seconds |
| 2 | Identity | `keccak(runtime.bin)` equals the on-chain code hash; constructor args / immutables per `environment.json` | seconds |
| 3 | Theory | build the vendored semantics (with patches); re-check every re-checkable `annotations.json` fact against `runtime.bin` | minutes |
| 4 | Graph | see below | minutes |
| 5 | Replay (v1) | topological order over the trusted-lemma subgraph; for each node, run the pinned invocation with children as trusted; expect Accept. **Unknown = refusal** (retry per `toolchain.lock`) | CPU hours |
| 6 | Semantic step | read the roots. The only step needing formal literacy — bounded to the roots, not the graph, the code, or the session | human |

**Step 4 checks in full:**

- hash links resolve; every trusted claim used in a node's evidence is a
  proved node with a corresponding edge (closure);
- edge typing: trusted-lemma targets are proved, progress-carrying nodes;
  zero-step nodes are never trusted-lemma targets;
- acyclicity on the trusted-lemma subgraph;
- explicit all-path attribute present on every claim;
- every loop has its `guar` node;
- rely-closure holds for every interference claim (by form, or via its
  dedicated node);
- compat coverage is complete: for every ordered pair of loops with observed
  footprint intersection (`writes_i ∩ (reads_j ∪ writes_j) ≠ ∅`) a compat
  node exists, and the `env` node is present;
- every root-assembly record is well-formed: the chain is linear and
  alternating, all references resolve, substitution witnesses apply literally;
- roots are reachable and each `roots_R` member lies in the proved subgraph;
- the oracle record's signature covers the current root hashes (freeze binds
  the record to the roots; drift between approval and freeze invalidates it).

**What the bundle transfers and what it does not.** It transfers the entire
mechanical part — that the bytecode satisfies the root claims, with the stated
composition — without trust in author, model, or session. It does not transfer
the semantic part: that the roots express the property the reader cares about.
That step is irreducibly the verifier's own reading of the roots.

## 9. Conformance

An implementation of `verify` must refuse the certificate on each of these
controls, and must pass the last one:

1. any single flipped byte in `runtime.bin` → refusal at step 2;
2. deletion of a proved child claim → refusal at step 4 (closure);
3. injection of a false trusted lemma → refusal at step 5 (replay of children);
4. unknown on replay → refusal (conservative), retried per `toolchain.lock`;
5. deleting `nav/` entirely → `verify` passes unchanged, and no link into
   `nav/` is reachable from the trust root.
