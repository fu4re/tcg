"""runs/ storage of raw Check records (protocol.md 16.10): check.json.gz is a
deterministic gzip of the same bytes, check_summary.json carries their
sha256, and readers accept both forms."""
import gzip
import hashlib
import json
import tempfile
import unittest
from pathlib import Path

from tests._util import ROOT

import runstore  # noqa: E402

DOC = {"spec": "Spec.sol", "mode": "isolated",
       "check": {"verdict": "Unknown", "reason": "unproved", "mode": "isolated", "timeout_ms": 60000,
                 "wall_timeout_s": 600, "workers": 4, "duration_s": 1.5, "cpu_s": 2.0,
                 "checks": [{"check": "check_a", "result": {"verdict": "Accept", "reason": "all_targets_safe",
                                                            "duration_s": 0.5, "solc_input_sha256": "aa",
                                                            "raw_output": "x" * 1000}},
                            {"check": "check_b", "result": {"verdict": "Unknown", "reason": "unproved",
                                                            "duration_s": 1.0, "solc_input_sha256": "bb",
                                                            "raw_output": "y" * 1000}}]}}


class RunStore(unittest.TestCase):
    def test_round_trip_summary_and_determinism(self):
        data = (json.dumps(DOC, indent=1, sort_keys=True) + "\n").encode()
        with tempfile.TemporaryDirectory() as t:
            a, b = Path(t) / "a", Path(t) / "b"
            a.mkdir(), b.mkdir()
            s = runstore.write_check_record(a, data)
            runstore.write_check_record(b, data)
            self.assertEqual((a / runstore.CHECK_GZ).read_bytes(), (b / runstore.CHECK_GZ).read_bytes())
            self.assertEqual(gzip.decompress((a / runstore.CHECK_GZ).read_bytes()), data)
            self.assertEqual(s["check_json_sha256"], hashlib.sha256(data).hexdigest())
            self.assertEqual([(c["check"], c["verdict"], c["reason"]) for c in s["checks"]],
                             [("check_a", "Accept", "all_targets_safe"), ("check_b", "Unknown", "unproved")])
            # both forms, and the plain name falling back to the .gz sibling
            self.assertEqual(runstore.read_check_json(a / runstore.CHECK_GZ), DOC)
            self.assertEqual(runstore.read_check_json(a / runstore.CHECK_JSON), DOC)
            (b / runstore.CHECK_JSON).write_bytes(data)
            self.assertEqual(runstore.read_check_json(b / runstore.CHECK_JSON), DOC)

    def test_convert_replaces_plain_file(self):
        data = (json.dumps(DOC) + "\n").encode()
        with tempfile.TemporaryDirectory() as t:
            d = Path(t)
            (d / runstore.CHECK_JSON).write_bytes(data)
            s = runstore.convert(d)
            self.assertFalse((d / runstore.CHECK_JSON).exists())
            self.assertEqual(runstore.read_check_bytes(d / runstore.CHECK_JSON), data)
            self.assertEqual(s["check_json_bytes"], len(data))

    def test_v3_runs_use_the_gz_layout(self):
        runs = ROOT / "runs" / "v3"
        self.assertEqual(sorted(runs.rglob("check.json")), [])
        gz = sorted(runs.rglob(runstore.CHECK_GZ))
        self.assertGreaterEqual(len(gz), 7)
        for g in gz:
            s = json.loads((g.parent / runstore.CHECK_SUMMARY).read_text())
            self.assertEqual(hashlib.sha256(runstore.read_check_bytes(g)).hexdigest(), s["check_json_sha256"], g)
