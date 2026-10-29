import GemJoin.JumpDest
import GemJoin.KernelRfl

/-!
# `ilk()` of GemJoin ETH-A over EVMYulLean (variant B, claim `ilk`)

Translation of the K claim `ilk` (tests/reference/getters-full/src/ilk/ilk.k):
a message call into the GemJoin runtime with calldata = the 4-byte selector
`0xc5ce281e`, call value 0, non-static, from any caller, into any account
address, over any account map, ends in `success` with output the 32 big-endian
bytes of storage slot 2 of the callee, and leaves the account map unchanged.

Narrowings relative to the K claim (K runs with `useGas false`):
* gas available at entry is fixed at `G0 = 30 000 000`;
* the substate at entry is empty (`default`; slot 2 is cold).

Proof: `xi` unfolds `Ξ` once; `D_J_runtime` replaces the jump-destination
analysis by its 59-entry table; `run` lets the kernel evaluate all 77
instructions of `X` with the account map, the addresses and so the storage
word symbolic.
-/

namespace GemJoin.Ilk
open EvmYul EvmYul.EVM GemJoin.DJ

def ilkSelector : ByteArray := ⟨#[0xc5, 0xce, 0x28, 0x1e]⟩

def G0 : UInt256 := ⟨30000000⟩

/-- The call environment of the K claim: `<callValue> 0`, `<static> false`,
`<callData> b"\xc5\xce\x28\x1e"`, `<program>` = the GemJoin runtime. -/
def env (a s o : AccountAddress) (gp : ℕ) (h : BlockHeader) (d : ℕ) (bvh : List ByteArray) :
    ExecutionEnv .EVM :=
  { codeOwner := a, sender := s, source := o, weiValue := ⟨0⟩, calldata := ilkSelector,
    code := GemJoin.runtime, gasPrice := gp, header := h, depth := d, perm := true,
    blobVersionedHashes := bvh }

/-- Storage slot `k` of account `a`, as EVMYulLean's `State.sload` reads it. -/
def slot (σ : AccountMap .EVM) (a : AccountAddress) (k : UInt256) : UInt256 :=
  (σ.find? a).option ⟨0⟩ (Account.lookupStorage (k := k))

/-- What `Ξ` returns from a finished `X` run. -/
def post (r : ExecutionResult EVM.State) :
    Except EVM.ExecutionException
      (ExecutionResult (Batteries.RBSet AccountAddress compare × AccountMap .EVM × UInt256 × Substate)) :=
  match r with
  | .success st o => .ok (.success (st.createdAccounts, st.accountMap, st.gasAvailable, st.substate) o)
  | .revert g o => .ok (.revert g o)

/-- The state `Ξ` builds before calling `X`. -/
def s0 (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader) (blocks : ProcessedBlocks)
    (σ σ₀ : AccountMap .EVM) (I : ExecutionEnv .EVM) : EVM.State :=
  let d : EVM.State := default
  { d with
    accountMap := σ
    σ₀ := σ₀
    executionEnv := I
    substate := default
    createdAccounts := cA
    gasAvailable := G0
    blocks := blocks
    genesisBlockHeader := gbh }

set_option maxRecDepth 100000

-- Kernel: one unfolding of `Ξ`.
kernel_theorem xi : ∀ (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (I : ExecutionEnv .EVM),
    Ξ (f + 1) cA gbh blocks σ σ₀ G0 default I
      = bind (X f (D_J I.code ⟨0⟩) (s0 cA gbh blocks σ σ₀ I)) post

-- Kernel: the 77 instructions, ending in `RETURN` of memory [0x80, 0xa0).
kernel_theorem run : ∀ (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)
    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray),
    (match X (f + 78) table (s0 cA gbh blocks σ σ₀ (env a s o gp h d bvh)) with
      | .ok (.success st out) => some (st.accountMap, out)
      | _ => none)
      = some (σ, UInt256.toByteArray (slot σ a ⟨2⟩))

/-- **Claim `ilk` over EVMYulLean.** For every account map `σ`, callee `a`,
caller `s`, origin `o` and every other environment field, the message call
`Ξ` with the `ilk()` calldata succeeds, returns the 32 big-endian bytes of
slot 2 of `a`, and leaves the account map unchanged. -/
theorem ilk_correct (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)
    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray) :
    ∃ cA' g' A', Ξ (f + 79) cA gbh blocks σ σ₀ G0 default (env a s o gp h d bvh)
      = .ok (.success (cA', σ, g', A') (UInt256.toByteArray (slot σ a ⟨2⟩))) := by
  have hdj : D_J (env a s o gp h d bvh).code ⟨0⟩ = table := D_J_runtime
  rw [show f + 79 = (f + 78) + 1 by omega, xi, hdj]
  have hr := run f cA gbh blocks σ σ₀ a s o gp h d bvh
  generalize X (f + 78) table (s0 cA gbh blocks σ σ₀ (env a s o gp h d bvh)) = r at hr ⊢
  rcases r with e | ⟨st, out⟩ | ⟨g, out⟩
  · simp at hr
  · simp only [Option.some.injEq, Prod.mk.injEq] at hr
    obtain ⟨h1, h2⟩ := hr
    exact ⟨st.createdAccounts, st.gasAvailable, st.substate, by
      simp only [bind, Except.bind, post, h1, h2]⟩
  · simp at hr

end GemJoin.Ilk
