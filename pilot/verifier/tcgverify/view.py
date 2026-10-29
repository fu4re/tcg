"""A hash-verified view of a bundle directory.

The verifier never reads the bundle directory directly after loading the
manifest: it copies every child whose bytes match the manifest hash into a
scratch directory and works only on that copy. Unlisted files and children
with wrong bytes are therefore invisible to L1-L4, so they can only make a
level fail, never pass.
"""
from __future__ import annotations

import json
import os
import shutil
import tempfile

from . import manifest as M


class View:
    def __init__(self, bundle_dir: str):
        self.bundle_dir = os.path.abspath(bundle_dir)
        self.manifest: dict | None = None
        self.load_error: str | None = None
        self.child_problems: list[str] = []
        self.good: set[str] = set()
        self._tmp = tempfile.TemporaryDirectory(prefix="tcg-view-")
        self.dir = os.path.join(self._tmp.name, "bundle")
        os.makedirs(self.dir)
        try:
            with open(os.path.join(self.bundle_dir, "manifest.json"), encoding="utf-8") as f:
                man = json.load(f)
            if not isinstance(man, dict) or not isinstance(man.get("children"), list):
                raise ValueError("manifest is not an object with a children list")
            if not all(isinstance(c, dict) and isinstance(c.get("path"), str) for c in man["children"]):
                raise ValueError("a child is not an object with a string path")
            self.manifest = man
        except (OSError, ValueError) as e:
            self.load_error = f"manifest.json unreadable: {e}"
            return
        self.child_problems, good = M.child_file_problems(man, self.bundle_dir)
        bad_paths = {p for p in good if M.validate(p, M.load_schema("manifest.schema.json")
                                                   ["$defs"]["child"]["properties"]["path"])}
        self.good = good - bad_paths
        for p in sorted(self.good):
            dst = os.path.join(self.dir, p)
            os.makedirs(os.path.dirname(dst), exist_ok=True)
            shutil.copyfile(os.path.join(self.bundle_dir, p), dst)

    def close(self):
        self._tmp.cleanup()

    def children(self, role: str | None = None) -> list[dict]:
        return [c for c in (self.manifest or {}).get("children", [])
                if role is None or c.get("role") == role]

    def path(self, rel: str) -> str | None:
        """Absolute path of a verified child in the view, or None."""
        return os.path.join(self.dir, rel) if rel in self.good else None

    def read(self, rel: str) -> bytes | None:
        p = self.path(rel)
        if p is None:
            return None
        with open(p, "rb") as f:
            return f.read()

    def json(self, rel: str):
        """(object, error). error is None iff the child is verified and parses."""
        data = self.read(rel)
        if data is None:
            return None, f"{rel}: absent or not hash-verified"
        try:
            return json.loads(data), None
        except ValueError as e:
            return None, f"{rel}: not JSON ({e})"

    def copy_to(self, dst: str) -> str:
        """A disposable copy of the view, for running bundle-supplied commands."""
        shutil.copytree(self.dir, dst)
        return dst
