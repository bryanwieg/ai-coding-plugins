# Sourced by tasks/<id>/check.sh. Sets KIT, TASK, RUN (the run repo),
# WORK (temp dir, removed on exit), BASELINE (the task's starting repo,
# rebuilt fresh in WORK), TODAY (the report's checked date), OUT (file the
# check lines go to) and defines finish.
set -u
KIT=$(cd "$(dirname "$0")/../.." && pwd)
. "$KIT/lib/env.sh"
TASK=$(basename "$(cd "$(dirname "$0")" && pwd)")
if [ $# -ne 1 ] || [ ! -d "$1" ]; then
  echo "usage: check.sh RUN_REPO" >&2
  exit 2
fi
RUN=$(cd "$1" && pwd)
WORK=$(mktemp -d)
trap 'rm -rf "$WORK"' EXIT
BASELINE=$WORK/baseline
sh "$KIT/lib/make-repo.sh" "$TASK" "$BASELINE" || exit 2
export PYTHONDONTWRITEBYTECODE=1
TODAY=$(python3 -c 'import json,sys; print(json.load(open(sys.argv[1]))["checked"])' \
  "$BASELINE/plugins/phased-delivery/model-report.json")
OUT=$WORK/out
export KIT TASK RUN WORK BASELINE TODAY

# Scope first, before anything runs inside the run repo.
python3 "$KIT/lib/scope.py" "$BASELINE" "$RUN" "$KIT/tasks/$TASK/files.txt" > "$OUT"

# finish: print the check lines, then RESULT pass|fail; exit 0|1.
finish() {
  cat "$OUT"
  if grep -q '^FAIL' "$OUT" || ! grep -q '^PASS' "$OUT"; then
    echo "RESULT fail"
    exit 1
  fi
  echo "RESULT pass"
  exit 0
}
