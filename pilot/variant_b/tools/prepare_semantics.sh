#!/bin/sh
# Rebuild ./semantics/evmyullean (gitignored working copy) from the vendored
# pristine tree plus the reviewed patches (staging/semantics/evmyullean, via its
# apply_patches.sh, which refuses if the pristine tree no longer matches
# TREE_SHA256.txt).
set -eu
here=$(cd "$(dirname "$0")/.." && pwd)
src="$here/staging/semantics/evmyullean"
dst="$here/semantics/evmyullean"
rm -rf "$dst.new"
mkdir -p "$here/semantics"
sh "$src/apply_patches.sh" "$dst.new"
# keep the lake build dir of the previous copy so unchanged modules are not rebuilt
if [ -d "$dst/.lake" ]; then mv "$dst/.lake" "$dst.new/.lake"; fi
rm -rf "$dst"
mv "$dst.new" "$dst"
