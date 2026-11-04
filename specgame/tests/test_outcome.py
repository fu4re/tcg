"""Outcome rule (Condition D) on crafted revert data."""
import unittest

from tests._util import core

O = core.Outcome


def panic(code: int) -> bytes:
    return bytes.fromhex("4e487b71") + code.to_bytes(32, "big")


def error_string(msg: bytes) -> bytes:
    n = len(msg)
    return (bytes.fromhex("08c379a0") + (32).to_bytes(32, "big") + n.to_bytes(32, "big")
            + msg + bytes((32 - n % 32) % 32))


class OutcomeRule(unittest.TestCase):
    def test_success(self):
        self.assertIs(core.classify_outcome(None), O.SUCCESS)

    def test_panic_assert_is_violation(self):
        self.assertIs(core.classify_outcome(panic(0x01)), O.VIOLATION)

    def test_other_panics_are_other(self):
        for code in (0x00, 0x11, 0x12, 0x21, 0x22, 0x31, 0x32, 0x41, 0x51, 0x101):
            self.assertIs(core.classify_outcome(panic(code)), O.OTHER, hex(code))

    def test_error_string_is_pre_unmet(self):
        self.assertIs(core.classify_outcome(error_string(b"not owner")), O.PRE_UNMET)
        self.assertIs(core.classify_outcome(error_string(b"")), O.PRE_UNMET)
        self.assertIs(core.classify_outcome(error_string(b"x" * 64)), O.PRE_UNMET)

    def test_empty_revert_is_pre_unmet(self):
        self.assertIs(core.classify_outcome(b""), O.PRE_UNMET)

    def test_malformed_and_custom_are_other(self):
        good = error_string(b"not owner")
        cases = {
            "custom error selector only": bytes.fromhex("30cd7471"),
            "custom error with arg": bytes.fromhex("30cd7471") + bytes(32),
            "Error(string) truncated": good[:-1],
            "Error(string) bad offset": good[:4] + (64).to_bytes(32, "big") + good[36:],
            "Error(string) dirty padding": good[:-1] + b"\x01",
            "Panic(0x01) with trailing byte": panic(0x01) + b"\x00",
            "Panic selector short": panic(0x01)[:35],
            "4 random bytes": b"\xde\xad\xbe\xef",
        }
        for name, data in cases.items():
            self.assertIs(core.classify_outcome(data), O.OTHER, name)

    def test_describe_is_not_a_verdict(self):
        self.assertEqual(core.describe_revert(panic(0x11)), "Panic(0x11)")
        self.assertEqual(core.describe_revert(error_string(b"cap exceeded")), 'Error("cap exceeded")')


if __name__ == "__main__":
    unittest.main()
