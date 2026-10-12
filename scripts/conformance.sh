#!/usr/bin/env bash
#
# conformance.sh -- the five bundle-spec.md Section 9 conformance controls,
# each run against `tcg verify` on an INDEPENDENT COPY of the frozen reference
# bundle (the pristine bundle is never mutated), each asserting an EXACT
# expected exit code AND the step at which verify must react:
#
#   1  flip one byte in subject/runtime.bin        -> exit 3, step 1-integrity
#   2  closure: a graph node whose claim file is
#      gone (child claim + evidence deleted, and
#      dropped from MANIFEST so step 1 still passes
#      -- the graph is left asserting it)           -> exit 3, step 4-graph
#   3  inject a false trusted lemma (re-key the
#      child body to a structurally false claim,
#      consistently so step 1/4 pass)               -> exit 3, step 5-replay
#   4  cut replay.timeout_seconds to 1 (rehashed
#      in MANIFEST)                                  -> exit 2, step 5-replay UNKNOWN
#   5  delete bundle/nav/ entirely                   -> exit 0, still passes
#   6  program binding (P0-A): change subject bytes
#      so the root's <program> no longer matches,
#      rehashed in MANIFEST so step 1 still passes   -> exit 3, step 4-graph
#
# Control 6 is the bundle-only re-check that closes gate G3's Hole 1: a bundle
# whose hash tree is fully self-consistent is STILL refused if its root proves a
# property of a different program than the installed subject. See docs/
# bundle-spec.md Section 9 and docs/findings/0002.
#
# Overall exit is non-zero if ANY control's actual (exit, step) disagrees with
# what it must be -- a verifier that fails to refuse when it must is the whole
# failure this guards against.
#
# Usage:  scripts/conformance.sh [BUNDLE]
#   BUNDLE   path to a frozen bundle dir (default: build a fresh one with
#            scripts/build-reference.sh into a temp dir).
# Env overrides: TCG_PYTHON (default pinned pyenv 3.12.2).
set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO="$(cd "$SCRIPT_DIR/.." && pwd)"
TCG_PYTHON="${TCG_PYTHON:-python3}"

BUNDLE="${1:-}"
if [ -z "$BUNDLE" ]; then
  echo "no BUNDLE given; building a fresh reference bundle ..."
  BUILDROOT="$(mktemp -d -t tcg-conf-build)"
  BUILDLOG="$(mktemp -t tcg-conf-build-log)"
  "$REPO/scripts/build-reference.sh" "$BUILDROOT" >"$BUILDLOG" 2>&1 \
    || { echo "build-reference.sh failed; see $BUILDLOG" >&2; exit 1; }
  # build-reference.sh's single source of truth: the bundle is at <WORKDIR>/bundle
  BUNDLE="$BUILDROOT/bundle"
fi
[ -f "$BUNDLE/MANIFEST.json" ] || { echo "no MANIFEST.json under $BUNDLE" >&2; exit 1; }
BUNDLE="$(cd "$BUNDLE" && pwd)"

WORK="$(mktemp -d -t tcg-conf)"
echo "reference bundle (pristine, never mutated): $BUNDLE"
echo "scratch copies + verify logs:               $WORK"
echo

FAILURES=0
declare -a ROWS

# verify a copy; prints its exit code, writes stdout+stderr to <copy>.log
verify_exit() {
  PYTHONPATH="$REPO" "$TCG_PYTHON" -m tcg verify "$1" >"$1.log" 2>&1
  echo $?
}

# record(name, expected_exit, actual_exit, expected_step, logfile)
record() {
  local name="$1" exp="$2" act="$3" step="$4" log="$5" ok="PASS"
  if [ "$act" != "$exp" ]; then ok="FAIL(exit $act != $exp)"; FAILURES=$((FAILURES+1))
  elif [ -n "$step" ] && ! grep -q "$step" "$log"; then
    ok="FAIL(step '$step' not in log)"; FAILURES=$((FAILURES+1))
  fi
  ROWS+=("$(printf '%-28s expect=%s actual=%s  %s' "$name" "$exp" "$act" "$ok")")
  printf '  %-28s expect=%s actual=%s  %s\n' "$name" "$exp" "$act" "$ok"
}

