import Lake
open Lake DSL

-- Variant B checker project: GemJoin ETH-A getters re-stated over EVMYulLean
-- and proved in Lean. The semantics is the vendored EVMYulLean
-- (pilot/variant_b/staging/semantics/evmyullean/upstream) with the kernel-transparency
-- patch applied by tools/prepare_semantics.sh into ./semantics/evmyullean.
package «variantB» where
  moreLeanArgs := #["-DautoImplicit=false"]
  moreServerOptions := #[⟨`autoImplicit, false⟩]

require evmyul from "semantics/evmyullean"

@[default_target]
lean_lib «GemJoin»
