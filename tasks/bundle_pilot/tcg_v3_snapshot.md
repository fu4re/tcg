<!-- Snapshot of https://claude.ai/artifact/57GjxDSW4qC8aqEiwnX3Jo (rev 14), taken 2026-10-29 for offline use by pilot agents. Formatting approximate; the Claude Doc is authoritative. -->

# TCG v3: Proof-Carrying Bundles for Critical Infrastructure

 · 

## Abstract

TCG v3 turns the trusted-code-generation pipeline of v2 into a portable unit of trust: the proof-carrying bundle. v2 showed that soundness is invariant to the generator and stopped at returning a pair (b, φ); the certificate that justified acceptance was consumed by the checker and discarded. v3 keeps it. A bundle β packages the artifact, the specification, the certificate, the instantiated trusted base and the evidence of non-vacuity into one content-addressed object that a third party re-verifies with a small checker, offline, with no access to the session that produced it.

The framework is parametric in the domain. Any domain that supplies a formal semantics, a specification language over its configurations and a sound certificate checker admits a bundle; the EVM is one instantiation, not the subject. The design claim of v2 is thereby strengthened from soundness does not depend on who wrote the code to verification does not depend on who wrote the code, where, with what tools, or whether they still exist. Anyone may write anything; the recipient knows how to check it.

The bundle separates three layers with different kinds of trust. The hard layer is checked by a kernel and admits no judgement. The evidence layer is judged by the human oracle and makes that judgement auditable. The provenance layer records how the artifact came to be and is informative only. A verdict ladder L0–L4 reports each layer separately so that a kernel-checked proof is never conflated with a well-documented opinion. The one non-formal gap of v2, alignment between specification and intent, stays with a human; the bundle gives that human tools and a signature, never a replacement.

## 1. Introduction

The unit of trust in critical infrastructure is not a pipeline but an artifact that crosses a boundary. A contract is deployed, a firmware image is flashed, a kernel module is loaded, a circuit is published; at that moment the producer and its tooling are gone, and whoever runs the artifact must decide whether to trust it with nothing but the artifact in hand. v2 answered the question how can an untrusted generator produce a trusted artifact? v3 asks the question that follows: how does that trust travel with the artifact to a party that never saw the generator?

The answer in v2 was already implicit. Acceptance was a decidable, syntactic check of a certificate c against a specification φ and an artifact b over a formal semantics. Everything the checker needed was an input; nothing about the producer entered. But the process returned (b, φ) and discarded c, so a second party had to re-run synthesis or take the first party's word. Both options reintroduce the trust the framework was built to remove. The fix is to return the inputs of the check, not its verdict.

This reframing changes what the paper is about. v2 reads as a paper on EVM verification with a generator in front of it; the EVM semantics, forks and fee schedules occupy the definitions. In v3 the EVM is a parameter. What remains when it is abstracted away is a general statement about any domain in which correctness is formalizable: there exists a bundle format such that the producer may be arbitrary, adversarial or absent, and the consumer still decides acceptance with a small trusted base. This is the thread the paper now follows end to end: let anyone write anything; you know how to check it.

Three commitments carry through from v2 unchanged. The generator is untrusted and stays untrusted; nothing in v3 makes it more reliable, and nothing needs to. Soundness is a theorem relative to an explicit trusted base, not a property of a tool. And the alignment between formal specification and human intent is a non-formal gap discharged by a human oracle, not hidden. v3 adds one commitment: every assumption in the trusted base that can be turned into a mechanical check is turned into one, and every assumption that cannot is written into the bundle as data the consumer can inspect.

Contributions.

A domain-parametric restatement of TCG in which the EVM is one instantiation of a verifiable domain (Section 2).

The proof-carrying bundle: a content-addressed object carrying artifact, specification, certificate, instantiated trusted base and evidence, with a re-verifiability proposition (Sections 4–5).

A verdict ladder that reports kernel-checked, judged and informative layers separately, so that a bundle never presents an opinion as a proof (Section 6).

A treatment of the generation session, including generator traces, as provenance that is recorded but never trusted, resolving the tension between auditability and capability-invariance (Section 8).

## 2. Verifiable domains

