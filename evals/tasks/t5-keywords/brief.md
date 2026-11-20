# Phase 01: More planning keywords in the prompt reminder

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: the UserPromptSubmit hook reminds the agent about the skills when
the prompt contains words such as plan, phases or refactor.
After: it also reacts to the words roadmap, milestone and milestones.

## Assumptions
- Verified: the hook reads the hook's JSON from stdin, keeps only the
  `"prompt"` string, and matches it with
  `grep -qiwE '(plan|plans|planning|phase|phases|phased|stages|break (it|this|that) down|migrat[a-z]*|rewrite|refactor[a-z]*|implement[a-z]*)'`
  (checked in `plugins/phased-delivery/hooks/prompt-reminder.sh`).
- Verified: `-w` makes grep match whole words only and `-i` ignores case,
  so a new alternative needs no word-boundary or case handling of its own
  (checked against the `grep` options used in the hook).
- Verified: `hooks.json` runs the hook as `sh ".../prompt-reminder.sh"`, so
  it must stay POSIX `sh` (checked in `plugins/phased-delivery/hooks/hooks.json`).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Add roadmap and milestone keywords | small | first | planned |

## 01.1 Add roadmap and milestone keywords

Goal:            The hook prints its reminder when the prompt contains the
                 whole word `roadmap`, `milestone` or `milestones` in any
                 case, and behaves as before otherwise.
Context:         `plugins/phased-delivery/hooks/prompt-reminder.sh`, read
                 while planning: line 1 is `#!/bin/sh`; the keyword regex
                 is the `grep -qiwE '(...)'` on line 11; the reminder JSON
                 is printed on line 12. `hooks.json` runs it with `sh`.
Contracts:       Hook input and output are unchanged: JSON on stdin with a
                 `"prompt"` field; on a match, the existing one-line JSON on
                 stdout; otherwise no output.
Files:           plugins/phased-delivery/hooks/prompt-reminder.sh
Work:            1. In the regex on line 11, insert `roadmap|milestone|milestones|`
                    right after `stages|`, so that part reads
                    `stages|roadmap|milestone|milestones|break (it|this|that) down`.
                    Change nothing else in the file.
                 2. Check it by piping JSON into the hook with `sh`, for
                    example
                    `printf '%s' '{"prompt":"draft the roadmap"}' | sh plugins/phased-delivery/hooks/prompt-reminder.sh`.
External inputs: none (the hook's existing prompt extraction is unchanged)
Done when:       - Prompts containing `roadmap`, `Milestone` or `milestones`
                   print the reminder JSON.
                 - Prompts containing `roadmapping` or `milestoned` but no
                   other keyword print nothing.
                 - Prompts that printed the reminder before still do, and
                   prompts that printed nothing before still print nothing.
                 - The file still starts with `#!/bin/sh` and runs with `sh`.
Out of scope:    `README.md` (its list of trigger words is not updated in
                 this stage), `session-start.sh`, `hooks.json`, the prompt
                 extraction and the reminder text.
Model basis:     J0 F0 R0 C0 K0 P0 V0 = 0 -> small

## Notes
- 2026-11-19: Roadmap and milestone prompts are planning prompts too.
