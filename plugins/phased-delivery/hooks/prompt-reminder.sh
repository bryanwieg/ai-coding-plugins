#!/bin/sh
# UserPromptSubmit: when the prompt asks to plan, build or change something,
# remind the agent which phased-delivery skill applies. Silent otherwise. The
# skill's capped estimate sends small changes back to direct work, so a broad
# match costs one estimate, not a plan.

# Take only the JSON "prompt" string, up to its closing unescaped quote, so
# other fields (cwd, transcript path) never match. Escaped newlines and tabs
# become spaces so words at line starts still match.
prompt=$(sed -nE 's/.*"prompt"[[:space:]]*:[[:space:]]*"(([^"\\]|\\.)*)".*/\1/p' |
  sed -e 's/\\[nt]/ /g')

if printf '%s' "$prompt" | grep -qiwE '(plan|plans|planning|phase|phases|phased|stages|break (it|this|that) down|migrat[a-z]*|rewrite|refactor[a-z]*|implement[a-z]*|add|adds|adding|build|builds|building|create|creates|creating|change|changes|changing|update|updates|updating|extend|extends|extending|replace|replaces|replacing|support|supports|supporting|integrate|integrates|integrating|feature|features)'; then
  printf '%s\n' '{"hookSpecificOutput":{"hookEventName":"UserPromptSubmit","additionalContext":"phased-delivery: if this is multi-step work, start the plan-in-phases skill (its first step is a capped estimate that may send the change straight to direct work); if it builds or continues a phased plan, use the implement-in-phases skill."}}'
fi
