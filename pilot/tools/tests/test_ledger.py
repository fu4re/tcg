"""Tests for pilot/tools/ledger.py and verify_ledger.py (stdlib unittest)."""
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEDGER = os.path.join(TOOLS, "ledger.py")
VERIFY = os.path.join(TOOLS, "verify_ledger.py")


def sh(args, cwd):
    return subprocess.run([sys.executable, *args], cwd=cwd, capture_output=True, text=True)


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        with open(os.path.join(self.d, "a.txt"), "w") as f:
            f.write("hello\n")

    def tearDown(self):
        self.tmp.cleanup()

    def lines(self):
        with open(os.path.join(self.d, "L.jsonl"), "rb") as f:
            return f.read().split(b"\n")[:-1]

    def run_event(self, *extra):
        return sh([LEDGER, "run", "--ledger", "L.jsonl", *extra], self.d)

    def test_run_records_hashes_and_chain(self):
        r = self.run_event("--in", "a.txt", "--out", "b.txt", "--",
                           "sh", "-c", "cat a.txt > b.txt")
        self.assertEqual(r.returncode, 0, r.stderr)
        r = self.run_event("--in", "b.txt", "--nondeterministic", "--", "sh", "-c", "exit 3")
        self.assertEqual(r.returncode, 3)  # wrapped exit code propagates
        l1, l2 = self.lines()
        e1, e2 = json.loads(l1), json.loads(l2)
        h = hashlib.sha256(b"hello\n").hexdigest()
        self.assertEqual(e1["seq"], 1)
        self.assertEqual(e1["prev"], "0" * 64)
        self.assertEqual(e1["inputs"], [{"path": "a.txt", "sha256": h}])
        self.assertEqual(e1["outputs"], [{"path": "b.txt", "sha256": h}])
        self.assertEqual(e1["argv"], ["sh", "-c", "cat a.txt > b.txt"])
        self.assertEqual(e1["cwd"], ".")
        self.assertTrue(e1["deterministic"])
        self.assertIsNotNone(e1["tool_hash"])
        self.assertTrue(e1["started"].endswith("Z") and e1["ended"].endswith("Z"))
        self.assertEqual(e2["seq"], 2)
        self.assertEqual(e2["prev"], hashlib.sha256(l1).hexdigest())
        self.assertEqual(e2["exit"], 3)
        self.assertFalse(e2["deterministic"])
        self.assertEqual(sh([VERIFY, "L.jsonl"], self.d).returncode, 0)

    def test_missing_input_appends_nothing(self):
        r = self.run_event("--in", "nope", "--", "true")
        self.assertEqual(r.returncode, 2)
        self.assertFalse(os.path.exists(os.path.join(self.d, "L.jsonl")))

    def test_missing_output_recorded_as_null(self):
        self.run_event("--out", "never.txt", "--", "true")
        self.assertEqual(json.loads(self.lines()[0])["outputs"],
                         [{"path": "never.txt", "sha256": None}])

    def test_options_after_double_dash_belong_to_command(self):
        self.run_event("--", "sh", "-c", "echo x", "--in", "zz")
        e = json.loads(self.lines()[0])
        self.assertEqual(e["argv"], ["sh", "-c", "echo x", "--in", "zz"])
        self.assertEqual(e["inputs"], [])

    def test_stdout_capture_is_an_output(self):
        self.run_event("--stdout", "o.txt", "--", "echo", "hi")
        e = json.loads(self.lines()[0])
        self.assertEqual(e["outputs"], [{"path": "o.txt",
                                         "sha256": hashlib.sha256(b"hi\n").hexdigest()}])

    def test_note_event(self):
        for n in ("p", "c"):
            with open(os.path.join(self.d, n), "w") as f:
                f.write(n)
        r = sh([LEDGER, "note", "--ledger", "L.jsonl", "--tool", "claude", "--model",
                "claude-opus-5-5", "--prompt", "p", "--completion", "c", "--text", "bt"], self.d)
        self.assertEqual(r.returncode, 0, r.stderr)
        e = json.loads(self.lines()[0])
        self.assertEqual(e["kind"], "note")
        self.assertFalse(e["deterministic"])
        self.assertEqual(e["model"], "claude-opus-5-5")
        self.assertEqual(e["prompt_sha256"], hashlib.sha256(b"p").hexdigest())
        self.assertEqual(e["completion_sha256"], hashlib.sha256(b"c").hexdigest())
        self.assertEqual(sh([VERIFY, "L.jsonl"], self.d).returncode, 0)

    def test_root_relative_paths(self):
        os.mkdir(os.path.join(self.d, "sub"))
        r = subprocess.run([sys.executable, LEDGER, "run", "--ledger", "../L.jsonl",
                            "--root", "..", "--in", "../a.txt", "--", "true"],
                           cwd=os.path.join(self.d, "sub"), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        e = json.loads(self.lines()[0])
        self.assertEqual(e["cwd"], "sub")
        self.assertEqual(e["inputs"][0]["path"], "a.txt")

    def test_tip(self):
        self.run_event("--", "true")
        r = sh([LEDGER, "tip", "--ledger", "L.jsonl"], self.d)
        seq, h = r.stdout.split()
        self.assertEqual(seq, "1")
        self.assertEqual(h, hashlib.sha256(self.lines()[0]).hexdigest())


class VerifyLedgerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        for i in range(3):
            sh([LEDGER, "run", "--ledger", "L.jsonl", "--", "echo", str(i)], self.d)
        self.path = os.path.join(self.d, "L.jsonl")
        with open(self.path, "rb") as f:
            self.data = f.read()

    def tearDown(self):
        self.tmp.cleanup()

    def verify(self, data):
        with open(self.path, "wb") as f:
            f.write(data)
        return sh([VERIFY, "L.jsonl"], self.d)

    def test_intact(self):
        r = self.verify(self.data)
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_edit_breaks_next_prev(self):
        r = self.verify(self.data.replace(b'"exit":0', b'"exit":1', 1))
        self.assertEqual(r.returncode, 1)
        self.assertIn("line 2: prev=", r.stdout)

    def test_deleted_line_breaks(self):
        ls = self.data.split(b"\n")
        r = self.verify(b"\n".join([ls[0], ls[2], b""]))
        self.assertEqual(r.returncode, 1)

    def test_fabricated_appended_line_with_wrong_prev(self):
        ev = json.loads(self.data.split(b"\n")[2])
        ev["seq"] = 4
        line = json.dumps(ev, sort_keys=True, separators=(",", ":")).encode()
        r = self.verify(self.data + line + b"\n")
        self.assertEqual(r.returncode, 1)
        self.assertIn("line 4: prev=", r.stdout)

    def test_noncanonical_rejected(self):
        ls = self.data.split(b"\n")
        pretty = json.dumps(json.loads(ls[2]), sort_keys=True).encode()  # spaces
        r = self.verify(b"\n".join([ls[0], ls[1], pretty, b""]))
        self.assertEqual(r.returncode, 1)
        self.assertIn("canonical", r.stdout)

    def test_truncated_rejected(self):
        self.assertEqual(self.verify(self.data[:-1]).returncode, 1)

    def test_empty_rejected(self):
        self.assertEqual(self.verify(b"").returncode, 1)


if __name__ == "__main__":
    unittest.main()
