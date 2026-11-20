#!/bin/sh
# check.sh RUN_REPO: hidden acceptance check for t4-rename.
. "$(dirname "$0")/../../lib/common.sh"
python3 -B "$KIT/tasks/$TASK/check.py" >> "$OUT" 2>&1
finish
