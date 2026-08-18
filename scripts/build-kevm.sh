#!/usr/bin/env bash
# scripts/build-kevm.sh — get a usable kompiled KEVM (Haskell/proving backend)
# definition onto this machine for `tcg prove`.
#
# Strategy (in order, each step idempotent / best-effort):
#   1. Reuse ~/toolchains/kevm-1.0.678/{haskell,evm-semantics-source,plugin}
#      if they already look complete (checked per-component, not as a whole
#      — see haskell_ok/source_ok/plugin_ok below).
#   2. Search the local /nix/store for a kompiled KEVM Haskell-backend target
#      that a sibling package (kevm-pyk, via kontrol) already built, and copy
#      it out (the nix store is read-only and not a stable GC root, so we
#      must not point toolchain.lock directly into /nix/store).
#   3. If nothing is found, fall back to a real `kompile --backend haskell`
#      build from kevm-pyk's vendored K sources (also discovered in the nix
#      store), targeting edsl.md/EDSL — matching the prebuilt target's own
#      main module (see "module alignment" below), NOT evm.md/EVM.
#
# Nothing here is hardcoded to a /nix/store hash (those are not stable across
# updates/GC) or picked by "first glob match": every discovered path is
# either verified by shape (does it look like a kompiled Haskell backend?
# does it contain the file a `requires` statement names?) or by content
# (does it match the kevm version tcg/commands/init.py pins?), and any
# genuine ambiguity is a loud refusal, never a guess. See "version
# verification" below.
#
# Output layout (persistent, outside any git repo):
#   ~/toolchains/kevm-1.0.678/haskell/                 kompiled definition
#   ~/toolchains/kevm-1.0.678/evm-semantics-source/     K sources (requires "evm.md" etc.)
#   ~/toolchains/kevm-1.0.678/plugin/plugin/krypto.md   K crypto-hook declarations
#   ~/toolchains/kevm-1.0.678/provenance.json           resolved paths + hashes (see below)
#
# Drop into .tcg/toolchain.lock:
#   "definition": "<TOOLCHAIN>/haskell"
#   "includes": ["<TOOLCHAIN>/evm-semantics-source", "<TOOLCHAIN>/plugin"]
# (provenance.json prints these as ready-to-paste JSON at the end of a run.)
#
# Module alignment: the prebuilt target found on this machine is kompiled
# from edsl.md with main module EDSL (not evm.md/EVM) — EDSL transitively
# imports EVM, so specs using `requires "evm.md"` / `imports EVM` still work
# against it unmodified (empirically confirmed: every tests/control/*.k spec
# does exactly this). The fallback build in step 3 targets the SAME
# edsl.md/EDSL pair, so a from-source build produces an equivalent substrate
# under the same toolchain.lock shape instead of a silently different one.
#
# Copies use `cp -Rc` (APFS clonefile: near-instant, no extra disk) with a
# plain `cp -R` fallback on non-APFS filesystems.
set -euo pipefail

TOOLCHAIN_DIR="${TOOLCHAIN_DIR:-$HOME/toolchains/kevm-1.0.678}"
FORCE=0
for arg in "$@"; do
  case "$arg" in
    --force) FORCE=1 ;;
    *) echo "usage: $0 [--force]" >&2; exit 1 ;;
  esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

log() { echo "[build-kevm] $*" >&2; }
die() { echo "[build-kevm] ERROR: $*" >&2; exit 1; }

# force_rm PATH — `cp -Rc` (APFS clonefile) preserves the source's
# permissions, and /nix/store trees are read-only, so a partial or discarded
# clone can be un-removable until it's made writable first.
force_rm() {
  [[ -e "$1" ]] || return 0
  chmod -R u+w "$1" 2>/dev/null || true
  rm -rf "$1"
}

# report_paths — the one place the lock-ready definition/includes JSON is
# printed (used by both the fast-path exit and the end of a full run).
report_paths() {
  log "definition: $TOOLCHAIN_DIR/haskell"
  log "includes:   $TOOLCHAIN_DIR/evm-semantics-source , $TOOLCHAIN_DIR/plugin"
  cat <<EOF
{
  "definition": "$TOOLCHAIN_DIR/haskell",
  "includes": ["$TOOLCHAIN_DIR/evm-semantics-source", "$TOOLCHAIN_DIR/plugin"]
}
EOF
}

# --- per-component completeness (item: a missing 12KB krypto.md must never
# risk the intact 151MB definition) -- each takes the dir that should
# DIRECTLY contain the named marker file. ---
haskell_ok() { [[ -f "$1/definition.kore" ]] && [[ "$(cat "$1/backend.txt" 2>/dev/null)" == haskell* ]]; }
source_ok()  { [[ -f "$1/evm.md" ]]; }
plugin_ok()  { [[ -f "$1/krypto.md" ]]; }

