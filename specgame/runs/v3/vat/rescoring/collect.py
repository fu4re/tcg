"""Collected numbers for REPORT.md section 4 (WP8), read from committed run artifacts only.

    python runs/v3/vat/rescoring/collect.py   (from specgame/)

Inputs per trajectory `runs/v3/vat/<cond>/seed_<s>/`: round_*/cand_*/{score.json,
check_summary.json, response.json}, round_*/selected.json, events.json, trajectory.json,
verify.json, kappa.json, vacuity_a.json; the aborted attempts
`runs/v3/vat/fM/seed_0_aborted_*`; the loop stdout logs copied to `loop_logs/` (WALL lines,
/usr/bin/time). Prices: claude-sonnet-5-5 at $2 per MTok input and $10 per MTok output
(thinking tokens are billed as output and are included in output_tokens).
Writes collect.json and tables.md next to this file.
"""
from __future__ import annotations

import collections
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "tools"))
import runstore  # noqa: E402

TRAJ = [("fM", 0), ("f0", 0), ("f0", 1), ("fMplus", 0), ("fMplus", 1), ("fM", 1)]
ABORTED = ["seed_0_aborted_max_tokens", "seed_0_aborted_code_size", "seed_0_aborted_stack_too_deep"]
PRICE_IN, PRICE_OUT = 2.0, 10.0
mj = json.loads((ROOT / "subjects/vat/mutants/mutants.json").read_text())
NAMES = {m["id"]: Path(m["path"]).stem for m in mj["mutants"]}


def j(p: Path):
    return json.loads(p.read_text())


def cost(tok_in: int, tok_out: int) -> float:
    return round(tok_in / 1e6 * PRICE_IN + tok_out / 1e6 * PRICE_OUT, 4)


def failure_kind(s: dict) -> str | None:
    if s["acc"] == "lint_rejected":
        if s.get("stop_reason") == "max_tokens":
            return "max_tokens (no text)"
        if s["errors"] and "solidity` code blocks" in s["errors"][0]:
            return "no single solidity block"
        rules = sorted({e.split()[0] for e in s["errors"]})
        return "lint " + "+".join(rules)
    if s.get("check_reason") == "compile_error":
        e = s["errors"][0] if s["errors"] else ""
        return "compile_error: Stack too deep" if "Stack too deep" in e else "compile_error: other"
    return None


def candidates(d: Path) -> list[dict]:
    calls = {}
    if (d / "trajectory.json").exists():
        calls = {(c["round"], c["cand"]): c for c in j(d / "trajectory.json")["calls"]}
    out = []
    for rd in sorted(d.glob("round_*"), key=lambda p: int(p.name.split("_")[1])):
        t = int(rd.name.split("_")[1])
        sel = j(rd / "selected.json")["selected"] if (rd / "selected.json").exists() else None
        for cd in sorted(rd.glob("cand_*"), key=lambda p: int(p.name.split("_")[1])):
            c = int(cd.name.split("_")[1])
            row = {"path": str(cd.relative_to(ROOT)), "round": t, "cand": c, "selected": sel == c}
            resp = j(cd / "response.json") if (cd / "response.json").exists() else None
            if resp:
                b = resp.get("body", resp)
                u = b.get("usage", {})
                row.update(stop_reason=b.get("stop_reason"), input_tokens=u.get("input_tokens"),
                           output_tokens=u.get("output_tokens"),
                           thinking_tokens=(u.get("output_tokens_details") or {}).get("thinking_tokens"))
            call = calls.get((t, c))
            if call:
                row["api_wall_s"] = call.get("wall_s")
            if (cd / "score.json").exists():
                s = j(cd / "score.json")
                row.update(acc=s["acc"], check_reason=s.get("check_reason"),
                           ms_cert=f"{s['ms_cert']['killed']}/{s['ms_cert']['total']}",
                           kill_set=sorted(NAMES.get(k, k) for k in s.get("kill_set", [])),
                           adversary_s=s.get("durations_s", {}).get("adversary"),
                           check_s=s.get("durations_s", {}).get("check"),
                           failure=failure_kind(s), n_errors=len(s["errors"]),
                           first_error=(s["errors"][0][:160] if s["errors"] else None))
            else:
                row.update(acc=None, failure="not scored (attempt stopped)")
            cs = cd / runstore.CHECK_SUMMARY
            if cs.exists():
                cj = j(cs)
                cnt = collections.Counter((x["verdict"], x["reason"]) for x in cj["checks"])
                row.update(n_checks=len(cj["checks"]), check_wall_s=cj["duration_s"],
                           check_counts={f"{v}/{r}": n for (v, r), n in sorted(cnt.items())},
                           non_accept=[(x["check"], x["reason"]) for x in cj["checks"] if x["verdict"] != "Accept"])
            out.append(row)
    return out


def wall_from_log(name: str) -> float | None:
    p = HERE / "loop_logs" / f"{name}.log"
    if not p.exists():
        return None
    m = re.search(r"^WALL ([0-9.]+) s$", p.read_text(), re.M)
    return float(m.group(1)) if m else None


