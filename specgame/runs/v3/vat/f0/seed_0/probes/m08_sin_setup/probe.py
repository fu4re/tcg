"""Hand σ for m08_grab_no_vice against the f0 seed 0 final spec (round 3 cand 1).

    python runs/v3/vat/f0/seed_0/probes/m08_sin_setup/probe.py   (from specgame/)

σ: deployer alice (the ward), the profile's setup, then alice calls
suck(bob, bob, 1 ray) so that sin[bob] = 1 ray, then the probe
check_grab_sin_up(GOLD, bob, dx = 0, dy = 1) from alice. evaluate_witness
(every check of the spec on its own replay of σ, core v2 executor) over b and
over m08. Writes result.json next to this file. pyrevm only; no solc run
beyond compiling the spec over each artifact.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[6]  # specgame/
sys.path.insert(0, str(ROOT / "tools"))
import specgame_core as core  # noqa: E402

vat = core.load_subject("vat")
spec = HERE.parents[1] / "round_3" / "cand_1" / "Spec.sol"
m08 = vat.mutants_dir / "m08_grab_no_vice.sol"
RAY = str(10 ** 27)
sigma = {"version": 1, "deployer": "alice", "ctor": {}, "setup": core.setup_for(vat, "alice"),
         "txs": [{"sender": "alice", "fn": "suck(address,address,uint256)", "args": ["bob", "bob", RAY]}],
         "probe": {"sender": "alice", "a": "alice", "b": "bob", "x": "0", "y": "0",
                   "i": "GOLD", "u": "bob", "dx": "0", "dy": "1", "check": "check_grab_sin_up"}}
core.validate_sigma(sigma, need_probe=True, subject=vat)
out = {"sigma": sigma, "sigma_sha256": core.json_sha256(sigma), "spec": str(spec.relative_to(ROOT)),
       "spec_source_sha256": core.sha256_file(spec), "core_version": core.CORE_VERSION, "results": {}}
for name, art in (("b", vat.source_path), ("m08_grab_no_vice", m08)):
    pair = core.compile_spec_over(spec, art, subject=vat)
    w = core.evaluate_witness(pair, sigma)
    pre = core.run_sequence(pair, {k: v for k, v in sigma.items() if k != "probe"})
    out["results"][name] = {
        "artifact": str(art.relative_to(ROOT)), "pair_runtime_sha256": pair["runtime_sha256"],
        "deploy_ok": w.deploy_ok, "violated": w.violated,
        "violated_checks": sorted(c for c, o in w.outcomes.items() if o == "violation"),
        "check_grab_sin_up": w.outcomes.get("check_grab_sin_up"),
        "suck_outcome": pre.data["txs"][0]["outcome"],
        "outcome_counts": {o: sum(v == o for v in w.outcomes.values()) for o in sorted(set(w.outcomes.values()))},
    }
(HERE / "result.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
for k, r in out["results"].items():
    print(k, "suck:", r["suck_outcome"], "| check_grab_sin_up:", r["check_grab_sin_up"],
          "| violated:", r["violated_checks"], "| counts:", r["outcome_counts"])
