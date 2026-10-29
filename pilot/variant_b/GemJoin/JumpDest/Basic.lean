import GemJoin.Runtime
import EvmYul.EVM.Semantics

/-!
# Jump-destination table of the GemJoin runtime, computed by the kernel

`D_J` (patched to a fuel-bounded `def`, patch 0001) is evaluated over the
3462-byte runtime. Evaluating it in one `decide` exhausts memory (the kernel
builds the unevaluated chain of `N i cᵢ` terms), so the scan is split into
chunks of `chunk` instructions whose end points are literals.
-/

namespace GemJoin.DJ
open EvmYul EvmYul.EVM

/-- One iteration of `D_J_aux`, as a total step on (pc, table). A stuck
position (`none`) is a fixed point. -/
def djStep (c : ByteArray) (p : UInt256 × Array UInt256) : UInt256 × Array UInt256 :=
  match c.get? p.1.toNat >>= EvmYul.EVM.parseInstr with
  | none => p
  | some ci => (N p.1 ci, if ci = .JUMPDEST then p.2.push p.1 else p.2)

def djIter (c : ByteArray) : ℕ → UInt256 × Array UInt256 → UInt256 × Array UInt256
  | 0, p => p
  | n + 1, p => djIter c n (djStep c p)

theorem D_J_aux_stuck (c : ByteArray) (p : UInt256 × Array UInt256)
    (h : (c.get? p.1.toNat >>= EvmYul.EVM.parseInstr) = none) :
    ∀ f, D_J_aux f c p.1 p.2 = p.2
  | 0 => rfl
  | f + 1 => by simp only [D_J_aux, h]

theorem djIter_stuck (c : ByteArray) (p : UInt256 × Array UInt256)
    (h : (c.get? p.1.toNat >>= EvmYul.EVM.parseInstr) = none) :
    ∀ m, djIter c m p = p
  | 0 => rfl
  | m + 1 => by simp only [djIter, djStep, h]; exact djIter_stuck c p h m

theorem D_J_aux_add (c : ByteArray) : ∀ (m f : ℕ) (p : UInt256 × Array UInt256),
    D_J_aux (f + m) c p.1 p.2 = D_J_aux f c (djIter c m p).1 (djIter c m p).2
  | 0, f, p => rfl
  | m + 1, f, p => by
    cases h : (c.get? p.1.toNat >>= EvmYul.EVM.parseInstr) with
    | none =>
      rw [djIter_stuck c p h, D_J_aux_stuck c p h, D_J_aux_stuck c p h]
    | some ci =>
      have e1 : D_J_aux (f + (m + 1)) c p.1 p.2
          = D_J_aux (f + m) c (N p.1 ci) (if ci = .JUMPDEST then p.2.push p.1 else p.2) := by
        show D_J_aux ((f + m) + 1) c p.1 p.2 = _
        simp only [D_J_aux, h]
      have e2 : djIter c (m + 1) p
          = djIter c m (N p.1 ci, if ci = .JUMPDEST then p.2.push p.1 else p.2) := by
        simp only [djIter, djStep, h]
      rw [e1, e2]
      exact D_J_aux_add c m f (N p.1 ci, if ci = .JUMPDEST then p.2.push p.1 else p.2)

theorem djIter_add (c : ByteArray) : ∀ (a b : ℕ) (p : UInt256 × Array UInt256),
    djIter c (a + b) p = djIter c b (djIter c a p)
  | 0, b, p => by simp [djIter]
  | a + 1, b, p => by
    rw [show a + 1 + b = (a + b) + 1 by omega]
    simp only [djIter]
    exact djIter_add c a b _

end GemJoin.DJ
