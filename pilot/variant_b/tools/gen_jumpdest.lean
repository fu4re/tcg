import GemJoin.JumpDest
open EvmYul EvmYul.EVM GemJoin.DJ

def lit (p : UInt256 × Array UInt256) : String :=
  s!"(⟨{p.1.toNat}⟩, #[{", ".intercalate (p.2.toList.map fun x => s!"⟨{x.toNat}⟩")}])"

def stopAt (c : ByteArray) : ℕ → UInt256 → ℕ
  | 0, _ => 0
  | n + 1, i => match c.get? i.toNat >>= parseInstr with
    | none => 0
    | some ci => stopAt c n (N i ci) + 1

def main1 : IO Unit := do
  let c := GemJoin.runtime
  let S := stopAt c 4000 ⟨0⟩
  let K := 25
  let mut p : UInt256 × Array UInt256 := (⟨0⟩, #[])
  let mut out := s!"-- S = {S}, chunk = {K}\n"
  let mut k := 0
  let mut done := 0
  let mut sizes : Array ℕ := #[]
  for _ in [0:1000] do
    if done ≥ S then break
    let n := min K (S - done)
    let q := djIter c n p
    out := out ++ s!"theorem chunk{k} : djIter GemJoin.runtime {n} {lit p} = {lit q} := by decide +kernel\n"
    sizes := sizes.push n
    p := q; done := done + n; k := k + 1
  out := out ++ s!"-- END {lit p}\n-- SIZES {sizes.toList}\n"
  IO.println out

#eval main1
