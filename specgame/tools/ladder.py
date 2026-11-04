"""The hand-written ladder end to end (WP6, gate E2): Check, adversary, bundle,
verify, survivor Checks, events, report.

    python tools/ladder.py [--timeout-ms 120000] [--wall-timeout-s 1500]
        [--seed 0] [--budget 2000] [--max-txs 6] [--per-mutant 1]
        [--specs-dir build/specs] [--skip-survivor phi_full] [--out build/ladder]

Per spec φ of events.LADDER, in order:

1. Check(b, φ) with `tools/check.py --json` -> <out>/check/<φ>.json; reused
   when the file's solc input sha256 equals the one re-derived from (b, φ,
   timeout) (the input fixes the verdict up to solver timing);
2. adversary -> build/witnesses/<φ>.json (+ .log.json);
3. `tools/bundle.py` -> bundles/<φ>/ (Check taken from step 1);
4. `tools/verify.py bundles/<φ>` -> <out>/verify/<φ>.json; must exit 0 (HOLDS);
5. survivor Checks: for every included mutant m not in K_own(φ), Check(m, φ)
   with the same settings -> <out>/survivors/<φ>__<m>.json (reused like 1).
   Accept proves m ∉ K_sem(φ) over CHC's state space, which contains Σ, so
   the survivor is not a budget artifact; Refute means a killable mutant the
   adversary missed within B_A; Unknown leaves it open. Reported, not used
   in any score;
6. `events.ladder` -> tables (i)-(iv), nesting and Prop. 6.3 asserted;
7. κ and vacuity (a) read from `--specs-dir/<φ>.json` (tools/specreport.py
   output) when its timeout and spec/b source hashes match, else "n/a".

Writes <out>/ladder_report.json and <out>/ladder_report.md. Exit 0 iff every
Check(b, φ) is Accept, every bundle HOLDS and every asserted relation holds.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import adversary  # noqa: E402
import events  # noqa: E402
import seqgen  # noqa: E402
import specgame_core as core  # noqa: E402

TOOLS = Path(__file__).resolve().parent
# Set from --subject in main() (default: protocol.json default_subject). The
# spec list and relations per subject are events.LADDERS; outputs of a subject
# other than capped_token go to bundles/<subject>/, build/witnesses/<subject>/
# and build/<subject>_ladder/.
SUBJECT = core.load_subject()
B = SUBJECT.source_path
MUTANTS = SUBJECT.mutants_dir / "mutants.json"
SPECS = SUBJECT.specs_dir
BUNDLES = core.ROOT / "bundles"
WITNESSES = core.ROOT / "build" / "witnesses"


def say(msg: str) -> None:
    print(f"ladder: {msg}", flush=True)


def py(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", *args], capture_output=True, text=True)


def cached_check(spec: Path, artifact: Path, timeout_ms: int, wall_s: float, out: Path) -> dict:
    """check.py --json (Check v2, isolated); per-check results come from the
    verdict cache build/cache/ when the exact solc input was checked before."""
    out.parent.mkdir(parents=True, exist_ok=True)
    p = py(str(TOOLS / "check.py"), str(spec), "--subject", SUBJECT.name, "--artifact", str(artifact),
           "--timeout-ms", str(timeout_ms),
           "--wall-timeout-s", str(wall_s), "--json", str(out))
    if p.returncode not in (0, 2, 3) or not out.is_file():
        raise SystemExit(f"check.py failed on {spec} over {artifact}: {p.stdout[-800:]}{p.stderr[-800:]}")
    d = json.loads(out.read_text())
    return d.get("check", d)


def specreport_row(specs_dirs: list[Path], name: str, timeout_ms: int) -> dict:
    whys = []
    for d in specs_dirs:
        r = _specreport_row(d, name, timeout_ms)
        if r["available"]:
            return r
        whys.append(r["why"])
    return {"available": False, "why": "; ".join(whys)}


def _specreport_row(specs_dir: Path, name: str, timeout_ms: int) -> dict:
    f = specs_dir / f"{name}.json"
    if not f.is_file():
        return {"available": False, "why": f"no {f}"}
    d = json.loads(f.read_text())
    if d.get("timeout_ms") != timeout_ms:
        return {"available": False, "why": f"{f} was run at timeout_ms {d.get('timeout_ms')}"}
    if d.get("spec_source_sha256") != core.sha256_file(SPECS / f"{name}.sol") \
            or d.get("artifact_source_sha256") != core.sha256_file(B):
        return {"available": False, "why": f"{f}: spec or b source differs"}
    k, v = d.get("kappa") or {}, d.get("vacuity_a") or {}
    return {"available": True, "source": str(f), "kappa": k.get("kappa"), "asserts": k.get("asserts"),
            "kappa_unproved": k.get("non_tautological_unproved"),
            "vacuity_a": "flag" if v.get("flagged") else ("unknown" if v.get("unknown") else "ok"),
            "vacuity_a_flagged": v.get("flagged"), "vacuity_s": v.get("duration_s")}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--timeout-ms", type=int, default=core.CHECK_TIMEOUT_MS)
    ap.add_argument("--wall-timeout-s", type=float, default=core.CHECK_WALL_TIMEOUT_S)
    ap.add_argument("--seed", type=int, default=adversary.DEFAULT_SEED)
    ap.add_argument("--budget", type=int, default=adversary.DEFAULT_BUDGET)
    ap.add_argument("--max-txs", type=int, default=seqgen.DEFAULT_MAX_TXS)
    ap.add_argument("--per-mutant", type=int, default=adversary.DEFAULT_PER_MUTANT)
    ap.add_argument("--specs-dir", type=Path, nargs="+", default=[core.ROOT / "build" / "specs"],
                    help="specreport output dirs, first match wins")
    ap.add_argument("--render-only", action="store_true",
                    help="re-read <out>/ladder_report.json, refresh kappa / vacuity (a) rows, rewrite the report")
    ap.add_argument("--skip-survivor", nargs="*", default=[], help="specs whose survivor Checks are not run")
    ap.add_argument("--reuse-witnesses", action="store_true",
                    help="reuse <witnesses>/<phi>.json when its log has the same adversary id and spec sha256")
    ap.add_argument("--survivor-specs", nargs="*", help="only these specs get survivor Checks (default: all)")
    ap.add_argument("--out", type=Path, help="default: build/ladder (capped_token), build/<subject>_ladder")
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    a = ap.parse_args(argv)
    global SUBJECT, B, MUTANTS, SPECS, BUNDLES, WITNESSES
    SUBJECT = core.load_subject(a.subject)
    B, MUTANTS, SPECS = SUBJECT.source_path, SUBJECT.mutants_dir / "mutants.json", SUBJECT.specs_dir
    default_subject = SUBJECT.name == "capped_token"
    if not default_subject:
        BUNDLES = core.ROOT / "bundles" / SUBJECT.name
        WITNESSES = core.ROOT / "build" / "witnesses" / SUBJECT.name
    out = a.out or core.ROOT / "build" / ("ladder" if default_subject else f"{SUBJECT.name}_ladder")
    ladder_specs = events.LADDERS[SUBJECT.name]["specs"]
    mutants = events.load_mutants(MUTANTS)
    names = {m["id"]: m["name"] for m in mutants}
    if a.render_only:
        doc = json.loads((out / "ladder_report.json").read_text())
        ok = True
        for p, r in doc["specs"].items():
            r["specreport"] = specreport_row(a.specs_dir, p, doc["timeout_ms"])
            vj = out / "verify" / f"{p}.json"
            if r.get("verify", {}).get("exit") is not None and vj.is_file():
                r["verify"]["consistent"] = verify_consistent(
                    json.loads(vj.read_text()), r["check"]["verdict"] == core.Verdict.ACCEPT.value,
                    r["adversary"]["kill_set"])
            ok &= r["check"]["verdict"] != core.Verdict.REFUTE.value and r.get("verify", {}).get("consistent", False)
        doc["ok"] = ok and doc["ladder"]["asserted_ok"]
        (out / "ladder_report.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
        (out / "ladder_report.md").write_text(report_md(doc, names))
        say(f"re-rendered {out / 'ladder_report.md'}")
        return 0 if doc["ok"] else 1
    rows, ok, all_accept = {}, True, True

    for p in ladder_specs:
        spec = SPECS / f"{p}.sol"
        r: dict = {"spec": f"specs/{p}.sol", "spec_source_sha256": core.sha256_file(spec)}
        t0 = time.monotonic()
        c = cached_check(spec, B, a.timeout_ms, a.wall_timeout_s, out / "check" / f"{p}.json")
        r["check"] = {"verdict": c["verdict"], "reason": c["reason"], "duration_s": c["duration_s"],
                      "cpu_s": c["cpu_s"], "cache_hits": c["cache_hits"], "mode": c["mode"],
                      "timeout_ms": c["timeout_ms"], "wall_timeout_s": c["wall_timeout_s"],
                      "checks": [{"check": x["check"], "verdict": x["result"]["verdict"],
                                  "duration_s": x["result"]["duration_s"], "cached": x["cached"],
                                  "solc_input_sha256": x["result"]["solc_input_sha256"]} for x in c["checks"]]}
        say(f"{p}: Check(b) {c['verdict']} ({c['reason']}, {c['duration_s']} s)")
        accepted = c["verdict"] == core.Verdict.ACCEPT.value
        all_accept &= accepted
        ok &= c["verdict"] != core.Verdict.REFUTE.value

        wfile, lfile = WITNESSES / f"{p}.json", WITNESSES / f"{p}.log.json"
        W = log = None
        if a.reuse_witnesses and wfile.is_file() and lfile.is_file():
            prev = json.loads(lfile.read_text())
            want = adversary.adversary_id(adversary.params(
                a.seed, a.budget, a.max_txs, a.per_mutant,
                seqgen.tx_functions(core.compile_artifact(B, subject=SUBJECT), SUBJECT), SUBJECT))
            if prev.get("adversary_id") == want and prev.get("spec_source_sha256") == core.sha256_file(spec):
                W, log = json.loads(wfile.read_text()), prev
                say(f"{p}: reusing witnesses ({wfile})")
        if W is None:
            W, log = adversary.search(spec, mutants, B, a.seed, a.budget, a.max_txs, a.per_mutant, SUBJECT)
            WITNESSES.mkdir(parents=True, exist_ok=True)
            wfile.write_text(json.dumps(W, indent=1, sort_keys=True) + "\n")
            lfile.write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
        r["adversary"] = {"id": log["adversary_id"], "wall_s": log["wall_s"], "W": len(W),
                          "discarded": len(log["discarded"]), "kill_set": log["kill_set"],
                          "tries": {m["name"]: m["sigmas_tried"] for m in log["mutants"]}}
        say(f"{p}: adversary {log['adversary_id'][:12]} |W| = {len(W)}, {log['wall_s']} s")

        bdir = BUNDLES / p
        t1 = time.monotonic()
        pb = py(str(TOOLS / "bundle.py"), "--out", str(bdir), "--subject", SUBJECT.name, "--artifact", str(B),
                "--spec", str(spec),
                "--mutants", str(MUTANTS), "--witnesses", str(wfile), "--adversary-id", log["adversary_id"],
                "--adversary-source", str(TOOLS / "adversary.py"), "--adversary-seed", str(a.seed),
                "--adversary-budget", str(a.budget), "--check-json", str(out / "check" / f"{p}.json"))
        r["bundle"] = {"exit": pb.returncode, "line": (pb.stdout.strip().splitlines() or [""])[-1],
                       "wall_s": round(time.monotonic() - t1, 3)}
        if pb.returncode != 0:
            say(f"{p}: bundle FAILED: {pb.stderr[-800:]}")
            ok = False
            r["verify"] = {"exit": None, "verdict": "not_run (bundle failed)", "consistent": False}
        else:
            verify_bundle(p, bdir, out, accepted, log, r)
            ok &= r["verify"]["consistent"]

        surv = []
        for m in mutants:
            if m["id"] in log["kill_set"]:
                continue
            if p in a.skip_survivor or (a.survivor_specs is not None and p not in a.survivor_specs):
                surv.append({"mutant": m["name"], "verdict": "not_run"})
                continue
            sc = cached_check(spec, m["path"], a.timeout_ms, a.wall_timeout_s,
                              out / "survivors" / f"{p}__{m['name']}.json")
            surv.append({"mutant": m["name"], "verdict": sc["verdict"], "reason": sc["reason"],
                         "duration_s": sc["duration_s"]})
        r["survivor_checks"] = surv
        r["specreport"] = specreport_row(a.specs_dir, p, a.timeout_ms)
        r["wall_s"] = round(time.monotonic() - t0, 3)
        rows[p] = r

    lad = events.ladder(SPECS, WITNESSES, mutants, {p: rows[p]["check"]["verdict"] for p in rows}, SUBJECT)
    ok &= lad["asserted_ok"]
    params = adversary.params(a.seed, a.budget, a.max_txs, a.per_mutant,
                              seqgen.tx_functions(core.compile_artifact(B, subject=SUBJECT), SUBJECT), SUBJECT)
    doc = {"version": 1, "subject": SUBJECT.name, "ok": ok, "all_accept": all_accept, "timeout_ms": a.timeout_ms, "wall_timeout_s": a.wall_timeout_s,
           "adversary_params": params, "adversary_id": adversary.adversary_id(params),
           "specs": rows, "ladder": lad}
    out.mkdir(parents=True, exist_ok=True)
    (out / "events_ladder.json").write_text(json.dumps(lad, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "ladder_report.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    (out / "ladder_report.md").write_text(report_md(doc, names))
    say(f"wrote {out / 'ladder_report.md'}; {'ALL OK' if ok else 'FAILED'}")
    return 0 if ok else 1


def verify_consistent(rep: dict, accepted: bool, kill_set: list[str]) -> bool:
    """What verify.py must say about a ladder bundle. Check(b) Accept: HOLDS
    (exit 0). Check(b) Unknown: the bundle is not a certificate, so verify
    says NOT_CERTIFIED (exit 2) at step 2 only, the recorded Unknown table
    reproduced with no Refute on re-run, while steps 3-5 pass, i.e. M, W and
    ms_cert are recomputed and the kill set equals the adversary's."""
    steps = {int(st["step"]): st for st in rep.get("steps", [])}
    if accepted:
        return rep.get("exit_code") == 0
    if (rep.get("verdict"), rep.get("exit_code")) != ("NOT_CERTIFIED", 2) or rep.get("failing_steps") != [2]:
        return False
    if any("Refute" in d for d in steps[2]["details"]):
        return False
    return all(steps[k]["status"] == "pass" for k in (3, 4, 5)) and rep.get("kill_set") == kill_set


