#!/usr/bin/env bash
# Back-translation step 1 (task 04 section 2): one headless model call as the
# isolated unix user `agent`, which cannot read /home/vladimir (so not
# hard/spec/requirements.md). Run from the bundle root. The model gets no
# tools (--tools ""), no MCP servers, no session persistence; its whole input
# is the stdin file recorded below (fixed prompt + the bt-input files).
# Records, under provenance/sessions/: <id>.stdin.txt, <id>.result.json,
# <id>.stderr, <id>.listing-before.txt, <id>.listing-after.txt, <id>.env.txt.
set -euo pipefail
MODEL="${BT_MODEL:-claude-opus-5-5}"
ID="bt-$(date -u +%Y%m%dT%H%M%SZ)"
S=provenance/sessions
IN=$S/bt-input
D=/home/agent/$ID
sudo -n -u agent -H mkdir "$D"
for f in "$IN"/*; do sudo -n -u agent -H sh -c "cat > '$D/$(basename "$f")'" < "$f"; done
{
  echo "# $ID listing of the model's working directory BEFORE the call (as user agent)"
  sudo -n -u agent -H sh -c "cd '$D' && ls -la && sha256sum *"
  echo "# isolation checks (as user agent)"
  sudo -n -u agent -H sh -c "id; ls /home/vladimir 2>&1; cat /home/vladimir/sheaf/tcg/pilot/bundle/hard/spec/requirements.md 2>&1 | head -1; find /home/agent /home -maxdepth 3 -iname 'CLAUDE*.md' 2>/dev/null | sed 's/^/CLAUDE.md found: /'; echo end-checks"
} > "$S/$ID.listing-before.txt"
{
  cat "$S/backtranslation_prompt.md"
  echo; echo "=== INPUT ==="
  for f in "$IN"/*; do echo; echo "--- FILE: $(basename "$f") ---"; cat "$f"; done
} > "$S/$ID.stdin.txt"
{
  echo "claude_version: $(sudo -n -u agent -H sh -c 'claude --version')"
  echo "model_requested: $MODEL"
  echo "argv: claude -p --model $MODEL --tools \"\" --strict-mcp-config --no-session-persistence --output-format json  (cwd $D, user agent, stdin = $ID.stdin.txt)"
  echo "started: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
} > "$S/$ID.env.txt"
rc=0
sudo -n -u agent -H bash -c "cd '$D' && claude -p --model '$MODEL' --tools '' --strict-mcp-config --no-session-persistence --output-format json" \
  < "$S/$ID.stdin.txt" > "$S/$ID.result.json" 2> "$S/$ID.stderr" || rc=$?
echo "ended: $(date -u +%Y-%m-%dT%H:%M:%SZ) exit: $rc" >> "$S/$ID.env.txt"
{
  echo "# $ID listing AFTER the call (as user agent)"
  sudo -n -u agent -H sh -c "cd '$D' && ls -la && sha256sum *"
} > "$S/$ID.listing-after.txt"
echo "$ID"
exit $rc
