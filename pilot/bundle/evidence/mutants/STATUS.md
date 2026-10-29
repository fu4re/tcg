# Mutant witnesses (task 04 §3) -- STATUS

Owner: WS-C session. Updated 2026-10-29 (04/05 recorded). Nothing committed or pushed. Owned path: `pilot/bundle/evidence/mutants/` only.

## How these were made

- **Generator:** `gen_mutants.py` (stdlib, deterministic). It is run from the bundle root: `python3 evidence/mutants/gen_mutants.py` for claims 01–03 and `… --revert` for claims 04–05.
- **Recorder:** `record_all.sh`. It wraps every run in `~/pilot-locks/with-slot.sh prover` and records each run as a ledger event in `provenance/ledger.jsonl`. The recording itself is `pilot/tools/mutant_witness.py record`, which replays twice and refuses unless both stdouts are byte-identical and the kind's rule holds.
- **Semantics for every run:** KEVM (evm-semantics d4bf484a + ghost.diff + lemmas2.diff, schedule OSAKA), run by kprove in the pinned checker image `sha256:7d4a35bc05dfdad97b244da3c75bb3c3e710be73713cac3ca1c5bb6226cdc465`. `replay.sh` inlines `pilot/checker/run-claim.sh`'s argv (`--network none --memory=6g --cpus=2`), because the verifier runs it from a bundle copy. Callers on the VM hold the prover slot. No anvil/revm is used anywhere.
- **Target claims:** the shipped `hard/spec/claim-0N.k`. For 01–03, the source the witnesses were generated from (`provenance/rebuild/controls-osaka/{vat-vat,ilk-ilk,gem-gem}-prove.k`) has the same sha256 as `hard/spec/claim-0{1,2,3}.k` (`37c196d1…`, `e6718350…`, `4c39f548…`) and as `phi.json`. Each `mutation.json` records `source_claim_sha256`. For 04–05, `gen_mutants.py` asserts the phi.json sha256, and the symbolic `replay.sh` re-checks at replay time that `claim.k` is `hard/spec/claim-0N.k` with only `<program>`/`<jumpDests>` and the module name changed.

### Two witness kinds per claim (never merged)

1. **`claim-0N[-tag]/`, kind `concrete_trace_violation` (the decisive one).** Three kprove runs on a fully concrete instance σ of the claim's Pre:
   - `witness-original.k`: the claim at σ on `hard/artifact.bin`. It **must Accept** (control).
   - `witness-mutant.k`: the same σ on `mutant.bin`, asserting the mutant's actual result X (getters: `?OUT ==K #buf(32, X) andBool ?OUT =/=K <claim RHS at σ>`; reverts: `?SC ==K EVMC_SUCCESS`). It **must Accept**.
   - `witness-negative.k`: the claim at σ on `mutant.bin`. It **must NOT Accept**. This guards against a vacuous concrete harness: if σ's `requires` were somehow false, every concrete claim would Accept.

   `TCG-VIOLATION:` is printed, with exit 0, only if all three hold. A kprove Accept on a fully concrete pre-state is a single concrete KEVM execution.
2. **`claim-0N[-tag]-symbolic/`, kind decided by the verifier's own judge.** The shipped claim verbatim, with `<program>` = `mutant.bin`. One trial replay is classified by `tcgverify.checkers.classify_kprove`, then the witness is recorded as `refute` if the judge says refute, else as `not_accept` (reported, never counted as a witness). `replay.sh` prints kprove's stderr (the judge needs the stuck/refute message) and then its stdout, with kore-exec's per-run `[NNN]` counter normalised to `[N]` so the output is byte-stable.

## Results

| claim | witness dir | mutant (byte edits on hard/artifact.bin) | concrete state σ | concrete-trace result | symbolic verdict (shipped claim on mutant) | ledger seq | record wall (2 replays) |
|---|---|---|---|---|---|---|---|
| claim-01 `vat()` | `claim-01` / `-symbolic` | 0x324 `01→02`: vat() SLOADs slot 2 (ilk) instead of 1 | σ_pin (GemJoin storage at block 26298481) | **concrete_trace_violation**: mutant returns `0x0` (= "ETH-A" & mask160), claim requires `0x…35d1b3f3d7966a1dfe207aa4514c12a259a0492b` (Vat). Control Accept, negative not Accept | **Unknown(c)** → recorded `not_accept` | 57 / 102, 109 | 740 s / 177 + 303 s |
| claim-01 `vat()` (2nd mutant) | `claim-01-mask` / `-symbolic` | 0x345, 0xd1, 0xe7 `16→50` (AND→POP): all three 160-bit masks on vat()'s path dropped | **σ_hi, SYNTHETIC**: σ_pin with slot 1 = `0xa5 << 248 \| Vat` | **concrete_trace_violation**: mutant returns `0xa5000000000000000000000035d1…492b`, claim requires `0x…35d1…492b`. Control Accept, negative not Accept | **Unknown(c)** → `not_accept` | 66 / 110, 111 | 693 s / 149 + 325 s |
| claim-02 `ilk()` | `claim-02` / `-symbolic` | 0xa5c `02→03`: ilk() SLOADs slot 3 (gem) instead of 2 | σ_pin | **concrete_trace_violation**: mutant returns `0x…c02aaa39b223fe8d0a0e5c4f27ead9083c756cc2` (WETH), claim requires `0x4554482d41…` ("ETH-A"). Control Accept, negative not Accept | **Unknown(c)** → `not_accept` | 75 / 112, 113 | 697 s / 120 + 261 s |
| claim-03 `gem()` | `claim-03` / `-symbolic` | 0x8e4 `03→01`: gem() SLOADs slot 1 (vat) instead of 3 | σ_pin | **concrete_trace_violation**: mutant returns `0x…35d1…492b` (Vat), claim requires `0x…c02a…6cc2` (WETH). Control Accept, negative not Accept | **Unknown(c)** → `not_accept` | 101 / 114, 115 | 717 s / 212 + 351 s |
| claim-04 `cage()` reverts | `claim-04` / `-symbolic` | 0x833 `14→17` (EQ→OR): the auth check `wards[msg.sender] == 1` becomes `1 \| wards[msg.sender]` (always ≠ 0) | σ_pin, caller with no wards entry | **concrete_trace_violation**: mutant halts `EVMC_SUCCESS`, claim requires `EVMC_REVERT`. Control Accept, negative not Accept | **Refute**: stuck with "cannot be rewritten further" in a final state with `<statusCode> EVMC_SUCCESS`, recorded `refute` | 116 / 118, 119 | 898 s / 231 + 512 s |
| claim-05 `join()` reverts | `claim-05` / `-symbolic` | 0x34e `14→17` (EQ→OR): `live == 1` becomes `1 \| live` | σ_pin with live = 0 (post-`cage()`), usr/wad concrete, + Vat stub (code `STOP`) + WETH stub (returns `true`) | **concrete_trace_violation**: mutant halts `EVMC_SUCCESS`, claim requires `EVMC_REVERT`. Control Accept, negative not Accept | **Unknown(c)** → `not_accept` (see Honest reading) | 117 / 120, 131 | 1561 s / 942 + 1807 s |

