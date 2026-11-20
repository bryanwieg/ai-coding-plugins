#!/bin/sh
# validate.sh: prove every task's check is sound. For each task, check.sh
# must FAIL on an untouched new-run copy and PASS on that copy plus the
# task's reference solution (p1-stop is facts-only: both runs must print the
# expected facts). Extra checks: t2 reference kills 5/5 mutants, an
# out-of-scope edit fails the scope check, and in p2 the visible test breaks
# after step 1 alone. Prints a summary; exit 0 only if all is green.
set -u
KIT=$(cd "$(dirname "$0")" && pwd)
. "$KIT/lib/env.sh"
LOGS=$RUNS/_validate-logs
rm -rf "$RUNS"/_validate-*
mkdir -p "$LOGS"
export PYTHONDONTWRITEBYTECODE=1
failures=0
summary=""

note() {  # note STATUS TEXT
  summary="$summary$(printf '%-5s %s' "$1" "$2")
"
  [ "$1" = ok ] || failures=$((failures + 1))
}

fresh() {  # fresh TASK NAME -> prints repo path
  sh "$KIT/new-run.sh" "$1" "_validate-$2" | tail -n 1
}

for dir in "$KIT"/tasks/*/; do
  task=$(basename "$dir")
  untouched=$(fresh "$task" "$task-untouched")
  sh "$KIT/tasks/$task/check.sh" "$untouched" > "$LOGS/$task-untouched.txt" 2>&1
  u_code=$?
  ref=$(fresh "$task" "$task-reference")
  sh "$KIT/lib/apply-reference.sh" "$task" "$ref"
  sh "$KIT/tasks/$task/check.sh" "$ref" > "$LOGS/$task-reference.txt" 2>&1
  r_code=$?
  u_fails=$(grep -c '^FAIL' "$LOGS/$task-untouched.txt")
  r_lines=$(grep -c '^PASS' "$LOGS/$task-reference.txt")
  if [ "$task" = p1-stop ]; then
    if [ $u_code -eq 0 ] && grep -q '^FACT format_cost defined: no' "$LOGS/$task-untouched.txt" \
       && grep -q '^FACT speed column present: no' "$LOGS/$task-untouched.txt" \
       && grep -q '^PASS scope (no changes)' "$LOGS/$task-reference.txt" \
       && grep -q '^RESULT facts-only' "$LOGS/$task-reference.txt"; then
      note ok "$task: facts-only; untouched and reference (stop, no changes) give the expected facts"
    else
      note FAIL "$task: unexpected facts (see $LOGS/$task-*.txt)"
    fi
    continue
  fi
  if [ $u_code -eq 1 ] && grep -q '^RESULT fail' "$LOGS/$task-untouched.txt"; then
    note ok "$task: untouched copy fails ($u_fails FAIL lines)"
  else
    note FAIL "$task: untouched copy did not fail (exit $u_code)"
  fi
  if [ $r_code -eq 0 ] && grep -q '^RESULT pass' "$LOGS/$task-reference.txt"; then
    note ok "$task: reference passes ($r_lines PASS lines)"
  else
    note FAIL "$task: reference did not pass (exit $r_code; see $LOGS/$task-reference.txt)"
  fi
done

# t2: every mutant applies and is killed by the reference tests.
if grep -q '^INFO mutants killed 5/5' "$LOGS/t2-tests-reference.txt"; then
  note ok "t2-tests: reference tests kill 5/5 mutants (each by its targeted test)"
else
  note FAIL "t2-tests: reference tests do not kill 5/5 mutants"
fi

# Scope: the t3 reference plus an unrequested README edit must fail "scope".
scoped=$(fresh t3-speed-col scope)
sh "$KIT/lib/apply-reference.sh" t3-speed-col "$scoped"
printf '\n' >> "$scoped/README.md"
sh "$KIT/tasks/t3-speed-col/check.sh" "$scoped" > "$LOGS/scope-negative.txt" 2>&1
if grep -q '^FAIL scope: .*README.md' "$LOGS/scope-negative.txt" && grep -q '^RESULT fail' "$LOGS/scope-negative.txt"; then
  note ok "scope: an unrequested README.md edit fails the scope check"
else
  note FAIL "scope: an unrequested edit was not caught"
fi

# p2: after step 1 alone, the visible test test_thinking_suffix fails.
step1=$(fresh p2-multistep step1)
cp "$KIT/tasks/p2-multistep/reference/plugins/phased-delivery/scripts/select-models.py" \
  "$step1/plugins/phased-delivery/scripts/select-models.py"
python3 -B "$KIT/lib/run_tests.py" "$step1/plugins/phased-delivery/tests" > "$LOGS/p2-step1.txt" 2>&1
if tail -n 1 "$LOGS/p2-step1.txt" | grep -q '"test_effort.NormalizeEffortTest.test_thinking_suffix": "fail"'; then
  note ok "p2-multistep: the visible test breaks after step 1 alone (test_thinking_suffix)"
else
  note FAIL "p2-multistep: the visible test does not break after step 1"
fi

# The cached base still matches the pinned commit.
check=$(mktemp -d)
git -C "$KIT/.." archive "$PIN" | tar -x -C "$check"
rm -rf "$check/evals"
if diff -r "$check" "$BASE" > "$LOGS/base-vs-pin.txt" 2>&1; then
  note ok "base matches the pinned commit $PIN"
else
  note FAIL "base differs from $PIN (see $LOGS/base-vs-pin.txt; delete $BASE to rebuild)"
fi
rm -rf "$check"

rm -rf "$RUNS"/_validate-*-untouched "$RUNS"/_validate-*-reference \
  "$RUNS"/_validate-scope "$RUNS"/_validate-step1
printf '%s' "$summary"
if [ $failures -eq 0 ]; then
  echo "VALIDATE: all green (logs in $LOGS)"
  exit 0
fi
echo "VALIDATE: $failures problem(s) (logs in $LOGS)"
exit 1
