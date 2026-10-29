import Lake
open Lake DSL

-- Lean certificate for claim-02 (GemJoin ETH-A ilk()) over EVMYulLean.
-- ./semantics/evmyullean is the bundle's semantics/evmyullean/upstream with
-- semantics/evmyullean/patches/0001..0005 applied (semantics/evmyullean/apply_patches.sh);
-- T_hat binds both trees by hash.
package «variantB» where
  moreLeanArgs := #["-DautoImplicit=false"]
  moreServerOptions := #[⟨`autoImplicit, false⟩]

require evmyul from "semantics/evmyullean"

@[default_target]
lean_lib «GemJoin»
