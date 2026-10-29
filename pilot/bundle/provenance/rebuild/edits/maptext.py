import json
d = json.load(open("provenance/tools/MAP.json"))
parts = []
for rec, st in d["summary"].items():
    b = next(e for e in d["events"] if e["recorded_path"] == rec)
    parts.append(f"{rec} -> {b['bundled']} sha256 {b['bundled_sha256']} (" + "; ".join(f"{k}: seq {v}" for k, v in st.items()) + ")")
print("CORRECTS seq 96 (same inputs, text lost to a quoting error in the producer's shell). "
      "Tool map (orchestrator decision, L4): producer scripts executed by deterministic events are bundled under provenance/tools/ "
      "(full per-event table: provenance/tools/MAP.json). Past events are NOT rewritten; replay an event by substituting the bundled copy "
      "whose sha256 equals the hash the event recorded (status same_bytes). " + " | ".join(parts) +
      " | version_not_retained events were superseded by byte-identical re-runs with the current version (seq 82-94, "
      "provenance/rebuild/edits/rerun_current.sh: all 35 outputs identical). run-claim.sh events recorded the image Id, not the script "
      "hash: the bundled copy is the current script, identity with the version that ran is not proven. Imports bundled: tcg/keccak.py, "
      "tcg/claims.py, tcg/verdict.py. Not bundled: pilot/verifier/tcgverify (the tcg-verifier checker), KEVM pins/tarball/K source (outside_bundle).")