def verify_bundle(p: str, bdir: Path, out: Path, accepted: bool, log: dict, r: dict) -> None:
    t2 = time.monotonic()
    vj = out / "verify" / f"{p}.json"
    vj.parent.mkdir(parents=True, exist_ok=True)
    pv = py(str(TOOLS / "verify.py"), str(bdir), "--json", str(vj))
    rep = json.loads(vj.read_text()) if vj.is_file() else {}
    steps = {st["step"]: st["status"] for st in rep.get("steps", [])}
    r["verify"] = {"exit": pv.returncode, "wall_s": round(time.monotonic() - t2, 3),
                   "verdict": rep.get("verdict"), "ms_cert": rep.get("ms_cert"), "kill_set": rep.get("kill_set"),
                   "steps": steps, "summary": pv.stdout.strip().splitlines()[-3:]}
    say(f"{p}: verify exit {pv.returncode} ({r['verify']['wall_s']} s)")
    r["verify"]["consistent"] = verify_consistent(rep, accepted, log["kill_set"])


def report_md(doc: dict, names: dict) -> str:
    lad, rows = doc["ladder"], doc["specs"]
    n = len(lad["mutants"])
    L = ["# Ladder report (WP6, gate E2)", "",
         "Generated by `tools/ladder.py`; every number below is recomputed from the committed sources.", "",
         "## Setup", "",
         "| Item | Value |", "|---|---|",
         f"| b | `subjects/{doc.get('subject', 'capped_token')}/{Path(str(B)).name}` |",
         f"| M | `subjects/{doc.get('subject', 'capped_token')}/mutants/mutants.json`, {n} included mutants |",
         f"| Check | protocol v2: SMTChecker CHC + z3 per check (isolated harnesses, 4 workers), timeout_ms {doc['timeout_ms']}, wall {doc['wall_timeout_s']} s per check |",
         f"| Adversary | `tools/adversary.py`, id `{doc['adversary_id'][:16]}…`, seed_A {doc['adversary_params']['seed']}, "
         f"B_A {doc['adversary_params']['B_A']}, max_txs {doc['adversary_params']['max_txs']}, "
         f"witnesses per mutant {doc['adversary_params']['per_mutant']} |",
         f"| W* | union of the {len(lad['specs'])} W, {lad['W_star']['size']} distinct pairs, sha256 `{lad['W_star']['sha256'][:16]}…` |",
         "", "## Per spec", "",
         "| Spec | Check(b) | Check s | κ / asserts | vacuity (a) | \\|W\\| | adversary s | bundle → verify | ms_cert (verifier) | verify s |",
         "|---|---|---|---|---|---|---|---|---|---|"]
    for p in lad["specs"]:
        r = rows[p]
        sr = r.get("specreport", {})
        kap = f"{sr['kappa']} / {sr['asserts']}" if sr.get("available") else "n/a"
        vac = sr["vacuity_a"] if sr.get("available") else "n/a"
        v = r.get("verify", {})
        rec = v.get("ms_cert")
        ms = f"{rec['killed']}/{rec['total']}" if rec else "-"
        vo = {0: "HOLDS", 2: "COULD NOT VERIFY", 3: "REFUSED"}.get(v.get("exit"), str(v.get("exit")))
        L.append(f"| {p} | {r['check']['verdict']} | {r['check']['duration_s']} | {kap} | {vac} | "
                 f"{r['adversary']['W']} | {r['adversary']['wall_s']} | {vo} | {ms} | {v.get('wall_s', '-')} |")
    missing = [p for p in lad["specs"] if not rows[p].get("specreport", {}).get("available")]
    if missing:
        L += ["", "κ / vacuity (a) n/a: " + "; ".join(f"{p}: {rows[p]['specreport']['why']}" for p in missing)]
    L += ["", "## (i) Spec × mutant (own W of each spec)", "", events.table_md(lad, "own_W"),
          "", f"## (i') Spec × mutant on the pooled W* (|W*| = {lad['W_star']['size']})", "",
          events.table_md(lad, "W_star"),
          "", "## Survivor Checks (solver evidence for the `none` cells, own W)", "",
          "Check(m, φ) over the surviving mutant, same settings. Accept = m ∉ K_sem(φ) "
          "(CHC's state space contains Σ), so the survivor is not a budget artifact; "
          "Refute = the adversary missed a killable mutant; Unknown = open.", "",
          "| Spec | " + " | ".join(f"m{i + 1:02d}" for i in range(n)) + " |", "|---|" + "---|" * n]
    for p in lad["specs"]:
        sv = {s["mutant"]: s["verdict"] for s in rows[p].get("survivor_checks", [])}
        cells = []
        for m in lad["mutants"]:
            cells.append("killed" if m["name"] not in sv else sv[m["name"]])
        L.append(f"| {p} | " + " | ".join(cells) + " |")
    L += ["", "## (ii) Nesting (asserted)", "", "| Pool | Relation | Holds |", "|---|---|---|"]
    for x in lad["nesting"]:
        L.append(f"| {x['pool']} | K({x['lower']}) ⊆ K({x['upper']}) | {'yes' if x['holds'] else 'NO ' + str(x['missing'])} |")
    p3 = lad["prop63"]
    L += ["", "## (iii) Prop. 6.3 (asserted)", "",
          f"Pool P = {p3['pool']}, {p3['pool_size']} distinct pairs.", "",
          f"- K_P({p3['a']}) = {sorted(names[i] for i in p3['K_a'])}",
          f"- K_P({p3['b']}) = {sorted(names[i] for i in p3['K_b'])}",
          f"- K_P({p3['union_spec']}) = {sorted(names[i] for i in p3['K_union_spec'])}",
          f"- K_P({p3['a']}) ∪ K_P({p3['b']}) = {sorted(names[i] for i in p3['K_a_union_K_b'])}",
          f"- equal: **{'yes' if p3['holds'] else 'NO'}**"]
    p2 = lad["prop62"]
    L += prop62_md(p2, rows, names) if p2 is not None else []
    return tail_md(doc, lad, rows, names, n, L)


