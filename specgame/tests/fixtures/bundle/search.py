"""Seeded random search used only to build the WP5 fixture bundle.

Not the WP4 adversary: a ~30-line sampler over the protocol's sigma space
(section 4) that finds, per mutant, a properness sigma (run(b, s) != run(m, s))
and witnesses against the fixture spec (evaluate_witness). Its sha256 is
recorded as the fixture bundle's adversary source; seed and budget are
arguments. Shortest sequences are tried first, so the found sigma are small.
"""
from __future__ import annotations

import random

UINTS = ["0", "1", "7", "50", "99", "100", "101"]
FNS = {"mint(address,uint256)": ("address", "uint256"), "transfer(address,uint256)": ("address", "uint256")}


def _sigma(rng: random.Random, n_txs: int, probe: bool, pool, senders) -> dict:
    s = {"version": 1, "deployer": rng.choice(senders), "ctor": {"cap": "100"}, "txs": []}
    for _ in range(n_txs):
        fn = rng.choice(sorted(FNS))
        args = [rng.choice(pool) if t == "address" else rng.choice(UINTS) for t in FNS[fn]]
        s["txs"].append({"sender": rng.choice(senders), "fn": fn, "args": args})
    if probe:
        s["probe"] = {"sender": rng.choice(senders), "a": rng.choice(pool), "b": rng.choice(pool),
                      "x": rng.choice(UINTS), "y": rng.choice(UINTS)}
    return s


def candidates(core, seed: int, budget: int, probe: bool):
    """`budget` sigma, lengths 0..3 in increasing order, deterministic in seed."""
    rng = random.Random(seed)
    pool, senders = sorted(core.POOL), list(core.SENDERS)
    for i in range(budget):
        yield _sigma(rng, min(3, i * 4 // budget), probe, pool, senders)


def find_properness(core, b_entry: dict, m_entry: dict, seed: int, budget: int) -> dict | None:
    for s in candidates(core, seed, budget, probe=False):
        if not core.observation_equal(core.run_sequence(b_entry, s), core.run_sequence(m_entry, s)):
            return s
    return None


def find_witness(core, spec_entry: dict, seed: int, budget: int) -> tuple[dict, str] | None:
    for s in candidates(core, seed, budget, probe=True):
        ev = core.evaluate_witness(spec_entry, s)
        if ev.violated:
            check = sorted(k for k, v in ev.outcomes.items() if v == "violation")[0]
            s["probe"]["check"] = check
            return s, check
    return None
