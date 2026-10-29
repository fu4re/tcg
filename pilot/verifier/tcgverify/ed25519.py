"""Ed25519 signature verification, RFC 8032 section 5.1.7, stdlib only (DECISIONS D3).

Verification only: the verifier never holds a private key. Strict decoding:
A and R must be canonical point encodings, S < L, and the check is the
encoded comparison  encode([S]B - [h]A) == R  (cofactorless). Signatures made
by `openssl pkeyutl -sign -rawin` verify under this rule; see
tests/test_crypto.py for the cross-test.
"""
from __future__ import annotations

import base64
import hashlib

P = 2 ** 255 - 19
L = 2 ** 252 + 27742317777372353535851937790883648493
D = (-121665 * pow(121666, P - 2, P)) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)
_BY = (4 * pow(5, P - 2, P)) % P
_SPKI_PREFIX = bytes.fromhex("302a300506032b6570032100")


def _recover_x(y: int, sign: int) -> int | None:
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P != 0:
        return None
    if (x & 1) != sign:
        x = P - x
    return x


_BX = _recover_x(_BY, 0)
_B = (_BX, _BY, 1, _BX * _BY % P)


def _add(p1, p2):
    x1, y1, z1, t1 = p1
    x2, y2, z2, t2 = p2
    a = (y1 - x1) * (y2 - x2) % P
    b = (y1 + x1) * (y2 + x2) % P
    c = 2 * t1 * t2 * D % P
    d = 2 * z1 * z2 % P
    e, f, g, h = b - a, d - c, d + c, b + a
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _mul(s: int, pt):
    q = (0, 1, 1, 0)
    while s > 0:
        if s & 1:
            q = _add(q, pt)
        pt = _add(pt, pt)
        s >>= 1
    return q


def _encode(pt) -> bytes:
    x, y, z, _ = pt
    zi = pow(z, P - 2, P)
    x, y = x * zi % P, y * zi % P
    return (y | ((x & 1) << 255)).to_bytes(32, "little")


def _decode(s: bytes):
    if len(s) != 32:
        return None
    y = int.from_bytes(s, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % P)


def verify(pubkey: bytes, msg: bytes, sig: bytes) -> bool:
    if len(pubkey) != 32 or len(sig) != 64:
        return False
    a = _decode(pubkey)
    if a is None or _decode(sig[:32]) is None:
        return False
    s = int.from_bytes(sig[32:], "little")
    if s >= L:
        return False
    h = int.from_bytes(hashlib.sha512(sig[:32] + pubkey + msg).digest(), "little") % L
    neg_a = ((P - a[0]) % P, a[1], a[2], (P - a[3]) % P)
    return _encode(_add(_mul(s, _B), _mul(h, neg_a))) == sig[:32]


def load_pubkey(data: bytes) -> bytes:
    """Accept a PEM SubjectPublicKeyInfo (openssl `pkey -pubout`), 32 raw bytes,
    or 64 hex characters. Anything else raises ValueError."""
    text = data.strip()
    if text.startswith(b"-----BEGIN PUBLIC KEY-----"):
        body = b"".join(l for l in text.splitlines() if not l.startswith(b"-----"))
        der = base64.b64decode(body, validate=True)
        if len(der) != 44 or not der.startswith(_SPKI_PREFIX):
            raise ValueError("PEM key is not an ed25519 SubjectPublicKeyInfo")
        return der[12:]
    if len(data) == 32:
        return data
    try:
        raw = bytes.fromhex(text.decode("ascii"))
    except (UnicodeDecodeError, ValueError):
        raw = b""
    if len(raw) == 32:
        return raw
    raise ValueError("unrecognised ed25519 public key format")