Replay one witness (from the witness dir inside a bundle copy, holding a prover slot on the VM):

```
~/pilot-locks/with-slot.sh prover -- sh replay.sh
```

Check all recorded witnesses the way the verifier's L2 does:

```
~/pilot-locks/with-slot.sh prover -- python3 pilot/tools/mutant_witness.py check pilot/bundle
```

Per-replay wall time (one slot, 8 vCPU VM shared with other workstreams) is about 350 s for a concrete getter witness (3 kprove runs), about 450 s (claim-04) and 780 s (claim-05) for the revert witnesses, 120–230 s for a symbolic getter or claim-04 run, and 900 s for claim-05-symbolic. Ledger seqs 121–130 are other sessions' events that interleaved with this recording.

## Honest reading

- **Only claim-04's symbolic run Refutes.** On the cage() mutant, kprove reaches a terminal state with `EVMC_SUCCESS` that cannot be rewritten further, so the judge says Refute, and the residual state is the counterexample. claim-05-symbolic is **Unknown(c)**: the first branch to fail is a REVERT-status branch that unifies with the destination, but whose implication check fails. Its path condition includes `ACCTID == storage[1] & maxUInt160` (GemJoin aliasing its own Vat) and empty code. 4 branches were left unexplored when kprove stopped, so the success path that the concrete witness exhibits is never reached symbolically. I have not diagnosed why that branch's implication fails, and I make no claim about it.
- **Getter symbolic runs never Refute.** For every getter mutant, kprove stops with `WarnStuckClaimState: … unifies with the destination's term, but the implication check between the conditions has failed`, which is Unknown(c). That only means "not proved". It is the same class as the smoke's wrong-slot discriminators, and it is why each claim also carries a concrete trace.
- **claim-01-mask is a witness on an unreachable state.** `vat` is `VatLike public vat` and is only ever written with an address, so a real GemJoin's slot 1 never has bits above 160 set. On σ_pin the mask-drop mutant returns the same value as the original. The witness shows that the claim's RHS (`&Int maxUInt160`) distinguishes the mask over the claim's own quantification (any `storage[1]` in [0, 2^256)). It does not show an observable defect on reachable states. claim-01's primary witness (`claim-01`, wrong slot) is behavioural on σ_pin.
- **Bounded concrete states.** σ uses id = GemJoin, caller = `0xC0FFEE01`. For 04/05, GemJoin's balance/nonce and `<callDepth>` are pinned to 0/1/0: the claims' Pre leaves them free, and a symbolic `<callDepth>` makes a CALL branch on depth ≥ 1024. Each σ is one point of the claim's Pre, recorded in `mutation.json`.
- **Stubs (claim-05 only).** Vat and WETH are stub accounts (Vat: `STOP`; WETH: returns `true`). claim-05's Pre leaves all other accounts unconstrained, so σ is inside its quantification. The stubs model only "the external calls succeed". They are not real Vat/WETH behaviour.
- **Witness-claim framing (04/05).** The mutant's success path writes storage (cage: `live := 0`), emits `LogNote`, warms/touches accounts and bumps ghost.diff's `<callCounter>`/`<inFunc>`. So `witness-mutant.k` (only) abstracts GemJoin's `<storage>`, `<substate>`, `<touchedAccounts>` and the two ghost cells, and asserts nothing but `?SC ==K EVMC_SUCCESS`. The control and negative claims are the shipped claim at σ with nothing abstracted.

## Incidents (recorded, not hidden)

- **Aborted first recording.** The first `record_all.sh` pass was aborted by me to add the negative control (ledger seq 46, `mutant-witness-record claim-01`, exit -15). A `replay.sh` it had spawned outlived it and ran one more kprove container (about 2 min, `--memory=6g --cpus=2`) **outside a prover slot**. My attempt to kill that container was refused by the session's permission layer, so I waited for it to exit before starting the real recording.
- **Lost console log.** The final `record_all.sh` console log was lost to a redirect mistake (`> /dev/null`). The per-witness `*.record.out|err` and `*-symbolic.trial.out|err` files next to the witness dirs, and the ledger events, carry every result.
