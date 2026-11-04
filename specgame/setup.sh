#!/usr/bin/env bash
# Install the pinned Specification Games toolchain into project-local paths.
#
#   .toolchain/bin/solc   solc 0.8.35+commit.47b9dedd, official static Linux release
#   .toolchain/bin/z3     z3 4.16.0, official x64-glibc-2.39 release (solc >= 0.8.29
#                         calls z3 as an external process found on PATH)
#   .venv/                Python 3.12 venv with pyrevm 0.3.7 (hash-pinned wheel)
#
# Idempotent: every step checks the pinned sha256 / version first and skips if
# already satisfied. Nothing is installed into /usr/local; the system-wide
# solc / z3 / forge are left untouched. sudo is used only for missing apt packages.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TC="$HERE/.toolchain"
VENV="$HERE/.venv"

SOLC_VERSION="0.8.35+commit.47b9dedd"
SOLC_URL="https://binaries.soliditylang.org/linux-amd64/solc-linux-amd64-v${SOLC_VERSION}"
SOLC_SHA256="fa8ac9a32d301ad023a36ee5a29f8e291fe3200c60244e43c142539e82a617f4"

Z3_VERSION="4.16.0"
Z3_DIST="z3-${Z3_VERSION}-x64-glibc-2.39"
Z3_URL="https://github.com/Z3Prover/z3/releases/download/z3-${Z3_VERSION}/${Z3_DIST}.zip"
Z3_ZIP_SHA256="7288c49a5bd6dbafd7b0b0d1f65956b91672da24b08f09242919af159be3418e"
Z3_BIN_SHA256="e583c4186a45e72411fa2cb2048401eed03f0f8e5f24694676a8f6271a50b765"

PYTHON="python3.12"
APT_PACKAGES=(ca-certificates curl unzip python3.12 python3.12-venv)

log() { printf 'setup: %s\n' "$*"; }
die() { printf 'setup: ERROR: %s\n' "$*" >&2; exit 1; }
sha256_of() { sha256sum "$1" | cut -d' ' -f1; }

[ "$(uname -s)" = Linux ] || die "Linux required (pinned binaries are linux-amd64)"
[ "$(uname -m)" = x86_64 ] || die "x86_64 required (pinned binaries are linux-amd64)"
if [ -r /etc/os-release ]; then
    . /etc/os-release
    [ "${ID:-}" = ubuntu ] && [ "${VERSION_ID:-}" = 24.04 ] \
        || log "warning: tested on Ubuntu 24.04 only, this is ${PRETTY_NAME:-unknown}"
fi

# --- 1. apt prerequisites (only the missing ones, only then sudo) ---
missing=()
for p in "${APT_PACKAGES[@]}"; do
    dpkg-query -W -f='${Status}' "$p" 2>/dev/null | grep -q 'install ok installed' || missing+=("$p")
done
if [ "${#missing[@]}" -gt 0 ]; then
    log "installing apt packages: ${missing[*]}"
    sudo apt-get update
    sudo DEBIAN_FRONTEND=noninteractive apt-get install -y --no-install-recommends "${missing[@]}"
else
    log "apt packages present (skip): ${APT_PACKAGES[*]}"
fi

mkdir -p "$TC/bin"

# Download $1 to $2 and verify sha256 $3; the target only appears when verified.
fetch() {
    local url="$1" dest="$2" want="$3" tmp
    tmp="$(mktemp "$dest.part.XXXXXX")"
    curl -sSfL --retry 3 -o "$tmp" "$url"
    local got; got="$(sha256_of "$tmp")"
    if [ "$got" != "$want" ]; then
        rm -f "$tmp"
        die "sha256 mismatch for $url: got $got, want $want"
    fi
    mv -f "$tmp" "$dest"
}

# --- 2. solc ---
SOLC="$TC/bin/solc"
if [ -x "$SOLC" ] && [ "$(sha256_of "$SOLC")" = "$SOLC_SHA256" ]; then
    log "solc $SOLC_VERSION present (skip)"
else
    log "downloading solc $SOLC_VERSION"
    fetch "$SOLC_URL" "$SOLC" "$SOLC_SHA256"
    chmod 0755 "$SOLC"
fi
"$SOLC" --version | grep -q "Version: ${SOLC_VERSION}\." || die "solc --version does not report $SOLC_VERSION"

# --- 3. z3 (external solver process for solc's SMTChecker) ---
Z3="$TC/bin/z3"
if [ -x "$Z3" ] && [ "$(sha256_of "$Z3")" = "$Z3_BIN_SHA256" ]; then
    log "z3 $Z3_VERSION present (skip)"
else
    log "downloading z3 $Z3_VERSION"
    zip="$TC/${Z3_DIST}.zip"
    fetch "$Z3_URL" "$zip" "$Z3_ZIP_SHA256"
    stage="$(mktemp -d "$TC/z3.stage.XXXXXX")"
    unzip -q "$zip" "${Z3_DIST}/bin/z3" "${Z3_DIST}/LICENSE.txt" -d "$stage"
    [ "$(sha256_of "$stage/${Z3_DIST}/bin/z3")" = "$Z3_BIN_SHA256" ] \
        || die "extracted z3 binary sha256 mismatch"
    install -m 0755 "$stage/${Z3_DIST}/bin/z3" "$Z3"
    install -m 0644 "$stage/${Z3_DIST}/LICENSE.txt" "$TC/z3-LICENSE.txt"
    rm -rf "$stage" "$zip"
fi
"$Z3" --version | grep -q "Z3 version ${Z3_VERSION} " || die "z3 --version does not report $Z3_VERSION"

# --- 4. Python venv + pyrevm (hash-pinned, binary wheel only) ---
if [ -x "$VENV/bin/python" ] && "$VENV/bin/python" -c 'import sys; sys.exit(sys.version_info[:2] != (3, 12))'; then
    log "venv $VENV present (skip)"
else
    log "creating venv $VENV"
    rm -rf "$VENV"
    "$PYTHON" -m venv "$VENV"
fi
if "$VENV/bin/python" -I -c 'import importlib.metadata as m, sys; sys.exit(m.version("pyrevm") != "0.3.7")' 2>/dev/null; then
    log "pyrevm 0.3.7 present (skip)"
else
    log "installing pyrevm from requirements.lock"
    "$VENV/bin/python" -m pip install --disable-pip-version-check --no-input --no-cache-dir \
        --require-hashes --only-binary=:all: --no-deps -r "$HERE/requirements.lock"
fi

log "done: solc=$SOLC z3=$Z3 python=$VENV/bin/python"
