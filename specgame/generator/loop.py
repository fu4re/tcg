"""Generator loop G (WP7; gates E3, E5; protocol.md section 16).

    python generator/loop.py --condition f0|fM|fMplus --seed N [--rounds 3] [--k 2] [--dry-run]
                             [--out runs/] [--max-calls N]

One trajectory = R rounds x k candidates. Per round t and candidate j: one
Messages API call (the conversation so far is replayed verbatim, append-only),
the single `solidity` block of the reply becomes Spec.sol, then
lint -> Check(b, Spec) -> adversary (W_t) -> ms_cert on W_t, all through the
judge tools in tools/ (never an LLM). The selection rule (protocol.md 16.3)
picks one candidate per round using only what the condition reveals; its
reply is appended to the conversation and the feedback for round t+1
(prompts/feedback_<condition>.md) follows it as the next user turn.

After R rounds: κ and vacuity (a) on the final selected spec, a bundle
(tools/bundle.py) and its verification (tools/verify.py), the per-round kill
sets K_t on W* (all candidates' W_t of this trajectory plus the ladder's W*)
and the events (tools/events.py) -> events.json, and trajectory.md.

This module is NOT on the judge path: nothing in tools/ imports it, and the
judge never reads model output except as a candidate spec file.

API key: ANTHROPIC_API_KEY, else ~/.specgame_env (`ANTHROPIC_API_KEY=...`).
The key is passed to the SDK client only; it is never printed or written.
`--dry-run` renders the round-1 request and exits without any network call.
Exit codes: 0 trajectory done (whatever its results), 1 usage / setup error,
2 an API call failed (the partial trajectory stays on disk).
"""
from __future__ import annotations

import argparse
import difflib
import json
import os
import re
import string
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent  # specgame/
sys.path.insert(0, str(ROOT / "tools"))
import specgame_core as core  # noqa: E402
import adversary  # noqa: E402
import check as check_cli  # noqa: E402
import events  # noqa: E402
import runstore  # noqa: E402
import kappa as kappa_mod  # noqa: E402
import vacuity as vacuity_mod  # noqa: E402

PROMPTS = HERE / "prompts"
PROMPT_FILES = ("system.md", "round_1.md", "feedback_f0.md", "feedback_fM.md", "feedback_fMplus.md")
# Set from --subject in main() (default: protocol.json default_subject). The
# prompts in generator/prompts/ are the capped token's; another subject needs a
# `generator` entry in protocol.json and its own prompts (protocol v3).
SUBJECT = core.load_subject()
B = SUBJECT.source_path
INTENT = SUBJECT.intent_path
MUTANTS = SUBJECT.mutants_dir / "mutants.json"
CONDITIONS = tuple(core.PROTOCOL["subjects"][core.DEFAULT_SUBJECT]["generator"]["conditions"])

# Frozen protocol values, read from protocol.json (authoritative).
def frozen_for(subject: str) -> dict:
    sub = core.PROTOCOL["subjects"][subject]
    g, a = sub["generator"], sub["adversary"]
    return {"model": g["model"], "max_tokens": g["max_tokens"], "effort": g["output_config"]["effort"],
            "rounds": g["rounds"], "k": g["k"], "timeout_ms": core.CHECK_TIMEOUT_MS,
            "wall_timeout_s": core.CHECK_WALL_TIMEOUT_S, "seed_A": a["seed_A"], "B_A": a["B_A"],
            "max_txs": a["max_txs"], "per_mutant": a["per_mutant"]}


FROZEN = frozen_for(core.DEFAULT_SUBJECT)
DEFAULT_LADDER_BUNDLES = "bundles/phi_*/manifest.json"  # the capped token's ladder
SOLIDITY_BLOCK = re.compile(r"```solidity[ \t]*\n(.*?)```", re.S)
KEY_ENV = "ANTHROPIC_API_KEY"
KEY_FILE = Path.home() / ".specgame_env"


class LoopError(Exception):
    pass


# ---------------------------------------------------------------- prompts

def prompt_path(name: str) -> Path:
    """subjects/<subject>/prompts/<name> if the subject has its own, else the
    shared generator/prompts/<name> (the feedback templates are shared)."""
    own = SUBJECT.dir / "prompts" / name
    return own if own.is_file() else PROMPTS / name


