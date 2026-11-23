---
name: implement-in-phases
description: "Build a written phased plan one phase at a time: revise the next phase file against the repository, hand its stage briefs to agents in the planned order, review the actual diff, make one local commit per stage (with model, effort and token trailers), then stop and report. Use whenever the user asks to implement, build, execute, start, continue or resume a phased plan or a numbered phase (\"implement phase 2\", \"build the next phase\", \"continue the plan\", \"start on the plan\"), or when a plan directory of NN-name.md phase files exists and the user wants it built. Requires a complete plan; if phase files or stage briefs are missing, use plan-in-phases first. Use proactively, without being asked, whenever the work at hand is described by phase files (their header says \"Implement with the implement-in-phases skill\"); never build them without this skill. Never pushes unless asked."
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
   mistaken for this work. Record the commit the plan's work starts from in
   the first phase's Notes as `Plan start: <commit>`; the work report counts
   from it. On resume, find where the phase left off from its
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
rules ([revising.md](../plan-in-phases/revising.md)) before building. For a
quick plan (its `Size` section says so), check that
the revision keeps it one phase of at most 3 stages and adds no contract
that existing code, the user or disk uses; if not, the plan must become a
full plan first. Planning-level changes
inside the approved design need no approval. A change to the specification or design, or work the
design lacks, goes to the user first.

### 2. Build the stages

Follow the stage table's order. Hand each stage to a new builder with
[stage-builder.md](stage-builder.md) unchanged and its inputs filled in; run
stages marked parallel together. Small or tightly coupled stages may be built
directly, under the same directions. Delegation keeps each agent's context
focused on its brief.

