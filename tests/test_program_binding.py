"""P0-A/P0-B pure helpers: program-cell extraction, root program binding, and
the vacuity-probe postcondition mutation (tcg.claims).

All pure text — no prover. The prover-in-the-loop demonstrations (a vacuous
claim actually refused end-to-end, a program!=subject bundle refused at verify)
live in scripts/false-green.sh and scripts/conformance.sh, which run the real
Haskell backend. Run: PYTHONPATH=. python3 -m unittest tests.test_program_binding
"""
from __future__ import annotations

import unittest
from pathlib import Path

from tcg.claims import (
    check_claim_body, emit_module, extract_body, extract_program_bytes,
    falsify_body, program_binding_error,
)

REPO = Path(__file__).resolve().parents[1]
SUBJECT = bytes.fromhex("604660005500")


def module(body: str, loop="withdraw", label="main") -> str:
    return emit_module(loop, label, ["evm.md"], ["EVM"], body)


class TestExtractProgramBytes(unittest.TestCase):
    def test_parsebytestack_bare_hex(self):
        m = module('claim <k> A => B </k> <program> #parseByteStack("604660005500") '
                   '</program>\n [label(main), all-path]')
        self.assertEqual(extract_program_bytes(m), SUBJECT)

    def test_parsebytestack_0x_prefixed(self):
        m = module('claim <k> A => B </k> <program> #parseByteStack("0x604660005500") '
                   '</program>\n [label(main), all-path]')
        self.assertEqual(extract_program_bytes(m), SUBJECT)

    def test_bare_hex_literal(self):
        m = module('claim <k> A => B </k> <program> 604660005500 </program>\n '
                   '[label(main), all-path]')
        self.assertEqual(extract_program_bytes(m), SUBJECT)

    def test_program_cell_rewrite_binds_on_initial(self):
        # If the <program> cell rewrites, the INSTALLED (left) program binds.
        m = module('claim <k> A => B </k> <program> #parseByteStack("604660005500") '
                   '=> #parseByteStack("00") </program>\n [label(main), all-path]')
        self.assertEqual(extract_program_bytes(m), SUBJECT)

    def test_no_program_cell_is_none(self):
        m = module('claim <k> #execute ~> _ </k>\n [label(main), all-path]')
        self.assertIsNone(extract_program_bytes(m))

    def test_odd_length_hex_is_none(self):
        m = module('claim <k> A => B </k> <program> #parseByteStack("abc") </program>\n '
                   '[label(main), all-path]')
        self.assertIsNone(extract_program_bytes(m))

    def test_reference_root_matches_committed_subject(self):
        body = (REPO / "tests/reference/src/withdraw/main.k").read_text()
        m = emit_module("withdraw", "main", ["evm.md"], ["EVM"], body)
        hexpath = (REPO / "tests/reference/subject/runtime.hex").read_text().strip()
        self.assertEqual(extract_program_bytes(m), bytes.fromhex(hexpath))


class TestProgramBindingError(unittest.TestCase):
    def test_match_is_none(self):
        m = module('claim <k> A => B </k> <program> #parseByteStack("604660005500") '
                   '</program>\n [label(main), all-path]')
        self.assertIsNone(program_binding_error(m, SUBJECT))

    def test_mismatch_is_reason(self):
        m = module('claim <k> A => B </k> <program> #parseByteStack("00") </program>\n '
                   '[label(main), all-path]')
        reason = program_binding_error(m, SUBJECT)
        self.assertIsNotNone(reason)
        self.assertIn("does not match subject/runtime.bin", reason)

    def test_no_program_is_reason_naming_the_fix(self):
        # The exact G3 vacuous-claim shape: no <program> cell at all.
        m = module('claim <k> #execute ~> _ </k>\n [label(debit), all-path]',
                   loop="demo", label="debit")
        reason = program_binding_error(m, SUBJECT)
        self.assertIsNotNone(reason)
        self.assertIn("no extractable <program> cell", reason)
        self.assertIn("#parseByteStack", reason)


class TestFalsifyBody(unittest.TestCase):
    def test_appends_ensures_false_and_keeps_form(self):
        body = ('claim <k> A => B </k> <program> #parseByteStack("00") </program>\n'
                ' [label(main), all-path]')
        mut = falsify_body(body)
        self.assertIn("ensures false", mut)
        # form discipline still holds (all-path + label preserved)
        self.assertEqual(check_claim_body(mut, "main"), [])

    def test_keeps_requires_drops_existing_ensures(self):
        body = ('claim <k> A => B </k>\n requires X >Int 0\n ensures Y ==Int 1\n'
                ' [label(main), all-path]')
        mut = falsify_body(body)
        self.assertIn("requires X >Int 0", mut)   # antecedent kept
        self.assertIn("ensures false", mut)         # postcondition falsified
        self.assertNotIn("Y ==Int 1", mut)          # old post dropped
        # exactly one ensures clause
        self.assertEqual(mut.count("ensures"), 1)

    def test_reference_root_falsifies_to_valid_claim(self):
        body = (REPO / "tests/reference/src/withdraw/main.k").read_text()
        mut = falsify_body(body)
        self.assertEqual(check_claim_body(mut, "main"), [])
        self.assertIn("ensures false", mut)
        # the <program> cell (antecedent) is untouched by the mutation
        self.assertEqual(extract_program_bytes(emit_module(
            "withdraw", "main", ["evm.md"], ["EVM"], mut)), SUBJECT)


if __name__ == "__main__":
    unittest.main()
