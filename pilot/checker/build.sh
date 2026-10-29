#!/usr/bin/env bash
# pilot/checker/build.sh -- build the variant-A checker image on the VM and
# pin it. Run once; a rebuild produces a DIFFERENT image (definition.kore is
# not byte-deterministic across kompiles), so the pin from the first good
# build is the checker identity and nobody rebuilds it.
#
# Usage:  pilot/checker/build.sh [OUT_DIR]      (default OUT_DIR=~/pilot-checker)
#
# Writes:
#   OUT_DIR/context/            the exact build context (Dockerfile + patches)
#   OUT_DIR/build.log           full `docker build` output, with wall time
#   OUT_DIR/tcg-kevm-checker.tar   `docker save` of the image (what a consumer loads)
#   OUT_DIR/pins.json           image Id, RepoDigests, docker save sha256,
#                               in-image provenance.json (definition.kore sha256)
#   pilot/checker/IMAGE_ID      the image Id, read by run-claim.sh
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="${1:-$HOME/pilot-checker}"
TAG="tcg-kevm-checker:lemmas2"   # convenience only; identity is the Id below
mkdir -p "$OUT/context/patches"

cp "$SCRIPT_DIR/Dockerfile" "$OUT/context/Dockerfile"
cp "$SCRIPT_DIR/patches/ghost.diff" "$SCRIPT_DIR/patches/lemmas2.diff" "$OUT/context/patches/"
( cd "$OUT/context" && sha256sum Dockerfile patches/* ) | tee "$OUT/context.sha256"

echo "[build] docker $(docker version --format '{{.Server.Version}}') on $(uname -m); building $TAG" >&2
start=$(date +%s)
docker build --platform linux/amd64 -t "$TAG" "$OUT/context" 2>&1 | tee "$OUT/build.log"
rc=${PIPESTATUS[0]}
end=$(date +%s)
echo "[build] docker build exit=$rc wall=$((end-start))s" | tee -a "$OUT/build.log" >&2
[[ $rc -eq 0 ]] || exit "$rc"

ID="$(docker image inspect --format '{{.Id}}' "$TAG")"
REPO_DIGESTS="$(docker image inspect --format '{{json .RepoDigests}}' "$TAG")"
ARCH="$(docker image inspect --format '{{.Os}}/{{.Architecture}}' "$TAG")"
SIZE="$(docker image inspect --format '{{.Size}}' "$TAG")"

docker save "$ID" -o "$OUT/tcg-kevm-checker.tar"
SAVE_SHA="$(sha256sum "$OUT/tcg-kevm-checker.tar" | cut -d' ' -f1)"
PROV="$(docker run --rm --network none "$ID" cat /opt/kevm/provenance.json)"
MANIFEST_SHA="$(docker run --rm --network none "$ID" sha256sum /opt/kevm/MANIFEST.sha256 | cut -d' ' -f1)"

cat > "$OUT/pins.json" <<JSON
{
  "image_id": "$ID",
  "repo_digests": $REPO_DIGESTS,
  "platform": "$ARCH",
  "size_bytes": $SIZE,
  "docker_save_sha256": "$SAVE_SHA",
  "docker_save_file": "tcg-kevm-checker.tar",
  "in_image_manifest_sha256": "$MANIFEST_SHA",
  "in_image_provenance": $PROV,
  "built_with_docker": "$(docker version --format '{{.Server.Version}}')",
  "built_at_utc": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "build_wall_seconds": $((end-start))
}
JSON
printf '%s\n' "$ID" > "$SCRIPT_DIR/IMAGE_ID"
cat "$OUT/pins.json"
