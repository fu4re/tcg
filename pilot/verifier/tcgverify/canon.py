"""Hashing and canonical JSON (DECISIONS D1, D2). Stdlib only."""
from __future__ import annotations

import hashlib
import json
import os

EXCLUDED_FROM_ROOT = ("root_hash", "producer_sig")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def canonical(obj) -> bytes:
    """D2: sorted keys, no whitespace, UTF-8 (non-ASCII kept as UTF-8, e.g. φ).
    Floats are rejected: their text form is not canonical across producers."""
    def no_floats(o):
        if isinstance(o, float):
            raise ValueError("floats are not allowed in canonical JSON")
        if isinstance(o, dict):
            for v in o.values():
                no_floats(v)
        elif isinstance(o, list):
            for v in o:
                no_floats(v)
    no_floats(obj)
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def root_hash(manifest: dict) -> str:
    """D2: sha256 of the canonical JSON of the manifest without root_hash and producer_sig."""
    body = {k: v for k, v in manifest.items() if k not in EXCLUDED_FROM_ROOT}
    return sha256_bytes(canonical(body))


def tree_hash(root: str) -> str:
    """sha256 of canonical JSON [[relpath, sha256(file)], ...] over every regular
    file under `root`, sorted by '/'-separated relpath. Symlinks are refused."""
    entries = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames.sort()
        for name in dirnames + filenames:
            if os.path.islink(os.path.join(dirpath, name)):
                raise ValueError(f"symlink in tree: {os.path.join(dirpath, name)}")
        for name in filenames:
            full = os.path.join(dirpath, name)
            entries.append([os.path.relpath(full, root).replace(os.sep, "/"), sha256_file(full)])
    entries.sort()
    return sha256_bytes(canonical(entries))
