"""Seeded generator of configurations σ (protocol.md section 4).

Used by WP2 (properness search, no probe) and meant to be reused unchanged by
the WP4 adversary (same σ prefix, probe appended). Pure function of
(seed, index, ABI, parameters): no state tracking, no wall clock, no Python
`random` (its algorithms are not part of any spec we can pin). The stream is
SHA-256 in counter mode, so the distribution below can be re-implemented from
this docstring alone.

Random stream
-------------
For σ number i under seed s, block k is
`sha256(b"specgame-seqgen-v1|" + str(s) + b"|" + str(i) + b"|" + str(k))`
(decimal ASCII), read as a 256-bit big-endian word; k = 0, 1, 2, ... in draw
order. `word()` returns the next word. `below(n)` takes the next word w and
returns `w mod n` if `w < floor(2^256 / n) * n`, else takes another (rejection
sampling, exact uniform). `pick(seq)` = `seq[below(len(seq))]`.

Distribution D (version `DIST_VERSION`), draws in this order
-------------------------------------------------------------
1. deployer: `pick(SENDERS)` (alice, bob, carol).
2. cap: `pick(CAP_KINDS)`, then
   - `0`, `1`, `2`, `max` (2^256-1), `max-1` (2^256-2), `half` (2^255): that value;
   - `small`: `below(1000) + 3` (3..1002);
   - `random`: a full 256-bit word.
3. number of transactions n: `below(max_txs + 1)` (0..max_txs, uniform).
4. per transaction: sender `pick(SENDERS)`; fn `pick(fns)` where fns are the
   artifact ABI functions that are not view/pure and take only address and
   uint256 parameters, sorted by canonical signature; then each argument in
   order: address → `pick(POOL)` (alice, bob, carol, zero); uint256 → `uint(cap)`.
5. probe (adversary only, `probe_checks` given): sender `pick(SENDERS)`,
   a `pick(POOL)`, b `pick(POOL)`, x `uint(cap)`, y `uint(cap)`, check
   `pick(sorted(probe_checks))`. Drawn after the transactions, so the σ with a
   probe has the same prefix as the σ without one (same seed, same index).

`uint(cap)`: `pick(UINT_KINDS)`, then
   - `0`, `1`, `2`, `max`, `max-1`: that value;
   - `cap`, `cap-1`, `cap+1`: clamped to [0, 2^256-1] (cap-1 at cap 0 is 0,
     cap+1 at cap max is max);
   - `half_cap`: cap // 2 (two of them reach cap from an empty supply);
   - `small`: `below(cap + 1)` if cap < 2^64 else `below(2^64)` (an amount
     at or under cap, the region where successful mints and transfers live);
   - `random`: a full 256-bit word.

The parameters and this module's sha256 are reported by `distribution_id()`;
the adversary id (WP4) includes them.

Subjects (protocol v3)
----------------------
The distribution above is generator kind `capped-v1` (profile
`generator.kind`); for such a subject `gen_sigma` is unchanged. Generator kind
`typed-v2` (Vat) uses the same stream with typed, per-call kinds:
1. deployer `pick(senders)`; σ.setup = the profile's setup (each transaction
   sent by its profile `sender`, else by the deployer; no draws); `used` = its
   uint256/int256 arguments in order; then each constructor argument by its
   type's default kinds;
2. n = `below(max_txs + 1)`; per transaction: fn `pick(fns)` (the profile's
   `functions`, sorted); sender by `kind = pick(calls[fn].sender or ["any"])`;
   then each argument by `kind = pick(calls[fn].args[j] or the type's default
   kinds)`;
3. probe (adversary only): sender `pick(senders)`, then every parameter of
   every probe signature in profile order by its type's default kinds, then
   check `pick(sorted(probe_checks))`.
Kinds (a list entry may repeat to weight it):
- sender: a sender name; `deployer`; `any` = `pick(senders)`.
- address: a pool name; `self` = the transaction's sender; `hoped` =
  `pick(sorted p : σ.setup has p.hope(sender))`, `self` if none; `any` =
  `pick(address pool)`.
- bytes32: a pool name; `any` = `pick(bytes32 pool)`.
- uint256 / int256: a decimal literal; `small` = `below(1001)`; `wad` / `ray` /
  `rad` = `below(1001)` x 10^18 / 10^27 / 10^45; `random` = a full word
  (int256: two's complement); `[+-]U_le_N` with U in raw, wad, ray, rad,
  mray (10^0, 10^18, 10^27, 10^45, 10^24) = `below(N + 1)` x U, sign `+` or
  `-` as written; `frac_prev` = the previous numeric argument of the same
  call x `below(91)` / 100, rounded toward zero, keeping its sign (`small` if
  there is none); `repeat` = `pick(used)`; `negate` = `-pick(used)` (both
  `small` when `used` is empty). Unsigned scaled kinds (small, wad, ray, rad,
  U_le_N without a sign) take a sign for int256: `pick((1, -1))` after the
  magnitude. Every drawn number is appended to `used`. A value is then fitted
  to its type: int256 clamped to its range; uint256 the absolute value,
  clamped.
"""
from __future__ import annotations

