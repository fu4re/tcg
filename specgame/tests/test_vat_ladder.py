"""Vat ladder texts: lint, phi_full = the textual union of the rungs, and an
execution sanity check on hand-written witnesses (b is never violated; every
mutant is killed by its intended rung and by phi_full). The kill sets the
experiment reports come from the adversary, not from these σ."""
import unittest

from tests._util import ROOT, core
from tests.test_vat_mutants import FILE3, FROB, RAD, WAD, sigma, tx

VAT = ROOT / "subjects" / "vat"
SPECS = VAT / "specs"
SUBJ = core.load_subject("vat")
RUNGS = ["phi_auth", "phi_consent", "phi_frob", "phi_frob_guards", "phi_fold", "phi_move_flux",
         "phi_grab_heal_suck", "phi_books"]
F11 = tx("alice", FROB, "GOLD", "alice", "alice", "alice", 1, 1)


def probe(sender, **kw):
    p = {"sender": sender, "a": "alice", "b": "bob", "x": "0", "y": "0",
         "i": "GOLD", "u": "alice", "dx": "0", "dy": "0"}
    p.update({k: str(v) for k, v in kw.items()})
    return p


# mutant -> (prefix txs, probe, rungs that must kill it on this σ)
HAND = {
    "m01_slip_no_auth": ([], probe("alice", dx=1), ["phi_auth"]),
    "m02_frob_no_consent_v": ([], probe("alice", u="carol", dx=1), ["phi_consent"]),
    "m03_frob_no_ceiling": ([tx("carol", FILE3, "GOLD", "line", 0)], probe("alice", dx=1, dy=1), ["phi_frob_guards"]),
    "m04_frob_no_safety": ([], probe("alice", dy=51 * WAD), ["phi_frob_guards"]),
    "m05_frob_no_dust": ([tx("carol", FILE3, "GOLD", "dust", 1000 * RAD)], probe("alice", dx=1, dy=1), ["phi_frob_guards"]),
    "m06_fold_no_debt": ([F11], probe("carol", u="bob", dx=1), ["phi_fold"]),
    "m07_move_no_debit": ([], probe("alice", x=1), ["phi_move_flux"]),
    "m08_grab_no_vice": ([F11], probe("carol", dx=-1, dy=-1), ["phi_grab_heal_suck"]),
}


class VatLadder(unittest.TestCase):
    def test_lint(self):
        import speclint
        b = core.compile_artifact(VAT / "Vat.sol", subject=SUBJ)
        names = speclint.names_from_entry(b)
        for p in sorted(SPECS.glob("phi_*.sol")):
            self.assertEqual(speclint.lint_spec(p.read_text(), names, SUBJ), [], p.name)

    def test_full_is_the_union(self):
        full = core.check_functions((SPECS / "phi_full.sol").read_text(), SUBJ)
        union = [c for r in RUNGS for c in core.check_functions((SPECS / f"{r}.sol").read_text(), SUBJ)]
        self.assertEqual(full, union)
        both = core.check_functions((SPECS / "phi_frob_both.sol").read_text(), SUBJ)
        self.assertEqual(both, [c for r in ("phi_frob", "phi_frob_guards")
                                for c in core.check_functions((SPECS / f"{r}.sol").read_text(), SUBJ)])

    def test_hand_witnesses(self):
        b = VAT / "Vat.sol"
        for name, (txs, p, rungs) in sorted(HAND.items()):
            s = {**sigma(txs), "probe": p}
            m = VAT / "mutants" / f"{name}.sol"
            for spec in rungs + ["phi_full"]:
                with self.subTest(mutant=name, spec=spec):
                    sp = SPECS / f"{spec}.sol"
                    self.assertTrue(core.evaluate_witness(core.compile_spec_over(sp, m, subject=SUBJ), s).violated)
                    self.assertFalse(core.evaluate_witness(core.compile_spec_over(sp, b, subject=SUBJ), s).violated)


if __name__ == "__main__":
    unittest.main()
