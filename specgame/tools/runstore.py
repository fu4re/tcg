"""Storage of a candidate's raw Check record in runs/ (protocol.md 16.10, a
storage note, not a protocol change).

The record a run keeps per candidate is `check.json`: the full Check result,
including every check's raw solc output (about 360 KB per check on Vat). In
runs/ it is stored gzipped as `check.json.gz` (gzip of the same bytes,
deterministic: mtime 0), next to `check_summary.json` with the sha256 and size
of the uncompressed bytes, the combined verdict and the per-check verdicts,
reasons and walls. Readers accept both `check.json` and `check.json.gz`.
Bundles are unaffected: their hard layer keeps the per-check certificates as
they are.
"""
from __future__ import annotations

import gzip
import hashlib
import json
from pathlib import Path

CHECK_JSON = "check.json"
CHECK_GZ = "check.json.gz"
CHECK_SUMMARY = "check_summary.json"


def summary_of(data: bytes) -> dict:
    doc = json.loads(data)
    c = doc.get("check", doc)
    return {
        "version": 1,
        "check_json_sha256": hashlib.sha256(data).hexdigest(),
        "check_json_bytes": len(data),
        "stored_as": CHECK_GZ,
        "verdict": c["verdict"], "reason": c["reason"], "mode": c.get("mode"),
        "timeout_ms": c["timeout_ms"], "wall_timeout_s": c["wall_timeout_s"], "workers": c.get("workers"),
        "duration_s": c["duration_s"], "cpu_s": c["cpu_s"],
        "checks": [{"check": r["check"], "verdict": r["result"]["verdict"], "reason": r["result"]["reason"],
                    "duration_s": r["result"]["duration_s"],
                    "solc_input_sha256": r["result"]["solc_input_sha256"]} for r in c["checks"]],
    }


def write_check_record(cdir: Path, data: bytes) -> dict:
    """check.json.gz + check_summary.json for the raw `check.json` bytes."""
    (cdir / CHECK_GZ).write_bytes(gzip.compress(data, compresslevel=9, mtime=0))
    s = summary_of(data)
    (cdir / CHECK_SUMMARY).write_text(json.dumps(s, indent=1, sort_keys=True) + "\n")
    return s


def read_check_bytes(path: Path) -> bytes:
    """The uncompressed check.json bytes from `path` (check.json or
    check.json.gz); a missing check.json falls back to its .gz sibling."""
    path = Path(path)
    if path.suffix != ".gz" and not path.exists() and path.with_name(path.name + ".gz").exists():
        path = path.with_name(path.name + ".gz")
    data = path.read_bytes()
    return gzip.decompress(data) if path.suffix == ".gz" else data


def read_check_json(path: Path) -> dict:
    return json.loads(read_check_bytes(path))


def convert(cdir: Path) -> dict | None:
    """Retroactive: replace cdir/check.json by check.json.gz + summary, and
    check that the gzip decompresses to the original bytes."""
    src = cdir / CHECK_JSON
    if not src.exists():
        return None
    data = src.read_bytes()
    s = write_check_record(cdir, data)
    if read_check_bytes(cdir / CHECK_GZ) != data:
        raise RuntimeError(f"{cdir}: gzip round trip differs")
    src.unlink()
    return s


if __name__ == "__main__":
    import sys
    for d in sys.argv[1:]:
        r = convert(Path(d))
        print(f"{d}: {'converted, sha256 ' + r['check_json_sha256'][:16] + '…' if r else 'no check.json'}")
