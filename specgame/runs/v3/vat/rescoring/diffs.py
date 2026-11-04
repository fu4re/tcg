"""The two weakening diffs quoted in REPORT.md 4.5, extracted from the committed specs.

    python runs/v3/vat/rescoring/diffs.py   (from specgame/)   -> weakening_diffs.md
"""
import difflib
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import specgame_core as core  # noqa: E402

V = core.load_subject("vat")
CASES = [
    ("fM/seed_0", "runs/v3/vat/fM/seed_0/round_2/cand_2/Spec.sol", ["check_grab_sin_up", "check_grab_sin_down"],
     "runs/v3/vat/fM/seed_0/round_3/cand_2/Spec.sol", ["check_grab_debt_unchanged"]),
    ("f0/seed_0", "runs/v3/vat/f0/seed_0/round_2/cand_1/Spec.sol", ["check_grab_sin"],
     "runs/v3/vat/f0/seed_0/round_3/cand_1/Spec.sol", ["check_grab_sin_up"]),
]
out = ["# Round 2 -> 3 weakening diffs (grab checks)\n"]
for name, a, fa, b, fb in CASES:
    ta, tb = dict(core.check_functions((ROOT / a).read_text(), V)), dict(core.check_functions((ROOT / b).read_text(), V))
    left = "\n\n".join(ta[f] for f in fa).splitlines()
    right = "\n\n".join(tb[f] for f in fb).splitlines()
    out.append(f"## {name}\n\n`{a}` ({', '.join(fa)}) -> `{b}` ({', '.join(fb)})\n")
    out.append("```diff")
    out += list(difflib.unified_diff(left, right, a, b, lineterm="", n=50))
    out.append("```\n")
(HERE / "weakening_diffs.md").write_text("\n".join(out) + "\n")
print("\n".join(out))