# find_all GLOB MARKER — every dir matching GLOB that directly contains
# MARKER, one per line. The one generic store-discovery helper (used by
# every candidate search below instead of three near-identical loops).
find_all() {
  local glob="$1" marker="$2" d
  for d in $glob; do
    [[ -e "$d/$marker" ]] && printf '%s\n' "$d"
  done
  return 0
}

# copy_component SRC DST CHECK_FN LABEL — copy SRC to a temp sibling of DST,
# verify with CHECK_FN, only then atomically swap it into place. DST is
# never removed before the replacement exists and has been verified; a
# failed/incomplete copy is deleted without ever touching DST, and without
# touching any *other* component (haskell/source/plugin are swapped
# independently).
copy_component() {
  local src="$1" dst="$2" check_fn="$3" label="$4"
  mkdir -p "$(dirname "$dst")"
  local tmp="${dst%/}.tmp.$$"
  force_rm "$tmp"
  if ! cp -Rc "$src" "$tmp" 2>/dev/null; then
    force_rm "$tmp"
    log "$label: cp -Rc (APFS clonefile) unavailable, falling back to cp -R"
    cp -R "$src" "$tmp"
  fi
  chmod -R u+w "$tmp"
  if ! "$check_fn" "$tmp"; then
    force_rm "$tmp"
    die "$label: copy from $src looks incomplete; aborting without touching $dst"
  fi
  local old=""
  if [[ -e "$dst" ]]; then
    old="${dst%/}.old.$$"
    mv "$dst" "$old"
  fi
  mv "$tmp" "$dst"
  [[ -n "$old" ]] && force_rm "$old"
  log "$label: installed at $dst"
}

# ---------------------------------------------------------------------------
# Fast path: everything already present and complete, --force not given.
# Exits without touching /nix/store at all -- an already-working install
# must keep working even if the store paths it was built from are later
# garbage-collected.
if [[ "$FORCE" -eq 0 ]] \
    && haskell_ok "$TOOLCHAIN_DIR/haskell" \
    && source_ok "$TOOLCHAIN_DIR/evm-semantics-source" \
    && plugin_ok "$TOOLCHAIN_DIR/plugin/plugin"; then
  log "already present and complete: $TOOLCHAIN_DIR"
  report_paths
  exit 0
fi

# ---------------------------------------------------------------------------
# Version verification, source of truth: tcg/commands/init.py's TOOLCHAIN
# dict is the ONE place this repo pins the kevm version -- read it from
# there (not re-typed here) so the two can never drift silently.
EXPECTED_KEVM_VERSION="$(cd "$REPO_ROOT" && PYTHONPATH="$REPO_ROOT" python3 -c \
  'from tcg.commands.init import TOOLCHAIN; print(TOOLCHAIN["kevm"])')" \
  || die "could not read the pinned kevm version from tcg/commands/init.py"
log "pinned kevm version (tcg/commands/init.py TOOLCHAIN[\"kevm\"]): $EXPECTED_KEVM_VERSION"

# The version-tagged kevm-pyk package: ground truth for what
# EXPECTED_KEVM_VERSION's K sources actually look like. Nix package names
# are not a stable API, but a package literally named "kevm-pyk-<version>"
# containing the vendored K sources is as close to one as this ecosystem
# offers, so this is the one place a version *string* is trusted -- every
# other version claim below is verified by content diff against this.
# bash 3.2 (macOS system bash) has no `mapfile`/`readarray` (bash 4+) --
# read line-by-line into the array instead.
VERSIONED_SRC_CANDIDATES=()
while IFS= read -r line; do
  [[ -n "$line" ]] && VERSIONED_SRC_CANDIDATES+=("$line")
done < <(find_all \
  "/nix/store/*-kevm-pyk-${EXPECTED_KEVM_VERSION}/lib/python*/site-packages/kevm_pyk/kproj/evm-semantics" \
  evm.md)
case "${#VERSIONED_SRC_CANDIDATES[@]}" in
  0) die "no kevm-pyk-${EXPECTED_KEVM_VERSION} package with vendored K sources found under /nix/store; is kevm-pyk on this machine's nix profile? (\`which kevm\`)" ;;
  1) VERSIONED_SRC="${VERSIONED_SRC_CANDIDATES[0]}" ;;
  *)
    log "multiple kevm-pyk-${EXPECTED_KEVM_VERSION} source trees found -- refusing to guess:"
    printf '[build-kevm]   - %s\n' "${VERSIONED_SRC_CANDIDATES[@]}" >&2
    die "ambiguous kevm-pyk-${EXPECTED_KEVM_VERSION} source tree; disambiguate manually (e.g. \`nix-collect-garbage\` the stale one, or pin a store path explicitly)"
    ;;
