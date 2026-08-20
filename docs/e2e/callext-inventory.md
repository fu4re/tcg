# callext reference — inventory for the composition E2E

Inventory of the existing single-bundle bridge reference (`tests/reference/callext/`)
— the RECURSE branch (`S⟸D`, in-graph D+B) that `COMPOSITION_CONTRACT.md` says we
are NOT changing. This doc records the exact on-disk layout, the graph shape, the
callee bytecode and its provenance, and — the load-bearing question for the linker
E2E — **precisely which pieces re-freeze as a standalone callee bundle and vendor
into `deps/<callee_root>/`, and which must be re-authored.**

Everything below was read on disk at branch `e2e-composition-fixtures`
(fast-forwarded to `main` = `5ab8b94`; the callext reference was added in
`a50ad31`, which post-dates the branch's original base `91da570`). All hex/hash
claims here were recomputed, not copied.

---

## 1. What is (and is NOT) on disk

**Important:** the committed reference is the **workspace INPUTS + scripts + proof
logs**, NOT a frozen bundle. `tests/reference/callext/tcg/{src,iface,subject}` are
the loop bodies, interfaces, and subject that the scripts feed to `tcg init /
subject set / loop new / compile-claims / prove / approve / graph check / freeze`.
The frozen bundle (`spec/graph.json` with the bridge block, `MANIFEST.json`, the
hash tree, `evidence/replay/…`) is **produced into a temp `$WORKDIR/bundle` by
`run-tcg-bridge.sh`** and is not checked in. Section 4 therefore documents both:
the committed source tree, and the frozen-bundle layout `freeze` emits.

### 1a. Committed source tree (`tests/reference/callext/`)

```
tests/reference/callext/
├── README.md                         # the Gap-#1 probe write-up + verdict table + repro
│
├── run.sh                            # raw kprove, all 10 raw/ specs, verdict-checked
├── run-tcg.sh                        # the "before": toy through tcg; graph check REFUSES
│                                     #   (abstract-summary node cannot be Accepted)
├── run-tcg-bridge.sh                 # the "after": bridge discharged -> graph OK, freeze,
│                                     #   verify holds bundle-only  (builds $WORKDIR/bundle)
├── run-tcg-bridge-discriminators.sh  # 5 anti-proxy controls, each MUST be refused (§5)
│
├── raw/                              # raw-kprove form (NOT tcg): hand-written .k specs
│   ├── bridge-s-at-p.k  callee-d.k
│   ├── caller-2a.k  caller-2a-broken.k  caller-2a-nosummary.k  caller-2a-vacuity.k
│   ├── caller-inline.k  caller-drain.k  compat-ok.k  compat-broken.k
│   └── logs/*.log                    # committed raw-kprove output per spec
│
└── tcg/                              # the tcg-pipeline form (what freeze consumes)
    ├── subject/
    │   ├── runtime.hex               # the CALLER bytecode (the subject) — see §2
    │   └── environment.json          # chainid 1, fork Shanghai, external_code[0xC8]=P (§3)
    ├── src/                          # loop bodies (canonical .k claims)
    │   ├── d.k          # D  : +5 over CONCRETE P, top-level (caller 999999999999)
    │   ├── s.k          # S  : ABSTRACT <program> _PGM summary (the bridged node)
    │   ├── sbridge.k    # B  : S re-proved by EXECUTION over concrete P (caller 100)
    │   ├── r2a.k        # ROOT: caller bytecode CALLs symbolic 0xC8; asserts A2[0]=105
    │   ├── guar2a.k     # the caller loop's guar node (own frame A1 untouched)
    │   ├── s6.k sbridge6.k rbroken.k          # broken-summary (+6) discriminator family
    │   ├── s_proxy.k sbridge_proxy.k rproxy.k # proxy-swap (+0 no-op) discriminator family
    │   └── compat_broken.k                    # broken-Rely interference discriminator
    ├── iface/                        # per-loop interface (Pre/Post/Eff/Exit -> claim refs)
    │   ├── iface-callee.json          # D node
    │   ├── iface-summary-bridged.json # S node — CARRIES THE BRIDGE BLOCK (§2)
    │   ├── iface-bridge.json          # B node
    │   ├── iface-caller_2a-bridged.json # ROOT loop: root=r2a, guar=guar2a, trusted=[summary/s]
    │   └── iface-…(bridge6|proxy|broken|compat_broken).json  # discriminator ifaces
    └── logs/                          # committed tcg-prove output
        ├── callee-d-prove.log         # "#Top"  (D Accepts over P)
        ├── caller_2a-r2a-prove.log    # ROOT Accepts (S injected)
        ├── caller_2a_broken-r2a-prove.log
        └── caller_inline-rinline-prove.log  # "#Top"
```

Sibling references under `tests/reference/` (`captured/`, `getters/`, `getters-full/`,
`src/`, `iface/`, `subject/`) belong to OTHER references (the withdraw/ledger e2e and
the getter-coverage work) — NOT callext. `tests/reference/captured/` is a frozen
*withdraw* bundle skeleton (no bridge, no assume), useful only as a shape example.

---

## 2. The graph: caller, callee, S, and the bridge block

The composition `run-tcg-bridge.sh` assembles has **four loops / five claim nodes**:

| loop | claim(s) | role | `<program>` | `<caller>`/`<id>` | verdict | file |
|---|---|---|---|---|---|---|
| `callee`    | `d`       | guar (root:false) | concrete **P** | 999999999999 / 200 | Accept `#Top` | `src/d.k` |
| `bridge`    | `sbridge` | guar (root:false) | concrete **P** | 100 / 200 | Accept (the B leg) | `src/sbridge.k` |
| `summary`   | `s`       | guar (root:false) | **`_PGM`** (abstract) | 100 / 200 | NOT proved — bridge-discharged | `src/s.k` |
| `caller_2a` | `r2a` **(ROOT)** + `guar` | root + guar | concrete caller | 999999999999 / 100 | Accept (S injected) | `src/r2a.k`, `src/guar2a.k` |

- **Caller loop / the subject.** `subject/runtime.hex` = `6000600060006000600060C86000F100`
  — a mini-join at address **100 (`0x64`)**: push the 7 `CALL` args, `CALL` into
  `0xC8`, `STOP`. The ROOT claim `r2a` executes this bytecode; at the `CALL` the
  callee account `200` has a **symbolic `<code> CODE`**, and the root asserts
  `A2.storage[0] == 105` and success flag `1` on the word stack — facts the caller
  never computes itself, closable ONLY by consuming the summary `S` at the CALL.
- **Callee.** Code **P** = `60005460050160005500` installed at address **200
  (`0xC8`)** via `environment.external_code` (§3). The callee is NOT the subject.
- **Abstract-summary node `S`** (`src/s.k`, node `summary/s`): `<program> _PGM`
  (a bare K variable), `<caller> 100`, `<id> 200`, callee `<storage> 0 |-> 100 => 0
  |-> 105`. A free `<program>` can never Accept (a symbolic program stalls), so
  graph closure does NOT demand it — it is discharged by the bridge instead, and is
  injected as a trusted child of `caller_2a` (`iface-caller_2a-bridged.json`,
  `"trusted":[{"loop":"summary","label":"s"}]`).
- **The bridge block** lives on `S`'s claim entry in
  `iface-summary-bridged.json` (and thus on the `summary/s` node in the frozen
  `spec/graph.json`). Verbatim:

  ```json
  "bridge": {
    "callee_address": "0x00000000000000000000000000000000000000c8",
    "code_hash": "a7d0eaef07694abd7dcad44e621c06a9dc7be164317d98d005a14caa63ecf512",
    "concrete_proof":    { "loop": "callee", "label": "d" },
    "at_program_proof":  { "loop": "bridge", "label": "sbridge" }
  }
  ```

  This is the **IN-GRAPH** bridge form the contract describes as "today":
  `concrete_proof` (**D**) and `at_program_proof` (**B**) are `{loop,label}` refs
  resolved to nodes in the SAME graph (`tcg/bridge.py:resolve_ref`). The
  cross-bundle **linker** form (Mechanism A) replaces `concrete_proof` with
  `{"dep":"<callee_root>","root":"<claim_hash>"}` and **omits** `at_program_proof`.

- **`environment.external_code` entry** (`tcg/subject/environment.json`):
  ```json
  "external_code": { "0x00000000000000000000000000000000000000c8": "60005460050160005500" }
  ```
  This is the concrete callee code P, and the fixed point of code-identity.
- **`code_hash`** `a7d0eaef07694abd7dcad44e621c06a9dc7be164317d98d005a14caa63ecf512`
  — **verified**: `keccak256(bytes.fromhex("60005460050160005500"))` recomputed with
  `tcg.keccak` equals it exactly. This is what `tcg/bridge.py:structural_errors`
  recomputes in step 4 (`keccak256(external_code[callee]) == code_hash`, PERFORMED,
  not assumed).

---

## 3. The callee runtime P and its provenance

- **P** = `60005460050160005500` (10 bytes) — a **hand-authored toy**, NOT a
  compiled contract. Opcode-by-opcode (per `callext/README.md`, verified against the
  bytes): `PUSH1 0; SLOAD; PUSH1 5; ADD; PUSH1 0; SSTORE; STOP` — i.e. `slot0 += 5`.
- Provenance: written directly as opcodes for the Gap-#1 probe (a constant `+5`, no
  arithmetic that would need P0 lemmas). It is stored in TWO places that must agree:
  (a) `environment.external_code[0xC8]` (the code installed at the callee address),
  and (b) the `<program>` cell of `d.k` and `sbridge.k`
  (`#parseByteStack("60005460050160005500")`). Code-identity ties them together.
