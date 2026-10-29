# Bundle formats read by the verifier (tcg-bundle/0.1)

What `pilot/verifier/` reads, field by field. A real bundle that follows this page plugs into the verifier unchanged. The toy bundle in `pilot/verifier/tests/fixtures/toy_bundle.py` is a working instance of every format here.

## Producing a bundle
`python3 pilot/tools/assemble.py <bundle> --check` (plan only) / `--key <producer.pem>` (write and sign). It assigns role, class, media and claim ids by the rules in its docstring. It refuses, writing nothing, if a file matches no rule, a D1–D11 row is missing from `DECISIONS.md`, a required role is missing, a cross-reference is stale, the ledger chain is broken, or the manifest fails lint. Working notes such as `HARD_STATUS.md` must therefore live outside the bundle directory.

## Manifest: `manifest.json` (bundle root, not itself a child)
- Schema: `manifest.schema.json`. Linter: `python3 pilot/tools/lint_manifest.py <bundle>/manifest.json` (exit 0 = no form problem).
- `root_hash` = sha256 of canonical JSON of the manifest without `root_hash` and `producer_sig` (D2). Canonical JSON = `json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`, no floats.
- `producer_sig.sig` = hex of the raw 64-byte ed25519 signature over the ASCII hex of `root_hash` (D3): `printf %s <root_hash> > m; openssl pkeyutl -sign -rawin -inkey producer.pem -in m -out sig`. `pubkey` = hex of the raw 32-byte key. The verifier checks the signature against the key the **consumer** supplies, and requires the manifest's `pubkey` to equal it.
- Roles → class (D10, enforced): `b, phi, a, c, T_hat, checker` → `T`; `V` → `T*`; `P` → `U`.
- `claim`: set on each claim's role-`phi` file (the `file` of its `phi.json` entry), on every `rediscuss` invocation, and on every Lean certificate. The claim set = the `claim` ids on `phi` children. Lean project support files (role `c`) carry none.
- `theorem`: only on a Lean certificate (role `c`, `media: text/x-lean`). **Only a child with a `theorem` is a proof object for rule 2.** `assemble.py` takes it from a sidecar `hard/certs/**/theorems.json` = `[{"claim", "theorem", "source": "hard/certs/.../X.lean"}]`.
- Media types the verifier dispatches on: `application/vnd.tcg.rediscuss+json` (KEVM re-discharge invocation, variant A, **not** a certificate for rule 2) and `text/x-lean` (Lean source certificate). Lean project files (`lean-toolchain`, `lakefile.lean`, `lake-manifest.json`) are role `c` children of the same claim, in an ancestor directory of the `.lean` source.
- Rule 4: no key containing verdict/level/proved/pass/score, no key `L0`–`L4`, no string value containing the word "proved". This deliberately over-rejects.
- `not_claimed`: the five v3 §10 sentences verbatim (D11), see the schema `const`.

## Trusted base: `trusted_base.json` (role `T_hat`)
- Schema: `trusted_base.schema.json` (required fields only; extra fields are allowed).
- `checker[]` entries the verifier looks up by `name`:
  - `kevm-prove`: `hash` = docker image digest `sha256:<64 hex>` (matched against `docker image inspect` `.Id` or a `RepoDigests` digest); optional `image` = a reference to inspect or pull.
  - `lean`: `hash` = sha256 of the `bin/lean` binary of the toolchain named in `lean-toolchain` (looked up under `~/.elan/toolchains/<name with / → -- and : → --->` or `$TCG_LEAN_TOOLCHAINS`). It may be a list, one hash per platform.
  - `tcg-verifier`: `hash` = output of `python3 pilot/verifier/verify.py --self-hash`. L1 fails if it is missing or differs.
- `assumptions[]`: must be non-empty, and every id in `hard/annotations.json` must be an assumption `id` or listed in some assumption's `covers` (e.g. `A_simp_lemmas` covering every K lemma id). Each covering assumption needs a non-empty `risk_if_false`. Otherwise L1 is `refused`.
- `semantics[]` with `path` (variant B): `hash` = `canon.tree_hash(<bundle>/<path>)` (`python3 pilot/tools/tree_hash.py <dir>`), i.e. sha256 of canonical JSON `[[relpath, sha256], ...]` sorted by relpath.
- `lean_axioms` (optional) can only **narrow** {propext, Classical.choice, Quot.sound}.

## Annotations: `hard/annotations.json` (role `a`)
`{"annotations": [{"id", "statement", "used_by", "justification", "class"}]}` (a bare list is accepted too).

