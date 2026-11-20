#!/bin/sh
# codex-run.sh RUN_ID MODEL EFFORT: run one eval stage with codex exec, then
# extract its log and usage. Create the run with new-run.sh first. Uses the
# operator's Codex login and quota; installed Codex plugins still apply.
set -u
KIT=$(cd "$(dirname "$0")/.." && pwd)
. "$KIT/lib/env.sh"
RUN=$1; MODEL=$2; EFFORT=$3
DIR=$RUNS/$RUN
sh "$KIT/prompt.sh" "$RUN" > "$DIR/prompt.md"
codex exec --skip-git-repo-check \
  -m "$MODEL" -c model_reasoning_effort="$EFFORT" \
  --cd "$DIR/repo" --sandbox workspace-write --json \
  -o "$DIR/report.md" \
  "Your complete directions are in $DIR/prompt.md. Read that file first and follow it exactly. Your final message is your report." \
  > "$DIR/codex-events.jsonl" 2> "$DIR/codex-stderr.txt"
status=$?
python3 -I "$KIT/tools/extract-codex.py" "$DIR"
echo "codex exit $status"
exit $status