def prompt_hashes() -> dict[str, str]:
    return {name: core.sha256_file(prompt_path(name)) for name in PROMPT_FILES}


def prompts_sha256() -> str:
    """One hash over all prompt files (recorded in bundles' provenance)."""
    return core.json_sha256(prompt_hashes())


def render(name: str, **values) -> str:
    """$placeholders only (string.Template), so Solidity braces need no escaping.
    A missing value is an error, never a silent blank."""
    return string.Template(prompt_path(name).read_text()).substitute(**values)


def system_prompt() -> str:
    return prompt_path("system.md").read_text()


def round1_prompt(rounds: int) -> str:
    return render("round_1.md", contract=B.read_text().rstrip("\n"),
                  intent=INTENT.read_text().strip(), rounds_left=rounds - 1)


def diagnostics_text(score: dict) -> str:
    """Lint / compile / checker text shown under every condition (protocol.md 16.4)."""
    if score["acc"] == "lint_rejected":
        lines = ["The file was rejected before checking:"]
        lines += [f"- {e}" for e in score["errors"]] or ["- (no reason recorded)"]
        return "\n".join(lines)
    if score["acc"] == "Accept":
        return "Every assert was proved."
    if score.get("check_reason") == "compile_error":
        return "The file does not compile:\n" + "\n".join(f"- {e}" for e in score["errors"])
    lines = []
    for t in score.get("not_proved", []):
        if t["status"] == "violated":
            what = "can fail"
        elif t["status"] == "wall_timeout":
            lines.append(f"- {t['function']} (line {t['line']}): the checker ran out of time on this check")
            continue
        elif t["status"] in ("compile_error", "solver_unavailable", "unparsed"):
            lines.append(f"- {t['function']} (line {t['line']}): the checker gave no verdict ({t['status']})")
            continue
        else:
            what = "could not be decided within the checker's budget"
        lines.append(f"- line {t['line']} in {t['function']}: `{t['text']}` {what}")
    if not lines:
        lines.append(f"- the checker gave no verdict ({score.get('check_reason')})")
    return "Not every assert was proved:\n" + "\n".join(lines)


def feedback_prompt(condition: str, round_no: int, rounds: int, score: dict, labels: dict[str, str]) -> str:
    vals = {"round": round_no, "rounds_left": rounds - round_no,
            "verdict": "Accept" if score["acc"] == "Accept" else "not accepted",
            "diagnostics": diagnostics_text(score)}
    if condition in ("fM", "fMplus"):
        vals.update(killed=score["ms_cert"]["killed"], total=score["ms_cert"]["total"])
    if condition == "fMplus":
        surv = score["survivors"]
        vals["survivors"] = "\n".join(f"- {m[:12]} ({labels[m]})" for m in surv) if surv else "- none"
    return render(f"feedback_{condition}.md", **vals)


def example_score() -> dict:
    """A fabricated score used only to render feedback in --dry-run and tests
    (placeholder ids if the subject has no mutants.json yet)."""
    if MUTANTS.is_file():
        ids = [m["id"] for m in json.loads(MUTANTS.read_text())["mutants"] if m["status"] == "included"]
    else:
        ids = [core.sha256_hex(f"example-mutant-{n}".encode()) for n in range(8)]
    return {"acc": "Refute", "check_reason": "counterexample", "errors": [],
            "ms_cert": {"killed": 2, "total": len(ids)}, "kill_set": ids[:2], "survivors": ids[2:],
            "not_proved": [{"function": "check_example", "line": 12, "status": "violated",
                            "text": "assert(totalSupply < cap);"}]}


# ---------------------------------------------------------------- selection (protocol.md 16.3)

def error_count(score: dict) -> int:
    return len(score.get("errors", []))


def select(condition: str, scores: list[dict]) -> int:
    """Index of the selected candidate. Uses only what `condition` reveals."""
    if not scores:
        raise LoopError("no candidates")
    if condition == "f0":
        key = lambda i: (scores[i]["acc"] != "Accept", error_count(scores[i]), i)
    elif condition in ("fM", "fMplus"):
        key = lambda i: (scores[i]["acc"] != "Accept", -scores[i]["ms_cert"]["killed"], i)
    else:
        raise LoopError(f"condition {condition!r}")
    return min(range(len(scores)), key=key)


# ---------------------------------------------------------------- candidate post-processing

