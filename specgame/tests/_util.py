"""Shared test helpers: import path for tools/ and common file locations."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))

import specgame_core as core  # noqa: E402,F401
import speclint  # noqa: E402,F401

TOKEN = ROOT / "subjects" / "capped_token" / "CappedToken.sol"
TAUTOLOGY = ROOT / "smoke" / "ProvedTautology.sol"
FALSE = ROOT / "smoke" / "ReachableFalse.sol"
FIXTURES = ROOT / "tests" / "fixtures"