- Contrast the fresh STUB fixture (`tests/reference/composition/opaque/`), which is a
  *real solc-compiled* runtime (121 bytes) — deliberately heavier, because the STUB
  branch's point is that the callee is opaque and un-proved.

---

## 4. Frozen-bundle layout (what `freeze` emits) + REUSABILITY for the linker

`run-tcg-bridge.sh` produces `$WORKDIR/bundle/` in the standard v1 layout
(`docs/bundle-spec.md` §2): `MANIFEST.json`, `subject/{runtime.bin,environment.json}`,
`spec/{claims/<h>.k, interfaces.json, graph.json}`, `theory/toolchain.lock`,
`evidence/replay/<h>.json`, `assumptions/{trust-manifest.json,oracle-record.json}`.
The `summary/s` node in `spec/graph.json` carries the bridge block from §2, and
`trust-manifest.json` gains a `bridge_S_from_D` entry (`docs/bundle-spec.md` §7).

### 4a. The linker target (Mechanism A)

The linker vendors a **full callee bundle** under `deps/<callee_root>/` where
`<callee_root> = sha256(deps/<callee_root>/MANIFEST.json)`, and the caller's summary
node points at it: `concrete_proof = {"dep":"<callee_root>","root":"<dep_root_hash>"}`,
`at_program_proof` omitted. `tcg verify` (per contract) then: recurses into the dep
(post-order), checks `dep_root ∈ dep MANIFEST roots`, recomputes
`keccak256(deps/<callee_root>/subject/runtime.bin) == caller code_hash` AND
`caller environment.external_code[callee] == deps/<callee_root>/subject/runtime.bin`
byte-for-byte, then runs `binding_errors(S_text, D_text=dep_root_text, addr, prefix)`
with the SAME strictness as today.

