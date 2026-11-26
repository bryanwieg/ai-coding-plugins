---
name: implement-in-phases
description: "Build a written phased plan one phase at a time: run the phase driver (run-phase.py), which revises the next phase's stage files against the repository, hands its stage briefs to headless builders, reviews the actual diff and makes one local commit per stage (with model, effort and token trailers); answer each halt it reports, then stop and report. Use whenever the user asks to implement, build, execute, start, continue or resume a phased plan or a numbered phase (\"implement phase 2\", \"build the next phase\", \"continue the plan\", \"start on the plan\"), or when a plan directory of NN-name phase folders (phase.json and stage files) exists and the user wants it built. Requires a complete plan; if phase folders or stage briefs are missing, use plan-in-phases first. Use proactively, without being asked, whenever the work at hand is described by a plan's phase.md files (their header says \"Implement with the implement-in-phases skill\"); never build them without this skill. Never pushes unless asked."
---

# Implement in phases

Companion to [plan-in-phases](../plan-in-phases/SKILL.md). The plan is its
JSON: `plan.json` and, per phase, a folder `NN-name` with `phase.json` and
one stage file `NN.n.json` per stage. Each has a `brief` (the structure,
contracts and stage briefs, written by planning and revising) and a `record`
(written only by the scripts). `plan.md` and each `phase.md` are rendered
from them; never edit a rendered file or a `record` by hand. The implementer
owns how each stage's code works inside its brief. The planner's simplicity
rules apply unchanged.

