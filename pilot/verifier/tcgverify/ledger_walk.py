"""tcg-ledger/0.1 chain walk (task 05 section 1), shared by the verifier's L4 and
tools/verify_ledger.py. Judges chain integrity only, never the truth of an event."""
from __future__ import annotations

import hashlib
import json

GENESIS = "0" * 64
FORMAT = "tcg-ledger/0.1"
REQUIRED = {
    "format": str, "kind": str, "seq": int, "prev": str, "tool": str,
    "inputs": list, "outputs": list, "started": str, "ended": str,
    "deterministic": bool,
}


def canonical(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False).encode("utf-8")


def _check_files(field: str, items, errs: list[str], n: int) -> None:
    for i, it in enumerate(items):
        if not (isinstance(it, dict) and isinstance(it.get("path"), str)
                and (it.get("sha256") is None or isinstance(it.get("sha256"), str))):
            errs.append(f"line {n}: {field}[{i}] must be {{path, sha256}}")


def walk(data: bytes) -> tuple[list[dict], list[str]]:
    """Return (events, errors). errors == [] iff the chain is intact."""
    events: list[dict] = []
    errs: list[str] = []
    if not data:
        return events, ["empty ledger"]
    if not data.endswith(b"\n"):
        errs.append("last line is not newline-terminated (truncated?)")
    prev_hash = GENESIS
    for n, raw in enumerate(data.split(b"\n")[:-1] if data.endswith(b"\n")
                            else data.split(b"\n"), start=1):
        try:
            ev = json.loads(raw)
        except ValueError as e:
            errs.append(f"line {n}: not JSON ({e})")
            prev_hash = hashlib.sha256(raw).hexdigest()
            continue
        if not isinstance(ev, dict):
            errs.append(f"line {n}: not a JSON object")
            prev_hash = hashlib.sha256(raw).hexdigest()
            continue
        if canonical(ev) != raw:
            errs.append(f"line {n}: not in canonical form")
        for k, t in REQUIRED.items():
            if not isinstance(ev.get(k), t) or (t is int and isinstance(ev.get(k), bool)):
                errs.append(f"line {n}: field {k!r} missing or not {t.__name__}")
        if ev.get("format") != FORMAT:
            errs.append(f"line {n}: format != {FORMAT}")
        if ev.get("kind") not in ("run", "note"):
            errs.append(f"line {n}: kind must be run|note")
        if ev.get("kind") == "run" and not isinstance(ev.get("argv"), list):
            errs.append(f"line {n}: run event without argv list")
        if ev.get("seq") != n:
            errs.append(f"line {n}: seq={ev.get('seq')!r}, expected {n}")
        if ev.get("prev") != prev_hash:
            errs.append(f"line {n}: prev={ev.get('prev')!r} != sha256(line {n - 1})={prev_hash}")
        _check_files("inputs", ev.get("inputs") or [], errs, n)
        _check_files("outputs", ev.get("outputs") or [], errs, n)
        events.append(ev)
        prev_hash = hashlib.sha256(raw).hexdigest()
    return events, errs
