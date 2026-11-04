"""Tamper bundles, generated from the good fixture bundle (never stored twice).

    python tests/fixtures/bundle/tamper.py <good-bundle> <kind> <out-dir>
    python tests/fixtures/bundle/tamper.py --list

Every kind copies the good bundle and edits it. Unless the kind is about the
files table itself, the files table is rehashed after the edit ("consistent"
tamper): what is tested is then the verifier's semantic recomputation, not a
hash comparison. EXPECT maps each kind to (exit code, first failing step,
steps that must fail); test_verify.py asserts exactly that.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tools"))
import specgame_core as core  # noqa: E402

MANIFEST = "manifest.json"


def _load(d: Path) -> dict:
    return json.loads((d / MANIFEST).read_text())


def _save(d: Path, m: dict) -> None:
    (d / MANIFEST).write_text(json.dumps(m, indent=1, sort_keys=True) + "\n")


def _rehash(d: Path, m: dict) -> None:
    """Recompute the files table from the bytes on disk (consistent tamper)."""
    m["files"] = {p.relative_to(d).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in sorted(d.rglob("*")) if p.is_file() and p.relative_to(d).as_posix() != MANIFEST}


def _w_index(m: dict, check: str) -> int:
    return next(i for i, w in enumerate(m["evidence"]["W"]) if w["sigma"]["probe"].get("check") == check)


def swapped_witness(d: Path, m: dict) -> None:
    """Swap the sigma of the two witnesses: each now points to a mutant it does not kill."""
    W = m["evidence"]["W"]
    W[0]["sigma"], W[1]["sigma"] = W[1]["sigma"], W[0]["sigma"]
    _rehash(d, m)


def swapped_bytecode(d: Path, m: dict) -> None:
    """Replace the first killed mutant's source by b's source and relabel it
    consistently everywhere (new id = b's runtime sha256, file renamed, W,
    metadata, kill set, files table). The id check passes; only properness
    can catch it."""
    old = m["claimed"]["kill_set"][0]
    new = m["hard"]["b"]["runtime_sha256"]
    (d / f"mutants/{old}.sol").unlink()
    shutil.copyfile(d / m["hard"]["b"]["path"], d / f"mutants/{new}.sol")
    for e in m["evidence"]["M"] + m["metadata"]["mutants"] + m["evidence"]["W"]:
        for k in ("id", "mutant"):
            if e.get(k) == old:
                e[k] = new
        if e.get("path") == f"mutants/{old}.sol":
            e["path"] = f"mutants/{new}.sol"
    m["claimed"]["kill_set"] = sorted(new if k == old else k for k in m["claimed"]["kill_set"])
    _rehash(d, m)


def edited_ms_cert(d: Path, m: dict) -> None:
    """Claim every mutant killed (the files table needs no change: manifest.json is not in it)."""
    m["claimed"]["ms_cert"]["killed"] = m["claimed"]["ms_cert"]["total"]
    _rehash(d, m)


def dropped_properness(d: Path, m: dict) -> None:
    """Remove the properness pair of the first mutant."""
    m["evidence"]["M"][0]["properness_sigma"] = []
    _rehash(d, m)


def void_properness(d: Path, m: dict) -> None:
    """Replace the first mutant's properness sigma by one that does not separate
    it from b (deploy only, no transaction)."""
    s = m["evidence"]["M"][0]["properness_sigma"][0]
    s["txs"] = []
    _rehash(d, m)


def error_string_probe(d: Path, m: dict) -> None:
    """Make the check_mint_adds witness mint past the cap: the probe now ends in
    Error("cap exceeded") (pre_unmet), so the pair is discarded by the verifier."""
    w = m["evidence"]["W"][_w_index(m, "check_mint_adds")]
    w["sigma"]["probe"]["x"] = str(int(w["sigma"]["ctor"]["cap"]) + 1)
    _rehash(d, m)


def v_completeness_claim(d: Path, m: dict) -> None:
    """Add a V-completeness claim (the prototype never carries one)."""
    m["claimed"]["V-completeness"] = {"V": "access_control", "N": 3}
    _rehash(d, m)


def flipped_spec_byte(d: Path, m: dict) -> None:
    """Flip one byte of phi (s0 + x -> s0 - x); the files table is NOT rehashed."""
    p = d / m["hard"]["phi"]["path"]
    data = p.read_bytes()
    i = data.index(b"s0 + x")
    p.write_bytes(data[:i + 3] + b"-" + data[i + 4:])


def refuted_spec(d: Path, m: dict) -> None:
    """Replace phi by a spec b violates (cap check made strict: totalSupply < cap)
    and re-derive everything consistently: phi hashes, Spec-over-b id, the solc
    input file and its sha256, the verdict left at Accept. Only the re-run of
    Check can catch it."""
    phi, b = d / m["hard"]["phi"]["path"], d / m["hard"]["b"]["path"]
    phi.write_text(phi.read_text().replace("assert(totalSupply <= cap);", "assert(totalSupply < cap);"))
    c = m["hard"]["c"]
    texts = dict(core.check_functions(phi.read_text()))
    for row in c["checks"]:
        inp = core.solc_input({core.SPEC_UNIT: core.isolated_harness(texts[row["check"]]),
                               core.ARTIFACT_UNIT: b.read_text()}, core.model_checker_settings(c["timeout_ms"]))
        (d / row["solc_input_path"]).write_bytes(core.canonical_json(inp))
        row["solc_input_sha256"] = core.json_sha256(inp)
    m["hard"]["phi"]["source_sha256"] = core.sha256_file(phi)
    m["hard"]["phi"]["pair_runtime_sha256"] = core.compile_spec_over(phi, b)["runtime_sha256"]
    _rehash(d, m)


def foreign_toolchain(d: Path, m: dict) -> None:
    """Declare another pyrevm version in the semantics version: the bundle is not
    shown wrong, but this verifier cannot reproduce its semantics."""
    m["provenance"]["toolchain"]["pyrevm"] = "0.3.8"
    _rehash(d, m)


# kind -> (function, exit code, first failing step, steps that must fail)
KINDS = {
    "swapped_witness": (swapped_witness, 3, 5, {5}),
    "swapped_bytecode": (swapped_bytecode, 3, 3, {3, 5}),
    "edited_ms_cert": (edited_ms_cert, 3, 5, {5}),
    "dropped_properness": (dropped_properness, 3, 0, {0}),
    "void_properness": (void_properness, 3, 3, {3}),
    "error_string_probe": (error_string_probe, 3, 5, {5}),
    "v_completeness_claim": (v_completeness_claim, 3, 0, {0, 6}),
    "flipped_spec_byte": (flipped_spec_byte, 3, 1, {1}),
    "refuted_spec": (refuted_spec, 3, 2, {2}),
    "foreign_toolchain": (foreign_toolchain, 2, 1, {1}),
}


def make(good: Path, kind: str, out: Path) -> Path:
    if out.exists():
        shutil.rmtree(out)
    shutil.copytree(good, out)
    m = _load(out)
    KINDS[kind][0](out, m)
    _save(out, m)
    return out


def main(argv: list[str]) -> int:
    if argv[:1] == ["--list"]:
        for k, (f, code, first, _) in KINDS.items():
            print(f"{k:22s} exit {code}, first failing step {first}: {f.__doc__.splitlines()[0]}")
        return 0
    if len(argv) != 3 or argv[1] not in KINDS:
        print(__doc__, file=sys.stderr)
        return 1
    make(Path(argv[0]), argv[1], Path(argv[2]))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
