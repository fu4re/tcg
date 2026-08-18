# Finding 0001 — Reference bundle end-to-end: the first real Accept, a structural Refute, and five conformance controls (gate G2)

- **Date:** 2026-08-18 · **Type:** engineering delivery + e2e measurement (N=1 contract-shaped subject) · **Substrate:** the kompiled KEVM Haskell backend validated in `docs/substrate.md` (Track B, gate G1) · **Decisions:** D1 (canonical claim form), D3 (correct/drain demo pair), D4 (init-time definition), D5 (one shared `classify()` judge)
- **TL;DR:** the `tcg` pipeline produced its first genuine end-to-end certificate on real, hand-authored, contract-shaped claims, on the real prover — no simulated output anywhere below. The CEI-correct storage-debit property proves to **Accept** (exit 0 **and** `#Top`) on the root claim and its guar/frame companions; a frozen bundle **self-verifies** (all 6 verifier steps, exit 0, every node re-proved from the bundle alone); the vulnerable `drain` variant **Refutes** (exit 3) — and, critically, it refutes **structurally** (the reached concrete storage cannot unify with the claimed one), *not* by a violated arithmetic side-condition, so it does **not** fall into the substrate's Refute-looks-like-Unknown trap (D5 / substrate §9). All five `bundle-spec.md` §9 conformance controls behave exactly as required. What is proved is honestly a **smaller safety claim** (the debit SSTORE reaches its post-storage state) than full withdraw-with-external-call functional correctness — stated plainly below — and several things remain **assumed**, chief among them bytecode-identity (a verifier action, not discharged) and the semantics (not vendored in the bundle).

---

## Setup (reproducible)

| | |
|---|---|
| Prover | `kprove` (Haskell backend), invoked once per goal claim by `tcg prove` / `tcg verify` replay |
| Definition | `/Users/akkedeline/toolchains/kevm-1.0.678/haskell` (the prebuilt kompiled KEVM copied out in substrate §1); includes `…/evm-semantics-source`, `…/plugin` |
| Toolchain (pinned, `theory/toolchain.lock`) | k `v7.1.337` · kore-exec `0.1.155` · kontrol `1.0.255` · kevm `1.0.678` · foundry `1.2.3` · solc `0.8.35` · z3 `4.16.0` · replay `{retries: 2, timeout_seconds: 3600}` |
| Runner | `PYTHONPATH=<repo> /Users/akkedeline/.pyenv/versions/3.12.2/bin/python3 -m tcg …` (python 3.12.2) |
| Subject | `subject/runtime.bin` = 6 raw bytes `60 46 60 00 55 00` (hand-assembled minimal runtime `604660005500` = `PUSH1 0x46; PUSH1 0x00; SSTORE; STOP`), decoded from `tests/reference/subject/runtime.hex`; `environment.json` = chainid 1 / Shanghai (a real environment, not the null skeleton) |
| Authored claims | `tests/reference/src/{ledger/base,withdraw/main,withdraw/guar,drain/drain}.k` — the human source-of-truth, committed verbatim before any iteration |
| Judge | **the solver, never prose.** Every verdict below is the exact exit code + log of `kprove`, classified by the single shared `tcg.verdict.classify()` (D5) that both `prove` and `verify` use. Accept requires exit 0 **and** `#Top`; Refute requires structural non-unification; anything undecided is Unknown (a refusal) |

Reproduction (both scripts exit 0 iff every stage behaves; env overrides `TCG_PYTHON`, `KEVM`):

```
scripts/build-reference.sh [WORKDIR]   # workspace + bundle + self-verify + drain control
scripts/conformance.sh    [BUNDLE]     # the five bundle-spec §9 controls
```

Artifacts committed under `tests/reference/`: authored `src/`, interface JSONs `iface/`, `subject/`, captured Accept/Refute logs `logs/`, the frozen bundle's `captured/MANIFEST.json` + `graph.json` + `interfaces.json` + `oracle-record.json` + `trust-manifest.json`, `verify.out`, and `logs/conformance.out`.

---

## What was proved, in words

