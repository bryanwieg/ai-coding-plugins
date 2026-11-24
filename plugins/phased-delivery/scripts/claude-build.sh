#!/bin/sh
# claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR: build one stage
# headless with claude -p, stopped at a dollar cap.
#
# PROMPT is a file holding stage-builder.md and its inputs, kept outside
# REPO; its text is passed as the prompt. Claude works in REPO with the
# phased-delivery plugin off and thinking summarized in the stream (the
# hidden --thinking-display flag; headless runs otherwise leave it empty).
# OUTDIR receives report.md (the final message), stream.jsonl (written as
# the call runs) and stderr.txt.
#
# CLAUDE_BUILD_PERMISSIONS sets the permission mode (default acceptEdits:
# file edits work and commands follow the project's allow rules). A session
# already in a sandbox container sets it to bypassPermissions (the ai-coding
# sandbox image does).
# CLAUDE_BUILD_STALL (seconds, default 900) stops the call when stream.jsonl
# gains no line for that long: a hung call, not a slow one (the longest
# silence in 39 recorded runs was 130 s).
# Prints "Tokens: N" (input, output, cache read and cache creation, from
# modelUsage, else usage) and
# "Cost: X.XX" (USD), or unknown, for the stage commit.
#
# Exit: 0 built; 2 usage; 7 stalled (stopped after CLAUDE_BUILD_STALL
# seconds without output); 8 the budget was reached; other non-zero: the
# claude exit status. Never commits; the orchestrator does.
set -u
[ $# -eq 6 ] || { sed -n '2,25p' "$0" >&2; exit 2; }
REPO=$1; PROMPT=$2; MODEL=$3; EFFORT=$4; BUDGET=$5; OUT=$6
MODE=${CLAUDE_BUILD_PERMISSIONS:-acceptEdits}
case "$MODE" in
  acceptEdits|bypassPermissions) ;;
  *) echo "CLAUDE_BUILD_PERMISSIONS must be unset or bypassPermissions, not '$MODE'" >&2; exit 2 ;;
esac
STALL=${CLAUDE_BUILD_STALL:-900}
case "$STALL" in
  ''|*[!0-9]*|0) echo "CLAUDE_BUILD_STALL must be a whole number of seconds, not '$STALL'" >&2; exit 2 ;;
esac
mkdir -p "$OUT"
TEXT=$(cat "$PROMPT") || exit 2
(cd "$REPO" && exec claude -p "$TEXT" --model "$MODEL" --effort "$EFFORT" \
  --max-budget-usd "$BUDGET" \
  --settings '{"enabledPlugins":{"phased-delivery@ai-coding-plugins":false}}' \
  --thinking-display summarized \
  --permission-mode "$MODE" --no-session-persistence \
  --output-format stream-json --verbose) \
  < /dev/null > "$OUT/stream.jsonl" 2> "$OUT/stderr.txt" &
pid=$!
rm -f "$OUT/stalled"
# the watchdog: stops claude after STALL seconds without a new stream line
(size=-1; quiet=0
 while sleep 1; do
   now=$(wc -c < "$OUT/stream.jsonl")
   if [ "$now" = "$size" ]; then quiet=$((quiet + 1)); else size=$now; quiet=0; fi
   [ $quiet -lt "$STALL" ] || { : > "$OUT/stalled"; kill $pid; exit; }
 done) > /dev/null 2>&1 &
watch=$!
wait $pid
status=$?
kill $watch 2>/dev/null
if [ -e "$OUT/stalled" ]; then
  : > "$OUT/report.md"
  printf 'Tokens: unknown\nCost: unknown\n'
  echo "No output for $STALL s; the call was stopped as stalled" >&2
  exit 7
fi
# Exits 0 for a successful result, 8 when the budget was reached, 9 for another
# error result, 1 without one.
python3 - "$OUT/stream.jsonl" "$OUT/report.md" <<'PY'
import json, sys
result = None
for line in open(sys.argv[1]):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if isinstance(event, dict) and event.get("type") == "result":
        result = event
found = result or {}
# modelUsage covers every model the run used and is filled even when a budget
# stop leaves usage at zero; usage is the fallback.
models = found.get("modelUsage")
usage = found.get("usage")
if isinstance(models, dict) and models:
    keys = ("inputTokens", "outputTokens", "cacheReadInputTokens", "cacheCreationInputTokens")
    tokens = sum(m.get(k) or 0 for m in models.values() if isinstance(m, dict) for k in keys)
elif isinstance(usage, dict):
    keys = ("input_tokens", "output_tokens", "cache_read_input_tokens", "cache_creation_input_tokens")
    tokens = sum(usage.get(k) or 0 for k in keys)
else:
    tokens = "unknown"
cost = found.get("total_cost_usd")
text = found.get("result")
open(sys.argv[2], "w").write(text if isinstance(text, str) else "")
print(f"Tokens: {tokens}")
print(f"Cost: {cost:.2f}" if isinstance(cost, (int, float)) else "Cost: unknown")
if result is None:
    sys.exit(1)
if result.get("subtype") == "error_max_budget_usd":
    sys.exit(8)
sys.exit(9 if result.get("is_error") or result.get("subtype") not in (None, "success") else 0)
PY
case $? in
  0) exit $status ;;
  8) echo "Budget of \$$BUDGET reached; the build was stopped" >&2; exit 8 ;;
  9) echo "claude reported an error result; the build did not finish" >&2 ;;
esac
grep -v '^[[:space:]]*$' "$OUT/stderr.txt" | tail -n 1 >&2
[ $status -ne 0 ] || status=1
exit $status
