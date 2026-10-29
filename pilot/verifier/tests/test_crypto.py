"""ed25519 (RFC 8032) verification: RFC vectors, plus a cross-test against
signatures produced by `openssl pkeyutl -sign -rawin` with throwaway keys."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tcgverify import ed25519  # noqa: E402

OPENSSL = shutil.which("openssl")
# RFC 8032 section 7.1, TEST 1 / TEST 2 / TEST 3 (public key, message, signature).
RFC_VECTORS = [
    ("d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a", "",
     "e5564300c360ac729086e2cc806e828a84877f1eb8e5d974d873e065224901555fb8821590a33bacc61e39701cf9b46bd25bf5f0595bbe24655141438e7a100b"),
    ("3d4017c3e843895a92b70aa74d1b7ebc9c982ccf2ec4968cc0cd55f12af4660c", "72",
     "92a009a9f0d4cab8720e820b5f642540a2b27b5416503f8fb3762223ebdb69da085ac1e43e15996e458f3613d0f11d8c387b2eaeb4302aeeb00d291612bb0c00"),
    ("fc51cd8e6218a1a38da47ed00230f0580816ed13ba3303ac5deb911548908025", "af82",
     "6291d657deec24024827e69c3abe01a30ce548a284743a445e3680d7db5ac3ac18ff9b538d16f290ae67f760984dc6594a7c15e9716ed28dc027beceea1ec40a"),
]


class RfcVectors(unittest.TestCase):
    def test_vectors_verify(self):
        for pk, msg, sig in RFC_VECTORS:
            self.assertTrue(ed25519.verify(bytes.fromhex(pk), bytes.fromhex(msg), bytes.fromhex(sig)))

    def test_tampering_rejected(self):
        pk, msg, sig = (bytes.fromhex(x) for x in RFC_VECTORS[1])
        self.assertFalse(ed25519.verify(pk, b"\x73", sig))
        bad = bytearray(sig)
        bad[5] ^= 1
        self.assertFalse(ed25519.verify(pk, msg, bytes(bad)))
        self.assertFalse(ed25519.verify(bytes.fromhex(RFC_VECTORS[0][0]), msg, sig))

    def test_s_not_reduced_rejected(self):
        pk, msg, sig = (bytes.fromhex(x) for x in RFC_VECTORS[0])
        s = int.from_bytes(sig[32:], "little") + ed25519.L
        self.assertFalse(ed25519.verify(pk, msg, sig[:32] + s.to_bytes(32, "little")))

    def test_bad_lengths(self):
        self.assertFalse(ed25519.verify(b"\x00" * 31, b"", b"\x00" * 64))
        self.assertFalse(ed25519.verify(b"\x00" * 32, b"", b"\x00" * 63))


@unittest.skipUnless(OPENSSL, "openssl not on PATH")
class OpensslCrossTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.d = self.tmp.name
        self.key, self.pub = os.path.join(self.d, "k.pem"), os.path.join(self.d, "k.pub.pem")
        subprocess.run([OPENSSL, "genpkey", "-algorithm", "ed25519", "-out", self.key], check=True)
        subprocess.run([OPENSSL, "pkey", "-in", self.key, "-pubout", "-out", self.pub], check=True)
        with open(self.pub, "rb") as f:
            self.pk = ed25519.load_pubkey(f.read())

    def tearDown(self):
        self.tmp.cleanup()

    def osign(self, msg: bytes) -> bytes:
        m, s = os.path.join(self.d, "m"), os.path.join(self.d, "s")
        with open(m, "wb") as f:
            f.write(msg)
        subprocess.run([OPENSSL, "pkeyutl", "-sign", "-rawin", "-inkey", self.key, "-in", m, "-out", s],
                       check=True)
        with open(s, "rb") as f:
            return f.read()

    def test_openssl_signatures_verify(self):
        # The messages the pilot signs: 64-char root hash (D3), 128-char phi||n (D4); plus 1 byte and random.
        for msg in (b"a", b"a" * 64, ("ab" * 64).encode(), os.urandom(1000)):
            sig = self.osign(msg)
            self.assertEqual(len(sig), 64)
            self.assertTrue(ed25519.verify(self.pk, msg, sig))
            self.assertFalse(ed25519.verify(self.pk, msg + b"x", sig))

    def test_pubkey_formats_agree(self):
        der = subprocess.run([OPENSSL, "pkey", "-pubin", "-in", self.pub, "-outform", "DER"],
                             capture_output=True, check=True).stdout
        self.assertEqual(ed25519.load_pubkey(der[-32:]), self.pk)
        self.assertEqual(ed25519.load_pubkey(der[-32:].hex().encode()), self.pk)
        with self.assertRaises(ValueError):
            ed25519.load_pubkey(b"not a key")

    def test_openssl_empty_message_limitation(self):
        """OpenSSL 3.0.x (3.0.13 on the VM) refuses -rawin on an EMPTY message
        ("Could not allocate 0 bytes for oneshot sign/verify buffer"). The pilot
        never signs an empty message, so this records the limit rather than hiding
        it: if openssl signs b"" here, our verifier must accept that signature."""
        m, s = os.path.join(self.d, "m0"), os.path.join(self.d, "s0")
        open(m, "wb").close()
        r = subprocess.run([OPENSSL, "pkeyutl", "-sign", "-rawin", "-inkey", self.key, "-in", m, "-out", s],
                           capture_output=True, text=True)
        if r.returncode == 0:
            with open(s, "rb") as f:
                self.assertTrue(ed25519.verify(self.pk, b"", f.read()))
        else:
            self.assertIn("Could not allocate 0 bytes", r.stderr + r.stdout)

    def test_openssl_verifies_rfc_vectors_too(self):
        """Ground our RFC vector table independently: openssl must accept each one
        (TEST 1 has an empty message: see test_openssl_empty_message_limitation)."""
        for pk_hex, msg_hex, sig_hex in RFC_VECTORS:
            if not msg_hex:
                continue
            paths = {n: os.path.join(self.d, n) for n in ("p.der", "m", "s")}
            data = {"p.der": bytes.fromhex("302a300506032b6570032100" + pk_hex),
                    "m": bytes.fromhex(msg_hex), "s": bytes.fromhex(sig_hex)}
            for n, b in data.items():
                with open(paths[n], "wb") as f:
                    f.write(b)
            r = subprocess.run([OPENSSL, "pkeyutl", "-verify", "-rawin", "-pubin", "-keyform", "DER",
                                "-inkey", paths["p.der"], "-in", paths["m"], "-sigfile", paths["s"]],
                               capture_output=True, text=True)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

if __name__ == "__main__":
    unittest.main()