def extract_spec(reply_text: str) -> tuple[str | None, str | None]:
    blocks = SOLIDITY_BLOCK.findall(reply_text)
    if len(blocks) != 1:
        return None, f"reply has {len(blocks)} `solidity` code blocks, exactly 1 required"
    return blocks[0], None


def reply_text(response: dict) -> str:
    return "".join(b.get("text", "") for b in response.get("content", []) if b.get("type") == "text")


def process_candidate(text: str, cdir: Path, mutants: list[dict], stop_reason: str | None = None) -> dict:
    """Spec.sol, lint.json, check.json.gz + check_summary.json, witnesses.json, score.json for one reply."""
    cdir.mkdir(parents=True, exist_ok=True)
    total = len(mutants)
    score: dict = {"acc": None, "check_reason": None, "errors": [], "ms_cert": {"killed": 0, "total": total},
                   "kill_set": [], "survivors": [m["id"] for m in mutants], "not_proved": [],
                   "stop_reason": stop_reason, "durations_s": {}}
    src, err = extract_spec(text)
    if src is None:
        if stop_reason and stop_reason != "end_turn":
            err += f" (stop_reason {stop_reason})"
        score.update(acc="lint_rejected", errors=[err])
        (cdir / "lint.json").write_text(json.dumps({"extracted": False, "problems": [err]}, indent=1) + "\n")
        (cdir / "score.json").write_text(json.dumps(score, indent=1, sort_keys=True) + "\n")
        return score
    spec = cdir / "Spec.sol"
    spec.write_text(src)
    score["spec_source_sha256"] = core.sha256_file(spec)
    try:
        problems = check_cli.lint(spec, B, subject=SUBJECT)
    except core.CompileError as e:
        raise LoopError(f"b does not compile: {e}")
    (cdir / "lint.json").write_text(json.dumps({"extracted": True, "problems": problems}, indent=1) + "\n")
    if problems:
        score.update(acc="lint_rejected", errors=problems)
        (cdir / "score.json").write_text(json.dumps(score, indent=1, sort_keys=True) + "\n")
        return score

    # The whole Spec over b must compile to bytecode (the executor runs it).
    # SMTChecker's own compile skips code generation, so codegen errors such
    # as "Stack too deep" pass lint and Check; protocol.md 16.2: compile_error,
    # no Check, no adversary.
    try:
        core.compile_spec_over(spec, B, subject=SUBJECT)
    except core.CompileError as e:
        score.update(acc=core.Verdict.UNKNOWN.value, check_reason="compile_error", errors=[str(e)])
        (cdir / "witnesses.json").write_text("[]\n")
        (cdir / "score.json").write_text(json.dumps(score, indent=1, sort_keys=True) + "\n")
        return score

    t0 = time.monotonic()
    r = core.smtcheck_isolated(spec, B, FROZEN["timeout_ms"], FROZEN["wall_timeout_s"], cache_dir=core.CACHE_DIR,
                               subject=SUBJECT)
    score["durations_s"]["check"] = round(time.monotonic() - t0, 3)
    score["check_cpu_s"], score["check_cache_hits"] = r.cpu_s, r.cache_hits
    # check.json.gz + check_summary.json (protocol.md 16.10 storage note)
    runstore.write_check_record(cdir, (json.dumps(
        {"spec": "Spec.sol", "artifact": str(B.relative_to(ROOT)), "spec_source_sha256": score["spec_source_sha256"],
         "artifact_source_sha256": core.sha256_file(B), "lint": [], "mode": "isolated", "check": asdict(r)},
        indent=1, sort_keys=True) + "\n").encode())
    score["acc"], score["check_reason"] = r.verdict, r.reason
    score["not_proved"] = not_proved(src, r)
    if r.reason == "compile_error":
        diags = [d for c in r.checks for d in c["result"]["diagnostics"]]
        score["errors"] = [d for d in diags if d.split(":")[0].endswith("Error")] or diags[:5] \
            or ["the check_* functions could not be isolated (unbalanced braces or no contract Spec)"]
        (cdir / "witnesses.json").write_text("[]\n")
        (cdir / "score.json").write_text(json.dumps(score, indent=1, sort_keys=True) + "\n")
        return score

    t0 = time.monotonic()
    W, log = adversary.search(spec, mutants, B, FROZEN["seed_A"], FROZEN["B_A"], FROZEN["max_txs"],
                              FROZEN["per_mutant"], SUBJECT)
    score["durations_s"]["adversary"] = round(time.monotonic() - t0, 3)
    (cdir / "witnesses.json").write_text(json.dumps(W, indent=1, sort_keys=True) + "\n")
    (cdir / "adversary_log.json").write_text(json.dumps(log, indent=1, sort_keys=True) + "\n")
    kill = sorted({w["mutant"] for w in W})
    score.update(ms_cert={"killed": len(kill), "total": total}, kill_set=kill,
                 survivors=[m["id"] for m in mutants if m["id"] not in kill], adversary_id=log["adversary_id"])
    (cdir / "score.json").write_text(json.dumps(score, indent=1, sort_keys=True) + "\n")
    return score