- **`withdraw/main`** (role `loop`, the single **root**, hash `19fed8e2…`): the runtime `604660005500`, run from an initial state whose executing account holds storage slot 0 = 100 (NORMAL mode, DEFAULT schedule, gas accounting off), is an **all-path reachability** claim — *every* path drives the EVM to `#halt` with `statusCode EVMC_SUCCESS`, empty output, `pc` advanced 0 ⟶ 5, and **storage slot 0 debited 100 ⟶ 70** (0x46). In one line: *the debit SSTORE reaches its claimed post-storage state.*
- **`withdraw/guar`** (role `guar`, hash `927c4d49…`): the same debit, carrying an extra slot 1 = 42 that stays 42 — the footprint/frame guarantee (slot 0 written, slot 1 untouched).
- **`ledger/base`** (role `frame`, hash `eb999885…`): the trivial `STOP` program (`00`) halts `EVMC_SUCCESS`. It is declared as a **trusted lemma** of `withdraw`, so proving `withdraw` writes trusted-lemma edges `main → base` and `guar → base` — a real closure structure (see caveat 5).
- **`drain/drain`** (role `loop`, hash `cc0f4c8c…`): the vulnerable ordering, runtime `006046600055` = `STOP; PUSH1 0x46; PUSH1 0x00; SSTORE`. The **leading `STOP` halts the segment at pc 0 before the debit SSTORE ever executes**, so the concrete post-storage stays 100 while the claim asserts slot 0 ⟶ 70. Claimed 70 vs reached-concrete 100 is a **structural** mismatch.

---

## Results

| Stage | Verdict | Exit | Wall | Artifact |
|---|---|---|---|---|
| prove `ledger/base` | **Accept** (`#Top`) | 0 | 15.8s | `logs/ledger-base-accept.log` (exactly `#Top`) |
| prove `withdraw/guar` (1 trusted child) | **Accept** (`#Top`) | 0 | 15.5s | `logs/withdraw-guar-accept.log` |
| prove `withdraw/main` (1 trusted child, ROOT) | **Accept** (`#Top`) | 0 | 15.8s | `logs/withdraw-main-accept.log` |
| `graph check` | OK (3 nodes, 2 edges, 1 root) | 0 | <1s | `captured/graph.json` |
| `freeze` | bundle (15 files, 1 root) | 0 | <1s | `captured/MANIFEST.json` |
| `verify <bundle>` | **Accept** — steps 1–5 pass, 3 nodes re-proved bundle-only | 0 | ~48s | `verify.out` |
| prove `drain/drain` | **Refute** — structural non-unification | 3 | ~15s | `logs/drain-refute.log` |

