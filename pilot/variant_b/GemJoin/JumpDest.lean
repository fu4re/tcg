import GemJoin.JumpDest.Chunks0
import GemJoin.JumpDest.Chunks1
import GemJoin.JumpDest.Chunks2
import GemJoin.JumpDest.Chunks3

/-!
# `D_J` of the GemJoin runtime equals a 59-entry literal table

The scan takes 1596 `D_J_aux` steps (it runs through the metadata tail and stops
at pc 3470, past the end of the 3462-byte code). The steps are checked by the
kernel in 64 chunks (`GemJoin.JumpDest.Chunks0..3`) and glued here.
-/

namespace GemJoin.DJ
open EvmYul EvmYul.EVM


/-- The jump-destination table of the GemJoin runtime (59 entries). -/
def table : Array UInt256 := #[⟨16⟩, ⟨113⟩, ⟨169⟩, ⟨174⟩, ⟨182⟩, ⟨248⟩, ⟨270⟩, ⟨324⟩, ⟨326⟩, ⟨348⟩, ⟨392⟩, ⟨394⟩, ⟨402⟩, ⟨404⟩, ⟨412⟩, ⟨478⟩, ⟨486⟩, ⟨508⟩, ⟨530⟩, ⟨574⟩, ⟨576⟩, ⟨584⟩, ⟨606⟩, ⟨628⟩, ⟨672⟩, ⟨694⟩, ⟨702⟩, ⟨724⟩, ⟨746⟩, ⟨800⟩, ⟨802⟩, ⟨840⟩, ⟨960⟩, ⟨1079⟩, ⟨1258⟩, ⟨1278⟩, ⟨1503⟩, ⟨1523⟩, ⟨1545⟩, ⟨1676⟩, ⟨1731⟩, ⟨1911⟩, ⟨2033⟩, ⟨2213⟩, ⟨2274⟩, ⟨2312⟩, ⟨2318⟩, ⟨2498⟩, ⟨2620⟩, ⟨2626⟩, ⟨2650⟩, ⟨2656⟩, ⟨2806⟩, ⟨2988⟩, ⟨3008⟩, ⟨3181⟩, ⟨3201⟩, ⟨3223⟩, ⟨3354⟩]

theorem djIter_runtime : djIter GemJoin.runtime 1596 (⟨0⟩, #[]) = (⟨3470⟩, table) := by
  rw [show (1596 : ℕ) = 25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (25 + (21))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))))) from rfl]
  rw [djIter_add, chunk0, djIter_add, chunk1, djIter_add, chunk2, djIter_add, chunk3, djIter_add, chunk4, djIter_add, chunk5, djIter_add, chunk6, djIter_add, chunk7, djIter_add, chunk8, djIter_add, chunk9, djIter_add, chunk10, djIter_add, chunk11, djIter_add, chunk12, djIter_add, chunk13, djIter_add, chunk14, djIter_add, chunk15, djIter_add, chunk16, djIter_add, chunk17, djIter_add, chunk18, djIter_add, chunk19, djIter_add, chunk20, djIter_add, chunk21, djIter_add, chunk22, djIter_add, chunk23, djIter_add, chunk24, djIter_add, chunk25, djIter_add, chunk26, djIter_add, chunk27, djIter_add, chunk28, djIter_add, chunk29, djIter_add, chunk30, djIter_add, chunk31, djIter_add, chunk32, djIter_add, chunk33, djIter_add, chunk34, djIter_add, chunk35, djIter_add, chunk36, djIter_add, chunk37, djIter_add, chunk38, djIter_add, chunk39, djIter_add, chunk40, djIter_add, chunk41, djIter_add, chunk42, djIter_add, chunk43, djIter_add, chunk44, djIter_add, chunk45, djIter_add, chunk46, djIter_add, chunk47, djIter_add, chunk48, djIter_add, chunk49, djIter_add, chunk50, djIter_add, chunk51, djIter_add, chunk52, djIter_add, chunk53, djIter_add, chunk54, djIter_add, chunk55, djIter_add, chunk56, djIter_add, chunk57, djIter_add, chunk58, djIter_add, chunk59, djIter_add, chunk60, djIter_add, chunk61, djIter_add, chunk62]
  exact chunk63

theorem runtime_size : GemJoin.runtime.size = 3462 := by decide +kernel

theorem stuck_end : (GemJoin.runtime.get? (⟨3470⟩ : UInt256).toNat >>= EvmYul.EVM.parseInstr) = none := by
  rw [← Option.isNone_iff_eq_none]; decide +kernel

theorem D_J_runtime : D_J GemJoin.runtime ⟨0⟩ = table := by
  show D_J_aux (GemJoin.runtime.size + 1) GemJoin.runtime ⟨0⟩ #[] = table
  rw [runtime_size, show (3462 + 1 : ℕ) = 1867 + 1596 from rfl]
  have h := D_J_aux_add GemJoin.runtime 1596 1867 (⟨0⟩, #[])
  rw [djIter_runtime] at h
  rw [h]
  exact D_J_aux_stuck GemJoin.runtime (⟨3470⟩, table) stuck_end _

end GemJoin.DJ