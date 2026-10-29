#!/usr/bin/env python3
"""Probe each candidate archive RPC at the pinned block and record what it
does now (for the consumer: which RPCs can serve L0 at this pin). Run from the
bundle root; writes provenance/rpc_status.json. Network-dependent: record it
--nondeterministic. Judges nothing about the bundle."""
import datetime, json, pathlib, subprocess, sys

sys.path.insert(0, str(pathlib.Path("../..").resolve()))
from tcg.keccak import keccak256_hex  # noqa: E402

BLOCK = "26298481"
GEMJOIN = "0x2F0b23f53734252Bda2277357e97e1517d6B042A"
DEV = "0x8661c673677de206fda20eb1883063ea4a827c2ac1c7f232dd30e276d20874fa"
RPCS = ["https://eth.drpc.org", "https://mainnet.gateway.tenderly.co", "https://eth-mainnet.public.blastapi.io",
        "https://1rpc.io/eth", "https://ethereum-rpc.publicnode.com"]
rows = []
for url in RPCS:
    r = subprocess.run(["cast", "code", GEMJOIN, "--block", BLOCK, "--rpc-url", url], capture_output=True, text=True, timeout=90)
    if r.returncode == 0 and r.stdout.strip().startswith("0x"):
        k = "0x" + keccak256_hex(bytes.fromhex(r.stdout.strip()[2:])).removeprefix("0x")
        rows.append({"rpc": url, "serves_pinned_block": True, "gemjoin_keccak_matches_identity": k == DEV})
    else:
        err = (r.stderr.strip().splitlines() or ["?"])[-1][:200]
        kind = ("rate_limited (HTTP 429)" if "429" in err else
                "no historical state at the pin (pruned / not archive)" if "historical state" in err or "not available" in err else
                "refuses archive requests" if "token" in err.lower() or "archive" in err.lower() else "error")
        rows.append({"rpc": url, "serves_pinned_block": False, "failure": kind, "detail": err})
doc = {"probed_at_utc": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
       "block": int(BLOCK), "method": "cast code <GemJoin> --block <pin> per RPC; keccak compared with identity.value",
       "rpcs": rows,
       "earlier_observations_2026_10_29": [
           {"rpc": "https://eth-mainnet.public.blastapi.io", "what": "HTTP 429 rate limit (compute units per second) during rehash, ledger seq 136 and 137 (exit 1, could not recompute); served again later"},
           {"rpc": "https://1rpc.io/eth", "what": "no historical state at block 26298481 during rehash, ledger seq 139; it served archive eth_getCode at fetch time (provenance/rpc_probe.json)"},
           {"rpc": "https://ethereum-rpc.publicnode.com", "what": "refuses archive requests without a personal token (provenance/rpc_probe.json)"},
           {"rpc": "https://rpc.flashbots.net, https://eth.llamarpc.com", "what": "504 / 525 at fetch time (provenance/chain_fetch.json)"}],
       "recommendation": "use an RPC with serves_pinned_block true (at probe time: " +
                         ", ".join(x["rpc"] for x in rows if x.get("serves_pinned_block")) +
                         "); public endpoints change: re-probe, and a failure to fetch is 'could not check', never a pass"}
pathlib.Path("provenance/rpc_status.json").write_text(json.dumps(doc, indent=2) + "\n")
print(json.dumps([(x["rpc"], x["serves_pinned_block"], x.get("failure")) for x in rows]))
