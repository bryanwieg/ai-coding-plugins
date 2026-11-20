#!/bin/sh
# collect.sh RUN_ID: after a builder run, write into runs/RUN_ID/:
#   check.txt         hidden check output (RESULT line last)
#   diff.txt          diff of the run repo against its starting state
#   grader-input.md   everything the blind grader sees, if report.md and
#                     log.txt (put there by the operator) exist
# Exit status is the check's exit status.
set -u
KIT=$(cd "$(dirname "$0")" && pwd)
. "$KIT/lib/env.sh"
DIR=$RUNS/$1
TASK=$(cat "$DIR/task")
REPO=$DIR/repo

sh "$KIT/tasks/$TASK/check.sh" "$REPO" > "$DIR/check.txt" 2>&1
code=$?

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT
sh "$KIT/lib/make-repo.sh" "$TASK" "$tmp/before"
ln -s "$REPO" "$tmp/after"
(cd "$tmp" && diff -ruN -x __pycache__ -x '*.pyc' before after) > "$DIR/diff.txt"

if [ -f "$DIR/report.md" ] && [ -f "$DIR/log.txt" ]; then
  {
    echo "# Grader input: run $(basename "$DIR"), task $TASK"
    echo
    echo "Grade with grading.md. The model and thinking level are deliberately not given."
    echo
    echo "## 1. Stage brief (phase file given to the builder as plan/01-$TASK.md)"
    echo
    echo '````markdown'
    cat "$KIT/tasks/$TASK/brief.md"
    echo '````'
    echo
    echo "## 2. Builder directions and inputs (the builder's whole prompt)"
    echo
    echo '````markdown'
    sh "$KIT/prompt.sh" "$(basename "$DIR")" | sed "s#$REPO#<REPO>#g"
    echo '````'
    echo
    echo "## 3. Builder's final report"
    echo
    echo '````'
    sed "s#$REPO#<REPO>#g" "$DIR/report.md"
    echo '````'
    echo
    echo "## 4. Tool-call log"
    echo
    echo '````'
    sed "s#$REPO#<REPO>#g" "$DIR/log.txt"
    echo '````'
    echo
    echo "## 5. Diff (starting state -> after the run)"
    echo
    echo '````diff'
    cat "$DIR/diff.txt"
    echo '````'
    echo
    echo "## 6. Hidden check output"
    echo
    echo '````'
    cat "$DIR/check.txt"
    echo '````'
  } > "$DIR/grader-input.md"
  echo "wrote $DIR/grader-input.md"
else
  echo "no report.md/log.txt in $DIR yet; wrote check.txt and diff.txt only"
fi
tail -n 1 "$DIR/check.txt"
exit $code