`scripts/run-phase.py` (the driver, in this plugin, two directories above
this skill's directory) builds a phase: it revises the phase, routes,
dispatches, gates and commits every stage, runs the review and its fixes
and finishes the phase, each model call a headless `claude`. The session
runs the driver and answers its halts; it does not dispatch, gate or commit
a stage itself, except a stage whose brief sets `session_only`. What the
driver does at each step is in [build-guide.md](build-guide.md); why it
works this way is in
[structured-implementation-notes.md](structured-implementation-notes.md).

## Before the first phase

1. Read the project instructions, specification, design and every `phase.md`.
2. Check that all phase folders exist with complete stage briefs. If not, stop
   and complete the plan with plan-in-phases first; implementation never fills
   planning gaps.
3. Note the starting git state and any edits already present, so they are not
   mistaken for this work. The commit the plan's work starts from is the
   first phase's `record.start_commit` in its `phase.json`, written by
   the driver; the work report counts from it. On resume, rerun the driver:
   it finds where the phase left off from the records.
4. Project rules (testing, size limits, what may be run) apply throughout.
   Writing code gives no permission to run it, and delegating to another agent
   does not lift any rule.

## Each phase

1. **Run the driver** from the repository, for every phase:

   ```
   python3 scripts/run-phase.py <phase dir> [--instructions <path>]... \
     [--subject-suffix "[skip ci]"] [--extra-trailer "Co-Authored-By: ..."]...
   ```

   Pass each project instruction file (CLAUDE.md, AGENTS.md) with
   `--instructions`, and the project's required commit subject annotation
   and trailers with the other two options. It prints a report and exits 0
   (built), 10 (halted) or 2 (bad usage: fix the command). Run it as a
   background shell: a phase outlasts a foreground command's time limit,
   and the user watches the live feed on its stderr (each call's thinking,
   messages and tool calls, the driver's own steps as `[driver]` lines and
   each stage check's command, output and exit as `[check-NN.n]` lines) in
   the tool's view of that shell. Do not read
   the feed into your own context; wait for the exit and read the report.
2. **On exit 10, answer the halt.** Read `record.halt` in the phase's
   `phase.json` (the report prints it too): `step`, `stage`, `reason`,
   `detail` and `next`. Do what `next` says, as the table below expands it,
   then rerun the same command; the rerun clears the halt and resumes from
   the records. Repeat until it exits 0. Never edit a `record`, and never
   build, record or commit a stage that is not `session_only` to get past a
   halt.
3. **On exit 0, report** (below). Never push or publish unless asked.

"Revise" below means: follow [revise-guide.md](revise-guide.md) yourself,
with the halt's detail as the problem; edit the briefs, raise the
`revision` of each changed brief and run `plan-check.py` until clean. A
change that guide does not allow (another phase, `plan.json`, the
specification or the design) is settled with the user first.

| Reason | What happened | What the session does, then reruns |
| --- | --- | --- |
| `revise-failed` | The revised plan fails `plan-check.py`, or `build-check.py start` refused (a stage's file was already modified). | Revise to clear the errors in the detail, or clean the working tree. |
| `escalated` | The reviser says the problem is above this phase. | **Ask the user**; settle it in the specification, the design or the plan, then revise the stage files to match. |
| `revise-capped` | A stage was revised twice for failures in this run, or its model pairs are used up and the reviser changed nothing. | **Ask the user**: go through the stage's attempts and brief with them, then revise the brief and raise its revision. |
| `builder-stopped` | The builder reported the brief cannot be built, and the reviser changed nothing. | Read the detail; revise the brief and raise its revision. |
| `brief-changed` | A brief changed without a higher revision. | Raise the stage's revision, or restore the brief. |
| `record-changed` | A model call changed a record; the driver restored it. | Check the directions named in the detail with the user. |
| `models-stale` | `models.md` no longer matches the model profiles. | Refresh as [model-selection.md](../plan-in-phases/model-selection.md) says ("Handle what the script reports"). |
| `session-only` | The stage's brief sets `session_only`. | Build, record and commit it yourself ("A session-only stage", below). |
| `build-error` | A call failed for a reason that is not the model's (sign-in, service, usage limit, a script error). | Clear the cause in the detail yourself; ask the user only when you cannot. |
| `stalled` | A model call gave no output for `CLAUDE_BUILD_STALL` seconds (default 900), twice; the driver undid its edits each time. | Check that `claude` works (sign-in, service), then rerun. |
| `review-capped` | The review stopped at its cost cap; there is no review. | Tell the user; rerun when they agree. |
| `review-invalid` | `review.json` is missing or does not match `review.schema.json`. | Delete `review.json`. |
| `plan-gap` | A review finding is a gap in the plan. | Revise the stage files to cover it; a built stage whose revision is raised is rebuilt by the driver. |
| `question` | A review finding is a question. | **Ask the user**; revise if the answer needs it. |
| `fix-failed` | The fix for a review finding failed. | Revise the stage's brief and raise its revision so the driver rebuilds it, or settle the finding with the user. |

### A session-only stage

The one stage the session builds. On the `session-only` halt, for the stage
it names:

1. Print its packet: `python3 scripts/plan-check.py <plan dir> --packet
   <NN.n>`. Build from the packet alone, under
   [stage-builder.md](stage-builder.md), like a headless builder.
2. Gate it: `build-check.py record <phase dir> <NN.n> --tool claude-code
   --model orchestrator --effort default --exit 0 --tokens unknown --cost
   unknown` (add `--fix` when the stage already has a commit). Exit 1
   names the files outside the stage or the failing checks: correct the
   work and record again.
3. Commit it: `build-check.py commit <phase dir> <NN.n>` with the same
   subject suffix and trailers as the driver's. Commit before rerunning: a
   rerun restores uncommitted stage files.

## The phase report

When the driver exits 0, stop and report to the user:

- the driver's report: each stage and where to see it, the review findings
  and their outcome, and the models' work in this phase (the table from
  `scripts/stage-stats.sh`);
- every halt of the phase and how it was answered;
- what was verified by running something versus only by reading code, and
  what could not be verified;
- plan adjustments made, as recorded in the phase's `notes`;
- that Codex was off (the driver, version 1, builds with Claude only);
- questions, and the next phase.

A phase left halted for the user is reported the same way, with the halt
and the stages left.

Continue to the next phase only when the user says so; a user stop wins.

## Report the models' work

After the last phase is committed, write `work-report.md` in the plan
directory, commit it with the trailer `Phase: <plan directory>` (unless git
ignores the plan directory), and give the user its tables and Reading.

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
