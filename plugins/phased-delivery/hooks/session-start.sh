#!/bin/sh
# SessionStart: tell the agent when to use the phased-delivery skills, and
# list unfinished phase files written by plan-in-phases in this repository
# (and in its ignored .ai-scratchpad/plans).
# Phase files are found by the header line plan-in-phases puts in each one.

marker='Implement with the implement-in-phases skill'

json_escape() {
  sed -e 's/\\/\\\\/g' -e 's/"/\\"/g' -e 's/	/\\t/g' | awk '{printf "%s\\n", $0}'
}

unfinished=""
if git rev-parse --is-inside-work-tree >/dev/null 2>&1; then
  # plans kept out of the repository in .ai-scratchpad/plans (git grep skips ignored files)
  plans="$(git rev-parse --show-cdup).ai-scratchpad/plans"
  unfinished=$({ git grep -l --untracked -F "$marker" -- '*.md' 2>/dev/null
      [ -d "$plans" ] && grep -rlF --include='*.md' "$marker" "$plans" 2>/dev/null; } |
    grep -E '(^|/)[0-9][0-9]-[^/]*(/phase)?\.md$' | head -50 |
    while IFS= read -r f; do
      status=$(grep -m1 '^Status:' "$f" | sed 's/^Status:[[:space:]]*//')
      case "$status" in
        built*|reviewed*) ;;
        *) printf -- '- %s (%s)\n' "$f" "${status:-no status}" ;;
      esac
    done)
fi

context="The phased-delivery plugin is enabled.
- Before a multi-step change (a feature, migration, rewrite, or work touching several files, a shared contract or the architecture), start the plan-in-phases skill. Its first step is a capped estimate (at most 5 files read) that picks direct work, a quick plan or a full plan; small changes go straight back to direct work.
- Use the implement-in-phases skill to build any phased plan. Never build phase files without it."

if [ -n "$unfinished" ]; then
  context="${context}

Unfinished phased plans in this repository (phase file and status):
${unfinished}
When the user wants this work continued, built or implemented, use implement-in-phases."
fi

# Codex availability, cached for the day by codex-usage.py; only exits 3 and 4 mean off.
if command -v python3 >/dev/null 2>&1; then
  codex_line=$(python3 "$(dirname "$0")/../scripts/codex-usage.py" 2>/dev/null)
  case $? in
    3|4)
      if [ "$AI_CODEX" = off ]; then fix='Unset AI_CODEX to use it.'; else fix='Run codex-usage.py --recheck after fixing it.'; fi
      context="${context}

Codex is off today, so do not consider Codex this session: no Codex model files, usage checks or Codex builds and reviews. Cause: ${codex_line}
${fix}" ;;
    5)
      context="${context}

Codex check timed out at session start; the skills check again before using Codex." ;;
  esac
fi

printf '{"hookSpecificOutput":{"hookEventName":"SessionStart","additionalContext":"%s"}}\n' \
  "$(printf '%s' "$context" | json_escape)"