esac
VERSIONED_KPROJ="$(dirname "$VERSIONED_SRC")"
VERSIONED_PLUGIN="$VERSIONED_KPROJ/plugin/plugin"
plugin_ok "$VERSIONED_PLUGIN" || die "kevm-pyk-${EXPECTED_KEVM_VERSION} package has no plugin/krypto.md at $VERSIONED_PLUGIN"
log "kevm-pyk-${EXPECTED_KEVM_VERSION} sources: $VERSIONED_SRC"

# ---------------------------------------------------------------------------
# Step 2: search for an already-kompiled Haskell KEVM target, by SHAPE
# (backend.txt == haskell, module EVM present) -- never by hash. If more
# than one candidate matches, refuse loudly rather than taking the first;
# for whichever single candidate is used, derive its source/plugin dirs
# from ITS OWN embedded Source(...) annotation (i.e. exactly what it was
# actually kompiled from), not from a separate glob -- then cross-check
# that embedded source's content against the version-tagged sources above
# to confirm it really is EXPECTED_KEVM_VERSION and refuse on mismatch.
DEF_SHAPE_CANDIDATES=()
while IFS= read -r line; do
  [[ -n "$line" ]] && DEF_SHAPE_CANDIDATES+=("$line")
done < <(find_all "/nix/store/*-kevm-*/evm-semantics/haskell" definition.kore)
DEF_CANDIDATES=()
for d in "${DEF_SHAPE_CANDIDATES[@]:-}"; do
  [[ -z "$d" ]] && continue
  haskell_ok "$d" || continue
  grep -q '^module EVM ' "$d/compiled.txt" 2>/dev/null || continue
  DEF_CANDIDATES+=("$d")
done

PREBUILT_DEF=""
PREBUILT_SRC=""
PREBUILT_PLUGIN=""
case "${#DEF_CANDIDATES[@]}" in
  0)
    log "no prebuilt Haskell-backend target found under /nix/store."
    ;;
  1)
    d="${DEF_CANDIDATES[0]}"
    # compiled.txt embeds each module's Source(...) file path; module EVM's
    # is inside the exact kevm_pyk package this definition was kompiled
    # from.
    embedded_evm_md="$(grep -m1 -o '/nix/store/[^) ]*/kevm_pyk/kproj/evm-semantics/evm\.md' "$d/compiled.txt" || true)"
    if [[ -z "$embedded_evm_md" || ! -f "$embedded_evm_md" ]]; then
      log "prebuilt target's embedded source path is missing or unreadable"
      log "  ($embedded_evm_md) -- cannot verify its version by content; refusing to use it silently."
    elif ! diff -q "$embedded_evm_md" "$VERSIONED_SRC/evm.md" >/dev/null 2>&1; then
      log "prebuilt target at $d was kompiled from:"
      log "  $embedded_evm_md"
      log "which differs from the pinned kevm-pyk-${EXPECTED_KEVM_VERSION} sources at:"
      log "  $VERSIONED_SRC/evm.md"
      die "prebuilt definition does not match the pinned kevm version; refusing (pass --force to re-derive, or fix the version pin)"
    else
      PREBUILT_DEF="$d"
      PREBUILT_SRC="$(dirname "$embedded_evm_md")"
      PREBUILT_PLUGIN="$(dirname "$PREBUILT_SRC")/plugin/plugin"
      plugin_ok "$PREBUILT_PLUGIN" || PREBUILT_PLUGIN=""
      log "found prebuilt Haskell-backend KEVM definition: $PREBUILT_DEF"
      log "content-verified against kevm-pyk-${EXPECTED_KEVM_VERSION}: OK"
    fi
    ;;
  *)
    log "multiple prebuilt Haskell-backend KEVM targets found -- refusing to guess:"
    printf '[build-kevm]   - %s\n' "${DEF_CANDIDATES[@]}" >&2
    die "ambiguous prebuilt definition (${#DEF_CANDIDATES[@]} candidates)"
    ;;
esac

# Fall back to the version-tagged sources/plugin if the prebuilt target's
# own embedded paths were unusable (still correct: those ARE the pinned
# sources, just not provably what this specific .kore was built from).
[[ -z "$PREBUILT_SRC" ]] && PREBUILT_SRC="$VERSIONED_SRC"
[[ -z "$PREBUILT_PLUGIN" ]] && PREBUILT_PLUGIN="$VERSIONED_PLUGIN"