def main() -> int:
    doc = {"version": 1, "script": str(Path(__file__).relative_to(ROOT)),
           "prices_usd_per_mtok": {"input": PRICE_IN, "output": PRICE_OUT}, "trajectories": [], "aborted": []}
    all_cands = []
    for c, s in TRAJ:
        d = ROOT / "runs/v3/vat" / c / f"seed_{s}"
        t = j(d / "trajectory.json")
        ev = j(d / "events.json")
        v = j(d / "verify.json")
        k = j(d / "kappa.json")
        va = j(d / "vacuity_a.json")
        cands = candidates(d)
        all_cands += [dict(x, trajectory=f"{c}/seed_{s}") for x in cands]
        tok = t["tokens"]
        doc["trajectories"].append({
            "trajectory": f"{c}/seed_{s}", "condition": c, "seed": s, "path": str(d.relative_to(ROOT)),
            "candidates": cands,
            "rounds": [{"t": r["t"], "acc": r["acc"], "K_on_W_star": sorted(NAMES[x] for x in r["kill_set"]),
                        "size": len(r["kill_set"])} for r in ev["rounds"]],
            "events": [{"t": e["t"], "kind": e["kind"], "gained": sorted(NAMES[x] for x in e["gained"]),
                        "lost": sorted(NAMES[x] for x in e["lost"])} for e in ev["events"]],
            "W_star_size": ev["pool"]["size"], "status": t["result"]["status"], "final": t["result"]["final"],
            "verify": {"verdict": v["verdict"], "exit": v["exit_code"], "ms_cert": v["ms_cert"],
                       "failing_steps": v["failing_steps"]},
            "kappa": {"kappa": k["kappa"], "asserts": k["asserts"], "determined": k["determined"],
                      "unproved_over_H": k["non_tautological_unproved"],
                      "over_H_counts": dict(collections.Counter(f"{x['verdict']}/{x['reason']}" for x in k["checks_over_H"])),
                      "wall_s": t["result"]["kappa"]["wall_s"]},
            "vacuity_a": {"n": len(va["rows"]), "flagged": va["flagged"], "unknown": len(va["unknown"]),
                          "probe_status": dict(collections.Counter(r["probe_status"] for r in va["rows"])),
                          "wall_s": va["duration_s"]},
            "tokens": tok, "cost_usd": cost(tok["input"], tok["output"]),
            "wall_s": wall_from_log(f"{c}_seed_{s}"),
        })
    for a in ABORTED:
        d = ROOT / "runs/v3/vat/fM" / a
        cands = candidates(d)
        tin = sum(x.get("input_tokens") or 0 for x in cands)
        tout = sum(x.get("output_tokens") or 0 for x in cands)
        doc["aborted"].append({"attempt": a, "path": str(d.relative_to(ROOT)), "candidates": cands,
                               "tokens_received": {"input": tin, "output": tout}, "cost_usd_received": cost(tin, tout),
                               "wall_s": wall_from_log(f"fM_{a}")})
    # format failures over the 36 candidates of the six trajectories
    kinds = collections.Counter(x["failure"] or "runnable" for x in all_cands)
    doc["format_failures"] = {"n_candidates": len(all_cands), "by_kind": dict(kinds),
                              "list": [{k: x[k] for k in ("trajectory", "round", "cand", "failure", "n_errors", "first_error", "stop_reason")}
                                       for x in all_cands if x["failure"]]}
    # Unknown reasons over every Check run of the six trajectories
    per_check = collections.Counter()
    n_runs = 0
    for x in all_cands:
        if "check_counts" in x:
            n_runs += 1
            for kk, n in x["check_counts"].items():
                per_check[kk] += n
    spec_reason = collections.Counter(x["check_reason"] for x in all_cands if x.get("acc") == "Unknown")
    doc["unknown_reasons"] = {"check_runs": n_runs, "per_check_totals": dict(per_check),
                              "spec_level_unknown_reasons": dict(spec_reason)}
    tot_in = sum(t["tokens"]["input"] for t in doc["trajectories"])
    tot_out = sum(t["tokens"]["output"] for t in doc["trajectories"])
    tot_th = sum(t["tokens"]["thinking"] for t in doc["trajectories"])
    doc["totals"] = {"wall_s": round(sum(t["wall_s"] for t in doc["trajectories"]), 2),
                     "tokens": {"input": tot_in, "output": tot_out, "thinking": tot_th},
                     "cost_usd": cost(tot_in, tot_out),
                     "aborted_cost_usd_received": round(sum(a["cost_usd_received"] for a in doc["aborted"]), 4),
                     "aborted_wall_s_logged": round(sum(a["wall_s"] or 0 for a in doc["aborted"]), 2)}
    (HERE / "collect.json").write_text(json.dumps(doc, indent=1, sort_keys=True) + "\n")

    md = []
    for t in doc["trajectories"]:
        md.append(f"### {t['trajectory']} (`{t['path']}`)\n")
        md.append("| round | cand | acc | Check: Accept / non-Accept (wall) | own ms_cert | adversary s | output / thinking tok |")
        md.append("|---|---|---|---|---|---|---|")
        for x in t["candidates"]:
            acc = x["acc"] + (f" ({x['check_reason']})" if x.get("check_reason") and x["acc"] != "Accept" else "")
            if x["failure"]:
                acc = f"{x['acc']}: {x['failure']}" + (f" ({x['n_errors']} errors)" if x["n_errors"] > 1 else "")
            chk = "—"
            if "check_counts" in x:
                acc_n = x["check_counts"].get("Accept/all_targets_safe", 0)
                rest = ", ".join(f"{n} {k}" for k, n in x["check_counts"].items() if not k.startswith("Accept"))
                chk = f"{acc_n} / {rest or '0'} ({x['check_wall_s']:.0f} s)"
            adv = "—" if not x.get("adversary_s") else f"{x['adversary_s']:.0f}"
            md.append(f"| {x['round']} | {x['cand']}{' ★' if x['selected'] else ''} | {acc} | {chk} | {x['ms_cert']} | "
                      f"{adv} | {x['output_tokens']} / {x['thinking_tokens']} |")
        md.append("")
    (HERE / "tables.md").write_text("\n".join(md) + "\n")
    print(json.dumps({"format_failures": doc["format_failures"]["by_kind"], "unknown_reasons": doc["unknown_reasons"],
                      "totals": doc["totals"]}, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())