A domain admits a bundle exactly when it supplies five things: configurations, a formal transition relation validated against the real machine, a specification language over traces, a certificate language with a sound checker, and an identity function that ties the verified artifact to the deployed one. The EVM supplies all five; so do several other substrates of critical infrastructure (Section 9). Nothing else about the EVM is used.

Definition 1 (Verifiable domain). A verifiable domain is a tuple

where Σ is the set of full machine configurations; 𝓔 is a family of environment classes, each a set of configurations agreeing on the parameters that make execution deterministic (for the EVM: fork, fee schedule, external code, caller and calldata shape); →M is the transition relation of the real machine and →𝓓 that of the formal semantics, both indexed by an environment class; Obs is the set of externally observable events a trace may emit; Exit is the finite set of terminating statuses; Spec is the set of specifications; 𝓒 is the set of certificates; Check : Spec × B × A × 𝓒 → Res is the checker with Res = Accept(𝓒) ⊎ Refute(CE) ⊎ Unknown as in v2; and id : B → H maps an artifact to the identity under which it is deployed, typically a cryptographic hash of its exact deployed form.

Definition 2 (Specification, domain-parametric). A specification is φ = (Pre, Trace, Post, Exit*) with Pre, Post predicates over Σ, Trace a predicate over traces (sequences of configurations with their Obs events), and Exit* ⊆ Exit. This is v2's Definition 2 with the exit set drawn from the domain. For domains with a single terminating status, Exit* is trivial and the specification collapses to a trace-sensitive Hoare triple.

Definition 3 (Semantic claim). For an environment class E ∈ 𝓔, write →𝓓,E ⊨ φ(b) when every terminating →𝓓,E-trace of b from a configuration satisfying Pre satisfies φ. Termination is guaranteed in gas- or fuel-bounded domains and assumed as partial correctness otherwise; the bundle records which.

Two requirements on the domain are not formal and must be met by evidence. Adequacy: →𝓓,E agrees with →M,E; the standard form of evidence is a conformance suite that both relations pass, strengthened by a second, independently written semantics on which critical properties are cross-checked. Identity: id is injective on the artifacts that can actually be deployed, so that equality of identities is equality of behavior. For bytecode and firmware images this is a collision-resistant hash; for domains that deploy source, the compiler enters the trusted base and the bundle must say so.

The boundary of applicability is unchanged from v2: a task without a correctness predicate (design a profitable protocol, write a fair governance rule) has no φ and admits no bundle. What v3 adds is that within the boundary the format is uniform. A consumer who can check one domain's bundle learns nothing domain-specific to check another's; only the semantics and the checker binary change, and both arrive inside the bundle by hash.

## 3. Trust classes

Every component and every artifact in v3 carries one of three trust statuses, and the bundle makes the status of each part explicit rather than letting the reader infer it. The classes are those of v2; what changes is that they now label data in the bundle as well as components in the pipeline.

 | 

Class | 

Meaning | 

Pipeline components | 

Bundle contents

 | 

U untrusted | 

May behave arbitrarily, including adversarially; nothing it produces is believed until checked | 

Formalizer F, generator G, invariant synthesizer I, any LLM, any symbolic executor producing counterexamples | 

Provenance layer: session ledger, iteration log, generator traces, model attestations

 | 

T trusted-formal | 

Belongs to the formal core; its correctness is an explicit assumption with a named size | 

Check, the certificate checker, the formal semantics →𝓓 | 

Hard layer: b, φ, a, c, the semantics by hash, the checker by hash

 | 

T* trusted non-formal | 

Sole bearer of meaning that no formal artifact can carry; cannot be replaced by a proof | 

Human oracle H | 

Evidence layer: signed approvals of φ, back-translations, mutant witnesses, coverage indicators

The principle governing the table is that a component's output inherits the class of the component only until it is checked. A certificate written by an untrusted synthesizer is U while it is being written and T once Check accepts it, because acceptance is a property of the certificate, not of its author. A counterexample from an untrusted symbolic executor is U until it is replayed under →𝓓, at which point it is a concrete trace and belongs to no class at all: it is simply a fact. The bundle records both the origin and the moment of promotion.

