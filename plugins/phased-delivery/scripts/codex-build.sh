#!/bin/sh
# codex-build.sh REPO PROMPT MODEL EFFORT OUTDIR: build one stage with
# codex exec, for an orchestrator running in another tool.
#
# PROMPT is a file holding stage-builder.md and its inputs, kept outside
# REPO. Codex works in REPO with write access to it only (and /tmp). OUTDIR
# receives report.md (the final message), events.jsonl and stderr.txt.
#
# CODEX_BUILD_SANDBOX sets Codex's sandbox mode (default workspace-write).
# A container that is itself the boundary, where Codex's own bubblewrap
# sandbox cannot start, sets it to danger-full-access; Codex then has the
# whole container rather than REPO alone, and its plugin hooks run without
# per-hook trust review, as in that container's own Codex sessions.
# Prints "Tokens: N" (input + output, from Codex's own usage report) for
# the stage commit.
#
# Exit: 0 built; 3 Codex needs `codex login` again; other non-zero: the
# codex exit status. Never commits; the orchestrator does.
set -u
[ $# -eq 5 ] || { sed -n '2,18p' "$0" >&2; exit 2; }
REPO=$1; PROMPT=$2; MODEL=$3; EFFORT=$4; OUT=$5
SANDBOX=${CODEX_BUILD_SANDBOX:-workspace-write}
case "$SANDBOX" in
  workspace-write) set -- ;;
  danger-full-access) set -- --dangerously-bypass-hook-trust ;;
  *) echo "CODEX_BUILD_SANDBOX must be workspace-write or danger-full-access, not '$SANDBOX'" >&2; exit 2 ;;
esac
mkdir -p "$OUT"
codex exec -m "$MODEL" -c model_reasoning_effort="$EFFORT" \
  --cd "$REPO" --sandbox "$SANDBOX" "$@" --json -o "$OUT/report.md" \
  "Your complete directions are in $PROMPT. Read that file first and follow it exactly. Your final message is your report." \
  > "$OUT/events.jsonl" 2> "$OUT/stderr.txt"
status=$?
if grep -q 'could not be refreshed\|Please log out and sign in again\|Not logged in' "$OUT/stderr.txt"; then
  echo "Codex sign-in has lapsed: run 'codex logout && codex login --device-auth'" >&2
  exit 3
fi
python3 - "$OUT/events.jsonl" <<'PY'
import json, sys
usage = {}
for line in open(sys.argv[1]):
    if '"turn.completed"' in line:
        usage = json.loads(line).get("usage") or usage
total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
print(f"Tokens: {total if usage else 'unknown'}")
PY
exit $status
