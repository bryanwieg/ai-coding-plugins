#!/bin/sh
# SessionStart: tell the agent when to use the phased-delivery skills, and
# list unfinished phase files written by plan-in-phases in this repository.
# Phase files are found by the header line plan-in-phases puts in each one.

marker='Implement with the implement-in-phases skill'

json_escape() {
  sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/	/\\t/g' | awk '{printf "%s\\n", $0}'
}

unfinished=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  unfinished=$(git grep -l --untracked -F "$marker" -- '*.md' 2>/dev/null |
    grep -E '(^|/)[0-9][0-9]-[^/]*\.md$' | head -50 |
    while IFS= read -r f; do
      status=$(grep -m1 '^Status:' "$f" | sed 's/^Status:[[:space:]]*//')
      case "$status" in
        built*|reviewed*) ;;
        *) printf -- '- %s (%s)\n' "$f" "${status:-no status}" ;;
      esac
    done)
fi

context="The phased-delivery plugin is enabled.
- Use the plan-in-phases skill to plan any multi-step change (a feature, migration, rewrite, or work touching several files, a shared contract or the architecture) before writing code. It decides from the code whether a small plan is enough; do not skip it because a change seems small or familiar.
- Use the implement-in-phases skill to build any phased plan. Never build phase files without it."

if [ -n "$unfinished" ]; then
  context="${context}

Unfinished phased plans in this repository (phase file and status):
${unfinished}
When the user wants this work continued, built or implemented, use implement-in-phases."
fi

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
  "$(printf '%s' "$context" | json_escape)"
