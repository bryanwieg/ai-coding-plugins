#!/bin/sh
# apply-reference.sh TASK REPO: overlay tasks/TASK/reference/ onto REPO and
# remove the paths listed in tasks/TASK/reference-delete.txt, if any.
set -eu
KIT=$(cd "$(dirname "$0")/.." && pwd)
. "$KIT/lib/env.sh"
TASK=$1
REPO=$2
cp -a "$KIT/tasks/$TASK/reference/." "$REPO/"
if [ -f "$KIT/tasks/$TASK/reference-delete.txt" ]; then
  while IFS= read -r path; do
    [ -n "$path" ] && rm -f "$REPO/$path"
  done < "$KIT/tasks/$TASK/reference-delete.txt"
fi