### 4b. Reusable AS-IS (lift verbatim)

| piece | from | becomes | why it just works |
|---|---|---|---|
| callee runtime **P** `60005460050160005500` | `env.external_code[0xC8]` / `d.k`,`sbridge.k` `<program>` | dep bundle `subject/runtime.bin` | same bytes; also already equals the caller's `external_code[0xC8]` (contract step 3 byte-match) |
| **`code_hash`** `a7d0eaef…` | summary bridge block | caller node `code_hash` | = `keccak256(P)` (verified); verifier recomputes it from the vendored dep subject |
| **environment class** chainid 1 / fork Shanghai / SHANGHAI schedule | `env.json` | both bundles' `subject/environment.json` | callee proofs use `<schedule> DEFAULT`,`<useGas> false`; compatible |
| **`s.k` (S)** | `src/s.k` | caller's summary node claim, verbatim | unchanged; only its bridge block's `concrete_proof` shape changes (dep/root) |
| **`r2a.k` + `guar2a.k`** | `src/` | caller subject root + guar, verbatim | root `<program>` already binds to the caller subject |
| the **B claim `sbridge.k`** | `src/sbridge.k` | the **dep bundle's ROOT** (re-cast `root:true`) | see 4c — it is the tight execution proof over P that binds to S |
| the whole **discriminator set** | §5 | templates for the linker discriminators | one-to-one mapping in `docs/e2e/composition-matrix.md` |

### 4c. The one non-obvious call: the dep ROOT must be **B-shaped, not D-shaped**

The contract says the dep's `concrete_proof.root` "plays the role of both D and B"
and that the verifier runs `binding_errors(S_text, D_text)` against it with today's
strictness. Concretely, **`d.k` (the `callee/d` node) is NOT directly reusable as the
dep root**, because `binding_errors(S, d)` would REJECT it:

- `d.k` pins `<caller> 999999999999`; `S` pins `<caller> 100` → *entry differs* error.
- `d.k` pins `<gas> 100000`, `<callGas> 0`, `<callDepth> 0`, `<codeAddr> 200`
  (concrete literals) that `S` frames → *"bridge proof must be at least as general as
  the summary at entry"* errors.

