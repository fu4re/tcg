# φ delta for variant B: claim `ilk` re-stated over EVMYulLean

Proposed new φ entry; it changes the approved statement, so H must re-sign
(L3 must fail until then). Source claim: `tests/reference/getters-full/src/ilk/ilk.k`
(label `ilk`, all-path). Lean statement: `GemJoin.Ilk.ilk_correct` in
`GemJoin/Ilk.lean` (dev project `pilot/variant_b/`; in the bundle `hard/certs/ilk/GemJoin/Ilk.lean`),
over EVMYulLean @ `56253eb4` + patches 0001–0005. Machine-readable entry:
`hard/spec/phi.claim-02.lean.json` (staging: `pilot/variant_b/staging/`).

```lean
theorem ilk_correct (f : ℕ) (cA) (gbh) (blocks) (σ σ₀ : AccountMap .EVM)
    (a s o : AccountAddress) (gp : ℕ) (h : BlockHeader) (d : ℕ) (bvh : List ByteArray) :
    ∃ cA' g' A', Ξ (f + 79) cA gbh blocks σ σ₀ G0 default (env a s o gp h d bvh)
      = .ok (.success (cA', σ, g', A') (UInt256.toByteArray (slot σ a ⟨2⟩)))
```

## Cell-by-cell translation

| K claim | Lean | Same? |
|---|---|---|
| `<program>` / `<jumpDests>` = GemJoin runtime, `#computeValidJumpDests` | `code := GemJoin.runtime` (3462 bytes, keccak = D8); jump table = `D_J runtime 0` (proved = 59-entry table) | yes |
| `<id> ACCTID` (any address) | `codeOwner := a`, `a` universally quantified | yes |
| `<caller> MSGSENDER` (any address) | `sender := s`, universally quantified; also `source := o` | yes |
| `<callData> b"\xc5\xce\x28\x1e"` | `calldata := ⟨#[0xc5, 0xce, 0x28, 0x1e]⟩` | yes |
| `<callValue> 0` | `weiValue := 0` | yes |
| `<static> false` | `perm := true` | yes |
| `<wordStack> .WordStack`, `<localMem> .Bytes`, `<pc> 0`, `<memoryUsed> 0` | fresh `X` state built by `Ξ` (empty stack and memory, pc 0, 0 active words) | yes |
| `<storage> STORAGE` of `ACCTID` (any map), `#rangeUInt(256, #lookup(STORAGE, 2))` | `σ` arbitrary; the word read is `slot σ a 2` = EVMYulLean's `SLOAD` read (0 if the account or key is absent, as `#lookup` gives 0); always < 2^256 by type | yes |
| `ensures ?SC ==K EVMC_SUCCESS` | `Ξ … = .ok (.success …)` | yes |
| `ensures ?OUT ==K #buf(32, #lookup(STORAGE, 2))` | output `UInt256.toByteArray (slot σ a 2)`; `GemJoin.toByteArray_eq` shows it is the 32 big-endian bytes of the word | yes |
| accounts not rewritten in the claim (unchanged) | returned account map is `σ` | yes |
| `<log>` unchanged | returned substate (holds the logs) is existential | **weaker** |
| `<useGas> false` | gas at entry fixed: `G0 = 30 000 000` | **narrower** |
| substate not in the claim | substate at entry `default` (empty; slot 2 cold) | **narrower** |
| `<schedule> OSAKA` (bundle claim-02.k; the Finding 0003b source said SHANGHAI) | EVMYulLean's single schedule; gas does not reach the claimed cells | n/a |
| `<callStack> .List` | `depth := d`, universally quantified (no call on the path) | yes |
| other env (`gasPrice`, `header`, blob hashes), `σ₀`, created accounts, blocks | universally quantified | yes |
| (none) | fuel `f + 79` for any `f` (EVMYulLean is fuel-bounded) | n/a |

## Narrowings to record in φ

1. **Gas.** Proved for exactly 30 000 000 gas at entry (the run uses 2393). K ignores gas.
   Generalising to every gas ≥ 2393 needs the kernel to compare symbolic gas, which
   EVMYulLean's `UInt256` subtraction (`% 2^256`) blocks; not attempted.
2. **Substate.** Proved for an empty substate. With slot 2 already warm the run is the
   same except the `SLOAD` cost; not proved.
3. **Log.** K's Post keeps the log unchanged; the Lean statement leaves the returned
   substate (logs, touched accounts, refunds) existential, so "no log emitted" is not stated.
4. **Semantics.** The statement is about the patched semantics (patches 0001–0005;
   0001 and 0002 are assumptions, 0003–0005 are proved equal to upstream).
