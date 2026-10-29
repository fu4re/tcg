import Lean

/-!
# `kernel_theorem`: a definitional equality checked by the kernel only

`kernel_theorem n : ∀ xs, a = b` adds the theorem `n` with proof
`fun xs => Eq.refl a`. The declaration goes through `addDecl`, so the Lean
kernel type-checks it: it is accepted only if `a` and `b` are definitionally
equal in the kernel. Nothing else is trusted; the elaborator's own `isDefEq`
(which is slower on these terms) is skipped. No axiom is introduced.
-/

open Lean Elab Command Meta

elab "kernel_theorem " n:ident " : " t:term : command => do
  let name := (← getCurrNamespace) ++ n.getId
  let (type, value) ← liftTermElabM do
    let type ← Term.elabType t
    Term.synthesizeSyntheticMVarsNoPostponing
    let type ← instantiateMVars type
    let value ← forallTelescope type fun xs body => do
      let some (_, lhs, _) := body.eq? | throwError "kernel_theorem: expected an equality, got{indentExpr body}"
      mkLambdaFVars xs (← mkEqRefl lhs)
    let value ← instantiateMVars value
    if type.hasMVar || value.hasMVar then throwError "kernel_theorem: unresolved metavariables"
    return (type, value)
  liftCoreM <| addDecl <| .thmDecl { name, levelParams := [], type, value }
