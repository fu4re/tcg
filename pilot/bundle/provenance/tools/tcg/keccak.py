"""Pure-Python Keccak-256 (Ethereum's pre-NIST padding), no external deps.

The code-identity binding of the bridge S<==D (docs/findings/0005) needs the
verifier to COMPUTE keccak256(callee code) and compare it against the declared
on-chain code hash — a check the verifier PERFORMS, not one it assumes. Python's
`hashlib.sha3_256` is NIST SHA3 (0x06 domain padding), which is NOT Ethereum's
keccak256 (0x01 padding); they differ. So this module implements Keccak-f[1600]
directly, keeping `verify` self-contained (no unpinned wheel in the trusted
base) and bundle-only.

Validated against the pinned Ethereum vectors in tests/test_keccak.py:
keccak256(b"") == c5d2460186f7233c927e7db2dcc703c0e500b653ca82273b7bfad8045d85a470.
"""
from __future__ import annotations

_RC = (
    0x0000000000000001, 0x0000000000008082, 0x800000000000808A,
    0x8000000080008000, 0x000000000000808B, 0x0000000080000001,
    0x8000000080008081, 0x8000000000008009, 0x000000000000008A,
    0x0000000000000088, 0x0000000080008009, 0x000000008000000A,
    0x000000008000808B, 0x800000000000008B, 0x8000000000008089,
    0x8000000000008003, 0x8000000000008002, 0x8000000000000080,
    0x000000000000800A, 0x800000008000000A, 0x8000000080008081,
    0x8000000000008080, 0x0000000080000001, 0x8000000080008008,
)
_ROT = (
    (0, 36, 3, 41, 18), (1, 44, 10, 45, 2), (62, 6, 43, 15, 61),
    (28, 55, 25, 21, 56), (27, 20, 39, 8, 14),
)
_MASK = (1 << 64) - 1


def _rotl(x: int, n: int) -> int:
    return ((x << n) | (x >> (64 - n))) & _MASK


def _keccak_f(a: list[list[int]]) -> None:
    for rnd in range(24):
        # theta
        c = [a[x][0] ^ a[x][1] ^ a[x][2] ^ a[x][3] ^ a[x][4] for x in range(5)]
        d = [c[(x - 1) % 5] ^ _rotl(c[(x + 1) % 5], 1) for x in range(5)]
        for x in range(5):
            for y in range(5):
                a[x][y] ^= d[x]
        # rho + pi
        b = [[0] * 5 for _ in range(5)]
        for x in range(5):
            for y in range(5):
                b[y][(2 * x + 3 * y) % 5] = _rotl(a[x][y], _ROT[x][y])
        # chi
        for x in range(5):
            for y in range(5):
                a[x][y] = b[x][y] ^ ((~b[(x + 1) % 5][y]) & b[(x + 2) % 5][y])
        # iota
        a[0][0] ^= _RC[rnd]


def keccak256(data: bytes) -> bytes:
    """Keccak-256 digest (32 bytes) with Ethereum's 0x01 padding."""
    rate = 136  # 1088-bit rate for Keccak-256
    # pad10*1 with Ethereum/Keccak domain byte 0x01
    padded = bytearray(data)
    padded.append(0x01)
    while len(padded) % rate != 0:
        padded.append(0x00)
    padded[-1] ^= 0x80

    a = [[0] * 5 for _ in range(5)]
    for off in range(0, len(padded), rate):
        block = padded[off:off + rate]
        for i in range(rate // 8):
            lane = int.from_bytes(block[i * 8:i * 8 + 8], "little")
            a[i % 5][i // 5] ^= lane
        _keccak_f(a)

    out = bytearray()
    while len(out) < 32:
        for i in range(rate // 8):
            out += a[i % 5][i // 5].to_bytes(8, "little")
            if len(out) >= 32:
                break
        if len(out) < 32:
            _keccak_f(a)
    return bytes(out[:32])


def keccak256_hex(data: bytes) -> str:
    return keccak256(data).hex()
