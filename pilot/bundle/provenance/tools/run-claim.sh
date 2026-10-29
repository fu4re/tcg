#!/usr/bin/env bash
# pilot/checker/run-claim.sh -- the single entry the verifier calls to
# re-discharge one KEVM claim inside the pinned checker image (DECISIONS D6,
# variant A).
#
# Usage:  run-claim.sh <claim.k> --spec-module <MODULE> [extra kprove args...]
#
# Runs, inside the image, exactly the kprove argv tcg's `prove` uses
# (tcg/commands/prove.py):
#   kprove <claim.k> --definition /opt/kevm/haskell --spec-module <MODULE>
#          -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin [extra...]
# with the claim's directory mounted read-only and a fresh scratch dir as cwd
# (tcg runs kprove with cwd = .tcg/build; a backend crash report lands there).
#
# Image selection is by IMAGE ID only, never by tag:
#   TCG_CHECKER_IMAGE_ID (env) or, if unset, the first line of IMAGE_ID next to
#   this script. Format: sha256:<64 hex>. The script refuses to run unless the
#   local image's Id equals it.
#
# Output: kprove's stdout/stderr pass through unchanged and the exit status is
# kprove's own. Accept iff exit 0 AND stdout contains #Top (tcg/verdict.py).
# This script judges nothing.
set -euo pipefail

usage() { echo "usage: $0 <claim.k> --spec-module <MODULE> [extra kprove args...]" >&2; exit 64; }
[[ $# -ge 1 ]] || usage
CLAIM="$1"; shift
[[ -f "$CLAIM" ]] || { echo "run-claim: no such claim file: $CLAIM" >&2; exit 64; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ID="${TCG_CHECKER_IMAGE_ID:-}"
if [[ -z "$IMAGE_ID" && -f "$SCRIPT_DIR/IMAGE_ID" ]]; then
  IMAGE_ID="$(head -1 "$SCRIPT_DIR/IMAGE_ID")"
fi
[[ "$IMAGE_ID" =~ ^sha256:[0-9a-f]{64}$ ]] \
  || { echo "run-claim: TCG_CHECKER_IMAGE_ID / IMAGE_ID must be sha256:<64 hex>, got '${IMAGE_ID}'" >&2; exit 64; }

LOCAL_ID="$(docker image inspect --format '{{.Id}}' "$IMAGE_ID" 2>/dev/null || true)"
if [[ "$LOCAL_ID" != "$IMAGE_ID" ]]; then
  echo "run-claim: checker image $IMAGE_ID is not loaded (docker image inspect gave '${LOCAL_ID}')." >&2
  echo "run-claim: load the pinned tarball first: docker load -i tcg-kevm-checker.tar" >&2
  exit 69
fi

CLAIM_DIR="$(cd "$(dirname "$CLAIM")" && pwd)"
CLAIM_FILE="$(basename "$CLAIM")"
SCRATCH="$(mktemp -d -t tcg-run-claim.XXXXXX)"
trap 'rm -rf -- "$SCRATCH"' EXIT

# --network none: re-discharge must not depend on anything outside the image.
# --memory=6g --cpus=2: hard per-container bound (VM rule after unbounded
# parallel containers hung the 4-vCPU VM). On the VM, callers must also hold a
# prover slot: ~/pilot-locks/with-slot.sh prover -- run-claim.sh ... (this
# script does not lock itself: a nested lock under an outer wrapper would
# take two slots and can deadlock).
# kprove runs as the caller's uid, so scratch output stays removable.
docker run --rm --platform linux/amd64 --network none --memory=6g --cpus=2 \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$CLAIM_DIR:/claim:ro" -v "$SCRATCH:/work" -w /work \
  "$IMAGE_ID" \
  kprove "/claim/$CLAIM_FILE" --definition /opt/kevm/haskell \
    -I /opt/kevm/evm-semantics-source -I /opt/kevm/plugin "$@"
