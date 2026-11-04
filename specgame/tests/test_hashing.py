"""Identity by runtime hash: stable across staging directories and file names."""
import shutil
import tempfile
import unittest
from pathlib import Path

from tests._util import FALSE, TOKEN, core


class Hashing(unittest.TestCase):
    def test_sha256_and_canonical_json(self):
        self.assertEqual(core.sha256_hex(b""),
                         "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855")
        self.assertEqual(core.canonical_json({"b": 1, "a": [1, "x"]}), b'{"a":[1,"x"],"b":1}\n')
        self.assertEqual(core.json_sha256({"a": 1, "b": 2}), core.json_sha256({"b": 2, "a": 1}))

    def test_artifact_hash_stable_across_directories(self):
        h0 = core.compile_artifact(TOKEN)["runtime_sha256"]
        with tempfile.TemporaryDirectory() as t1, tempfile.TemporaryDirectory() as t2:
            p1 = Path(t1) / "a" / "CappedToken.sol"
            p1.parent.mkdir()
            p2 = Path(t2) / "mutant_m99.sol"
            shutil.copy(TOKEN, p1)
            shutil.copy(TOKEN, p2)
            self.assertEqual(core.compile_artifact(p1)["runtime_sha256"], h0)
            self.assertEqual(core.compile_artifact(p2)["runtime_sha256"], h0)

    def test_pair_hash_stable_and_distinct_from_artifact(self):
        e0 = core.compile_spec_over(FALSE, TOKEN)
        with tempfile.TemporaryDirectory() as t:
            s, a = Path(t) / "phi.sol", Path(t) / "b.sol"
            shutil.copy(FALSE, s)
            shutil.copy(TOKEN, a)
            e1 = core.compile_spec_over(s, a)
        self.assertEqual(e0["runtime_sha256"], e1["runtime_sha256"])
        self.assertNotEqual(e0["runtime_sha256"], core.compile_artifact(TOKEN)["runtime_sha256"])
        self.assertEqual(e0["checks"], ["check_reachable"])

    def test_source_change_changes_hash(self):
        text = TOKEN.read_text().replace('"cap exceeded"', '"cap exceeded!"')
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "m.sol"
            p.write_text(text)
            self.assertNotEqual(core.compile_artifact(p)["runtime_sha256"],
                                core.compile_artifact(TOKEN)["runtime_sha256"])

    def test_compile_error_raises(self):
        with tempfile.TemporaryDirectory() as t:
            p = Path(t) / "bad.sol"
            p.write_text("pragma solidity 0.8.35; contract CappedToken { function f( }")
            with self.assertRaises(core.CompileError):
                core.compile_artifact(p)


if __name__ == "__main__":
    unittest.main()
