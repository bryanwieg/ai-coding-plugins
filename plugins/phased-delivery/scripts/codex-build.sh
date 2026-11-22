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
# OUTDIR also receives error.txt: Codex's last error message, or empty.
#
# Exit: 0 built; 3 Codex needs `codex login` again; 5 Codex's sandbox
# cannot start here; 6 Codex ran no turn (subscription, account or service
# problem); 7 Codex is out of quota; other non-zero: the codex exit status.
# Never commits; the orchestrator does.
set -u
[ $# -eq 5 ] || { sed -n '2,22p' "$0" >&2; exit 2; }
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
  < /dev/null > "$OUT/events.jsonl" 2> "$OUT/stderr.txt"
status=$?
if grep -q 'could not be refreshed\|Please log out and sign in again\|Not logged in\|authentication token has expired' "$OUT/stderr.txt"; then
  echo "Codex sign-in has lapsed: run 'codex logout && codex login --device-auth'" >&2
  exit 3
fi
python3 - "$OUT/events.jsonl" "$OUT/error.txt" <<'PY'
import json, sys
usage, error = {}, ""
for line in open(sys.argv[1]):
    try:
        event = json.loads(line)
    except ValueError:
        continue
    if not isinstance(event, dict):
        continue
    if '"turn.completed"' in line:
        usage = event.get("usage") or usage
    if event.get("type") in ("error", "turn.failed"):
        nested = event.get("error")
        texts = [event.get("message"), nested.get("message") if isinstance(nested, dict) else None]
        error = next((t for t in texts if isinstance(t, str) and t), error)
total = usage.get("input_tokens", 0) + usage.get("output_tokens", 0)
print(f"Tokens: {total if usage else 'unknown'}")
open(sys.argv[2], "w").write(error)
PY
error=$(cat "$OUT/error.txt")
[ -n "$error" ] || error=$(grep -v '^[[:space:]]*$' "$OUT/stderr.txt" | tail -n 1)
# Match only a command whose output starts with the error, not a file that quotes it.
if grep -q '"aggregated_output":"bwrap: No permissions to create a new namespace' "$OUT/events.jsonl"; then
  echo "Codex's sandbox cannot start here (no user namespaces); if this session already runs in a sandbox, set CODEX_BUILD_SANDBOX=danger-full-access" >&2
  status=5
elif ! grep -q '"turn.completed"' "$OUT/events.jsonl"; then
  # The free plan's limit, which a lapsed subscription reaches, means Codex is unusable, not just out of quota.
  if ! grep -qF 'Upgrade to Plus' "$OUT/error.txt" "$OUT/stderr.txt" &&
     grep -qF 'hit your usage limit' "$OUT/error.txt" "$OUT/stderr.txt"; then
    echo "Codex is out of quota: $error" >&2
    status=7
  else
    echo "Codex could not run a turn (subscription, account or service problem): ${error:-no error text}" >&2
    status=6
  fi
fi
exit $status