**Certificate identity:** `sha256(MANIFEST.json) = eccc09597ea6b0d60fc34e8fcdea0a6682b5ba32cc541862745b14247b7ec349` *(this machine — the lock's absolute definition path is inside the hash tree, so the cert hash is machine-local; the four claim hashes above are pure canonical-text SHA-256 and are machine-independent).* Full `build-reference.sh` run (both workspaces): ~1:50 wall.

The `drain` refutation is **structural, not arithmetic** — the point of D5 / substrate §9. Its witness (`logs/drain-refute.log`) opens with `Warning (WarnStuckClaimState): The configuration's term doesn't unify with the destination's term …` (the `TermsNotUnifiableStuck` body → **Refute**), dumps a final config with `<storage> 0 |-> 100 </storage>`, and contains **no** ECRECOVER/Krypto crash trace. It did **not** fall back to Unknown. Had the defect instead been a violated *arithmetic bound* on a reached state, this substrate would (honestly) return Unknown(c), not Refute — that class of defect is not exercised here.

## Conformance (bundle-spec §9)

`scripts/conformance.sh` runs each control against `tcg verify` on an **independent copy** of the frozen bundle (the pristine is never mutated) and asserts the **exact** exit code **and** the step verify reacts at. Captured run: `logs/conformance.out`.

| # | Control (tamper on a copy) | Expected | Actual | Step / message |
|---|---|---|---|---|
| 1 | flip one byte in `subject/runtime.bin` | exit 3 | **3** | `step 1-integrity` — `hash mismatch: subject/runtime.bin` |
| 2 | delete a proved child claim (closure) | exit 3 | **3** | `step 4-graph` — `eb999885a372: claim file missing` |
| 3 | inject a false trusted lemma | exit 3 | **3** | `step 5-replay` — `ledger/base did not replay to Accept (Refute)` |
| 4 | cut `replay.timeout_seconds` to 1 | exit 2 | **2** | `step 5-replay` — `Unknown(b) after 3 attempt(s) — conservative refusal` |
| 5 | delete `bundle/nav/` entirely | exit 0 | **0** | `certificate holds` (unchanged) |

Overall: **5/5**, script exit 0, ~68s. Controls 2/3/4 re-key and re-hash the `MANIFEST` so the tamper survives the step-1 hash tree and the defect surfaces only at its **intended** step — a plain file edit would trip step 1 and never exercise closure/replay, which would make those controls test nothing. Control 2 leaves the graph node *asserting* `base` is proved while its claim artifact is gone (`bundle-spec` §9's "a graph node whose claim file is missing"); control 3 re-keys `base`'s body to a structurally false claim (`STOP` claiming `pc 0 => 999`) so steps 1/3/4 pass and only the replay catches it. Control 4 confirms the Unknown-≠-Refute discipline on the verifier side: a timeout is a **conservative** exit 2, never conflated with the genuine structural Refute of control 3 (exit 3).

---

## What remains assumed / unproved (honest caveats)

1. **Bytecode-identity is a verifier action, not discharged here.** `verify` step 2 only *prints* the instruction to compare `keccak(subject/runtime.bin)` with the on-chain code hash (`trust-manifest.json`: `subject_identity: machine-checkable`). Nothing in this pass touches a chain. The bundle guarantees a property of a *bytecode string*, not that any deployed contract *is* that bytecode.
2. **Semantics not vendored.** `theory/semantics/` is absent; replay uses the local kompiled KEVM, and `verify` step 3 says so (`semantics not vendored — replay uses the local definition; the trust manifest records this as assumed`). The bundle is self-contained for spec/graph/evidence/patches but **not** for the semantics — replaying it needs a machine with the pinned KEVM 1.0.678 on disk. (This contradicts bundle-spec §1's "vendoring, not pinning" ideal; vendoring the semantics release is future work.)
3. **A smaller safety claim than full CEI withdraw.** No `CALL` opcode is exercised. The proved property is "the debit SSTORE reaches its post-storage state" (plus the framed slot in `guar`), i.e. a *storage-effect* safety property of the correct-order bytecode — not withdraw-with-external-call functional correctness. Per the task, a smaller honestly-proved claim was chosen over a grand Unknown. The checks-effects-interactions *ordering* is represented only structurally: in `main` the debit precedes `STOP`; in `drain` a leading `STOP` makes the debit dead code.
4. **Gas off, schedule abstracted.** Proofs run under `<useGas> false` and the DEFAULT schedule; `environment.json` records mainnet / Shanghai intent but the proved segment abstracts the concrete fork's fee schedule. Binding that environment is, again, the verifier's business.
5. **The trusted-lemma edge is a structural closure demonstration.** `withdraw`'s proof does not logically *need* `ledger/base` (a `STOP` fact); `base` is supplied as a trusted lemma so that (a) `main → base` / `guar → base` are real trusted-lemma edges and (b) conformance control 2 is a genuine closure violation rather than the nearest fallback. This is disclosed, not hidden.
6. **Refute reachability is bounded to structural non-unification (D5 / substrate §9).** This delivery's Refute (`drain`) *is* structural and did not degrade to Unknown — but the substrate still under-detects the *arithmetic-postcondition-false* class (it looks identical to an under-specified true claim). Lifting that needs structured counterexample extraction (`kore-rpc` `implies`/`get-model`, or `pyk` `APRProof`), not attempted here.
7. **`tcg` is trusted on the workspace side; the bundle side re-derives.** `prove` trusts the tool that built the workspace; `verify` reads only the bundle (+ the assumed semantics) and re-judges replay with the *same* `classify()` (D5), so a claim is not "more accepted" for having been judged by the workspace tool. The format's structural checks (hash tree, DAG, topological replay) are JSON + SHA-256, re-implementable without `tcg`.
8. **The prior session's `kore-exec-1211.tar.gz`** (the documented ECRECOVER Krypto crash, substrate §5) is kept as scratchpad evidence and deliberately **not** committed. The `drain` refutation in *this* delivery is crash-free.

## Reproduction commands

```
# full workspace + bundle + self-verify + drain refutation control
scripts/build-reference.sh /tmp/refws
#   -> 3 Accepts (#Top), graph check OK, freeze, verify exit 0, drain exit 3

# the five bundle-spec §9 conformance controls, on copies of the bundle
scripts/conformance.sh /tmp/refws/ws/bundle
#   -> 5/5 PASS: exits 3,3,3,2,0

# a single verdict directly, matching the tables above
PYTHONPATH=<repo> python3 -m tcg verify /tmp/refws/ws/bundle
```
