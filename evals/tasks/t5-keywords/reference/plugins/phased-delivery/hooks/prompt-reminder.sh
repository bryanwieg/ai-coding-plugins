#!/bin/sh
# UserPromptSubmit: when the prompt is about planning or building multi-step
# work, remind the agent which phased-delivery skill applies. Silent otherwise.

# Take only the JSON "prompt" string, up to its closing unescaped quote, so
# other fields (cwd, transcript path) never match. Escaped newlines and tabs
# become spaces so words at line starts still match.
prompt=$(sed -nE 's/.*"prompt"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\1/p' |
  sed -e 's/\\[nt]/ /g')

if printf '%s' "$prompt" | grep -qiwE '(plan|plans|planning|phase|phases|phased|stages|roadmap|milestone|milestones|break (it|this|that) down|migrat[a-z]*|rewrite|refactor[a-z]*|implement[a-z]*)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"phased-delivery: if this is multi-step work, plan it with the plan-in-phases skill (it sizes the plan from the code); if it builds or continues a phased plan, use the implement-in-phases skill."}}'
fi
