#!/bin/sh
# make-repo.sh TASK DEST: build the starting repository for TASK at DEST:
# a copy of base/, the task's setup/ overlay, and plan/ (the phase file,
# project rules, models-available.json and a generated models.md).
set -eu
KIT=$(cd "$(dirname "$0")/.." && pwd)
. "$KIT/lib/env.sh"
TASK=$1
DEST=$2
[ -f "$KIT/tasks/$TASK/brief.md" ] || { echo "unknown task: $TASK" >&2; exit 2; }
[ -e "$DEST" ] && { echo "already exists: $DEST" >&2; exit 2; }
mkdir -p "$(dirname "$DEST")"
cp -a "$BASE" "$DEST"
cp "$DIRECTIONS" "$DEST/plugins/phased-delivery/skills/implement-in-phases/stage-builder.md"
if [ -d "$KIT/tasks/$TASK/setup" ]; then
  cp -a "$KIT/tasks/$TASK/setup/." "$DEST/"
fi
mkdir "$DEST/plan"
cp "$KIT/tasks/$TASK/brief.md" "$DEST/plan/01-$TASK.md"
cp "$KIT/lib/project-rules.md" "$DEST/plan/project-rules.md"
cp "$KIT/fixtures/live-claude.json" "$DEST/plan/models-available.json"
today=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["checked"])' \
  "$BASE/plugins/phased-delivery/model-report.json")
PYTHONDONTWRITEBYTECODE=1 python3 "$BASE/plugins/phased-delivery/scripts/select-models.py" \
  "$DEST/plan/models-available.json" --today "$today" --out "$DEST/plan/models.md"
