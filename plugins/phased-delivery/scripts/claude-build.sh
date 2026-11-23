#!/bin/sh
# claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR: build one stage
# headless with claude -p, stopped at a dollar cap.
#
# PROMPT is a file holding stage-builder.md and its inputs, kept outside
# REPO; its text is passed as the prompt. Claude works in REPO with the
# phased-delivery plugin off. OUTDIR receives report.md (the final
# message), stream.jsonl and stderr.txt.
#
# CLAUDE_BUILD_PERMISSIONS sets the permission mode (default acceptEdits:
# file edits work and commands follow the project's allow rules). A session
# already in a sandbox container sets it to bypassPermissions (the ai-coding
# sandbox image does).
# Prints "Tokens: N" (input, output, cache read and cache creation, from
# modelUsage, else usage) and
# "Cost: X.XX" (USD), or unknown, for the stage commit.
#
# Exit: 0 built; 2 usage; 8 the budget was reached; other non-zero: the
# claude exit status. Never commits; the orchestrator does.
set -u
[ $# -eq 6 ] || { sed -n '2,17p' "$0" >&2; exit 2; }
REPO=$1; PROMPT=$2; MODEL=$3; EFFORT=$4; BUDGET=$5; OUT=$6
MODE=${CLAUDE_BUILD_PERMISSIONS:-acceptEdits}
case "$MODE" in
  acceptEdits|bypassPermissions) ;;
  *) echo "CLAUDE_BUILD_PERMISSIONS must be unset or bypassPermissions, not '$MODE'" >&2; exit 2 ;;
esac
mkdir -p "$OUT"
TEXT=$(cat "$PROMPT") || exit 2
(cd "$REPO" && exec claude -p "$TEXT" --model "$MODEL" --effort "$EFFORT" \
  --max-budget-usd "$BUDGET" \
  --settings '{"enabledPlugins":{"phased-delivery@ai-coding-plugins":false}}' \
  --permission-mode "$MODE" --no-session-persistence \
  --output-format stream-json --verbose) \
  < /dev/null > "$OUT/stream.jsonl" 2> "$OUT/stderr.txt"
status=$?
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