The second principle is that T* material never enters Check. Back-translations, mutant results and approvals are inputs to the human's decision, and the bundle carries them so that the decision is auditable; they are never inputs to the kernel. This is what keeps capability-invariance intact. v2 proved that replacing F, G, I with adversaries leaves soundness unchanged; v3 extends the claim to the evidence and provenance layers. Replacing every piece of evidence in the bundle with fabrications leaves the hard layer's verdict unchanged, and the verdict ladder (Section 6) is designed so that such fabrication can only lower a bundle's reported level, never raise it.

A consequence for the question of why the generator chose what it chose: the answer, in whatever form it is recorded, is U. Mechanistic traces of an open-weight model, attribution over the specification, ranked alternatives and counterfactual re-runs are useful to the human who must judge φ and to the engineer who must improve completeness, and they are placed in the provenance layer for exactly those readers. They have no bearing on acceptance and the bundle format forbids them from acquiring one.

## 4. The proof-carrying bundle

A bundle is the complete set of inputs to Check, plus the instantiated trusted base and the evidence on which the human oracle acted, bound into one content-addressed object. Nothing in it is a verdict; verdicts are recomputed by whoever holds it.

Definition 4 (Bundle). A bundle over a verifiable domain 𝓓 is

where b is the artifact in its deployed form; φ the specification; a ∈ A_chk the checked annotations; c ∈ 𝓒 the certificate; T̂ the instantiated trusted base; V the evidence layer; and P the provenance layer. The first four are the hard layer. T̂ is the data form of v2's Assumptions 1–6: the hash and version of the formal semantics, the environment class E as a machine-readable description, the exact Aasm facts with their justifications, the identity id(b), the satisfiability witness for Pre, and the hash of the certificate checker itself. V and P are described in Sections 7 and 8.

Structure. The bundle is a Merkle DAG, not an archive. Each component is a node addressed by the hash of its content; the manifest is the root and holds, for each child, its hash, its trust class and its media type. Three properties follow. A consumer may fetch a subset of nodes and verify them against the root without fetching the rest, so a kernel check needs b, φ, a, c, T̂ and the checker and nothing else. Any change to any component changes the root, so a bundle cannot be edited after signing. And identical components across bundles deduplicate, so the formal semantics of a domain, several megabytes, is stored once per consumer and referenced by every bundle in that domain.

Only the left column is an input to the checker; the manifest records a trust class for every child so that a reader cannot mistake evidence or provenance for proof.

Signatures. The root is signed by the producer. The approval of φ inside V is signed separately by H. These are different keys with different meanings: the producer's signature says this is what I assembled; the oracle's signature says this specification is the one I accepted as the meaning of the intent. A bundle whose root signature is valid but whose approval signature is missing or belongs to the producer is well-formed and reports as such on the ladder: the hard layer stands, the T* layer does not.

The checker travels with the bundle. T̂ includes the source and hash of a certificate checker for 𝓓 that is small enough to audit and self-contained enough to build from the bundle alone. For a kernel-based domain this is an exported-declaration checker of a few thousand lines, not the proof assistant that produced the declarations; for an SMT-based domain it is a proof-format checker, not the solver. The bundle therefore does not depend on the continued existence, availability or compatibility of the producer's toolchain. The consumer builds the checker, confirms its hash matches T̂, and runs it. A bundle that can only be checked with tools outside itself is not self-contained and is reported as such.

What is deliberately absent. The bundle does not contain the generator, its weights, its prompts in trusted form, or any claim about the quality of the generation process. Those belong to P, are informative, and are discussed in Section 8. The bundle also does not contain the human's reasoning for approving φ, only the fact and the inputs. v2's position that H cannot be replaced by a formal artifact is preserved by not pretending to formalize H.

## 5. Re-verifiability

The central result of v3 is modest in proof and large in consequence: a bundle is sufficient for a third party to recompute acceptance, and two of v2's seven assumptions become mechanical checks on the way.

Proposition 1 (Re-verifiability). Let β = (b, φ, a, c, T̂, V, P) be a bundle over 𝓓 and let Check′ be any checker satisfying Assumption 3 for 𝓓 whose hash matches the one in T̂. Then Check′(φ, b, a, c) = Accept(c) if and only if the producer's Check did, and the verdict is computable from β alone.

