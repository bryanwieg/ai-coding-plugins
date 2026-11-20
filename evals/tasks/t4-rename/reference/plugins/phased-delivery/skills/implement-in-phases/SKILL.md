---
name: implement-in-phases
description: "Build a written phased plan one phase at a time: revise the next phase file against the repository, hand its stage briefs to agents in the planned order, review the actual diff, make one local commit per phase, then stop and report. Use whenever the user asks to implement, build, execute, start, continue or resume a phased plan or a numbered phase (\"implement phase 2\", \"build the next phase\", \"continue the plan\", \"start on the plan\"), or when a plan directory of NN-name.md phase files exists and the user wants it built. Requires a complete plan; if phase files or stage briefs are missing, use plan-in-phases first. Use proactively, without being asked, whenever the work at hand is described by phase files (their header says \"Implement with the implement-in-phases skill\"); never build them without this skill. Never pushes unless asked."
---

# Implement in phases

Companion to [plan-in-phases](../plan-in-phases/SKILL.md). The plan's phase
files hold the structure, contracts and stage briefs; the implementer owns how
each stage's code works inside its brief. The planner's simplicity rules apply
unchanged.

## Before the first phase

1. Read the project instructions, specification, design and every phase file.
2. Check that all phase files exist with complete stage briefs. If not, stop
   and complete the plan with plan-in-phases first; implementation never fills
   planning gaps.
3. Note the starting git state and any edits already present, so they are not
   mistaken for this work. On resume, find where the phase left off from its
   status line and stage table.
4. Project rules (testing, size limits, what may be run) apply throughout.
   Writing code gives no permission to run it, and delegating to another agent
   does not lift any rule.

## Each phase

### 1. Revise the phase file

Before building, check the phase file against what actually exists: earlier
phases may have changed names, paths or details. Update its context, contracts
and briefs so each stage is correct for the repository as it is, and record each
adjustment in the phase's Notes. Check each open assumption in the phase's
Assumptions section against the code now: mark it verified with where it was
checked, or, if it is wrong, revise the plan through plan-in-phases' revision
rules before building. For a small plan, also confirm its Size criteria still
hold; if not, the plan must become a full plan first. Planning-level changes
inside the approved design need no approval. A change to the specification or design, or work the
design lacks, goes to the user first.

### 2. Build the stages

Follow the stage table's order. Hand each stage to a subagent with
[stage-builder.md](stage-builder.md) unchanged and its inputs filled in; run
stages marked parallel together. Small or tightly coupled stages may be built
directly, under the same directions. Delegation keeps each agent's context
focused on its brief.

Before the phase's first dispatch, refresh the plan's
`models-available.json` from the running tool and rerun
`scripts/select-models.py` to regenerate `models.md`, as
[model-selection.md](../plan-in-phases/model-selection.md) describes; note
any change in the phase's Notes. Then choose each subagent's tier: start from the
brief's `Model basis` scores, re-score against the revised brief and the code
as it now is, record any change in the Notes, and use the model and thinking
level `models.md` gives for that tier, where the tool lets you choose; never
above the model's thinking-level ceiling in model-selection.md. When a builder fails or
finds the stage harder than its tier, rerun it one tier higher; when it stops
because the brief is wrong, revise the plan instead.

Mark each stage's status in the table as it completes.

### 3. Review the phase

Hand the review to a new subagent that built none of the phase, with
[phase-review.md](phase-review.md) unchanged and its inputs filled in, on
the `top` candidate from the plan's `models.md`. It reads the actual diff and code, not
the builders' reports. Then read the diff yourself and decide on each
finding.

The review may remove, simplify or fix deviations. Anything it wants to add
goes in the report as a question. Problems the plan does not cover go back
through plan-in-phases' revision rules before any code changes.

### 4. Commit and stop

Update the phase's status line and Notes, then make one local commit for the
phase, staging only its files and keeping edits that were already present. Use
the project's required annotations (such as `[skip ci]`). Never push or publish
unless asked.

Stop and report to the user:

- each stage: done or not, and where to see it;
- deviations from the briefs, or "none";
- what was verified by running something versus only by reading code, and what
  could not be verified;
- plan adjustments made in the Notes;
- questions, and the next phase.

Continue to the next phase only when the user says so. An explicit user stop
always wins.

## Corrections

Fix exactly what the user raised. Remove accidental edits rather than expanding
the plan to keep them. If the same point comes back a second time, stop and
discuss the instruction itself; the brief or a rule is probably unclear.
