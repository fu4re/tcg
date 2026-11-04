"""Historical engine probe (BMC: deprecated upstream, not used in any protocol version;
kept only to reproduce the recorded numbers): a Vat check's isolated harness under
SMTChecker engine bmc / all at the frozen per-query timeout."""
import json, sys, time
sys.path.insert(0, "tools")
import specgame_core as core
V = core.load_subject("vat")
spec = (V.specs_dir / "measurement" / "vat_measure.sol").read_text()
texts = dict(core.check_functions(spec, V))
out_rows = []
for check in ("check_frob_conserves_collateral", "check_two_dai_balances_within_debt", "check_suck_needs_auth"):
    for engine in ("bmc", "all"):
        mc = core.model_checker_settings(core.CHECK_TIMEOUT_MS)
        mc["engine"] = engine
        harness = core.isolated_harness(texts[check], V)
        inp = core.solc_input({core.SPEC_UNIT: harness, V.unit: V.source_path.read_text()}, mc)
        t0 = time.monotonic()
        out, raw, dt = core.run_solc(inp, core.Toolchain.default(), core.CHECK_WALL_TIMEOUT_S)
        msgs = []
        if out is None:
            msgs = ["WALL TIMEOUT"]
        else:
            for e in out.get("errors", []):
                m = e["message"]
                if core.SMT_MARKERS.search(m):
                    loc = e.get("sourceLocation") or {}
                    line = harness.count("\n", 0, loc["start"]) + 1 if loc.get("file") == "Spec.sol" else None
                    msgs.append(f"{e['severity']} {loc.get('file')}:{line} {m.splitlines()[0]}")
        row = {"check": check, "engine": engine, "timeout_ms": core.CHECK_TIMEOUT_MS, "duration_s": round(dt, 1),
               "messages": msgs, "solc_input_sha256": core.json_sha256(inp)}
        out_rows.append(row)
        print(json.dumps(row), flush=True)
json.dump(out_rows, open(sys.argv[1], "w"), indent=1)