Proof. Check is a decidable, syntactic procedure on its inputs (v2, Definition 3), and all four inputs are components of β. Two sound checkers agree on acceptance because acceptance of a certificate is a property of the certificate relative to the semantics in T̂, which is also fixed by hash. No component of the proof references F, G, I, the session, or any material outside β. ∎

The proposition is trivial, and its triviality is the design goal: if re-verification required anything not in the bundle, the bundle would be incomplete. The engineering content is in making the inputs genuinely self-contained, which is what Section 4 specifies.

Theorem 1 (Soundness, transported). Under v2's Assumptions 1–3 and 5–7 instantiated by T̂, and with Assumption 4 discharged as below, if Check′(φ, b, a, c) = Accept(c) for a bundle β then every real →M,E-trace of the deployed artifact from a reachable Pre-configuration satisfies φ.

Proof. As in v2, Theorem 1, with the checker replaced by Check′ via Proposition 1 and the deployed artifact identified with b by the identity check below. ∎

### Assumptions that become checks

v2 listed artifact identity (Assumption 4) and environment adequacy (Assumption 2) as assumptions because the process ended before deployment. The bundle outlives deployment, so the consumer is in a position to verify both.

Identity. T̂ contains id(b). The consumer computes id of the artifact actually present in the deployment target (the code at an address, the image in a partition, the module in a loaded table) and compares. For the EVM this is keccak of the runtime bytecode at the address against the constant in the Lean or K development, with the constructor and immutables handled as T̂ specifies. Inequality is not a weaker verdict; it is a different artifact, and the bundle says nothing about it. This turns the assumption v2 flagged as a frequent practical failure into the cheapest check in the ladder.

Environment. T̂ encodes E as data: chain identifier and fork, fee schedule version, assumptions on callers and external code, precompile set, resource limits. The consumer compares it with the live deployment environment. A mismatch does not invalidate the proof; it invalidates the transfer from →𝓓 to →M for that deployment, and the ladder reports exactly that. A bundle proven under one fork and consumed under another is a proof about a machine that no longer exists.

What stays an assumption. Adequacy of the semantics (Assumption 1) and soundness of the checker (Assumption 3) cannot be checked by the consumer; they are the irreducible trusted base. T̂ names them with hashes and sizes so that the consumer knows exactly what they are trusting and can substitute an independently audited semantics or checker of the same hash. Specification well-formedness (Assumption 6) is partly checkable: T̂ carries a satisfiability witness for Pre, which the consumer replays. Reachability of that witness in the deployment remains judgement. Annotation discipline (Assumption 5) is checkable in that every Aasm fact must be listed in T̂; the justification of each is not.

## 6. The verdict ladder

A bundle is never summarized by one bit. The consumer's verifier reports a level per layer, and the levels are ordered so that each is a strictly stronger statement than the one below, with a change of kind at L2: below it the statements are mechanically decided, above it they are evidence for a judgement.

 | 

Level | 

Statement | 

Decided by | 

Trust class

 | 

L0 | 

Root hash and signatures valid; id(b) equals the deployed artifact; E matches the deployment | 

Hash comparison | 

—

 | 

L1 | 

Check′ accepts c; no admitted holes; only the domain's standard axioms used; checker hash matches T̂ | 

Certificate checker | 

T

 | 

L2 | 

Every requirement of the informal specification maps to ≥1 clause of φ; every clause maps back; back-translation of φ agrees with the informal text; known-bad mutants are refuted; Pre witness replays | 

Tools run by the consumer, judged by H | 

T*

 | 

L3 | 

H's approval of this exact φ is present and signed; the approved version is the proven version | 

Signature + hash equality | 

T*

 | 

L4 | 

P is present, internally consistent, and the tool invocations it records replay to the hashes it claims | 

Replay of U tools | 

U

L0 and L1 are the hard layer and are the only levels that correspond to a theorem. A consumer who stops at L1 holds a kernel-checked proof that the deployed artifact satisfies φ under the stated trusted base, and knows nothing about whether φ is the right specification. That is a complete and honest position.