# ---- control 1: flipped byte in runtime.bin -> step 1 integrity --------------
C1="$WORK/c1-flip-byte"; cp -R "$BUNDLE" "$C1"
"$TCG_PYTHON" - "$C1" <<'PY'
import sys, pathlib
p = pathlib.Path(sys.argv[1]) / "subject" / "runtime.bin"
b = bytearray(p.read_bytes()); b[0] ^= 0x01; p.write_bytes(b)
PY
echo "control 1: flip one byte in subject/runtime.bin"
A1="$(verify_exit "$C1")"
record "1 flipped-runtime-byte" 3 "$A1" "REFUSED at step 1-integrity" "$C1.log"

# ---- control 2: closure -- graph node whose claim file is missing ------------
C2="$WORK/c2-closure"; cp -R "$BUNDLE" "$C2"
"$TCG_PYTHON" - "$C2" <<'PY'
import sys, json, pathlib
C = pathlib.Path(sys.argv[1])
graph = json.loads((C / "spec" / "graph.json").read_text())
# the deleted child is the trusted-lemma target (role frame in this bundle)
base = next(h for h, n in graph["nodes"].items() if n.get("role") == "frame")
(C / "spec" / "claims" / f"{base}.k").unlink()
(C / "evidence" / "replay" / f"{base}.json").unlink()
man = json.loads((C / "MANIFEST.json").read_text())
# drop the deleted files from the hash tree so step 1 still passes -- the graph
# is left asserting `base` is a proved node, which step 4 (closure) must catch.
for k in (f"spec/claims/{base}.k", f"evidence/replay/{base}.json"):
    man["files"].pop(k, None)