The claim that DOES bind is **`sbridge.k` (B)**: `<caller> 100` (== S), cells framed
where S frames, callee `<storage> 0 |-> 100 => 0 |-> 105` (== S's delta), `<program>`
== P. That is exactly the S⟺B binding already green in the in-graph bridge. So the
reusable proved artifact for the dep root is **`sbridge.k`**, promoted to `root:true`
over a subject == P. (`sbridge.k`'s `<program>` = `#parseByteStack("60005460050160005500")`
= P, so it also satisfies root program-binding in the callee bundle.)

### 4d. Needs RE-AUTHORING (not liftable)

- **The callee workspace itself.** Build a standalone workspace: `subject set
  --runtime P`, one loop whose ROOT is the `sbridge`-shaped claim, `prove`, `approve`,
  `freeze` → the callee bundle. In callext the subject is the CALLER, and `d`/`sbridge`
  are `root:false` guar nodes — so the callee bundle's subject + a root marking are new.
- **The cross-bundle bridge schema + product code.** `tcg/bridge.py:resolve_ref`
  resolves ONLY `{loop,label}` within one graph; `{dep,root}` resolution, the
  post-order **dep recursion**, and code-identity against
  `deps/<root>/subject/runtime.bin` are UNBUILT (contract Mechanism A, verify steps
  1–5). `tcg verify` today does NOT read `deps/`. **NOT built here** — the E2E
  verdicts for these rows are "to be produced in the join step."
- **The vendoring/copy step.** Copying the frozen callee bundle into the caller's
  `deps/<callee_root>/` and hash-linking every file into the caller MANIFEST is the
  linker's job — UNBUILT.
- Everything the STUB branch needs is separate (`assume` node, `--strict`,
  `A_callee_*` ledger entry, `tcg roots` author-assumption surfacing) — also UNBUILT;
  see the fixture in `tests/reference/composition/opaque/`.

---

## 5. The discriminator harness — invocation and assertions

`tests/reference/callext/run-tcg-bridge-discriminators.sh [WORKROOT]`
(env: `KEVM` default `~/toolchains/kevm-1.0.678`, `TCG_PYTHON`, `REPO`). It builds one
**GOOD** bundle once (`init → subject set → 4 loops → prove callee/bridge/caller_2a →
vacuity → approve → graph check → freeze → verify`, baseline `verify` expected exit
**0**), then runs five controls. Each is asserted via `expect <want_rc> <got_rc>` and
the script exits non-zero if any fails. All verdicts come from the solver (the bridge
legs) or the bundle-only structural checks — never from prose.

| # | discriminator | tamper / setup | catch | expected |
|---|---|---|---|---|
| 2 | **wrong-code-identity** | copy GOOD bundle; set `external_code[0xC8]` := `600154600501600155` (P′); rehash `MANIFEST` | `verify` step 4: `keccak256(P′) ≠ code_hash` (`bridge.py:structural_errors`) | `verify` exit **3** |
| 4 | **undischarged** | copy GOOD bundle; strip the `bridge` block off the summary node; rehash `MANIFEST` | node is no longer an abstract-summary node → step 4 demands replay evidence S can never have | `verify` exit **3** |
| 1 | **broken-summary (+6)** | fresh workspace with `s6.k`/`sbridge6.k`/`rbroken.k` | `prove bridge6` **Refutes** over P (+6 ≠ +5) → `graph check` refuses (S's B leg not Accepted) | `bridge6` Refute (3) + `graph check` **3** |
| 3 | **proxy-swap (+0 no-op)** | fresh workspace with `s_proxy.k`/`sbridge_proxy.k`/`rproxy.k` | `prove bridge_proxy` **Refutes** over P (no-op ≠ +5) → `graph check` refuses | `bridge_proxy` Refute (3) + `graph check` **3** |
| 5 | **compat-broken** | fresh workspace with `compat_broken.k` | interference obligation **Refutes** (caller relies on A1[1]=999 the callee never provides) | `prove` Refute (**3**) |

Related runners: `run.sh` (raw kprove over the 10 `raw/` specs, verdict-checked);
`run-tcg.sh` (the Finding-0005 "before": `graph check` REFUSES because the abstract
summary cannot be Accepted); `run-tcg-bridge.sh` (the "after": honest bundle freezes
and `verify` holds bundle-only, exit 0). These require the kompiled KEVM definition
(`~/toolchains/kevm-1.0.678`); they were NOT re-run for this inventory — the committed
logs (`tcg/logs/*.log` show `#Top`) and `callext/README.md`'s verdict table are the
evidence cited, and every fresh verdict in the E2E is a real run per ground-rule 1.