L2 and L3 concern the single non-formal gap. L2 reports that the tools which help a human judge alignment were run and what they returned; it does not report that alignment holds, because no tool can. L3 reports that a human took responsibility for exactly the φ that was proven, by signing its hash. The distinction between proven φ and approved φ is a real failure mode: a specification is approved, then weakened during synthesis to make the proof go through, and the weakened version is what ships. L3 fails in that case even though L1 passes.

L4 concerns provenance and is strictly informative. A bundle at L4 tells the consumer how the artifact came to be and lets them replay the deterministic parts of that history. It adds nothing to the correctness claim and the ladder's ordering encodes that: no combination of provenance can lift a bundle past L1 without L2 and L3, and fabricating provenance can only cause L4 to fail.

Monotonicity. The ladder has the property that adding fraudulent material to a bundle can lower its level and never raise it, because every level is decided by recomputation or by signature verification against keys the consumer chooses to trust. This is the bundle-level form of capability-invariance: the producer may be arbitrary, and the only thing an arbitrary producer can do to the verdict is make it worse.

Reporting. The verifier emits the ladder as structured output alongside the hashes it compared and the axioms it found, so that a second tool or a model can read the result without re-running the check. A consumer-facing summary that collapses the ladder to a single mark is a misrepresentation of the bundle and the reference verifier does not produce one.

## 7. The evidence layer

The evidence layer V exists because a correct proof of the wrong specification is the dominant failure mode once the hard layer is in place. V does not close the gap between φ and intent; it makes the human's closing of it inspectable and gives the human instruments that reduce the chance of a false approval. Everything in V is produced by untrusted tools and consumed by H.

Coverage matrix. The informal specification n is split into numbered requirements. Each clause of φ carries references to the requirements it is meant to express; each requirement lists the clauses that express it. A tool checks the matrix is total in both directions. A requirement with no clause is a declared blind spot (v2, Corollary 1) and is listed as such; a clause with no requirement is either a strengthening the human should know about or a leak of implementation detail into the specification.

Blind back-translation. An untrusted model that has not seen n translates each clause of φ into natural language. A second step compares the translation with the requirement it references. Disagreement is reported, not resolved; the human decides. The method is cheap and catches the common autoformalization errors of quantifier scope, off-by-one boundaries and silently dropped conditions, which are invisible in the formal text to a reader who already believes they know what it says.

Mutant witnesses. For each clause, V contains at least one artifact b′ that violates the intended property together with a Refute(ce) from Check or a concrete trace under →𝓓 showing the violation. A clause that no mutant violates is vacuous or too weak, which is the caveat v2 attached to Proposition 1. The witnesses are replayable: the consumer runs the trace and confirms the clause fails. This is the only part of V that is mechanically decisive, and it decides weakness, never adequacy.

Non-vacuity witness. A concrete configuration σ₀ ⊨ Pre, replayable by the consumer, so that the guarantee is known to quantify over a non-empty set.

Versioned approval. The specification is versioned. Each approval by H is a signature over the hash of a specific version and the hash of the requirement list it was checked against. The bundle carries the chain of versions from the first the human saw to the one that was proven. L3 requires that the last approved hash equals the proven hash; the chain lets an auditor see what changed between approvals and whether a weakening happened after the last one.

Coverage indicators. v2's Definition 6 and its companion metrics (mutation score, obligation coverage, exit-status coverage, boundary coverage, adversarial-property checklist) are reported as numbers with their computation method named. None is a completeness measure and the bundle labels each as a heuristic. Their value is comparative: two bundles for the same requirement list can be ranked, and a drop between versions is a signal.

What the evidence layer refuses to contain. V does not contain a claim that φ matches n, in any form, from any tool. A model's statement this specification captures the intent is an opinion of a U component about a T* question and has no place in the bundle outside the provenance layer. The design accepts that this makes V look weaker than a confident summary would; it is weaker, and that is the point.

## 8. The provenance layer

The provenance layer P records how the bundle came to exist and is the only place the generation session appears. It is informative by construction: nothing in P is an input to Check, to the ladder below L4, or to the human's approval of φ as a formal matter. Its readers are auditors reconstructing a decision, engineers improving specification completeness, and future producers reusing a lineage.