# ---------------------------------------------------------------------------
# Install each component independently (item: a missing plugin file must
# never trigger deleting/recopying the intact definition).
if [[ "$FORCE" -eq 1 ]] || ! haskell_ok "$TOOLCHAIN_DIR/haskell"; then
  if [[ -n "$PREBUILT_DEF" ]]; then
    copy_component "$PREBUILT_DEF" "$TOOLCHAIN_DIR/haskell" haskell_ok "Haskell definition"
  else
    # --- Step 3: no prebuilt target -- kompile it ourselves (slow path). ---
    log "kompiling from source (Haskell/proving target only, not LLVM). This can"
    log "take well over an hour on a cold build; see docs/substrate.md for the"
    log "measured wall time on this machine (well under that in practice)."
    tmp_def="$TOOLCHAIN_DIR/haskell.tmp.$$"
    force_rm "$tmp_def"
    mkdir -p "$tmp_def"
    if ! kompile --backend haskell "$VERSIONED_SRC/edsl.md" \
        --main-module EDSL --syntax-module EDSL \
        -I "$VERSIONED_SRC" -I "$VERSIONED_KPROJ/plugin" \
        --md-selector "k & ! concrete" \
        --hook-namespaces "JSON KRYPTO" \
        --emit-json \
        -o "$tmp_def"; then
      force_rm "$tmp_def"
      die "kompile failed; see output above"
    fi
    if ! haskell_ok "$tmp_def"; then
      force_rm "$tmp_def"
      die "kompile finished but output does not look complete"
    fi
    old=""
    if [[ -e "$TOOLCHAIN_DIR/haskell" ]]; then
      old="$TOOLCHAIN_DIR/haskell.old.$$"
      mv "$TOOLCHAIN_DIR/haskell" "$old"
    fi
    mv "$tmp_def" "$TOOLCHAIN_DIR/haskell"
    [[ -n "$old" ]] && force_rm "$old"
    log "Haskell definition: kompiled and installed at $TOOLCHAIN_DIR/haskell"
    PREBUILT_SRC="$VERSIONED_SRC"
    PREBUILT_PLUGIN="$VERSIONED_PLUGIN"
  fi
else
  log "Haskell definition: already complete, keeping $TOOLCHAIN_DIR/haskell (pass --force to replace)"
fi

if [[ "$FORCE" -eq 1 ]] || ! source_ok "$TOOLCHAIN_DIR/evm-semantics-source"; then
  copy_component "$PREBUILT_SRC" "$TOOLCHAIN_DIR/evm-semantics-source" source_ok "K sources"
else
  log "K sources: already complete, keeping $TOOLCHAIN_DIR/evm-semantics-source"
fi

if [[ "$FORCE" -eq 1 ]] || ! plugin_ok "$TOOLCHAIN_DIR/plugin/plugin"; then
  copy_component "$PREBUILT_PLUGIN" "$TOOLCHAIN_DIR/plugin/plugin" plugin_ok "plugin (krypto.md)"
else
  log "plugin: already complete, keeping $TOOLCHAIN_DIR/plugin"
fi

chmod -R u+w "$TOOLCHAIN_DIR" 2>/dev/null || true

if ! haskell_ok "$TOOLCHAIN_DIR/haskell" || ! source_ok "$TOOLCHAIN_DIR/evm-semantics-source" \
    || ! plugin_ok "$TOOLCHAIN_DIR/plugin/plugin"; then
  die "finished but output does not look complete; inspect $TOOLCHAIN_DIR"
fi

# ---------------------------------------------------------------------------
# provenance.json: resolved store paths, the version cross-check result, and
# the definition's own content hash -- so a stale/replaced /nix/store input
# is at least detectable after the fact, even though toolchain.lock only
# records the (mutable, machine-local) ~/toolchains copy.
DEFINITION_SHA256="$(shasum -a 256 "$TOOLCHAIN_DIR/haskell/definition.kore" | cut -d' ' -f1)"
PROVENANCE="$TOOLCHAIN_DIR/provenance.json"
cat > "$PROVENANCE" <<EOF
{
  "kevm_version_pinned": "$EXPECTED_KEVM_VERSION",
  "kevm_version_source": "tcg/commands/init.py:TOOLCHAIN[\"kevm\"]",
  "resolved": {
    "prebuilt_definition_store_path": $( [[ -n "$PREBUILT_DEF" ]] && printf '"%s"' "$PREBUILT_DEF" || echo null ),
    "versioned_kevm_pyk_sources_store_path": "$VERSIONED_SRC",
    "definition_source_used": "$PREBUILT_SRC",
    "definition_plugin_used": "$PREBUILT_PLUGIN"
  },
  "definition_kore_sha256": "$DEFINITION_SHA256",
  "generated_by": "scripts/build-kevm.sh"
}
EOF
log "provenance: $PROVENANCE"

log "done."
report_paths
