#!/bin/sh
# Derive the semantics the Lean certificates are checked against:
#   sh apply_patches.sh <dst>
# copies ./upstream (pristine EVMYulLean 56253eb4) to <dst> after checking it
# against TREE_SHA256.txt, then applies ./patches/*.patch in order.
# <dst> must not exist. Needs sh, find, sort, xargs, sha256sum, cmp, cp, patch.
set -eu
here=$(cd "$(dirname "$0")" && pwd)
dst=${1:?usage: apply_patches.sh <dst>}
[ ! -e "$dst" ] || { echo "$dst exists" >&2; exit 1; }
(cd "$here/upstream" && find . -type f | LC_ALL=C sort | xargs sha256sum) \
  | cmp -s - "$here/TREE_SHA256.txt" || { echo "pristine tree does not match TREE_SHA256.txt" >&2; exit 1; }
cp -a "$here/upstream" "$dst"
for p in "$here"/patches/*.patch; do
  [ -e "$p" ] || continue
  (cd "$dst" && patch -p1 --forward --quiet < "$p")
  echo "applied $(basename "$p") sha256=$(sha256sum "$p" | cut -d" " -f1)"
done