Iteration log. v2's process (Definition 5) runs up to Kmax iterations and discards everything but the accepted one. P keeps the sequence: for each k, the hashes of b_k, a_k and c_k, the checker's result, and for Refute the counterexample ce_k. This record is a direct input to specification completeness. Every Refute shows a path φ constrains; every Unknown shows a region where the checker could not decide, and Unknown regions are the natural candidates for both a stronger annotation and a missing requirement. v2 identified completeness as the central open problem; the iteration log is the cheapest data source for it and v2 threw it away.

Session ledger. Every tool invocation during the session (compiler, test runner, symbolic executor, checker, formatter) is recorded as an event with the hashes of its inputs, its outputs and the tool's own identity. The ledger is append-only and hash-chained. L4 replays the deterministic events and confirms the hashes. Generator outputs are recorded as events too but are not replayed; the model is not reproducible and the bundle does not pretend it is. The ledger answers what ran, on what, and what came out, which is the question an auditor asks first.

Decision records. At each design decision the producer deems significant, P holds a record: the alternatives considered, the one taken, and the evidence that discriminated them. The evidence must be a reference into the ledger (a test that failed on the alternative, a counterexample, a checker result), not prose. A decision record whose only support is the generator's stated reasoning is permitted but tagged as unsupported. This is where the answer to why this and not that lives, and the format forces the answer to point at a fact or admit it cannot.

Generator attestations. For a closed-weight generator: the provider's signature over model identifier, input hash, output hash and sampling parameters, when the provider offers one. For an open-weight generator: the weight hash, tokenizer hash, inference configuration and hardware fingerprint needed to reproduce activations. Neither says anything about correctness. Both say which untrusted component produced a given output, which matters when a defect is traced back and a producer wants to know whether to stop using a model.

Interpretability traces. For open-weight generators, P may carry compressed mechanistic records at decision points: sparse feature activations, attribution graphs for the token at which a decision was made, and counterfactual interventions showing that suppressing a feature changed the output. For any generator it may carry input attribution: which requirements of n, when removed, flip the decision. These are the most informative and least trustworthy objects in the bundle. Feature labels are themselves generated by a model; the faithfulness of a reasoning trace to the computation that produced it is not guaranteed; and none of it can be replayed by a consumer without the weights. P tags each trace with its reproducibility class and the ladder never reads them. Their value is to the human reviewing a decision record and to the engineer asking why a model keeps weakening the same clause.

Specification lineage. The chain of φ versions, with the ledger events between approvals. Together with the versioned approvals in V, this makes visible the moment a specification was weakened to admit a proof, which is the failure L3 is built to catch and P is built to explain.

The resolution of the auditability tension. v2's capability-invariance says the generator's internals do not matter. The practical demand for an answer to why says they do. Both are right about different questions. The internals do not matter to acceptance, and P is kept out of the hard layer so that remains true. They matter to the humans who must decide whether φ is right and whether the process should be trusted again, and P is kept in the bundle so they can be examined. The format's job is to keep the two readers from confusing each other's questions.

## 9. Instantiations

The EVM is the reference instantiation because it is the easiest: deterministic once the environment is fixed, gas-bounded, with an executable semantics validated against an official conformance suite and a second independent semantics for cross-checking. The table lists it beside other substrates of critical infrastructure that supply the five parameters of Definition 1, with the point at which each departs from the EVM case.

 | 

Domain | 

Configurations and environment | 

Exit statuses | 

Certificate and checker | 

Identity id(b) | 

Where it differs from the EVM

 | 

EVM bytecode | 

World state, tx and block parameters, fork, fee schedule, external code | 

halt, revert, oog, exc | 

K proof object or exported Lean declarations; external kernel checker | 

keccak of runtime bytecode at the address, constructor and immutables handled per T̂ | 

Reference case

 | 

WebAssembly modules | 

Linear memory, tables, globals, host imports as environment | 

trap, return | 

Proof terms over a mechanized Wasm semantics; kernel checker | 

Hash of the binary module | 

Host imports are the environment; E must enumerate their contracts, and adequacy evidence is per host

 | 

