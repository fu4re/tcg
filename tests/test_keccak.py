"""tcg.keccak — pure-Python Keccak-256 (Ethereum's pre-NIST 0x01 padding).

Pinned against known Ethereum vectors. The bridge S<==D's code-identity check
(tcg.bridge) COMPUTES keccak256(callee code) and compares it to the declared
on-chain hash, so a correct digest is trust-critical; a silent swap to NIST
SHA3 (hashlib.sha3_256, 0x06 padding) would pass sha3 test vectors yet compute
the WRONG hash for every real contract. The last test guards exactly that.

Run: PYTHONPATH=. python3 -m unittest tests.test_keccak
"""
from __future__ import annotations

import hashlib
import unittest

from tcg.keccak import keccak256, keccak256_hex

# Pinned Ethereum keccak256 vectors (independently reproducible with eth-hash /
# pysha3; NOT hashlib.sha3_256, which is a different function).
VECTORS = {
    b"": "c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470",
    b"abc": "4e03657aea45a94fc7d47ba826c8d667c0d1e6e33a64a036ec44f58fa12d6c45",
    # the callext callee bytecode P (mini-slip, slot0 += 5)
    bytes.fromhex("60005460050160005500"):
        "a7d0eaef07694abd7dcad44e621c06a9dc7be164317d98d005a14caa63ecf512",
    # >1 sponge block (272 bytes > 136-byte rate) exercises the permutation loop
    bytes(range(256)):
        "dc924469b334aed2a19fac7252e9961aea41f8d91996366029dbe0884229bf36",
}


class TestKeccak256(unittest.TestCase):
    def test_pinned_vectors(self):
        for data, want in VECTORS.items():
            self.assertEqual(keccak256_hex(data), want,
                             f"keccak256 mismatch for {data[:8]!r}")

    def test_digest_is_32_bytes(self):
        self.assertEqual(len(keccak256(b"anything")), 32)

    def test_not_nist_sha3(self):
        # keccak256 != sha3_256 (different domain padding). If this ever passes
        # equal, someone swapped in hashlib.sha3 and every code-identity check
        # is silently wrong.
        for data in (b"", b"abc", bytes.fromhex("60005460050160005500")):
            self.assertNotEqual(keccak256_hex(data),
                                hashlib.sha3_256(data).hexdigest())


if __name__ == "__main__":
    unittest.main()
