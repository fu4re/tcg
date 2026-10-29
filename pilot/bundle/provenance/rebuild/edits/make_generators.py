#!/usr/bin/env python3
"""Write provenance/generators.json and provenance/traces.json (task 05
sections 3 and deferred). Run from the bundle root. Lists each untrusted
generator (model) that produced material in this bundle, and what it
produced. Says nothing about correctness."""
import json, pathlib

bt = json.loads(pathlib.Path("evidence/backtranslation.json").read_text())["translator"]
gens = {
    "format": "tcg-pilot-generators/0.1", "class": "U",
    "generators": [
        {
            "role": "blind back-translation (task 04 s2)",
            "provider": "Anthropic", "interface": bt["cli"] + " headless (claude -p), run as unix user agent",
            "model": bt["model"], "session_id": bt["session_id"],
            "sampling": "CLI defaults; not set by the caller and not reported by the CLI (temperature unknown); extended thinking was used (480 thinking tokens per result.json usage)",
            "produced": ["evidence/backtranslation.json (translation fields only)"],
            "ledger": "note event with model + prompt/completion hashes (provenance/ledger.jsonl, tool claude-code-cli)",
            "attestation": "none available",
        },
        {
            "role": "producing agent, WS-H session 2 (hard layer + T-hat after the VM reboot; evidence + provenance assembly)",
            "provider": "Anthropic", "interface": "Claude Code in the Claude desktop app (interactive agent session, driven by an orchestrator session)",
            "model": "claude-opus-5-5",
            "sampling": "unknown (app defaults)",
            "produced": ["claim variants cagews/joinsym (via assemble_hard.py variant, ledger seq 8-11)", "hard/annotations.json edits (seq 23)",
                         "hard/spec/requirements.md is from session 1 (DRAFT, unsigned)", "every script under pilot/tools/assemble_hard.py additions and provenance/rebuild/edits/",
                         "pilot/HARD_STATUS.md (working log, outside the bundle), provenance/decision-stub.md, provenance/sessions/backtranslation_prompt.md"],
            "ledger": "tool runs are ledger events; the agent's own reasoning is not recorded in the bundle",
            "attestation": "none available",
        },
        {
            "role": "producing agent, WS-H session 1 (pin, chain fetch, claim rebuild, requirements.md draft); ended when the VM rebooted",
            "provider": "Anthropic", "interface": "Claude Code in the Claude desktop app",
            "model": "not recorded in the bundle",
            "sampling": "unknown",
            "produced": ["provenance/chain_fetch.json, rpc_probe.json (seq 2-3)", "provenance/rebuild/src/{cage,join,joinempty}/ (rebuilt claims, decision-stub N1)",
                         "hard/spec/requirements.md (DRAFT)", "hard/annotations.json (initial)", "pilot/tools/assemble_hard.py (initial)"],
            "attestation": "none available",
        },
        {
            "role": "original August 2026 G4 pilot agents (Finding 0003 claims, of which this bundle rebuilds two)",
            "provider": "Anthropic (by project history)", "model": "not recorded", "sampling": "unknown",
            "produced": ["nothing in this bundle directly: their artefacts were not retained (provenance/iterations.json august_2026_pilot)"],
            "attestation": "none available",
        },
    ],
    "not_generators": "kprove/kore-exec/z3 (checker, in T-hat) and the deterministic scripts are tools, not generators; they are ledger run events.",
}
pathlib.Path("provenance/generators.json").write_text(json.dumps(gens, indent=2) + "\n")
pathlib.Path("provenance/traces.json").write_text(json.dumps({
    "format": "tcg-pilot-traces/0.1", "class": "U", "traces": "not recorded",
    "reason": "interpretability traces are deferred in the pilot (task 05); no model internals were captured",
}, indent=2) + "\n")
print("ok")
