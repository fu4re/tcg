"""Regenerate the captured solc outputs in tests/fixtures/smt/ (run by hand).

    .venv/bin/python -B tests/make_fixtures.py

Each fixture is {"sources": {...}, "timeout_ms": N, "toolchain": "...", "output": <solc JSON>}
so that the classifier tests run on real solc output without running solc.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import specgame_core as core  # noqa: E402

TOKEN = ROOT / "subjects" / "capped_token" / "CappedToken.sol"
OUT = ROOT / "tests" / "fixtures" / "smt"
CASES = {
    "proved": (ROOT / "smoke" / "ProvedTautology.sol", 20000, True),
    "counterexample": (ROOT / "smoke" / "ReachableFalse.sol", 20000, True),
    "might_happen": (OUT / "Nonlinear.sol", 1, True),
    "no_solver": (ROOT / "smoke" / "ProvedTautology.sol", 20000, False),
}


def main() -> None:
    tc = core.Toolchain.default()
    for name, (spec, timeout_ms, with_z3) in CASES.items():
        t = tc if with_z3 else core.Toolchain(tc.solc, None)
        sources = {core.SPEC_UNIT: spec.read_text(), core.ARTIFACT_UNIT: TOKEN.read_text()}
        out, _, _ = core.run_solc(core.solc_input(sources, core.model_checker_settings(timeout_ms)), t, 300)
        doc = {"sources": sources, "timeout_ms": timeout_ms, "with_z3": with_z3,
               "toolchain": f"solc {core.SOLC_VERSION}, z3 {core.Z3_VERSION if with_z3 else 'absent'}",
               "output": out}
        (OUT / f"{name}.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
        print(name, core.classify_smt_output(out, sources)[:2])


if __name__ == "__main__":
    main()
