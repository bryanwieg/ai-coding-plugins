# Structured implementation: design

Agreed with the user on 2026-11-23. The plan in this folder builds it.

## Goal

implement-in-phases follows the architecture plan-in-phases now has: a
short SKILL.md that sends each step to its own guide, JSON written against
schemas where a step's result is read by something else, a script that
decides everything that needs no judgment, and a review limited to a
closed list of finding types. The LLM still orchestrates the phase.

## What stays the same

The routing, budget, retry ladder, premium spend limit, Codex rules,
commit trailers and work report keep their current meaning. They move from
SKILL.md into guides or into the script, not into new rules. The trailer
format is unchanged, so `stage-stats.sh` needs no change.

## Revision

Revising a phase against the repository ends in a revision JSON for the
phase, written against a schema: for each stage, the files it may change,
the check commands that show its "Done when", and its re-scored measures;
the verdict on each open assumption; and the adjustments made. The script
reads the revision JSON, not the phase file's prose, so plans written in
older layouts work too.

## Check gate

After each build, the script checks the stage: no file outside the stage's
files changed (edits present before the phase do not count), and every
check command passes. A failing check counts as a failed "Done when": the
stage goes to `route --up` as today. The orchestrator cannot accept a
stage past a failing check; it may still reject one that passes.

## Bookkeeping

The script owns the per-phase ledger: each attempt's tool, model, effort,
exit status, tokens, cost and check result. From it the script refuses a
pair already tried for the stage, reports the premium spend for
`route --premium-spent`, makes each stage commit (staging only the stage's
files, with the trailers from the ledger), and updates the phase file's
stage table and status line. The orchestrator no longer writes trailers
or sums spend by hand.

## Review

The phase reviewer reports only these finding types, each with file, line
and evidence: untraced change, check on internal data, bug or contract
mismatch, unmet "Done when" or "After", missing or wrong test, broken
assumption, project rule broken, and unneeded code (code nothing calls, a
wrapper or option no brief asks for, or duplicated logic). The open-ended
"a simpler structure exists" check is dropped. Findings are written as
JSON against a schema, each with its action: remove, fix, plan gap or
question.

## Validation

Offline tests run the script against temporary git repositories with no
model calls. One paid end-to-end run of the new skill on the builder eval
task `p2-multistep` (Opus, medium thinking, with a ceiling of about $8: the session capped at $2.40 plus the stage and review caps route prints; agreed with the user 2026-11-24) checks
that an agent follows the split guides; it runs only after the user
confirms its cost.

## Later

A driver script that owns the whole loop and calls `claude -p` for each
step (the draft on the `plan-phase-driver` branch) is recorded as a todo
for later investigation, not built here.
