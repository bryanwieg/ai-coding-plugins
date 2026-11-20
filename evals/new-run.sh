#!/bin/sh
# new-run.sh TASK RUN_ID: create runs/RUN_ID/repo as the task's starting
# repository (base/ + the task's setup/ + plan/), record the task, and print
# the absolute repo path.
set -eu
KIT=$(cd "$(dirname "$0")" && pwd)
. "$KIT/lib/env.sh"
if [ $# -ne 2 ]; then
  echo "usage: new-run.sh TASK RUN_ID   (tasks: $(ls "$KIT/tasks" | tr '\n' ' '))" >&2
  exit 2
fi
TASK=$1
RUN_ID=$2
case "$RUN_ID" in
  */*|.*|'') echo "bad RUN_ID: $RUN_ID" >&2; exit 2 ;;
esac
DIR=$RUNS/$RUN_ID
[ -e "$DIR" ] && { echo "run exists: $DIR" >&2; exit 2; }
mkdir -p "$DIR"
sh "$KIT/lib/make-repo.sh" "$TASK" "$DIR/repo"
printf '%s\n' "$TASK" > "$DIR/task"
printf '%s\n' "$DIR/repo"