Before the phase's first dispatch, run `scripts/select-models.py check
<plan>/models.md`. Only on exit 1, or when a dispatch fails because a model
is unavailable, refresh the plan's `models-available.json` from the running
tool, rerun the selector to regenerate `models.md` and note the change in
the phase's Notes; exit 3 means the fallback, as
[model-selection.md](../plan-in-phases/model-selection.md) describes.

Route every dispatch by "Route each stage" in model-selection.md: start
from the brief's `Model basis` scores, re-score against the revised brief
and the code as it now is, record any change in the Notes, and run
`scripts/select-models.py route <plan>/models-available.json --scores
<scores> --premium-spent <X>`, with X from the phase's
`Premium spend: $X of $10` Notes line (0 until the first premium run).
Build a Claude stage headless: write stage-builder.md and its filled-in
inputs to a prompt file outside the repository and run
`scripts/claude-build.sh <repo> <prompt> <model> <effort> <cap_usd>
<outdir>` with route's `model`, `effort` and `cap_usd`. Read its report
from `<outdir>/report.md`; it prints `Tokens:` and `Cost:` for the commit.
Accept it exactly as a subagent's work. The limits:

- **Exit 8, budget reached:** retry with `route --down 1`, one step
  further on each further stop; each stopped attempt is an Earlier-Attempt.
  Never re-dispatch a pair already tried for the stage; when `route` would,
  revise the plan (model-selection.md, "Adjust while working").
- **Any other non-zero exit** (2: bad arguments or permissions setting;
  otherwise claude's own status, such as a sign-in or service failure):
  report stderr's last line to the user and stop; do not step up.
- **Fails its "Done when" or is harder than its scores:** rerun with
  `route --up 1` (one step further on each further failure). When it stops
  because the brief is wrong, revise the plan instead.
- **Premium spend:** after each `claude-build.sh` run of a pair route
  printed with `"premium": true`, and of every review it runs, add its
  `Cost:` (its `cap_usd` when unknown) to the `Premium spend` line. From
  $10, builds get no premium pair. Codex runs add nothing and their
  `route` calls pass no `--premium-spent`.
- `CLAUDE_BUILD_PERMISSIONS` unset gives the builder `acceptEdits`: file
  edits, and commands the project's allow rules permit. A session already
  in a sandbox container may set it to `bypassPermissions`.

When the plan has `models-codex.md` and the session is not Codex, first
check Codex availability by "Builders in another tool" in
model-selection.md, before the phase's first dispatch and ahead of
refreshing `models-codex.md`; when Codex is off, skip the rest of this
paragraph and record why in the Notes. While Codex is on, refresh
`models-codex.md` the same way, then before each dispatch run
`scripts/claude-usage.py` and `scripts/codex-usage.py` and route the stage
by the routing table there. A Codex dispatch runs alone (stages marked
parallel run one after another when one goes to Codex) and starts with the
snapshot of REPO; follow the rules there for failed Codex builds.
For a Codex build, write stage-builder.md and its filled-in inputs to a
prompt file outside the repository and run `scripts/codex-build.sh <repo> <prompt> <model> <effort>
<outdir>`, with the model and effort `route` prints for
`models-available-codex.json` (Codex builds have no cap).
Read its report from `<outdir>/report.md`; it prints the token count for
the commit. Accept it exactly as a subagent's work.

For a `small` stage, never take the builder's report as evidence: rerun its
"Done when" commands yourself and read its diff before accepting it.

When a stage is accepted, mark its status in the table and commit it (see
"Commit each stage" below).

### Commit each stage

One local commit per stage, so each model's work can be traced and counted.
Stage only that stage's files; keep edits that were already present out of
it. Stages built in parallel are still committed one by one; if two must
share a commit, give it one set of trailers per stage. Subject: the stage
number and title, plus the project's required annotations (such as
`[skip ci]`). End the message with these trailers:

```
Stage: 02.3
Plan: <path to the phase file>
Tier: small
Tool: <tool that built it, such as claude-code or codex>
Model: <model as dispatched>
Effort: <thinking level as dispatched, or "default">
Attempt: 1
Tokens: <total tokens for this attempt, or "unknown">
Cost: <the Cost line claude-build.sh printed, or "unknown">
Tool-Calls: <count, or "unknown">
```

- **Model, Effort** are what was dispatched; "orchestrator" when the stage
  was built directly.
- **Tokens, Cost, Tool-Calls** come from the tool's own usage report (the
  lines `claude-build.sh` or `codex-build.sh` prints; for an in-session
  subagent, its completion notice), never from the builder's report. Use
  "unknown" when the tool gives none; the build scripts print no tool-call
  count.
- **Attempt** counts dispatches of this stage, including `--down` and
  `--up` reruns; commit only the accepted attempt, and list earlier ones as
  `Earlier-Attempt: <model> <effort> <tokens> <why it failed>` (for exit 8,
  "budget reached").
- A change made later to fix a committed stage, from the phase review or
  later work, gets its own commit with `Fixes-Stage: <stage>`,
  `Model:`, `Effort:` and `Tokens:` of whoever made the fix.

`scripts/stage-stats.sh` turns these trailers into the work report (see
"Report the models' work" below).

### 3. Review the phase

Hand the review to a new agent that built none of the phase, with
[phase-reviewer.md](phase-reviewer.md) unchanged and its inputs filled in,
written to a prompt file outside the repository. Run `route --review` and
`scripts/claude-build.sh` with its `model`, `effort` and `cap_usd`; add its
`Cost:` to the phase's premium spend. A review never drops a step: if it
stops at its cap (exit 8), report that to the user. While Codex is on,
check the routing rule first; when it sends the review to Codex, run
`scripts/codex-build.sh` with the pair `route --review` prints for
`models-available-codex.json`. It reads the actual diff and code, not
the builders' reports. Then read the diff yourself and decide on each
finding.

The review may remove, simplify or fix deviations. Anything it wants to add
goes in the report as a question. Problems the plan does not cover go back
through plan-in-phases' revision rules
([revising.md](../plan-in-phases/revising.md)) before any code changes.

### 4. Commit and stop

Commit each review fix as described in "Commit each stage". Then update the
phase's status line and Notes and commit them on their own, with the
trailer `Phase: <phase file>`. Never push or publish unless asked.

Stop and report to the user:

- each stage: done or not, and where to see it;
- deviations from the briefs, or "none";
- what was verified by running something versus only by reading code, and what
  could not be verified;
- plan adjustments made in the Notes;
- the models' work in this phase: the table from
  `scripts/stage-stats.sh <phase start>..HEAD`;
- whether Codex was on or off this phase, and why;
- questions, and the next phase.

When the routing rule stops the phase (both tools nearly out), stop the
same way after committing the stage in progress, and also report the
stages left and both usage scripts' output lines (usage and reset times).
A stop at the check before the review sets
`Status: in progress (stages done: all; review pending)`; resuming starts
with the review, after checking availability and the routing rule again.

Continue to the next phase only when the user says so. An explicit user stop
always wins.

## Report the models' work

After the last phase is committed, write `work-report.md` in the plan
directory, commit it with the trailer `Phase: <plan directory>`, and give
the user its tables and Reading.

1. Generate it, never by hand: `sh scripts/stage-stats.sh <plan start>..HEAD`.
   Per model and effort it gives stages, first-try and clean counts, failed
   tries, fixes needed, tokens spent and wasted, and tokens per stage, with
   every rerun and fix listed.
2. Add a short **Reading** section judging each candidate by those numbers:
   - **Effectiveness** is the clean rate: stages accepted on the first
     dispatch and never fixed afterwards. Failed tries and fixes needed
     count against it, and so do review findings on its stages.
   - **Cost** is tokens per clean stage, counting wasted tokens and the
     tokens others spent fixing its work.
   - Name what the reruns and fixes had in common (the measure that was
     under-scored, or the kind of mistake), and whether a tier's candidate
     should change, citing the counts. Too few stages to judge is a valid
     answer; say how many.
3. List any "unknown" token counts and why they are unknown.

## Corrections

Fix exactly what the user raised. Remove accidental edits rather than expanding
the plan to keep them. If the same point comes back a second time, stop and
discuss the instruction itself; the brief or a rule is probably unclear.