eBPF programs | 

Kernel context struct, maps, helpers as environment | 

exit code, reject | 

Proof that the program satisfies a property stronger than the in-kernel verifier's; kernel checker | 

Hash of the bytecode as loaded | 

The deployment target already runs a checker; the bundle's claim must be stated relative to it, not instead of it

 | 

Zero-knowledge circuits | 

Witness and public inputs; the constraint system is the artifact | 

satisfied, unsatisfied | 

Proof that the constraint system is equivalent to a reference function (soundness and completeness of the circuit) | 

Hash of the verifying key or constraint system | 

Both directions matter: an under-constrained circuit accepts bad witnesses and is the common defect; Trace is trivial, Pre/Post carry everything

 | 

Firmware for a fixed ISA | 

Registers, memory, device state as environment; interrupts as events | 

halt, fault, loop | 

Proof over an executable ISA semantics; kernel checker | 

Hash of the image in the partition | 

Termination is not bounded by fuel; the bundle records partial correctness and names the liveness assumption

 | 

PLC safety logic | 

I/O image, timers, cycle | 

end of cycle, fault | 

Proof of cycle invariants over a semantics of the control language | 

Hash of the compiled program on the controller | 

Properties are invariants over an unbounded run of bounded cycles; Trace carries the interlock discipline

Two observations cut across the rows. First, the dimension along which domains vary most is the environment class E, not the semantics; the bundle's decision to encode E as data the consumer compares with the deployment (Section 5) does the most work outside the EVM. Second, in every row the checker that travels with the bundle is smaller than the tool that produced the certificate, and in every row the deployed form of the artifact has a canonical hash. These two facts are what make the format uniform.

The EVM instantiation of v2 is recovered by taking 𝓓 to be the first row, Exit = {halt, revert, oog, exc}, E parameterized by fork and fee schedule, and Check backed by the formal semantics validated in v2's Assumption 1. Every definition and result of v2 is then a special case of Sections 2–6.

## 10. Threats and limits

The bundle shrinks the trusted base and moves most of it into data; it does not remove it. The following are the ways a bundle at L1 can accompany a defective artifact, and what the format does about each.

Wrong specification. The dominant risk, unchanged from v2. A proof of φ says nothing about ψ ∉ closure(φ). The format's response is L2 and L3: tools that make a wrong φ more visible and a signature that makes a human responsible for it. It cannot do more, and a bundle that claimed to would be lying.

Semantics mismodels the machine. Assumption 1 is validated, not proven. A property true under →𝓓 and false under →M is undetectable from inside the bundle. Mitigation is cross-checking critical clauses against a second semantics with no shared code and recording both checker hashes in T̂. A consumer who distrusts a semantics can substitute another of the same interface and re-run; the bundle format makes that substitution a hash change, not a reconstruction.

Checker unsoundness. Assumption 3. The bundle ships a small checker precisely so that this assumption is auditable; a consumer who audits it once trusts every bundle in the domain. A bug in the checker that accepts a malformed certificate is caught by running a second independent checker of the same format, which the bundle's content addressing makes cheap.

Custom axioms and admitted holes. A certificate may introduce an axiom that makes everything provable. L1 requires the checker to enumerate the axioms used and compare against the domain's standard set, and to reject any admitted obligation. This is a mechanical check and the single most common defect in machine-generated proofs; it is listed under threats because a verifier that omits it passes bundles that prove nothing.

Artifact substitution. The bundle is about b; the deployment holds b′. L0 catches this when the consumer actually computes id of the deployed artifact rather than trusting a hash the producer supplied. The threat is procedural: a verifier that reads id(b) from T̂ and compares it with id(b) from T̂ passes everything.

Environment drift. A proof under fork f consumed under fork f′. L0 catches a declared mismatch. An undeclared one, where E in T̂ is silent about a parameter that changed, is a specification-completeness failure in T̂ rather than in φ, and the mitigation is the same: enumerate what E must mention per domain and reject T̂ that omits a required field.

