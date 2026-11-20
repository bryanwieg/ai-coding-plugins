#!/bin/sh
# check.sh RUN_REPO: facts for p1-stop. This task is graded by the blind
# grader with the p1 rule in grading.md; the script cannot judge the report.
# It prints the scope line and FACT lines, then "RESULT facts-only"; exit 0.
. "$(dirname "$0")/../../lib/common.sh"
python3 -B "$KIT/tasks/$TASK/check.py" >> "$OUT" 2>&1
cat "$OUT"
echo "RESULT facts-only"
exit 0