def not_proved(src: str, r) -> list[dict]:
    """Asserts not proved safe, located in the candidate's own file: a target's
    line in the isolated harness is mapped back through the check's offset."""
    lines = src.splitlines()
    header_lines = SUBJECT.header().count("\n")
    texts = dict(core.check_functions(src, SUBJECT))
    out = []
    for c in r.checks:
        res = c["result"]
        start = core.strip_source(src).count("\n", 0, src.index(texts[c["check"]])) + 1 if c["check"] in texts else None
        if res["reason"] in ("wall_timeout", "compile_error", "solver_unavailable", "unparsed") and not res["targets"]:
            out.append({"function": c["check"], "line": start, "status": res["reason"], "text": ""})
            continue
        for t in res["targets"]:
            if t["status"] == "safe":
                continue
            line = start + (t["line"] - header_lines - 1) if start and t["line"] else None
            txt = lines[line - 1].strip() if line and line <= len(lines) else ""
            out.append({"function": c["check"], "line": line, "status": t["status"] or "no result", "text": txt})
    return out


# ---------------------------------------------------------------- API

def api_key() -> str | None:
    key = os.environ.get(KEY_ENV)
    if key:
        return key
    if KEY_FILE.is_file():
        for line in KEY_FILE.read_text().splitlines():
            if line.startswith(KEY_ENV + "="):
                return line.split("=", 1)[1].strip().strip("'\"") or None
    return None


def request_body(system: str, messages: list[dict]) -> dict:
    """The exact request body (no key; no sampling parameters, protocol.md 16.1)."""
    return {"model": FROZEN["model"], "max_tokens": FROZEN["max_tokens"],
            "output_config": {"effort": FROZEN["effort"]}, "system": system, "messages": messages}


def content_params(response: dict) -> list[dict]:
    """The assistant turn to replay: the response's content blocks, unchanged."""
    out = []
    for b in response["content"]:
        if b["type"] == "text":
            out.append({"type": "text", "text": b["text"]})
        elif b["type"] == "thinking":
            out.append({"type": "thinking", "thinking": b["thinking"], "signature": b["signature"]})
        elif b["type"] == "redacted_thinking":
            out.append({"type": "redacted_thinking", "data": b["data"]})
        else:
            raise LoopError(f"unexpected content block type {b['type']!r}")
    if not out:
        raise LoopError("empty assistant content cannot be replayed")
    return out


class Client:
    def __init__(self, key: str):
        import anthropic  # generator dependency only (generator/requirements.lock)
        self.sdk_version = anthropic.__version__
        self._c = anthropic.Anthropic(api_key=key, max_retries=4, timeout=600.0)
        self.anthropic_version = self._c.default_headers.get("anthropic-version")

    def create(self, body: dict) -> dict:
        # Streamed transport (the SDK requires it for large max_tokens, protocol v3
        # vat: 64 000); the request body is unchanged and the final Message is the
        # same object messages.create would return.
        with self._c.messages.stream(**body) as stream:
            return stream.get_final_message().model_dump(mode="json", exclude_none=True)


def assert_no_key(paths: list[Path], key: str | None) -> None:
    if not key:
        return
    for root in paths:
        for f in root.rglob("*") if root.is_dir() else [root]:
            if f.is_file() and key.encode() in f.read_bytes():
                raise LoopError(f"API key found in {f}")


# ---------------------------------------------------------------- after the rounds

def ladder_bundles() -> list[Path]:
    pattern = core.PROTOCOL["subjects"][SUBJECT.name]["generator"].get("ladder_bundles", DEFAULT_LADDER_BUNDLES)
    return sorted(ROOT.glob(pattern))


