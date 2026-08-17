#!/usr/bin/env bash
# scripts/build-kevm.sh — get a usable kompiled KEVM (Haskell/proving backend)
# definition onto this machine for `tcg prove`.
#
# Strategy (in order, each step idempotent / best-effort):
#   1. Reuse ~/toolchains/kevm-1.0.678/haskell if it already looks complete.
#   2. Search the local /nix/store for a kompiled KEVM Haskell-backend target
#      that a sibling package (kevm-pyk, via kontrol) already built, and copy
#      it out (the nix store is read-only and not a stable GC root, so we
#      must not point toolchain.lock directly into /nix/store).
#   3. If nothing is found, fall back to a real `kompile --backend haskell`
#      build from kevm-pyk's vendored K sources (also discovered in the nix
#      store). This is the slow path (can take well over an hour on a full
#      dual-target build; this script only builds the Haskell proving target,
#      which is faster — see docs/substrate.md for the measured wall time).
#
# Output layout (persistent, outside any git repo):
#   ~/toolchains/kevm-1.0.678/haskell/               kompiled definition
#   ~/toolchains/kevm-1.0.678/evm-semantics-source/   K sources (requires "evm.md" etc.)
#   ~/toolchains/kevm-1.0.678/plugin/plugin/krypto.md K crypto-hook declarations
#
# Drop into .tcg/toolchain.lock:
#   "definition": "<TOOLCHAIN>/haskell"
#   "includes": ["<TOOLCHAIN>/evm-semantics-source", "<TOOLCHAIN>/plugin"]
#
# This script is best-effort: every external path is discovered, nothing is
# hardcoded to a specific /nix/store hash (those are not stable across
# updates/GC). Re-running is safe; existing output is left alone unless
# --force is passed.
set -uo pipefail

TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$HOME/toolchains/kevm-1.0.678}"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    *) echo "usage: $0 [--force]" >&2; exit 1 ;;
  esac
done

log() { echo "[build-kevm] $*" >&2; }

definition_looks_complete() {
  local dir="$1"
  [[ -f "$dir/haskell/definition.kore" ]] \
    && [[ -f "$dir/haskell/backend.txt" ]] \
    && [[ "$(cat "$dir/haskell/backend.txt" 2>/dev/null)" == haskell* ]] \
    && [[ -f "$dir/evm-semantics-source/evm.md" ]] \
    && [[ -f "$dir/plugin/plugin/krypto.md" ]]
}

if [[ "$FORCE" -eq 0 ]] && definition_looks_complete "$TOOLCHAIN_DIR"; then
  log "already present and looks complete: $TOOLCHAIN_DIR/haskell"
  log "definition: $TOOLCHAIN_DIR/haskell"
  log "includes:   $TOOLCHAIN_DIR/evm-semantics-source , $TOOLCHAIN_DIR/plugin"
  exit 0
fi

mkdir -p "$TOOLCHAIN_DIR"

# --- Step 2: search /nix/store for an already-kompiled Haskell KEVM target ---
# kontrol depends on kevm-pyk's KEVM build; on this machine that build lands
# fully compiled (definition.kore, compiled.txt, ...) under a package whose
# name matches "kevm-<rev>" and contains evm-semantics/{haskell,llvm,...}.
# We match on *shape* (backend.txt == "haskell" AND module EVM present in
# compiled.txt), never on a hash, since the hash is not stable.
find_prebuilt_haskell_dir() {
  local d backend
  for d in /nix/store/*-kevm-*/evm-semantics/haskell; do
    [[ -d "$d" ]] || continue
    backend="$(cat "$d/backend.txt" 2>/dev/null || true)"
    [[ "$backend" == haskell* ]] || continue
    [[ -f "$d/definition.kore" ]] || continue
    grep -q '^module EVM ' "$d/compiled.txt" 2>/dev/null || continue
    echo "$d"
    return 0
  done
  return 1
}

find_kevm_pyk_source_dir() {
  # kevm_pyk/kproj/evm-semantics — vendored K sources (evm.md, edsl.md, ...).
  # Prefer a package tree that HAS a lib/python*/site-packages layout (the
  # plain `kevm` package under kontrol's closure is bin-only).
  local d
  for d in /nix/store/*-kevm-pyk-*/lib/python*/site-packages/kevm_pyk/kproj/evm-semantics; do
    [[ -f "$d/evm.md" ]] && { echo "$d"; return 0; }
  done
  return 1
}

find_kevm_pyk_plugin_dir() {
  local d
  for d in /nix/store/*-kevm-pyk-*/lib/python*/site-packages/kevm_pyk/kproj/plugin/plugin; do
    [[ -f "$d/krypto.md" ]] && { echo "$d"; return 0; }
  done
  return 1
}

PREBUILT_DEF="$(find_prebuilt_haskell_dir || true)"
SRC_DIR="$(find_kevm_pyk_source_dir || true)"
PLUGIN_DIR="$(find_kevm_pyk_plugin_dir || true)"

if [[ -z "$SRC_DIR" || -z "$PLUGIN_DIR" ]]; then
  log "ERROR: could not find kevm_pyk sources under /nix/store (looked for"
  log "  */kevm-pyk-*/lib/python*/site-packages/kevm_pyk/kproj/{evm-semantics,plugin/plugin})."
  log "  Is kevm-pyk on this machine's nix profile? (\`which kevm\`, \`kevm --help\`)"
  exit 1
fi

if [[ -n "$PREBUILT_DEF" ]]; then
  log "found prebuilt Haskell-backend KEVM definition: $PREBUILT_DEF"
  log "copying to $TOOLCHAIN_DIR/haskell (nix store is read-only / not a GC root)"
  rm -rf "$TOOLCHAIN_DIR/haskell"
  cp -R "$PREBUILT_DEF" "$TOOLCHAIN_DIR/haskell"
else
  # --- Step 3: no prebuilt target — kompile it ourselves (slow path). ---
  log "no prebuilt Haskell-backend target found under /nix/store; kompiling from source."
  log "this builds ONLY the Haskell (proving) target (not the LLVM concrete-execution"
  log "target) — see docs/substrate.md for measured wall time on this machine."
  rm -rf "$TOOLCHAIN_DIR/haskell"
  mkdir -p "$TOOLCHAIN_DIR/haskell"
  kompile --backend haskell "$SRC_DIR/evm.md" \
    --main-module EVM --syntax-module EVM \
    -I "$SRC_DIR" -I "$PLUGIN_DIR" \
    --md-selector "k & ! concrete" \
    --hook-namespaces "JSON KRYPTO" \
    --emit-json \
    -o "$TOOLCHAIN_DIR/haskell"
fi

rm -rf "$TOOLCHAIN_DIR/evm-semantics-source"
cp -R "$SRC_DIR" "$TOOLCHAIN_DIR/evm-semantics-source"

mkdir -p "$TOOLCHAIN_DIR/plugin"
rm -rf "$TOOLCHAIN_DIR/plugin/plugin"
cp -R "$PLUGIN_DIR" "$TOOLCHAIN_DIR/plugin/plugin"

chmod -R u+w "$TOOLCHAIN_DIR"

if definition_looks_complete "$TOOLCHAIN_DIR"; then
  log "done."
  log "definition: $TOOLCHAIN_DIR/haskell"
  log "includes:   $TOOLCHAIN_DIR/evm-semantics-source , $TOOLCHAIN_DIR/plugin"
  exit 0
else
  log "ERROR: build finished but output does not look complete; inspect $TOOLCHAIN_DIR"
  exit 1
fi