## KEVM invocation: `hard/certs/claim-0N.rediscuss.json` (role `c`, variant A)
Schema: `rediscuss.schema.json`. The verifier builds the docker command itself, in the same shape as `pilot/checker/run-claim.sh`:
`docker run --rm --platform linux/amd64 --network none --user <uid>:<gid> -e HOME=/tmp -v <copy of claim dir>:/claim:ro -v <scratch>:/work -w /work <image Id> kprove /claim/<file> --definition /opt/kevm/haskell -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin --spec-module <spec_module> <kprove_args...>`.
The mounted directory is a copy of the claim file's directory in the hash-verified view, so it holds verified children only. `requires "edsl.md"` resolves inside the image through `-I`. Verdict judge: ported from `tcg/verdict.py`: exit 0 + `#Top` → accept; "cannot be rewritten further" → refute; timeout, "unifies with the destination" or anything else → unknown.

## Evidence (role `V`)
- `hard/spec/phi.json`: `{"claims": [{"id", "file", "sha256", "requirements": ["R1", ...], "pre", "post", "exit"}], "declared_blind_spots": [{"requirement", "reason", "partial"?: bool}]}`. Each requirement gets one of three states: **covered** (claimed, no blind-spot entry), **partial** (claimed *and* listed: `"partial": true` plus a reason saying what is not proved), **blind** (no claim). `total` is true only if every requirement is covered. `file`/`sha256` must match the manifest child that carries that `claim` id.
- `hard/spec/requirements.md`: requirement ids are `R<n>` at the start of a line, optionally after `- ` and/or `**`.
- `evidence/coverage.json`: written by `python3 pilot/tools/coverage.py <bundle>` (exit 0 even with gaps; 1 only on malformed input). The verifier recomputes it with the same code (`tcgverify/evidence.py`) and only compares the stored copy.
- `evidence/backtranslation.json`: `{..., "claims": [{claim, translation, referenced_requirement, agreement, note, ...}]}`. The verifier reads the list under `claims`, falling back to `entries` (the earlier draft) or a bare list. Every other top-level field (translator, requirements_withheld, caveats, ...) is reported as `backtranslation_meta`. Reported as data, never re-run.
- `evidence/mutants/<name>/` (name `claim-0N` or `claim-0N-<tag>`): `mutant.bin` (must differ from `hard/artifact.bin`) or `harness/`, plus `replay.sh` and `refutation.json` `{"claim", "kind", "output_sha256", "runs"}`, written by `python3 pilot/tools/mutant_witness.py record <bundle> <name> --claim <id> --kind <kind>`. It runs `sh replay.sh` twice in a scratch copy of the bundle (cwd = that directory, env = PATH + scratch HOME), refuses unstable stdout, and applies the kind's rule. The rules, shared with the verifier: `refute` = the KEVM judge classifies stdout as refute (a symbolic stuck state, no counterexample); `concrete_trace_violation` = exit 0 and a stdout line `TCG-VIOLATION: <what>`; `not_accept` = not judged accept (reported, never a witness). On the shared VM, real provers run inside `~/pilot-locks/with-slot.sh prover -- …`.
- `evidence/pre_witness/replay.sh` + `expected.json` `{"output_sha256"}`: replays iff exit 0 and the stdout hash matches.
- `evidence/approval.json` `{"phi_sha256", "requirements_sha256"}` + `evidence/approval.sig` = raw 64-byte oracle signature over the ASCII `phi_sha256 ‖ requirements_sha256` (D4).

## Provenance (role `P`)
`provenance/ledger.jsonl`, written by `pilot/tools/ledger.py` with `--root <bundle>`. An event that touches any path outside the bundle root (an input, an output or stdout/stderr, the cwd, or a path-like argv element such as `../tools/x.py` or `/home/...`) is reported as `not_replayable: input|output outside bundle`, listed with those paths, and named in `outside_bundle`. It is never replayed and never counted as a pass or a mismatch; it makes L4 `partial` at best. Exception, the stand-in rule: a relative outside **input** whose recorded sha256 equals a verified bundle child is materialized from that child at its recorded location in the replay sandbox, so `../tools/x.py` recorded with its hash replays from `provenance/tools/x.py`. Record **every** file the command reads, imports included, or the replay fails on the missing ones (a mismatch, with `replay_stderr_tail`). Otherwise L4 replays every `deterministic: true` run event whose `argv[0]` resolves on the consumer's PATH to a binary with sha256 = `tool_hash`, and whose inputs are bundle children with the recorded hashes. Every bundle child that a ledger event last wrote must carry that event's hash.

## State snapshot (consumer-supplied, never a bundle child, D9)
`<dir>/snapshot.json` = `{"chain_id", "block": {"number", "hash", "timestamp"}, "fork"?, "code": {"0x<addr>": "0x<runtime hex>"}}`.
