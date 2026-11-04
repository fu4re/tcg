"""Build the WP5 fixture bundle (`make bundle-fixture`).

    python tests/fixtures/bundle/make_fixture.py [--out DIR]

Inputs (committed, self-contained; nothing is read from contracts/ or mutants/):

    inputs/CappedToken.sol           b: a copy of the placeholder contract
    inputs/Spec.sol                  phi: check_mint_adds + check_cap
    inputs/m01_mint_no_supply.sol    mint does not increase totalSupply
    inputs/m02_no_cap_check.sol      the cap require removed from mint
    inputs/m03_transfer_no_debit.sol transfer does not debit the sender (phi has no
                                     transfer check, so m03 survives: ms_cert 2/3)

This script runs search.py (seed SEED, budget BUDGET) to find a properness
sigma per mutant and a witness per mutant, writes inputs/mutants.json and
inputs/witnesses.json, and assembles the bundle with tools/bundle.py into
good/ (default). witnesses.json also carries one deliberately bad candidate:
m01's witness re-labelled as a witness for m03, so the bundle shows the
producer-side discard path (it lands in evidence.discarded, not in W).
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPECGAME = HERE.parent.parent.parent
sys.path.insert(0, str(SPECGAME / "tools"))
sys.path.insert(0, str(HERE))
import bundle  # noqa: E402
import search  # noqa: E402
import specgame_core as core  # noqa: E402

INPUTS = HERE / "inputs"
B = INPUTS / "CappedToken.sol"
SPEC = INPUTS / "Spec.sol"
MUTANTS = [
    ("m01_mint_no_supply.sol", "statement_deletion", "missing_state_update"),
    ("m02_no_cap_check.sol", "require_deletion", "missing_bound_check"),
    ("m03_transfer_no_debit.sol", "statement_deletion", "missing_state_update"),
]
SEED, BUDGET = 1, 400
ADVERSARY_ID = "wp5-fixture-search-v1"


def _json(path: Path, obj) -> None:
    path.write_text(json.dumps(obj, indent=1, sort_keys=True) + "\n")


def build_inputs() -> None:
    b = core.compile_artifact(B)
    spec_sha = core.sha256_file(SPEC)
    muts, wits = [], []
    for name, op, fc in MUTANTS:
        path = INPUTS / name
        ent = core.compile_artifact(path)
        sp = search.find_properness(core, b, ent, SEED, BUDGET)
        if sp is None:
            raise SystemExit(f"no properness sigma for {name} within {BUDGET}")
        ob, om = core.run_sequence(b, sp), core.run_sequence(ent, sp)
        muts.append({"id": ent["runtime_sha256"], "path": f"inputs/{name}", "source_sha256": ent["source_sha256"],
                     "operator": op, "fault_class": fc, "status": "included",
                     "properness": {"sigma": sp, "obs_base_sha256": ob.sha256(), "obs_mutant_sha256": om.sha256()},
                     "behavioural_duplicate_of": []})
        pair = core.compile_spec_over(SPEC, path)
        found = search.find_witness(core, pair, SEED, BUDGET)
        print(f"{name}: id {ent['runtime_sha256'][:12]}, properness {len(sp['txs'])} txs, "
              f"witness {'none within budget' if found is None else found[1]}")
        if found is not None:
            sigma, check = found
            wits.append({"version": 1, "mutant": ent["runtime_sha256"], "sigma": sigma,
                         "observed": {"spec_source_sha256": spec_sha, "pair_runtime_sha256": pair["runtime_sha256"],
                                      "check": check, "outcome": "violation"}})
    # Deliberately bad candidate: m01's witness presented against m03.
    m03 = muts[2]["id"]
    bad = json.loads(json.dumps(wits[0]))
    bad["mutant"] = m03
    bad["observed"]["pair_runtime_sha256"] = core.compile_spec_over(SPEC, INPUTS / MUTANTS[2][0])["runtime_sha256"]
    wits.append(bad)
    _json(INPUTS / "mutants.json", {"version": 1, "base": {"path": "inputs/CappedToken.sol",
                                                           "source_sha256": b["source_sha256"],
                                                           "runtime_sha256": b["runtime_sha256"]},
                                    "mutants": muts})
    _json(INPUTS / "witnesses.json", wits)


def bundle_args(out: Path) -> list[str]:
    return ["--out", str(out), "--artifact", str(B), "--spec", str(SPEC),
            "--mutants", str(INPUTS / "mutants.json"), "--root", str(HERE),
            "--witnesses", str(INPUTS / "witnesses.json"),
            "--adversary-id", ADVERSARY_ID, "--adversary-source", str(HERE / "search.py"),
            "--adversary-seed", str(SEED), "--adversary-budget", str(BUDGET)]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--out", type=Path, default=HERE / "good")
    ap.add_argument("--no-search", action="store_true", help="reuse the committed inputs/*.json")
    a = ap.parse_args()
    if not a.no_search:
        build_inputs()
    return bundle.main(bundle_args(a.out))


if __name__ == "__main__":
    sys.exit(main())
