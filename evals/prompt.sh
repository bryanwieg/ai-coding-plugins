#!/bin/sh
# prompt.sh RUN_ID: print the builder's prompt for a run, exactly as an
# orchestrator would send it: stage-builder.md unchanged, then the filled-in
# inputs block with the repository root stated.
set -eu
KIT=$(cd "$(dirname "$0")" && pwd)
. "$KIT/lib/env.sh"
DIR=$RUNS/$1
TASK=$(cat "$DIR/task")
REPO=$DIR/repo
cat "$REPO/plugins/phased-delivery/skills/implement-in-phases/stage-builder.md"
printf '\n---\n\n'
sed "s#{{REPO}}#$REPO#g" "$KIT/tasks/$TASK/inputs.md"
