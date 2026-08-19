# callext — the Gap-#1 call-site-summary probe (two-contract CALL toy)

A bounded, decisive experiment answering the single unknown that gates the
value-conservation coverage work (P1): **can the prover apply a separately-proved
callee summary as a circularity at an external `CALL`, or must the driver migrate
to Kontrol/pyk `APRProof` (CSE)?**

Answer, measured on the real kompiled KEVM Haskell backend (`kevm-1.0.678`, stock/
unpatched — no ghost cells, no P0 lemmas; the toy uses a constant `+5`, no
arithmetic): **raw `kprove` applies the summary at an unresolved (symbolic-code)
external CALL.** So P1 is tcg-native work (~1–2 days), not a driver migration.
Full write-up and the P1-path reasoning: `docs/findings/0005_callsite_summary_probe.md`.

## The toy (design §6 of the P1 spike)

- **Callee `C_callee`** — a mini-slip at address `200` (`0xC8`), runtime
  `60005460050160005500` = `PUSH1 0; SLOAD; PUSH1 5; ADD; PUSH1 0; SSTORE; STOP`
  (`slot0 += 5`).
- **Caller `C_caller`** — a mini-join at address `100` (`0x64`), runtime
  `6000600060006000600060C86000F100` = push the 7 CALL args, `CALL` into `200`,
  `STOP`. `C_caller` is the subject; its root asserts `A2.storage[0] == 105`
  (100+5) — a fact the caller never computes itself, establishable only by
  consuming the callee delta at the CALL. The returned success flag `1` is
  asserted on the caller's word stack (the `require(success)` analogue).

## Verdicts (all from the solver; reproduce with `run.sh`)

| Spec (raw/) | Variant | classify() | exit | What it shows |
|---|---|---|---|---|
| `callee-d` | callee delta `D` (concrete code) | Accept `#Top` | 0 | the +5 delta discharged over the real callee bytecode |
| `caller-inline` | INLINE baseline (concrete A2 code) | Accept `#Top` | 0 | multi-contract CALL plumbing; callee **inlined** — NOT a Gap-#1 probe |
| **`caller-2a`** | **SUMMARY 2a (symbolic A2 code + trusted `S`)** | **Accept `#Top`** | **0** | **DECISIVE: `kprove` applies the summary as a circularity at the symbolic CALL** |
| `caller-2a-broken` | non-vacuity: `S` says +6 | Refute | 3¹ | R depends on the *correct* +5 summary |
| `caller-2a-nosummary` | non-vacuity: no `S` | Refute | 3¹ | `S` is necessary; stuck at the symbolic-code callee frame (inline-leak proof) |
| `caller-2a-vacuity` | non-vacuity: `ensures false` | Unknown (not Accept) | — | the 2a pass is non-vacuous (antecedent feasible) |
| `bridge-s-at-p` | bridge `S ⟸ D` | Accept `#Top` | 0 | the abstract summary, at the concrete program, proves by execution over the real bytecode |
| `caller-drain` | control: leading `STOP` before CALL | Refute | 3¹ | callee never runs → `A2.storage[0]` stays 100 → structural refute |
| `compat-ok` | interference obligation Guar⟹Rely | Accept `#Top` | 0 | callee frames A1 (Rely: A1 untouched) |
| `compat-broken` | broken-Rely discriminator | Refute | 3¹ | caller relies on A1[1]=999 the callee never provides → structural refute + counterexample |

¹ raw `kprove` exits 1 on any non-`#Top`; the `3` is tcg's `Exit.REFUSED` after
`verdict.classify()` maps the log to Refute (`doesn't unify with the destination …
cannot be rewritten further`). `run.sh`/`run-tcg.sh` show both.

## The inline-leak check (2a is not inlining in disguise)

`caller-2a-nosummary.log` shows the stuck configuration with A2's code symbolic:

```
<k> #next [ #lookupOpCode ( CODE0 , 0 , DEFAULT ) ] ~> #execute ~> #return 0 0 ~> #pc [ CALL ] ~> #execute ~> .K </k>
```

`CODE0` is a free variable — there is **no concrete callee bytecode to inline**;
the frame stalls precisely because the program is symbolic. So 2a's `#Top` can
only come from applying `S`. (The INLINE variant, by contrast, closes because
`kprove` executes the 9 concrete bytes — composition-by-inlining, which does not
scale to real external callees.)

## The soundness residual — the bridge `S ⟸ D`

The summary `S` (`raw/caller-2a.k`, claim `[s]`) pins the callee ENTRY state
exactly as KEVM's `#mkCall`/`#initVM` produces it; the **only** abstracted cell is
`<program> _PGM` (free), so it unifies with the stalled symbolic code. A free
program cell is too general to be sound in isolation — it is justified by the
bridge `S ⟸ D`: `D` proved over the concrete code `P`, plus the code-identity
binding `code(200) = P` (`tcg/subject/environment.json` `external_code`; in
production `keccak(P)` vs the on-chain hash — pure text, no prover). `bridge-s-at-p`
discharges the execution half: `S` with `_PGM := P` proves by running the real
bytecode.

## Reproduce

```
tests/reference/callext/run.sh        # raw kprove, all 10 specs, verdict-checked
tests/reference/callext/run-tcg.sh    # the toy through tcg's real pipeline (prove.py)
```

`run-tcg.sh` shows tcg's own `prove` step already applies the summary
(`caller_2a` → Accept), the +6 twin refutes (`caller_2a_broken` → exit 3), and
`graph check` reporting the one residual gap: closure requires the abstract
summary node to be *Accepted*, which it cannot be. Committed evidence:
`raw/logs/` (raw kprove), `tcg/logs/` (tcg prove).