def ladder_pool() -> list[list[dict]]:
    ws = []
    for m in ladder_bundles():
        ws.append(json.loads(m.read_text())["evidence"]["W"])
    return ws


def kill_on_pool(scorer: events.Scorer, spec: Path, pool: list[dict]) -> tuple[list[str], list[str]]:
    """K_t on W*; a spec that does not compile over some mutant scores no pair of it."""
    kill, problems = set(), []
    for mid in sorted({p["mutant"] for p in pool}):
        sub = [p for p in pool if p["mutant"] == mid]
        try:
            k, _ = scorer.kill_set(spec, sub)
        except core.CompileError as e:
            problems.append(f"{mid[:12]}: {str(e)[:200]}")
            continue
        kill |= set(k)
    return sorted(kill), problems


def py(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, "-I", "-B", *args], capture_output=True, text=True)


def finish(tdir: Path, condition: str, seed: int, selected: list[dict], all_cands: list[dict],
           mutants: list[dict], meta: dict) -> dict:
    """κ, vacuity (a), bundle + verify, events on W*, trajectory.md."""
    labels = {m["id"]: m["name"] for m in mutants}
    final = selected[-1]
    fdir = Path(final["dir"])
    out: dict = {"final": {"round": final["t"], "cand": final["j"], "acc": final["score"]["acc"]}}

    # κ and vacuity (a): once, for the final selected spec only; never fed back.
    if final["score"]["acc"] != "lint_rejected" and final["score"].get("check_reason") != "compile_error":
        spec = fdir / "Spec.sol"
        t0 = time.monotonic()
        k = kappa_mod.kappa(spec, B, FROZEN["timeout_ms"], FROZEN["wall_timeout_s"], subject=SUBJECT)
        out["kappa"] = {"kappa": k["kappa"], "asserts": k["asserts"], "determined": k["determined"],
                        "unproved_over_H": k["non_tautological_unproved"], "wall_s": round(time.monotonic() - t0, 3)}
        (tdir / "kappa.json").write_text(json.dumps(k, indent=1, sort_keys=True) + "\n")
        t0 = time.monotonic()
        v = vacuity_mod.vacuity(spec, B, FROZEN["timeout_ms"], FROZEN["wall_timeout_s"], subject=SUBJECT)
        out["vacuity_a"] = {"flagged": v["flagged"], "unknown": v["unknown"], "wall_s": round(time.monotonic() - t0, 3)}
        (tdir / "vacuity_a.json").write_text(json.dumps(v, indent=1, sort_keys=True) + "\n")

        # Bundle of the final spec with its own W_R, and its verification.
        fb = {"condition": condition, "round": final["t"], "seed": seed, "model": meta["model_returned"] or FROZEN["model"],
              "temperature": meta["temperature_recorded"], "prompts_sha256": prompts_sha256()}
        (tdir / "feedback_provenance.json").write_text(json.dumps(fb, indent=1, sort_keys=True) + "\n")
        bdir = tdir / "bundle"
        pb = py(str(ROOT / "tools" / "bundle.py"), "--out", str(bdir), "--subject", SUBJECT.name,
                "--artifact", str(B), "--spec", str(spec),
                "--mutants", str(MUTANTS), "--witnesses", str(fdir / "witnesses.json"),
                "--adversary-id", final["score"]["adversary_id"], "--adversary-source",
                str(ROOT / "tools" / "adversary.py"), "--adversary-seed", str(FROZEN["seed_A"]),
                "--adversary-budget", str(FROZEN["B_A"]), "--check-json", str(fdir / runstore.CHECK_GZ),
                "--feedback", str(tdir / "feedback_provenance.json"))
        out["bundle"] = {"exit": pb.returncode, "stderr_tail": pb.stderr.strip().splitlines()[-3:]}
        if pb.returncode == 0:
            vj = tdir / "verify.json"
            pv = py(str(ROOT / "tools" / "verify.py"), str(bdir), "--json", str(vj))
            rep = json.loads(vj.read_text()) if vj.is_file() else {}
            out["verify"] = {"exit": pv.returncode, "verdict": rep.get("verdict"), "ms_cert": rep.get("ms_cert"),
                             "summary": pv.stdout.strip().splitlines()[-3:]}
            out["status"] = {0: "bundle_holds", 2: "bundle_not_certified"}.get(pv.returncode, "bundle_refused")
            if pv.returncode != 0:
                out["reason"] = f"verify exit {pv.returncode}: {rep.get('verdict')}"
        else:
            out["status"], out["reason"] = "bundle_refused", "bundle.py failed: " + " ".join(out["bundle"]["stderr_tail"])
    else:
        out["status"], out["reason"] = "bundle_refused", f"final spec is {final['score']['acc']} " \
                                                         f"({final['score'].get('check_reason')}); nothing to bundle"

    # Events on W* = all W_t of this trajectory's candidates + the ladder's W*.
    traj_ws = [json.loads((Path(c["dir"]) / "witnesses.json").read_text())
               for c in all_cands if (Path(c["dir"]) / "witnesses.json").is_file()]
    pool = events.pool_from(traj_ws + ladder_pool())
    (tdir / "W_star.json").write_text(json.dumps(pool, indent=1, sort_keys=True) + "\n")
    scorer = events.Scorer(mutants, SUBJECT)
    rounds, notes = [], {}
    for s in selected:
        sc = s["score"]
        if sc["acc"] == "lint_rejected" or sc.get("check_reason") == "compile_error":
            k, probs = [], []
        else:
            k, probs = kill_on_pool(scorer, Path(s["dir"]) / "Spec.sol", pool)
        notes[s["t"]] = probs
        rounds.append({"t": s["t"], "phi_source_sha256": sc.get("spec_source_sha256", core.sha256_hex(b"")),
                       "acc": sc["acc"], "kill_set": k})
    doc = events.trajectory(condition, seed, [m["id"] for m in mutants], pool, rounds)
    (tdir / "events.json").write_text(json.dumps(doc, indent=1, sort_keys=True, ensure_ascii=False) + "\n")
    out["events"] = [{"t": e["t"], "kind": e["kind"], "acc_t": e["acc_t"]} for e in doc["events"]]
    out["W_star"] = doc["pool"]

    # trajectory.md
    L = [f"# Trajectory {condition} seed {seed}", "",
         f"Model requested `{FROZEN['model']}`, returned `{meta['model_returned']}`; R = {len(selected)}, "
         f"k = {meta['k']}; |W*| = {doc['pool']['size']} (this trajectory's W_t plus the ladder's W*).", "",
         "| round | selected | acc | own ms_cert (shown under fM/fMplus) | K_t on W* | event t -> t+1 |",
         "|---|---|---|---|---|---|"]
    ev = {e["t"]: e["kind"] for e in doc["events"]}
    for s, r in zip(selected, doc["rounds"]):
        own = s["score"]["ms_cert"]
        L.append(f"| {s['t']} | cand {s['j']} | {r['acc']} | {own['killed']}/{own['total']} | "
                 f"{r['ms_cert']['killed']}/{r['ms_cert']['total']} {[labels[i] for i in r['kill_set']]} | "
                 f"{ev.get(s['t'], '-')} |")
    for s in selected:
        if notes.get(s["t"]):
            L.append(f"\nRound {s['t']}: pairs not scored (spec does not compile over the mutant): {notes[s['t']]}")
    L += ["", f"Final: {out['status']}" + (f" ({out.get('reason')})" if out.get("reason") else "")]
    if "kappa" in out:
        L.append(f"κ = {out['kappa']['kappa']} / {out['kappa']['asserts']} asserts; "
                 f"vacuity (a) flagged {out['vacuity_a']['flagged']}, unknown {out['vacuity_a']['unknown']}")
    for a, b_ in zip(selected, selected[1:]):
        pa, pb_ = Path(a["dir"]) / "Spec.sol", Path(b_["dir"]) / "Spec.sol"
        ta = pa.read_text().splitlines() if pa.is_file() else []
        tb = pb_.read_text().splitlines() if pb_.is_file() else []
        diff = list(difflib.unified_diff(ta, tb, f"round_{a['t']}/Spec.sol", f"round_{b_['t']}/Spec.sol", lineterm=""))
        L += ["", f"## Round {a['t']} -> {b_['t']}: {ev.get(a['t'], '-')}", "", "```diff", *(diff or ["(identical)"]), "```"]
    (tdir / "trajectory.md").write_text("\n".join(L) + "\n")
    return out


