-- Negative controls for GemJoin.Ilk.run. Run: lake env lean controls/IlkMutants.lean
-- Expected: the three mut_* declarations are REJECTED (kernel type mismatch), ctl is accepted.
-- Checked 2026-10-29: as expected (198 s, 5.8 GB).
import GemJoin.JumpDest.Basic
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
open EvmYul EvmYul.EVM
def table : Array UInt256 := #[⟨16⟩, ⟨113⟩, ⟨169⟩, ⟨174⟩, ⟨182⟩, ⟨248⟩, ⟨270⟩, ⟨324⟩, ⟨326⟩, ⟨348⟩, ⟨392⟩, ⟨394⟩, ⟨402⟩, ⟨404⟩, ⟨412⟩, ⟨478⟩, ⟨486⟩, ⟨508⟩, ⟨530⟩, ⟨574⟩, ⟨576⟩, ⟨584⟩, ⟨606⟩, ⟨628⟩, ⟨672⟩, ⟨694⟩, ⟨702⟩, ⟨724⟩, ⟨746⟩, ⟨800⟩, ⟨802⟩, ⟨840⟩, ⟨960⟩, ⟨1079⟩, ⟨1258⟩, ⟨1278⟩, ⟨1503⟩, ⟨1523⟩, ⟨1545⟩, ⟨1676⟩, ⟨1731⟩, ⟨1911⟩, ⟨2033⟩, ⟨2213⟩, ⟨2274⟩, ⟨2312⟩, ⟨2318⟩, ⟨2498⟩, ⟨2620⟩, ⟨2626⟩, ⟨2650⟩, ⟨2656⟩, ⟨2806⟩, ⟨2988⟩, ⟨3008⟩, ⟨3181⟩, ⟨3201⟩, ⟨3223⟩, ⟨3354⟩]

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

-- MUTANTS: every one of these must be REJECTED by the kernel.
kernel_theorem mut_slot3 : ∀ (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)
    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray),
    (match X (f + 78) table (s0 cA gbh blocks σ σ₀ (env a s o gp h d bvh)) with
      | .ok (.success st out) => some (st.accountMap, out)
      | _ => none)
      = some (σ, UInt256.toByteArray (slot σ a ⟨3⟩))
kernel_theorem mut_gem_selector : ∀ (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)
    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray),
    (match X (f + 78) table (s0 cA gbh blocks σ σ₀ ({ env a s o gp h d bvh with calldata := ⟨#[0x7b, 0xd2, 0xbe, 0xa7]⟩ })) with
      | .ok (.success st out) => some (st.accountMap, out)
      | _ => none)
      = some (σ, UInt256.toByteArray (slot σ a ⟨2⟩))
kernel_theorem mut_callvalue : ∀ (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)
    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray),
    (match X (f + 78) table (s0 cA gbh blocks σ σ₀ ({ env a s o gp h d bvh with weiValue := ⟨1⟩ })) with
      | .ok (.success st out) => some (st.accountMap, out)
      | _ => none)
      = some (σ, UInt256.toByteArray (slot σ a ⟨2⟩))
-- CONTROL: the unmutated statement, must be ACCEPTED.
kernel_theorem ctl : ∀ (f : ℕ) (cA : Batteries.RBSet AccountAddress compare) (gbh : BlockHeader)
    (blocks : ProcessedBlocks) (σ σ₀ : AccountMap .EVM) (a s o : AccountAddress) (gp : ℕ)
    (h : BlockHeader) (d : ℕ) (bvh : List ByteArray),
    (match X (f + 78) table (s0 cA gbh blocks σ σ₀ (env a s o gp h d bvh)) with
      | .ok (.success st out) => some (st.accountMap, out)
      | _ => none)
      = some (σ, UInt256.toByteArray (slot σ a ⟨2⟩))

end GemJoin.Ilk