(C / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
PY
echo "control 2: delete a proved child claim (closure violation)"
A2="$(verify_exit "$C2")"
record "2 deleted-child-claim" 3 "$A2" "REFUSED at step 4-graph" "$C2.log"

# ---- control 3: inject a false trusted lemma -> step 5 replay ----------------
C3="$WORK/c3-false-lemma"; cp -R "$BUNDLE" "$C3"
"$TCG_PYTHON" - "$C3" <<'PY'
import sys, json, hashlib, pathlib
C = pathlib.Path(sys.argv[1])
sha = lambda s: hashlib.sha256(s.encode()).hexdigest()
gpath = C / "spec" / "graph.json"
graph = json.loads(gpath.read_text())
base = next(h for h, n in graph["nodes"].items() if n.get("role") == "frame")
kpath = C / "spec" / "claims" / f"{base}.k"
text = kpath.read_text()
# STOP halts at pc 0; claiming pc reaches 999 is a STRUCTURAL falsehood (the
# reached state does not unify with the destination) -> Refute at replay.
false_text = text.replace("<pc> 0 </pc>", "<pc> 0 => 999 </pc>")
assert false_text != text, "pc line not found to tamper"
new = sha(false_text)
kpath.unlink(); (C / "spec" / "claims" / f"{new}.k").write_text(false_text)
epath = C / "evidence" / "replay" / f"{base}.json"
ev = json.loads(epath.read_text()); ev["claim"] = new
epath.unlink()
(C / "evidence" / "replay" / f"{new}.json").write_text(
    json.dumps(ev, indent=2, sort_keys=True) + "\n")
graph["nodes"][new] = graph["nodes"].pop(base)
for e in graph["edges"]:
    if e["to"] == base: e["to"] = new
gpath.write_text(json.dumps(graph, indent=2, sort_keys=True) + "\n")
# re-key + re-hash the tampered files in the MANIFEST so step 1/3/4 all pass
# and the injected false lemma only surfaces at replay (step 5).
man = json.loads((C / "MANIFEST.json").read_text())
f = man["files"]
f.pop(f"spec/claims/{base}.k", None); f.pop(f"evidence/replay/{base}.json", None)
f[f"spec/claims/{new}.k"] = new
f[f"evidence/replay/{new}.json"] = hashlib.sha256(
    (C / "evidence" / "replay" / f"{new}.json").read_bytes()).hexdigest()
f["spec/graph.json"] = hashlib.sha256(gpath.read_bytes()).hexdigest()
(C / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
PY
echo "control 3: inject a false trusted lemma (re-keyed to pass steps 1-4)"
A3="$(verify_exit "$C3")"
record "3 false-trusted-lemma" 3 "$A3" "REFUSED at step 5-replay" "$C3.log"

# ---- control 4: replay.timeout_seconds = 1 -> conservative UNKNOWN -----------
C4="$WORK/c4-timeout"; cp -R "$BUNDLE" "$C4"
"$TCG_PYTHON" - "$C4" <<'PY'
import sys, json, hashlib, pathlib
C = pathlib.Path(sys.argv[1])
lpath = C / "theory" / "toolchain.lock"
lock = json.loads(lpath.read_text())
lock.setdefault("replay", {})["timeout_seconds"] = 1
lpath.write_text(json.dumps(lock, indent=2, sort_keys=True) + "\n")
man = json.loads((C / "MANIFEST.json").read_text())
man["files"]["theory/toolchain.lock"] = hashlib.sha256(lpath.read_bytes()).hexdigest()
(C / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
PY
echo "control 4: cut replay.timeout_seconds to 1 (real proof needs ~16s)"
A4="$(verify_exit "$C4")"
record "4 timeout-1s" 2 "$A4" "UNVERIFIED at step 5-replay" "$C4.log"

# ---- control 5: delete nav/ entirely -> still passes -------------------------
C5="$WORK/c5-no-nav"; cp -R "$BUNDLE" "$C5"
rm -rf "$C5/nav"
echo "control 5: delete bundle/nav/ entirely (must NOT change the verdict)"
A5="$(verify_exit "$C5")"
record "5 deleted-nav" 0 "$A5" "certificate holds" "$C5.log"

# ---- control 6: program binding -- subject != root <program> -> step 4 -------
C6="$WORK/c6-program-binding"; cp -R "$BUNDLE" "$C6"
"$TCG_PYTHON" - "$C6" <<'PY'
import sys, json, hashlib, pathlib
C = pathlib.Path(sys.argv[1])
# Change the installed subject bytes (a self-consistent tamper: rehash it in
# the MANIFEST so step 1 integrity still passes). The root's <program> cell is
# left untouched, so it no longer binds to subject/runtime.bin -- step 4 must
# refuse even though every hash in the bundle matches.
p = C / "subject" / "runtime.bin"
b = bytearray(p.read_bytes()); b[0] ^= 0x01; p.write_bytes(b)
man = json.loads((C / "MANIFEST.json").read_text())
man["files"]["subject/runtime.bin"] = hashlib.sha256(p.read_bytes()).hexdigest()
(C / "MANIFEST.json").write_text(json.dumps(man, indent=2, sort_keys=True) + "\n")
PY
echo "control 6: change subject bytes so root <program> no longer binds (rehashed)"
A6="$(verify_exit "$C6")"
record "6 program-binding" 3 "$A6" "does not match subject/runtime.bin" "$C6.log"

echo
echo "== conformance summary =="
for r in "${ROWS[@]}"; do echo "  $r"; done
echo
if [ "$FAILURES" -eq 0 ]; then
  echo "conformance: OK (6/6 controls behaved exactly as required)"
  exit 0
fi
echo "conformance: FAILED ($FAILURES control(s) did not refuse/pass as required)" >&2
exit 1