# ---------------------------------------------------------------- the loop

def run(condition: str, seed: int, rounds: int, k: int, out_root: Path, dry_run: bool,
        client=None, max_calls: int | None = None) -> int:
    tdir = out_root / condition / f"seed_{seed}"
    system = system_prompt()
    first = round1_prompt(rounds)
    messages: list[dict] = [{"role": "user", "content": first}]
    if dry_run:
        body = request_body(system, messages)
        chars = len(system) + len(first)
        print(f"[dry-run] {condition} seed {seed}: round-1 request, system {len(system)} chars, "
              f"user {len(first)} chars, total {chars} chars (~{chars // 4} tokens at 4 chars/token)")
        print(f"[dry-run] prompts sha256 {prompts_sha256()}")
        for name, h in prompt_hashes().items():
            print(f"[dry-run]   {name}: {h}")
        example = example_score()
        labels = ({m["id"]: m["fault_class"] for m in json.loads(MUTANTS.read_text())["mutants"]}
                  if MUTANTS.is_file() else {i: "example" for i in example["kill_set"] + example["survivors"]})
        print(f"[dry-run] subject {SUBJECT.name}; mutants.json {'present' if MUTANTS.is_file() else 'MISSING'}; "
              f"ladder bundles {len(ladder_bundles())}")
        fb = feedback_prompt(condition, 1, rounds, example, labels)
        print(f"[dry-run] feedback after round 1 on an EXAMPLE score (not a result): {len(fb)} chars")
        print(fb)
        print(json.dumps({**body, "system": f"<{len(system)} chars>"}, indent=1)[:4000])
        return 0

    missing = []
    if not MUTANTS.is_file():
        missing.append(f"{MUTANTS} (the mutation class M)")
    if not any(ladder_pool()):
        missing.append(f"ladder W* ({core.PROTOCOL['subjects'][SUBJECT.name]['generator'].get('ladder_bundles', DEFAULT_LADDER_BUNDLES)})")
    if missing:
        print(f"loop: subject {SUBJECT.name} is not ready for a live run; missing: {'; '.join(missing)}", file=sys.stderr)
        return 1
    key = api_key()
    if client is None:
        if not key:
            print(f"loop: no API key ({KEY_ENV} unset and no {KEY_FILE})", file=sys.stderr)
            return 1
        client = Client(key)
    if tdir.exists() and any(tdir.iterdir()):
        print(f"loop: {tdir} exists and is not empty; refusing to overwrite a trajectory", file=sys.stderr)
        return 1
    tdir.mkdir(parents=True)
    mutants = events.load_mutants(MUTANTS)
    labels = {m["id"]: m["fault_class"] for m in json.loads(MUTANTS.read_text())["mutants"]}
    meta = {"condition": condition, "seed": seed, "rounds": rounds, "k": k, "frozen": FROZEN,
            "model_requested": FROZEN["model"], "model_returned": None,
            # Not sent (claude-sonnet-5-5 rejects non-default sampling values); the API default 1.0 is
            # recorded because the bundle schema needs a number (protocol.md 16.1).
            "temperature_recorded": 1.0,
            "temperature_note": "API default; non-default values rejected by this model; not sent",
            "seed_param": "not supported by the Messages API (SDK has no seed parameter); "
                          "the trajectory seed is recorded only",
            "sdk_version": getattr(client, "sdk_version", None),
            "anthropic_version_header": getattr(client, "anthropic_version", None),
            "fallbacks": "none (a refusal is a failed candidate)", "prompt_sha256": prompt_hashes(),
            "prompts_sha256": prompts_sha256(), "calls": [], "tokens": {"input": 0, "output": 0, "thinking": 0}}
    selected, all_cands = [], []
    calls = 0
    try:
        for t in range(1, rounds + 1):
            rdir = tdir / f"round_{t}"
            body = request_body(system, messages)
            cands = []
            for j in range(1, k + 1):
                if max_calls is not None and calls >= max_calls:
                    raise LoopError(f"--max-calls {max_calls} reached")
                cdir = rdir / f"cand_{j}"
                cdir.mkdir(parents=True)
                (cdir / "request.json").write_text(json.dumps(body, indent=1, sort_keys=True) + "\n")
                t0 = time.monotonic()
                resp = client.create(body)
                calls += 1
                (cdir / "response.json").write_text(json.dumps(resp, indent=1, sort_keys=True) + "\n")
                u = resp.get("usage", {})
                meta["tokens"]["input"] += u.get("input_tokens", 0)
                meta["tokens"]["output"] += u.get("output_tokens", 0)
                thinking = u.get("output_tokens_details", {}).get("thinking_tokens", 0)
                meta["tokens"]["thinking"] += thinking
                meta["model_returned"] = resp.get("model")
                meta["calls"].append({"round": t, "cand": j, "model": resp.get("model"), "id": resp.get("id"),
                                      "stop_reason": resp.get("stop_reason"), "stop_details": resp.get("stop_details"),
                                      "input_tokens": u.get("input_tokens", 0), "output_tokens": u.get("output_tokens", 0),
                                      "thinking_tokens": thinking, "usage": u,
                                      "wall_s": round(time.monotonic() - t0, 3)})
                score = process_candidate(reply_text(resp), cdir, mutants, resp.get("stop_reason"))
                c = {"t": t, "j": j, "dir": str(cdir), "score": score, "response": resp}
                cands.append(c)
                all_cands.append(c)
                print(f"round {t} cand {j}: {score['acc']} ({score.get('check_reason')}), "
                      f"own ms_cert {score['ms_cert']['killed']}/{score['ms_cert']['total']}", flush=True)
            i = select(condition, [c["score"] for c in cands])
            sel = cands[i]
            selected.append(sel)
            (rdir / "selected.json").write_text(json.dumps(
                {"condition": condition, "selected": sel["j"], "rule": "protocol.md 16.3",
                 "candidates": [{"cand": c["j"], "acc": c["score"]["acc"], "errors": error_count(c["score"]),
                                 "ms_cert": c["score"]["ms_cert"]} for c in cands]}, indent=1) + "\n")
            if t < rounds:
                fb = feedback_prompt(condition, t, rounds, sel["score"], labels)
                (rdir / "feedback.md").write_text(fb)
                messages = messages + [{"role": "assistant", "content": content_params(sel["response"])},
                                       {"role": "user", "content": fb}]
        meta["result"] = finish(tdir, condition, seed, selected, all_cands, mutants, meta)
        code = 0
    except LoopError as e:
        meta["error"] = str(e)
        print(f"loop: {e}", file=sys.stderr)
        code = 1
    except Exception as e:  # API errors and anything unexpected: keep the partial trajectory
        meta["error"] = f"{type(e).__name__}: {e}"
        print(f"loop: {meta['error']}", file=sys.stderr)
        code = 2
    meta["tokens"]["total"] = meta["tokens"]["input"] + meta["tokens"]["output"]  # thinking is part of output
    (tdir / "trajectory.json").write_text(json.dumps(meta, indent=1, sort_keys=True) + "\n")
    assert_no_key([tdir], key)
    return code


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--condition", choices=CONDITIONS, required=True)
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--rounds", type=int, help="default: the subject's frozen R")
    ap.add_argument("--k", type=int, help="default: the subject's frozen k")
    ap.add_argument("--out", type=Path, default=ROOT / "runs" / f"v{core.PROTOCOL['protocol_version']}")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-calls", type=int)
    ap.add_argument("--subject", default=core.DEFAULT_SUBJECT)
    try:
        a = ap.parse_args(argv)
    except SystemExit as e:
        return 1 if e.code else 0
    global SUBJECT, B, INTENT, MUTANTS, FROZEN
    SUBJECT = core.load_subject(a.subject)
    if "generator" not in core.PROTOCOL["subjects"][SUBJECT.name]:
        print(f"loop: protocol.json has no generator configuration for subject {SUBJECT.name}", file=sys.stderr)
        return 1
    B, INTENT, MUTANTS = SUBJECT.source_path, SUBJECT.intent_path, SUBJECT.mutants_dir / "mutants.json"
    FROZEN = frozen_for(SUBJECT.name)
    a.rounds = a.rounds or FROZEN["rounds"]
    a.k = a.k or FROZEN["k"]
    if a.rounds < 1 or a.k < 1:
        print("loop: rounds and k must be >= 1", file=sys.stderr)
        return 1
    return run(a.condition, a.seed, a.rounds, a.k, a.out, a.dry_run, max_calls=a.max_calls)


if __name__ == "__main__":
    sys.exit(main())