import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402

DIST_VERSION = 1
DEFAULT_MAX_TXS = 6
MAX = core.UINT256_MAX
CAP_KINDS = ("0", "1", "2", "small", "half", "max-1", "max", "random")
UINT_KINDS = ("0", "1", "2", "cap-1", "cap", "cap+1", "half_cap", "small", "max-1", "max", "random")
_TAG = b"specgame-seqgen-v1"


class Stream:
    """Deterministic uniform draws from SHA-256 in counter mode."""

    def __init__(self, seed: int, index: int):
        self._prefix = _TAG + b"|" + str(seed).encode() + b"|" + str(index).encode() + b"|"
        self._k = 0

    def word(self) -> int:
        h = hashlib.sha256(self._prefix + str(self._k).encode()).digest()
        self._k += 1
        return int.from_bytes(h, "big")

    def below(self, n: int) -> int:
        if n <= 0:
            raise ValueError("below(n) needs n >= 1")
        limit = (2**256 // n) * n
        while True:
            w = self.word()
            if w < limit:
                return w % n

    def pick(self, seq):
        return seq[self.below(len(seq))]


def _clamp(v: int) -> int:
    return min(max(v, 0), MAX)


def draw_cap(st: Stream) -> int:
    kind = st.pick(CAP_KINDS)
    fixed = {"0": 0, "1": 1, "2": 2, "half": 2**255, "max-1": MAX - 1, "max": MAX}
    if kind in fixed:
        return fixed[kind]
    if kind == "small":
        return st.below(1000) + 3
    return st.word()  # random


def draw_uint(st: Stream, cap: int) -> int:
    kind = st.pick(UINT_KINDS)
    fixed = {"0": 0, "1": 1, "2": 2, "max-1": MAX - 1, "max": MAX,
             "cap": cap, "cap-1": _clamp(cap - 1), "cap+1": _clamp(cap + 1), "half_cap": cap // 2}
    if kind in fixed:
        return fixed[kind]
    if kind == "small":
        return st.below(cap + 1) if cap < 2**64 else st.below(2**64)
    return st.word()  # random


def _subject(subject):
    return subject if isinstance(subject, core.Subject) else core.load_subject(subject)


def tx_functions(entry: dict, subject=None) -> list[str]:
    """Canonical signatures of the functions σ may call, sorted. capped-v1: the
    state-changing ABI functions whose parameters are only address/uint256;
    typed-v2: the profile's `functions` (each must be in the ABI)."""
    subj = _subject(subject if subject is not None else entry.get("subject"))
    if subj.profile["generator"]["kind"] == TYPED:
        check_generator(subj)
        missing = [f for f in subj.functions if f not in entry["hashes"]]
        if missing:
            raise ValueError(f"profile functions not in the ABI: {missing}")
        return sorted(subj.functions)
    fns = []
    for item in entry["abi"]:
        if item.get("type") != "function" or item.get("stateMutability") in ("view", "pure"):
            continue
        types = [p["type"] for p in item.get("inputs", [])]
        if all(t in ("address", "uint256") for t in types):
            sig = f"{item['name']}({','.join(types)})"
            if sig in entry["hashes"] and not item["name"].startswith(core.CHECK_PREFIX):
                fns.append(sig)
    return sorted(fns)


MAG = {"small": 1, "wad": 10**18, "ray": 10**27, "rad": 10**45}
UNITS = {"raw": 1, "wad": 10**18, "ray": 10**27, "rad": 10**45, "mray": 10**24}
_LE = re.compile(r"^([+-]?)(raw|wad|ray|rad|mray)_le_([0-9]+)$")
TYPED = "typed-v2"


def _num(st: Stream, typ: str, kind: str, used: list[int], prev: int | None) -> int:
    if kind in ("repeat", "negate", "frac_prev") and not (used if kind != "frac_prev" else prev is not None):
        kind = "small"
    m = _LE.match(kind)
    if kind in ("repeat", "negate"):
        v = st.pick(used) * (-1 if kind == "negate" else 1)
    elif kind == "frac_prev":
        v = abs(prev) * st.below(91) // 100 * (-1 if prev < 0 else 1)
    elif kind == "random":
        w = st.word()
        v = w - 2**256 if (typ == "int256" and w >= 2**255) else w
    elif m:
        v = st.below(int(m.group(3)) + 1) * UNITS[m.group(2)]
        if m.group(1) == "-":
            v = -v
        elif m.group(1) == "" and typ == "int256":
            v *= st.pick((1, -1))
    elif kind in MAG:
        v = st.below(1001) * MAG[kind]
        if typ == "int256":
            v *= st.pick((1, -1))
    else:
        v = int(kind)
    if typ == "uint256":
        v = abs(v)
    lo, hi = (core.INT256_MIN, core.INT256_MAX) if typ == "int256" else (0, MAX)
    return min(max(v, lo), hi)


def draw_typed(st: Stream, typ: str, subj: core.Subject, used: list[int], kinds: list[str] | None = None,
               sender: str | None = None, hoped: dict[str, list[str]] | None = None,
               prev: int | None = None) -> str:
    gen = subj.profile["generator"]
    kinds = kinds or gen.get(typ) or ["any"]
    kind = st.pick(tuple(kinds))
    if typ in ("address", "bytes32"):
        pool = subj.pool(typ)
        if kind == "self" and typ == "address":
            return sender
        if kind == "hoped" and typ == "address":
            cands = (hoped or {}).get(sender) or []
            return st.pick(tuple(cands)) if cands else sender
        if kind == "any":
            return st.pick(tuple(pool))
        if kind not in pool:
            raise ValueError(f"{typ} kind {kind!r} is not a pool name")
        return kind
    v = _num(st, typ, kind, used, prev)
    used.append(v)
    return str(v)


def hoped_by(setup: list[dict]) -> dict[str, list[str]]:
    """sender -> sorted addresses that let it act for them (their setup hope(sender))."""
    out: dict[str, set] = {}
    for tx in setup:
        if tx["fn"] == "hope(address)":
            out.setdefault(tx["args"][0], set()).add(tx["sender"])
    return {k: sorted(v) for k, v in out.items()}


def gen_sigma_typed(seed: int, index: int, fns: list[str], max_txs: int, probe_checks: list[str] | None,
                    subj: core.Subject) -> dict:
    """typed-v2 (module docstring, Subjects)."""
    st = Stream(seed, index)
    calls = subj.profile["generator"].get("calls", {})
    deployer = st.pick(subj.senders)
    setup = core.setup_for(subj, deployer)
    hoped = hoped_by(setup)
    used = [int(v) for tx in setup for t, v in zip(core.sig_types(tx["fn"]), tx["args"])
            if t in ("uint256", "int256")]
    ctor = {n: draw_typed(st, t, subj, used) for n, t in subj.ctor_params}
    txs = []
    for _ in range(st.below(max_txs + 1)):
        fn = st.pick(fns)
        spec = calls.get(fn, {})
        skind = st.pick(tuple(spec.get("sender") or ["any"]))
        sender = deployer if skind == "deployer" else (st.pick(subj.senders) if skind == "any" else skind)
        args, prev = [], None
        for j, t in enumerate(core.sig_types(fn)):
            kinds = spec["args"][j] if spec.get("args") else None
            v = draw_typed(st, t, subj, used, kinds, sender, hoped, prev)
            if t in ("uint256", "int256"):
                prev = int(v)
            args.append(v)
        txs.append({"sender": sender, "fn": fn, "args": args})
    sigma = {"version": 1, "deployer": deployer, "ctor": ctor}
    if setup:
        sigma["setup"] = setup
    sigma["txs"] = txs
    if probe_checks:
        probe = {"sender": st.pick(subj.senders)}
        for sig in subj.probes:
            for n, t in sig:
                probe[n] = draw_typed(st, t, subj, used)
        probe["check"] = st.pick(sorted(probe_checks))
        sigma["probe"] = probe
    return sigma


def check_generator(subj: core.Subject) -> None:
    """The typed generator's profile rules the schema cannot express."""
    gen = subj.profile["generator"]
    for fn, spec in gen.get("calls", {}).items():
        if fn not in subj.functions:
            raise ValueError(f"generator.calls: {fn} is not in functions")
        if spec.get("args") is not None and len(spec["args"]) != len(core.sig_types(fn)):
            raise ValueError(f"generator.calls: {fn} needs {len(core.sig_types(fn))} kind lists")


def gen_sigma(seed: int, index: int, fns: list[str], max_txs: int = DEFAULT_MAX_TXS,
              probe_checks: list[str] | None = None, subject=None) -> dict:
    """σ number `index` under `seed`: distribution D (module docstring), or
    typed-v2 for a subject whose profile says so."""
    if not fns:
        raise ValueError("no transaction functions")
    subj = _subject(subject)
    if subj.profile["generator"]["kind"] == TYPED:
        return gen_sigma_typed(seed, index, fns, max_txs, probe_checks, subj)
    st = Stream(seed, index)
    pool = tuple(core.POOL)
    deployer = st.pick(core.SENDERS)
    cap = draw_cap(st)
    txs = []
    for _ in range(st.below(max_txs + 1)):
        sender = st.pick(core.SENDERS)
        fn = st.pick(fns)
        types = fn[fn.index("(") + 1:-1]
        args = [st.pick(pool) if t == "address" else str(draw_uint(st, cap))
                for t in (types.split(",") if types else [])]
        txs.append({"sender": sender, "fn": fn, "args": args})
    sigma = {"version": 1, "deployer": deployer, "ctor": {"cap": str(cap)}, "txs": txs}
    if probe_checks:
        sigma["probe"] = {"sender": st.pick(core.SENDERS), "a": st.pick(pool), "b": st.pick(pool),
                          "x": str(draw_uint(st, cap)), "y": str(draw_uint(st, cap)),
                          "check": st.pick(sorted(probe_checks))}
    return sigma


def generate(seed: int, n: int, fns: list[str], max_txs: int = DEFAULT_MAX_TXS,
             probe_checks: list[str] | None = None, subject=None) -> list[dict]:
    """σ_0 .. σ_{n-1} under `seed`. Each σ depends only on (seed, its index)."""
    return [gen_sigma(seed, i, fns, max_txs, probe_checks, subject) for i in range(n)]


def distribution_id(fns: list[str], max_txs: int = DEFAULT_MAX_TXS, subject=None) -> dict:
    """Everything the distribution depends on except the seed (part of the
    adversary id in WP4)."""
    subj = _subject(subject)
    if subj.profile["generator"]["kind"] == TYPED:
        return {"name": "specgame-seqgen", "kind": TYPED, "subject": subj.name, "max_txs": max_txs,
                "generator": subj.profile["generator"], "senders": list(subj.senders),
                "pools": subj.profile["pools"], "probes": subj.profile["spec"]["probes"], "fns": list(fns),
                "setup": subj.setup,
                "source_sha256": core.sha256_file(__file__)}
    return {"name": "specgame-seqgen", "dist_version": DIST_VERSION, "max_txs": max_txs,
            "cap_kinds": list(CAP_KINDS), "uint_kinds": list(UINT_KINDS),
            "senders": list(core.SENDERS), "pool": list(core.POOL), "fns": list(fns),
            "source_sha256": core.sha256_file(__file__)}


def summarize(sigma: dict) -> str:
    """One-line human-readable form of σ (logs and reports; never compared)."""
    def short(v: str) -> str:
        if not v.isdigit():
            return v
        x = int(v)
        if x >= 2**64:
            d = MAX - x
            return "max" if d == 0 else (f"max-{d}" if d < 2**32 else f"0x{x:x}"[:12] + "..")
        return v
    parts = [f"deploy({sigma['deployer']}" + "".join(f", {k}={short(v)}" for k, v in sigma["ctor"].items()) + ")"]
    for tx in sigma["txs"]:
        parts.append(f"{tx['sender']}.{tx['fn'].split('(')[0]}({','.join(short(a) for a in tx['args'])})")
    if "probe" in sigma:
        p = sigma["probe"]
        args = [short(v) for k, v in p.items() if k not in ("sender", "check")]
        parts.append(f"probe {p['sender']}.{p.get('check', 'check_*')}({','.join(args)})")
    return "; ".join(parts)


def coverage(subject=None, n: int = 2000, seed: int = 0, max_txs: int = DEFAULT_MAX_TXS) -> dict:
    """Successful / total calls per function over σ_0 .. σ_{n-1} (no probe), run
    on the core executor against the subject's b; plus setup failures. A
    measurement of how much of the subject a σ stream reaches."""
    subj = _subject(subject)
    entry = core.compile_artifact(subj.source_path, subject=subj)
    fns = tx_functions(entry, subj)
    calls = {f: 0 for f in fns}
    succ = {f: 0 for f in fns}
    setup_fail = 0
    for i in range(n):
        sigma = gen_sigma(seed, i, fns, max_txs, subject=subj)
        obs = core.run_sequence(entry, sigma)
        setup_fail += sum(s["outcome"] != core.Outcome.SUCCESS.value for s in obs.data.get("setup") or [])
        for tx, step in zip(sigma["txs"], obs.data["txs"]):
            calls[tx["fn"]] += 1
            succ[tx["fn"]] += step["outcome"] == core.Outcome.SUCCESS.value
    return {"subject": subj.name, "n": n, "seed": seed, "max_txs": max_txs,
            "distribution_sha256": core.json_sha256(distribution_id(fns, max_txs, subj)),
            "setup_failures": setup_fail,
            "per_function": {f: {"calls": calls[f], "successes": succ[f],
                                 "rate": round(succ[f] / calls[f], 4) if calls[f] else None} for f in fns}}


def coverage_table(doc: dict) -> str:
    rows = [f"coverage {doc['subject']}: {doc['n']} σ, seed {doc['seed']}, max_txs {doc['max_txs']}, "
            f"setup failures {doc['setup_failures']}, distribution {doc['distribution_sha256'][:12]}…"]
    for f, r in sorted(doc["per_function"].items()):
        rows.append(f"  {f:55s} {r['successes']:5d} / {r['calls']:5d}  {100 * (r['rate'] or 0):5.1f} %")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    ap = argparse.ArgumentParser(description="seqgen: coverage of a subject by the σ stream")
    ap.add_argument("--coverage", action="store_true", required=True)
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--n", type=int, default=2000)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--max-txs", type=int, default=DEFAULT_MAX_TXS)
    ap.add_argument("--json", type=Path)
    a = ap.parse_args(argv)
    doc = coverage(a.subject, a.n, a.seed, a.max_txs)
    print(coverage_table(doc))
    if a.json:
        a.json.parent.mkdir(parents=True, exist_ok=True)
        a.json.write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