def prop62_md(p2: dict, rows: dict, names: dict) -> list[str]:
    L: list[str] = []
    L += ["", "## (iv) Prop. 6.2 counterexample on M' = {m01_mint_no_owner} (measurement)", "",
          f"Note's claim: {p2['note_claim']}.", "",
          f"- K_M'(phi_owner) on W* = {sorted(names[i] for i in p2['K_owner'])}",
          f"- K_M'(phi_cap) on W* = {sorted(names[i] for i in p2['K_cap'])}",
          f"- measured: **{p2['measured']}**",
          "- phi_cap outcomes on the W* pairs of m01: "
          + "; ".join(f"{json.dumps(x['outcomes'], sort_keys=True)}" for x in p2["phi_cap_on_m01_pairs"])]
    cap_m01 = next((s for s in rows["phi_cap"].get("survivor_checks", []) if s["mutant"] == "m01_mint_no_owner"), None)
    if cap_m01:
        L.append(f"- solver: Check(m01, phi_cap) = **{cap_m01['verdict']}** ({cap_m01.get('reason', '')})")
    return L


def tail_md(doc: dict, lad: dict, rows: dict, names: dict, n: int, L: list[str]) -> str:
    ev = lad["events"]["events"]
    L += ["", "## Ladder as a sequence (events on W*, protocol.md section 13)", "",
          "Not a trajectory; the event kinds on consecutive ladder specs, as a check of events.py on real kill sets.", "",
          "| t → t+1 | kind | lost | gained |", "|---|---|---|---|"]
    for e in ev:
        a, b = lad["specs"][e["t"]], lad["specs"][e["t"] + 1]
        L.append(f"| {a} → {b} | {e['kind']} | {sorted(names[i] for i in e['lost'])} | {sorted(names[i] for i in e['gained'])} |")
    L += ["", "## Adversary tries per (spec, mutant) (σ evaluated until the first kept witness, or B_A)", "",
          "| Spec | " + " | ".join(f"m{i + 1:02d}" for i in range(n)) + " |", "|---|" + "---|" * n]
    for p in lad["specs"]:
        t = rows[p]["adversary"]["tries"]
        L.append(f"| {p} | " + " | ".join(str(t[m["name"]]) for m in lad["mutants"]) + " |")
    if doc.get("all_accept", True):
        verdict = "all asserted relations hold, every bundle HOLDS"
    else:
        verdict = ("all asserted relations hold; every bundle HOLDS where Check(b) Accepts; where Check(b) "
                   "is Unknown the verifier stops it at step 2 only (not a certificate) while M, W and "
                   "the score (steps 3-5) are recomputed and equal the claim")
    L += ["", f"Overall: **{verdict if doc['ok'] else 'FAILED'}**.", ""]
    return "\n".join(L)


if __name__ == "__main__":
    sys.exit(main())
