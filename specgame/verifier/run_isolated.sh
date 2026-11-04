#!/usr/bin/env bash
# Verify a bundle on the E1 "second machine": a container built from only the
# verifier sources, run with no network, a read-only root filesystem and the
# bundle mounted read-only at /bundle. The container never sees the workspace.
#
#   verifier/run_isolated.sh <bundle-dir> [<report.json>]
#
# Exit code = the verifier's: 0 HOLDS, 2 COULD NOT VERIFY, 3 REFUSED. A docker
# failure (build or run) is 2: the bundle was not verified.
set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"   # specgame/
[ $# -ge 1 ] && [ $# -le 2 ] || { echo "usage: $0 <bundle-dir> [<report.json>]" >&2; exit 2; }
[ -d "$1" ] || { echo "run_isolated: no bundle directory $1" >&2; exit 2; }
BUNDLE="$(cd "$1" && pwd -P)"
command -v docker >/dev/null || { echo "run_isolated: docker not found" >&2; exit 2; }

# Stage the build context: exactly the files the Dockerfile copies, nothing else.
STAGE="$(mktemp -d)"
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/tools"
cp "$HERE/setup.sh" "$HERE/requirements.lock" "$HERE/protocol.json" "$STAGE/"
cp -r "$HERE/schemas" "$STAGE/schemas"
for prof in "$HERE"/subjects/*/profile.json; do
    d="$STAGE/subjects/$(basename "$(dirname "$prof")")"; mkdir -p "$d"; cp "$prof" "$d/"
done
cp "$HERE/tools/specgame_core.py" "$HERE/tools/verify.py" "$STAGE/tools/"
cp "$HERE/verifier/Dockerfile" "$STAGE/Dockerfile"
CTX_SHA="$(cd "$STAGE" && find . -type f -print0 | LC_ALL=C sort -z | xargs -0 sha256sum | sha256sum | cut -c1-12)"
IMAGE="specgame-verifier:$CTX_SHA"

echo "run_isolated: build context $(cd "$STAGE" && find . -type f | LC_ALL=C sort | tr '\n' ' ')" >&2
docker build -q -t "$IMAGE" "$STAGE" >&2 || { echo "run_isolated: docker build failed" >&2; exit 2; }

MOUNTS=(-v "$BUNDLE:/bundle:ro")
ARGS=()
if [ $# -eq 2 ]; then
    REPORT_DIR="$(mkdir -p "$(dirname "$2")" && cd "$(dirname "$2")" && pwd -P)"
    MOUNTS+=(-v "$REPORT_DIR:/out")
    ARGS+=(--json "/out/$(basename "$2")")
fi
echo "run_isolated: docker run $IMAGE (network none, read-only rootfs, bundle $BUNDLE -> /bundle:ro)" >&2
set +e
docker run --rm --network none --read-only --tmpfs /tmp --user "$(id -u):$(id -g)" \
    "${MOUNTS[@]}" "$IMAGE" "${ARGS[@]}"
code=$?
set -e
case $code in
    0|2|3) exit $code ;;
    *) echo "run_isolated: container exited $code (not a verifier exit code)" >&2; exit 2 ;;
esac