Cross-artifact properties. A bundle is about one artifact. Reentrancy across two contracts, storage collision under delegated calls, a firmware image and the bootloader that loads it: none is in any single φ unless the environment models the other party explicitly. The format allows a bundle to reference another bundle by root hash as part of its E, which lets composed guarantees be stated, but composition is not automatic and v3 does not provide a composition theorem.

Forged evidence and provenance. V and P can be fabricated by the producer. The ladder's monotonicity guarantees this cannot raise the reported level; it can still mislead a human reading P. The defence is the rule that decision records must reference ledger events, and that ledger events replay; a fabricated chain of events that replays to the claimed hashes is a real chain of events.

What the bundle does not claim. It does not claim the artifact is secure, only that it satisfies φ. It does not claim φ is complete. It does not claim the generator is good, or that its reasoning was sound, or that its traces are faithful. It does not claim economic or game-theoretic properties of the system the artifact participates in. It does not claim anything about an artifact whose identity differs from id(b) by one byte. Each of these is a sentence in the manifest's not_claimed field, present in every bundle, because the absence of a claim is the thing a reader is most likely to miss.

## 11. Changes from v2 and open problems

v3 keeps every definition, assumption and result of v2 and changes where they live. The table lists each change and the section that carries it.

 | 

v2 | 

v3 | 

Section

 | 

EVM configurations, forks and fee schedules in the definitions | 

Verifiable domain 𝓓 as a parameter; EVM as its reference instantiation | 

2, 9

 | 

Process returns (b, φ); certificate discarded | 

Process returns bundle β; certificate, annotations and trusted base retained | 

4

 | 

Soundness relative to the producer's checker | 

Re-verifiability: any sound checker of the same hash recomputes acceptance from β alone | 

5

 | 

Assumption 4 (artifact identity) | 

Mechanical check at L0 against the deployed artifact | 

5, 6

 | 

Assumption 2 (environment adequacy) | 

E encoded as data in T̂ and compared with the deployment at L0 | 

5, 6

 | 

Refute(ce) consumed and discarded | 

Iteration log in P; counterexamples and Unknown regions kept as completeness signal | 

8

 | 

One φ, approved once | 

Versioned φ; each approval a signature over a hash; L3 requires approved hash = proven hash | 

7

 | 

Trust classes label components | 

Trust classes label bundle contents; verdict ladder reports each layer separately | 

3, 6

 | 

Heuristic coverage proxy | 

Same proxies, reported in V with method, explicitly comparative | 

7

 | 

Generator internals out of scope | 

Generator internals in P, informative only, with the auditability tension resolved by layer separation | 

8

Open problems.

Composition. A bundle is about one artifact. A composition rule that derives a bundle for a system from bundles of its parts, with E of each referencing the others by root hash, is the natural next result and is not provided here. The difficulty is not the proof but the specification language: cross-artifact Trace predicates have no agreed form.

Specification completeness. Unchanged from v2 as the central open problem. v3 contributes data sources (iteration log, Unknown regions, lineage) and no method. A method that proposes candidate clauses from Unknown regions and routes them through V to H would be the first use of the provenance layer as more than a record.

Checker minimality per domain. Proposition 1 assumes a checker small enough to audit. For kernel-based domains this exists; for SMT-backed domains the proof formats are less settled and the checkers larger. A survey of per-domain minimal checkers, with sizes, would make T̂ comparable across domains.

Oracle provenance. L3 verifies that a key signed an approval, not that a person did. Binding a signature to a human act without a trusted intermediary is outside this paper; the format leaves a field for an attestation of the signing context and does not specify its contents.

Evidence standards. V contains back-translations, mutants and coverage numbers with no agreed thresholds. The format reports them; it does not say what is enough. Deployment policies that set thresholds per domain are a separate, policy-level document and should stay separate, since the thresholds will change and the format should not.

Reproducibility of interpretability traces. P tags traces by reproducibility class, and for closed-weight generators the class is not reproducible. A provider-side interface that returns feature activations under a signature without exposing weights would move such traces one class up. Whether any provider will offer it is not a research question.

The narrow claim of v2 was that system soundness is invariant to the generator. The narrow claim of v3 is that this invariance can be carried in an object small enough to check and complete enough to need nothing else. Anyone may write anything; the bundle is how you know what to check, and the ladder is how you know what you have found.
