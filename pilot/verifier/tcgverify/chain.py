"""Chain-side reads for L0 (DECISIONS D8, D9). The consumer chooses the source:
an archive RPC (`--rpc`) or a state snapshot it obtained itself
(`--state-snapshot`). Nothing here reads the bundle: that separation is the
whole point of the identity check (TCG v3 section 10, artifact substitution).

Snapshot format (consumer-supplied directory, never a bundle child):
  snapshot.json = {"chain_id": int,
                   "block": {"number": int, "hash": "0x..", "timestamp": int},
                   "fork": "<name>" (optional),
                   "code": {"0x<address>": "0x<runtime bytecode hex>", ...}}
"""
from __future__ import annotations

import json
import os
import urllib.request

from . import canon

# Ethereum mainnet (chain id 1) post-merge forks, activated by block timestamp.
# Source: go-ethereum params/chainspecs/mainnet.json at commit
# 748cca24b5ece979f709f38b311f0cb993e10838 (2026-10-21; file sha256 f6266598755c9a33...):
#   shanghaiTime 1681338455, cancunTime 1710338135, pragueTime 1746612311,
#   osakaTime 1764798551, bpo1Time 1765290071, bpo2Time 1767747671.
# Cross-checked 2026-10-29 against eth_config from three RPCs (bundle
# provenance/chain_fetch.json): current activationTime 1767747671 with blob
# schedule target 14 / max 21 = geth's bpo2 entry.
# BPO1/BPO2 change blob parameters only: the execution fork stays "osaka".
MAINNET_FORKS_BY_TIME = (
    (1764798551, "osaka"),
    (1746612311, "prague"),
    (1710338135, "cancun"),
    (1681338455, "shanghai"),
)
MAINNET_BLOB_PARAM_FORKS_BY_TIME = ((1767747671, "bpo2"), (1765290071, "bpo1"))
# Paris activated by terminal total difficulty (58750000000000000000000, same
# file); the block number 15537394 is NOT in that file and is from memory. It
# only matters for blocks before Shanghai.
MAINNET_PARIS_BLOCK = 15537394


def fork_for(chain_id: int, number: int, timestamp: int) -> str | None:
    """Execution fork derived from the block itself, or None if not derivable."""
    if chain_id != 1:
        return None
    for ts, name in MAINNET_FORKS_BY_TIME:
        if timestamp >= ts:
            return name
    return "paris" if number >= MAINNET_PARIS_BLOCK else None


def blob_param_fork_for(chain_id: int, timestamp: int) -> str | None:
    """Blob-parameter-only fork (BPO) in force at the block, reported, not judged."""
    if chain_id != 1:
        return None
    return next((name for ts, name in MAINNET_BLOB_PARAM_FORKS_BY_TIME if timestamp >= ts), None)


class ChainError(Exception):
    pass


class RpcSource:
    def __init__(self, url: str, timeout: float = 60.0):
        self.url, self.timeout, self.requests = url, timeout, 0

    def _call(self, method: str, params: list):
        body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
        # An explicit User-Agent: some public RPCs (eth.drpc.org, 2026-10-29) answer 403 to urllib's default.
        req = urllib.request.Request(self.url, data=body, headers={"Content-Type": "application/json",
                                                                   "User-Agent": "tcg-verifier/0.1"})
        self.requests += 1
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as r:
                resp = json.loads(r.read())
        except (OSError, ValueError) as e:
            raise ChainError(f"{method}: {e}") from e
        if not isinstance(resp, dict) or resp.get("error") or "result" not in resp:
            raise ChainError(f"{method}: {resp.get('error') if isinstance(resp, dict) else resp}")
        return resp["result"]

    def chain_id(self) -> int:
        return int(self._call("eth_chainId", []), 16)

    def block(self, number: int) -> dict:
        b = self._call("eth_getBlockByNumber", [hex(number), False])
        if not b:
            raise ChainError(f"block {number} not found")
        return {"number": int(b["number"], 16), "hash": b["hash"], "timestamp": int(b["timestamp"], 16)}

    def code(self, address: str, number: int) -> bytes:
        return _hex_bytes(self._call("eth_getCode", [address, hex(number)]))

    def declared_fork(self):
        return None

    def describe(self, number: int) -> str:
        return f"JSON-RPC {self.url} (eth_getCode / eth_chainId / eth_getBlockByNumber at block {number})"


class SnapshotSource:
    def __init__(self, directory: str):
        self.path = os.path.join(directory, "snapshot.json")
        try:
            with open(self.path, encoding="utf-8") as f:
                self.data = json.load(f)
        except (OSError, ValueError) as e:
            raise ChainError(f"state snapshot unreadable: {e}") from e
        self.requests = 0

    def chain_id(self) -> int:
        self.requests += 1
        return int(self.data["chain_id"])

    def block(self, number: int) -> dict:
        self.requests += 1
        b = self.data.get("block") or {}
        if b.get("number") != number:
            raise ChainError(f"snapshot is at block {b.get('number')}, bundle pins {number}")
        return {"number": b["number"], "hash": b.get("hash"), "timestamp": int(b["timestamp"])}

    def code(self, address: str, number: int) -> bytes:
        self.requests += 1
        self.block(number)
        codes = {k.lower(): v for k, v in (self.data.get("code") or {}).items()}
        if address.lower() not in codes:
            raise ChainError(f"snapshot has no code entry for {address}")
        return _hex_bytes(codes[address.lower()])

    def declared_fork(self):
        return self.data.get("fork")

    def describe(self, number: int) -> str:
        return f"consumer state snapshot {self.path} (sha256 {canon.sha256_file(self.path)}) at block {number}"


def _hex_bytes(h) -> bytes:
    if not isinstance(h, str) or not h.startswith("0x"):
        raise ChainError(f"not a 0x hex string: {h!r}")
    try:
        return bytes.fromhex(h[2:])
    except ValueError as e:
        raise ChainError(f"bad hex: {e}") from e
