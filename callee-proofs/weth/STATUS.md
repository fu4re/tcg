# STATUS — WETH9 token-leg callee summaries over REAL mainnet bytecode

Deliverable D of the callee-proof problem (Finding 0005): the token-leg value-conservation
summaries that GemJoin.join/exit will later consume. Callee-side only; NO join/exit composition,
NO Vat.slip, NO lemma-def changes.

Judge = kprove on the KEVM Haskell backend, lemma-equipped def at
`~/toolchains/kevm-1.0.678-lemmas` (main module LEMMAS-DRIVER), classified by the SHARED judge
`tcg.verdict.classify()` (exit 0 + `#Top` => Accept; "unifies with the destination" residual =>
Unknown(c); "cannot be rewritten further" => Refute). Every verdict below is an actual kprove
run; the log path is given. The orchestrator independently re-verifies.

## 1. Subject bytecode — program-bound to the real WETH9 (SOUND ANCHOR)
- WETH9 = 0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2 (canonical mainnet Wrapped Ether, ETH-A gem).
- Fetched deployed RUNTIME via 3 public RPCs (ETH_RPC_URL unset): publicnode / 1rpc / drpc.
- on-chain EXTCODEHASH == keccak256(fetched runtime) across ALL THREE RPCs AND the independent
  keccak, and the fetched bytecode is byte-identical across all three:
  `0xd0a06b12ac47863b5c7be4185c2deaad1c61557033f56c7d4ea74429cbb25e23`  (bytecode/codehash.txt)
- Runtime = 3124 bytes. The proof `<program>` cell embeds this exact hex. CONFIRMED real WETH9.
- Storage layout: balanceOf = slot 3 (EMPIRICALLY confirmed vs the getter on-chain, see
  codehash.txt), allowance = slot 4 (standard layout; re-checked by the infinite-allowance branch).

## 2. The two summaries (what is proved), over the real WETH9 `<program>`
WETH9 (solc 0.4.19) transferFrom: `require(balanceOf[src] >= wad); if (src != msg.sender &&
allowance[src][msg.sender] != uint(-1)) { require(...); allowance -= wad; } balanceOf[src] -= wad;
balanceOf[dst] += wad; emit Transfer; return true;`  transfer(dst,wad) = transferFrom(msg.sender,
dst, wad). NO external call in either -> reentrancy frame holds trivially.

### transferFrom D — the GemJoin.join leg (adapter pulls wad from usr to itself)
- Parties: src = usr (0xaa), dst = adapter = msg.sender = ETH-A GemJoin (0x2F0b..042A). src != dst.
- Pre: callvalue 0; calldata = 0x23b872dd ++ usr ++ adapter ++ wad;
  `0 <= WAD < 2^256`; `WAD <= balanceOf[usr]` (the require); `balanceOf[adapter] + WAD < 2^256`
  (no overflow, raw ADD); **`allowance[usr][adapter] == uint(-1)`** (INFINITE-allowance precond:
  skips the allowance-decrement branch — the precondition I take; finite-allowance is an extension).
- Post: `balanceOf[usr] -= WAD`, `balanceOf[adapter] += WAD`, EVMC_SUCCESS. Total supply conserved
  (a -WAD and a +WAD at two distinct slots; allowance unchanged). Opaque slots (keccak constants):
  balanceOf[usr]=slot3 key, balanceOf[adapter]=slot3 key, allowance[usr][adapter]=slot4 nested.

### transfer D — the GemJoin.exit leg (adapter pushes wad to usr)
- Parties: msg.sender = src = adapter (GemJoin), dst = usr (0xaa). src == msg.sender => allowance
  branch skipped entirely (NO allowance precondition needed). src != dst.
- Pre: callvalue 0; calldata = 0xa9059cbb ++ usr ++ wad; `0 <= WAD < 2^256`;
  `WAD <= balanceOf[adapter]`; `balanceOf[usr] + WAD < 2^256`.
- Post: `balanceOf[adapter] -= WAD`, `balanceOf[usr] += WAD`, EVMC_SUCCESS.

## 3. SCOPE (stated honestly — concrete-pinned schema, NOT universal over addresses)
- `wad`: UNIVERSAL over uint256 (`0 <= WAD < 2^256`) and over pre-state `STORAGE`.
- `src, dst, msg.sender`: CONCRETE-PINNED (usr=0xaa, adapter=GemJoin). Concrete so keccak is a
  concrete constant in BOTH cast and KEVM — no keccak axiom invoked; the delta is proved at the
  opaque slot CONSTANTS. The ±WAD delta is independent of the concrete key VALUES, so this is a
  SCHEMA instantiable at any concrete (src,dst) with src != dst. Universal-over-address is the
  blocked keccak widening (klab uses the same concrete-key discipline), NOT a soundness gap.
- src==dst aliasing (balance nets to zero): EXCLUDED by construction — usr != adapter, so the two
  balanceOf slots are distinct concrete constants.

## 4. Non-vacuity discriminators (MANDATORY, per summary)
- WRONG-DELTA (`*_wrong.k`): identical claim but dst delta `+ WAD + 1`. MUST NOT Accept.
- VACUITY   (`*_vac.k`):   identical claim but `ensures false`. MUST NOT Accept.

## 5. VERDICTS (actual kprove runs) — PENDING (proofs running)
| spec                 | judge (lemma def)          | expected      | verdict | log |
|----------------------|----------------------------|---------------|---------|-----|
| transferFrom_d.k     | kevm-1.0.678-lemmas        | Accept        | PENDING |     |
| transferFrom_wrong.k | kevm-1.0.678-lemmas        | NOT Accept    | PENDING |     |
| transferFrom_vac.k   | kevm-1.0.678-lemmas        | NOT Accept    | PENDING |     |
| transfer_d.k         | kevm-1.0.678-lemmas        | Accept        | PENDING |     |
| transfer_wrong.k     | kevm-1.0.678-lemmas        | NOT Accept    | PENDING |     |
| transfer_vac.k       | kevm-1.0.678-lemmas        | NOT Accept    | PENDING |     |

## 6. Discharged vs assumed  (to be finalized after runs)
- Reentrancy frame: transfer/transferFrom make NO external CALL -> frame holds trivially.
- Assumed / ledgered: storage-layout (balanceOf slot 3 confirmed, allowance slot 4); keccak slots
  re-checkable via slots.sh; the infinite-allowance precondition for the join leg.
