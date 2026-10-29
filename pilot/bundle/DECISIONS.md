# Bundle pilot — decisions D1–D11

- **Status:** DRAFT 2026-10-29, awaiting the author's review. Not committed (pilot rule: nothing is committed until the author orders the commits). Its sha256 + UTC time is ledger event #1, and the oracle signs it once the oracle key exists (stands in for the timestamped commit task 00 asked for).
- **Source of truth:** TCG v3, https://claude.ai/artifact/57GjxDSW4qC8aqEiwnX3Jo (rev 14), local snapshot `tasks/bundle_pilot/tcg_v3_snapshot.md`.
- **Rule:** a producing agent that meets a question not settled here refuses to assemble and records the question. It does not guess.

| # | Decision | Chosen | Why |
|---|---|---|---|
| D1 | Content hash | sha256 over raw bytes, lowercase hex | stdlib, and the same hash the tcg v1 bundle already uses |
| D2 | Addressing | Merkle DAG. `manifest.json` is the root and lists each child by `path` + `hash` + `class` + `media` + `role`. Children are plain files in the bundle directory. No archive. `root_hash` = sha256 of the canonical JSON (sorted keys, no whitespace, UTF-8) of the manifest with `root_hash` and `producer_sig` removed | v3 §4: "a Merkle DAG, not an archive". Canonical JSON makes the root recomputable |
| D3 | Producer signature | ed25519, raw 64-byte signature over the ASCII hex of `root_hash`. Signed with `openssl pkeyutl -sign -rawin` (OpenSSL 3.x). Verified in the verifier by a stdlib-only RFC 8032 implementation, cross-tested against openssl | keeps the verifier stdlib-only, so no crypto binary goes in `outside_bundle` |
| D4 | Oracle signature (H) | separate ed25519 key, held by the author only, never readable by any agent. Signs the ASCII string `sha256(phi.json) ‖ sha256(requirements.md)` (two 64-char hex digests concatenated, 128 chars) | v3 §4: different keys, different meanings |
| D5 | Who is H | the author, personally | v3 §3: H is T*, not replaceable by a formal artefact |
| D6 | Check′ for KEVM claims | variant A: pinned KEVM docker image (linux/amd64, `kprove` + the kompiled `kevm-1.0.678-lemmas2` definition baked in), identified by **image digest**, never by tag. Bundle reports `self_contained: false`. Variant B (Lean over EVMYulLean) is tried for ≥1 claim | the only checker that exists today. The K prover emits no proof object. `definition.kore` is not byte-deterministic across kompiles, so the consumer pulls the exact artefact by digest and does not rebuild it |
| D7 | Check′ for Lean | `lake build` under the toolchain in `lean-toolchain`. `#print axioms` for each theorem must be ⊆ {propext, Classical.choice, Quot.sound}. Any `sorry`/admit/custom axiom → reject | v3 §10, custom axioms and admitted holes |
| D8 | Identity id(b) | keccak256 of GemJoin ETH-A runtime bytecode at `0x2F0b23f53734252Bda2277357e97e1517d6B042A`, read by the verifier from the chain at the pinned block (expected `0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa`, 3462 bytes). Constructor and immutables: none, runtime only. NB: task 03's address is a typo | v3 §5, Identity |
| D9 | Environment for L0 | primary: `--rpc` to an archive node, `eth_getCode(addr, block)` + `eth_chainId` + block header at the pinned block. Fallback: `--state-snapshot` that the **consumer** obtains independently. A snapshot is never a child of the bundle | a snapshot shipped inside the bundle would let the bundle vouch for its own identity (v3 §10, artifact substitution) |
| D10 | Trust-class labels | `U`, `T`, `T*` exactly as v3 §3. Hard layer + T̂ + checker = `T`, evidence = `T*`, provenance = `U`. The manifest itself carries no class | v3 §3 table |
| D11 | `not_claimed` | the **five** sentences of v3 §10 "What the bundle does not claim", verbatim (task 00 says "six"; §10 has five) | v3 §10: "Each of these is a sentence in the manifest's not_claimed field" |

## Pilot-specific decisions (recorded so they are not taken silently)

| # | Decision | Chosen |
|---|---|---|
| P1 | Claim set (5) | `vat()`, `ilk()`, `gem()` full getters (reproducible from `tests/reference/getters-full/`, Finding 0003b) + two G4 revert roots **rebuilt** from Finding 0003's description: `cage()` reverts for every caller when `wards` is empty; `join(usr,wad)` reverts for every caller when `live==0`, before any external call. The rebuild is new content, which task 02 forbids, and is recorded in `provenance/decision-stub.md` |
| P2 | Certificates under A | zero real certificates: all 5 claims go in `claims_without_certificate`. The K simplification lemmas (`theory/patches/lemmas.diff`, Findings 0004/0006) go in `a` and in T̂ (`A_simp_lemmas`) |
| P3 | Hard layer source | derived from a tcg v1 frozen bundle (`tcg freeze`) by `pilot/tools/assemble.py`. No hand-written hard-layer content beyond P1's two claims and `requirements.md` |
| P4 | Commits | none during the pilot. The author orders the commits afterwards |
| P5 | Consumer isolation (task 07) | VM `tcg`, a separate unix user with no read access to `/home/vladimir/sheaf`. Consumer agent B = fresh `claude -p`, given only bundle + verifier source + two pubkeys + RPC URL |
