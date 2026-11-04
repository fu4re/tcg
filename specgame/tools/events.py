"""Kill sets on witness pools, round-to-round events, and the ladder gate E2
(protocol.md sections 8, 13; note Def. 6.1, Prop. 6.2, 6.3).

    python tools/events.py --ladder [--witness-dir build/witnesses] [--check-dir build/ladder/check]
        [--mutants mutants/mutants.json] [--out build/ladder/events_ladder.json]
    python tools/events.py --trajectory rounds.json --condition fM --seed 0 --pool W1.json W2.json ...
        [--out events.json]

Every kill set here is computed by **replaying witnesses**: K_P(φ) = { m ∈ M :
some pair (m, σ) ∈ P has evaluate_witness(Spec φ over m, σ) violated }. The
spec text is only compiled, never read for its properties; a pair counts for
φ whatever spec it was found against (its `probe.check` is provenance,
protocol.md Sharpened definition 13).

Library (reused by WP7):
- `pool_from(witness_lists)`: W* as the deduplicated list of pairs
  {mutant, sigma}, sorted by canonical JSON; `pool_sha256(pool)`;
- `Scorer(mutants).kill_set(spec, pool)`: (sorted kill set, per-pair results);
- `relation(K_t, K_t1)`: weakening / strengthening / shift / unchanged, lost,
  gained (protocol.md section 13);
- `trajectory(condition, seed, M, pool, rounds)`: the events document
  (schemas/events.schema.json); a round with `acc = lint_rejected` has K = ∅.

Ladder mode (`--ladder`): W(φ) = build/witnesses/<φ>.json for the six ladder
specs; W* = their union. Reports, and exits 1 if any asserted relation fails:
(i) the spec × mutant table on own W and on W*; (ii) nesting
K(top) ⊆ K(owner), K(cap) ⊆ K(both), K(owner) ⊆ K(both), K(both) ⊆ K(full),
K(transfer) ⊆ K(full), asserted on every own W and on W*; (iii) Prop. 6.3 on
P = W(owner) ∪ W(cap) ∪ W(both): K_P(both) = K_P(owner) ∪ K_P(cap), asserted;
(iv) Prop. 6.2 on M' = {m01_mint_no_owner}: K_{M'}(owner) vs K_{M'}(cap) on W*,
**reported, not asserted** (a measurement of the note's counterexample).
Exit codes: 0 all asserted relations hold, 1 one fails, 2 input error.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import specgame_core as core  # noqa: E402

LADDER = ("phi_top", "phi_owner", "phi_cap", "phi_both", "phi_transfer", "phi_full")
NESTING = (("phi_top", "phi_owner"), ("phi_cap", "phi_both"), ("phi_owner", "phi_both"),
           ("phi_both", "phi_full"), ("phi_transfer", "phi_full"))
PROP62_MUTANT = "m01_mint_no_owner"

# Vat (protocol v3 step 2): every rung above phi_top and below phi_full;
# phi_frob_both = phi_frob ∪ phi_frob_guards (the Vat analogue of phi_both).
VAT_RUNGS = ("phi_auth", "phi_consent", "phi_frob", "phi_frob_guards", "phi_frob_both", "phi_fold",
             "phi_move_flux", "phi_grab_heal_suck", "phi_books")
VAT_LADDER = ("phi_top",) + VAT_RUNGS + ("phi_full",)
VAT_NESTING = tuple(("phi_top", r) for r in VAT_RUNGS + ("phi_full",)) \
    + tuple((r, "phi_full") for r in VAT_RUNGS) \
    + (("phi_frob", "phi_frob_both"), ("phi_frob_guards", "phi_frob_both"))

# Per subject: spec list, asserted nesting, Prop. 6.3 triple (a, b, a ∪ b), Prop. 6.2 mutant (or None).
LADDERS = {
    "capped_token": {"specs": LADDER, "nesting": NESTING,
                     "prop63": ("phi_owner", "phi_cap", "phi_both"), "prop62": PROP62_MUTANT},
    "vat": {"specs": VAT_LADDER, "nesting": VAT_NESTING,
            "prop63": ("phi_frob", "phi_frob_guards", "phi_frob_both"), "prop62": None},
}
ACCS = ("Accept", "Refute", "Unknown", "lint_rejected")


class EventsError(Exception):
    pass


# ---------------------------------------------------------------- pools and kill sets

def pool_from(witness_lists: list[list[dict]]) -> list[dict]:
    """W* = ⋃ W_t as pairs {mutant, sigma}, deduplicated and sorted by canonical JSON."""
    uniq: dict[bytes, dict] = {}
    for ws in witness_lists:
        for w in ws:
            pair = {"mutant": w["mutant"], "sigma": w["sigma"]}
            uniq.setdefault(core.canonical_json(pair), pair)
    return [uniq[k] for k in sorted(uniq)]


def pool_sha256(pool: list[dict]) -> str:
    return core.json_sha256(sorted(pool, key=core.canonical_json))


def load_witnesses(path: Path) -> list[dict]:
    doc = json.loads(Path(path).read_text())
    return doc["W"] if isinstance(doc, dict) else doc


def load_mutants(mutants_json: Path, root: Path = core.ROOT) -> list[dict]:
    """Included mutants: [{id, path, name}] in file order."""
    doc = json.loads(Path(mutants_json).read_text())
    return [{"id": m["id"], "path": (root / m["path"]).resolve(), "name": Path(m["path"]).stem}
            for m in doc["mutants"] if m["status"] == "included"]


class Scorer:
    """Evaluates pairs against specs; Spec-over-mutant compiles are cached by
    (spec source sha256, mutant id)."""

    def __init__(self, mutants: list[dict], subject=None):
        self.mutants = mutants
        self.subject = subject
        self.by_id = {m["id"]: m for m in mutants}
        self._entries: dict[tuple[str, str], dict] = {}

    def entry(self, spec: Path, mutant_id: str) -> dict:
        key = (core.sha256_file(spec), mutant_id)
        if key not in self._entries:
            self._entries[key] = core.compile_spec_over(spec, self.by_id[mutant_id]["path"], subject=self.subject)
        return self._entries[key]

    def kill_set(self, spec: Path, pool: list[dict], restrict: set[str] | None = None) -> tuple[list[str], list[dict]]:
        """K_pool(φ) as sorted mutant ids, plus one result per evaluated pair.
        Pairs naming a mutant outside M (or outside `restrict`) are skipped."""
        kill, results = set(), []
        for pair in pool:
            mid = pair["mutant"]
            if mid not in self.by_id or (restrict is not None and mid not in restrict):
                continue
            ev = core.evaluate_witness(self.entry(spec, mid), pair["sigma"])
            results.append({"mutant": mid, "sigma_sha256": core.json_sha256(pair["sigma"]),
                            "violated": ev.violated, "outcomes": ev.outcomes})
            if ev.violated:
                kill.add(mid)
        return sorted(kill), results


# ---------------------------------------------------------------- events (protocol.md section 13)

def relation(k_t: list[str] | set[str], k_t1: list[str] | set[str]) -> dict:
    a, b = set(k_t), set(k_t1)
    if a == b:
        kind = "unchanged"
    elif b < a:
        kind = "weakening"
    elif b > a:
        kind = "strengthening"
    else:
        kind = "shift"
    return {"kind": kind, "lost": sorted(a - b), "gained": sorted(b - a)}


def trajectory(condition: str, seed: int, M: list[str], pool: list[dict], rounds: list[dict]) -> dict:
    """rounds: [{t, phi_source_sha256, acc, kill_set}] with kill sets already
    computed on `pool` (lint_rejected rounds must carry an empty kill set)."""
    total = len(M)
    if total < 1:
        raise EventsError("M is empty")
    rs = []
    for r in sorted(rounds, key=lambda r: r["t"]):
        if r["acc"] not in ACCS:
            raise EventsError(f"round {r['t']}: acc {r['acc']!r}")
        k = sorted(r["kill_set"])
        if r["acc"] == "lint_rejected" and k:
            raise EventsError(f"round {r['t']}: a lint-rejected round has K = empty set")
        if not set(k) <= set(M):
            raise EventsError(f"round {r['t']}: kill set outside M")
        rs.append({"t": r["t"], "phi_source_sha256": r["phi_source_sha256"], "acc": r["acc"],
                   "kill_set": k, "ms_cert": {"killed": len(k), "total": total}})
    events = []
    for x, y in zip(rs, rs[1:]):
        events.append({"t": x["t"], **relation(x["kill_set"], y["kill_set"]), "acc_t": x["acc"]})
    return {"version": 1, "condition": condition, "seed": seed, "M": sorted(M),
            "pool": {"size": len(pool), "sha256": pool_sha256(pool)}, "rounds": rs, "events": events}


# ---------------------------------------------------------------- ladder (gate E2)

def ladder(spec_dir: Path, witness_dir: Path, mutants: list[dict], accs: dict[str, str] | None = None,
           subject=None) -> dict:
    subj = subject if isinstance(subject, core.Subject) else core.load_subject(subject)
    cfg = LADDERS[subj.name]
    specs_l, prop62_mutant = cfg["specs"], cfg["prop62"]
    pa, pb, pab = cfg["prop63"]
    accs = accs or {}
    sc = Scorer(mutants, subj)
    names = {m["id"]: m["name"] for m in mutants}
    specs = {p: spec_dir / f"{p}.sol" for p in specs_l}
    W = {p: load_witnesses(witness_dir / f"{p}.json") for p in specs_l}
    own = {p: sc.kill_set(specs[p], pool_from([W[p]]))[0] for p in specs_l}
    star = pool_from([W[p] for p in specs_l])
    on_star = {p: sc.kill_set(specs[p], star)[0] for p in specs_l}

    table = []
    for m in mutants:
        table.append({"mutant": m["id"], "name": m["name"],
                      "own_W": {p: m["id"] in own[p] for p in specs_l},
                      "W_star": {p: m["id"] in on_star[p] for p in specs_l}})

    def nest(k: dict, label: str) -> list[dict]:
        out = []
        for lo, hi in cfg["nesting"]:
            ok = set(k[lo]) <= set(k[hi])
            out.append({"pool": label, "lower": lo, "upper": hi, "holds": ok,
                        "missing": [names[i] for i in sorted(set(k[lo]) - set(k[hi]))]})
        return out
    nesting = nest(own, "own W") + nest(on_star, "W*")

    P = pool_from([W[pa], W[pb], W[pab]])
    kP = {p: sc.kill_set(specs[p], P)[0] for p in (pa, pb, pab)}
    union = sorted(set(kP[pa]) | set(kP[pb]))
    prop63 = {"pool": f"W({pa}) ∪ W({pb}) ∪ W({pab})", "pool_size": len(P), "pool_sha256": pool_sha256(P),
              "a": pa, "b": pb, "union_spec": pab, "K_a": kP[pa], "K_b": kP[pb], "K_union_spec": kP[pab],
              "K_a_union_K_b": union, "holds": kP[pab] == union}

    prop62 = None
    if prop62_mutant is not None:
        m1 = [m for m in mutants if m["name"] == prop62_mutant]
        if len(m1) != 1:
            raise EventsError(f"{prop62_mutant} not (uniquely) in the included library")
        mp = {m1[0]["id"]}
        k_owner = sc.kill_set(specs["phi_owner"], star, restrict=mp)[0]
        # Every pair in W* naming m01, with its outcome under phi_cap, so a reader
        # sees what the cap spec did on the configurations that kill m01 for phi_owner.
        k_cap, cap_rows = sc.kill_set(specs["phi_cap"], star, restrict=mp)
        prop62 = {"M_prime": [m1[0]["id"]], "M_prime_names": [prop62_mutant], "pool": "W*",
                  "K_owner": k_owner, "K_cap": k_cap, "equal": k_owner == k_cap,
                  "phi_cap_on_m01_pairs": cap_rows,
                  "note_claim": "phi_owner ≡_M' phi_cap (both kill m1)",
                  "measured": ("equal: the note's counterexample reproduces" if k_owner == k_cap else
                               f"not equal: K(phi_owner) = {[names[i] for i in k_owner]}, "
                               f"K(phi_cap) = {[names[i] for i in k_cap]} on M'")}

    sequence = [{"t": t, "phi_source_sha256": core.sha256_file(specs[p]), "acc": accs.get(p, "Unknown"),
                 "kill_set": on_star[p]} for t, p in enumerate(specs_l)]
    events = trajectory("ladder", 0, [m["id"] for m in mutants], star, sequence)
    asserted_ok = all(n["holds"] for n in nesting) and prop63["holds"]
    return {"version": 1, "subject": subj.name, "specs": list(specs_l),
            "mutants": [{"id": m["id"], "name": m["name"]} for m in mutants],
            "W_sizes": {p: len(W[p]) for p in specs_l}, "W_star": {"size": len(star), "sha256": pool_sha256(star)},
            "kill_own_W": own, "kill_W_star": on_star, "table": table, "nesting": nesting,
            "prop63": prop63, "prop62": prop62, "events": events, "asserted_ok": asserted_ok}


def table_md(doc: dict, which: str) -> str:
    specs = doc["specs"]
    rows = ["| mutant | " + " | ".join(specs) + " |", "|---|" + "---|" * len(specs)]
    for r in doc["table"]:
        rows.append(f"| {r['name']} | " + " | ".join("witness" if r[which][p] else "none" for p in specs) + " |")
    kk = doc["kill_own_W" if which == "own_W" else "kill_W_star"]
    rows.append("| **killed / total** | " + " | ".join(f"{len(kk[p])}/{len(doc['mutants'])}" for p in specs) + " |")
    return "\n".join(rows)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    mode = ap.add_mutually_exclusive_group(required=True)
    mode.add_argument("--ladder", action="store_true")
    mode.add_argument("--trajectory", type=Path, help="JSON list of rounds: {t, spec, acc} (spec = path)")
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    ap.add_argument("--spec-dir", type=Path, help="default: subjects/<subject>/specs")
    ap.add_argument("--witness-dir", type=Path, default=core.ROOT / "build" / "witnesses")
    ap.add_argument("--check-dir", type=Path, default=core.ROOT / "build" / "ladder" / "check",
                    help="check.py --json outputs <phi>.json (for acc)")
    ap.add_argument("--mutants", type=Path, help="default: subjects/<subject>/mutants/mutants.json")
    ap.add_argument("--condition", choices=["f0", "fM", "fMplus", "ladder"])
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--pool", type=Path, nargs="*", default=[], help="witness files whose union is W*")
    ap.add_argument("--out", type=Path)
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 2 if e.code else 0
    subj = core.load_subject(a.subject)
    a.spec_dir = a.spec_dir or subj.specs_dir
    a.mutants = a.mutants or subj.mutants_dir / "mutants.json"
    try:
        mutants = load_mutants(a.mutants)
        if a.ladder:
            accs = {}
            for p in LADDERS[subj.name]["specs"]:
                f = a.check_dir / f"{p}.json"
                if f.is_file():
                    d = json.loads(f.read_text())
                    accs[p] = d.get("check", d)["verdict"]
            doc = ladder(a.spec_dir, a.witness_dir, mutants, accs, subj)
            out = a.out or core.ROOT / "build" / "ladder" / "events_ladder.json"
        else:
            if a.condition is None:
                raise EventsError("--trajectory needs --condition")
            pool = pool_from([load_witnesses(p) for p in a.pool])
            sc = Scorer(mutants, subj)
            rounds = []
            for r in json.loads(a.trajectory.read_text()):
                k = [] if r["acc"] == "lint_rejected" else sc.kill_set(Path(r["spec"]), pool)[0]
                rounds.append({"t": r["t"], "phi_source_sha256": core.sha256_file(r["spec"]),
                               "acc": r["acc"], "kill_set": k})
            doc = trajectory(a.condition, a.seed, [m["id"] for m in mutants], pool, rounds)
            out = a.out or core.ROOT / "build" / "events.json"
    except (EventsError, core.CompileError, core.ExecutorError, core.SigmaError, OSError, KeyError) as e:
        print(f"events: ERROR: {e}", file=sys.stderr)
        return 2
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    if not a.ladder:
        for e in doc["events"]:
            print(f"t={e['t']} -> {e['t'] + 1}: {e['kind']} (lost {len(e['lost'])}, gained {len(e['gained'])}, acc_t {e['acc_t']})")
        print(f"wrote {out}")
        return 0
    print("(i) kill sets on own W\n" + table_md(doc, "own_W"))
    print("\n(i) kill sets on W* (|W*| = %d)\n" % doc["W_star"]["size"] + table_md(doc, "W_star"))
    print("\n(ii) nesting")
    for n in doc["nesting"]:
        print(f"  [{'ok' if n['holds'] else 'FAIL'}] {n['pool']}: K({n['lower']}) ⊆ K({n['upper']})"
              + (f"  missing {n['missing']}" if n["missing"] else ""))
    p3 = doc["prop63"]
    print(f"\n(iii) Prop. 6.3 on {p3['pool']} (|P| = {p3['pool_size']}): "
          f"K({p3['union_spec']}) = K({p3['a']}) ∪ K({p3['b']}): {'ok' if p3['holds'] else 'FAIL'}")
    if doc["prop62"] is not None:
        print(f"\n(iv) Prop. 6.2 on M' = {doc['prop62']['M_prime_names']}: {doc['prop62']['measured']} "
              "(measurement, not asserted)")
    print(f"\nwrote {out}")
    return 0 if doc["asserted_ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
