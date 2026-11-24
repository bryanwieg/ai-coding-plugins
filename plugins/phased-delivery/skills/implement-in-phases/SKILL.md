---
name: implement-in-phases
description: "Build a written phased plan one phase at a time: revise the next phase's stage files against the repository, hand its stage briefs to agents in the planned order, review the actual diff, make one local commit per stage (with model, effort and token trailers), then stop and report. Use whenever the user asks to implement, build, execute, start, continue or resume a phased plan or a numbered phase (\"implement phase 2\", \"build the next phase\", \"continue the plan\", \"start on the plan\"), or when a plan directory of NN-name phase folders (phase.json and stage files) exists and the user wants it built. Requires a complete plan; if phase folders or stage briefs are missing, use plan-in-phases first. Use proactively, without being asked, whenever the work at hand is described by a plan's phase.md files (their header says \"Implement with the implement-in-phases skill\"); never build them without this skill. Never pushes unless asked."
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

Each step below has its own guide; read it when you reach the step.
`scripts/build-check.py` (in this plugin, two directories above this
skill's directory) decides what needs no judgment: whether a build stayed
in its files and passed its checks, which model and thinking level pairs
were already tried, the premium spend, and every commit with its trailers.
Do not count, sum or write those by hand. Why it works this way is in
[structured-implementation-notes.md](structured-implementation-notes.md).

## Before the first phase

1. Read the project instructions, specification, design and every `phase.md`.
2. Check that all phase folders exist with complete stage briefs. If not, stop
   and complete the plan with plan-in-phases first; implementation never fills
   planning gaps.
3. Note the starting git state and any edits already present, so they are not
   mistaken for this work. The commit the plan's work starts from is the
   first phase's `record.start_commit` in its `phase.json`, written by
   `build-check.py start`; the work report counts from it. On resume, find
   where the phase left off from `phase.md`'s status line and stage table,
   which are rendered from the records.
4. Project rules (testing, size limits, what may be run) apply throughout.
   Writing code gives no permission to run it, and delegating to another agent
   does not lift any rule.

## Each phase

1. **Revise.** Read [revise-guide.md](revise-guide.md) and follow it with
   no problem: check the phase's stage files against the repository, edit
   the stale briefs, raise their revisions and run `plan-check.py` until
   clean. Then run `build-check.py start <phase dir>` until it exits 0.
2. **Build.** Read [build-guide.md](build-guide.md) and follow it for every
   stage: route, `can-try`, dispatch, `record` (the gate), and `commit`.
   Only a stage `record` accepted may be committed, and only a stage whose
   brief sets `session_only` may be built by the session itself.
3. **Review.** Hand the review to a new agent that built none of the phase,
   with [phase-reviewer.md](phase-reviewer.md) unchanged and its inputs
   filled in, written to a prompt file outside the repository. Run `route
   --review` and `scripts/claude-build.sh` with its `model`, `effort` and
   `cap_usd`, and record the run with `build-check.py record <phase dir>
   review ... --premium`. A review never drops a step: if it stops at its cap
   (claude-build.sh exit 8), report that to the user. While Codex is on, check
   the routing rule first; when it sends the review to Codex, run
   `scripts/codex-build.sh` with the pair `route --review` prints for
   `models-available-codex.json`. The reviewer writes
   `review.json` in the phase folder with only the finding types phase-reviewer.md
   lists. Read the diff yourself and decide on each finding by its action:
   - `remove` and `fix`: make the change, `record ... --fix` and `commit`
     it against the stage it changes (build-guide.md, "Commit each stage");
   - `plan-gap`: revise the plan before any code changes, following
     [revise-guide.md](revise-guide.md) with the finding as the problem; a
     built stage it reopens is rebuilt with `record ... --fix`;
   - `question`: put it to the user in the report.
4. **Finish.** Update the phase's `notes` in `phase.json`, then run
   `build-check.py finish <phase dir>`: it checks `review.json` and that
   every stage has a commit and none is reopened, records the built commit,
   re-renders `phase.md` and `plan.md` and commits the plan directory with a
   `Phase:` trailer. Never push or publish unless asked.

Then stop and report to the user:

- each stage: done or not, and where to see it;
- deviations from the briefs, or "none";
- what was verified by running something versus only by reading code, and what
  could not be verified;
- plan adjustments made, as recorded in the phase's `notes`;
- the models' work in this phase: the table from
  `scripts/stage-stats.sh <phase start>..HEAD`;
- whether Codex was on or off this phase, and why;
- questions, and the next phase.

A routing stop follows build-guide.md, "Stopping mid-phase"; report it the
same way, adding the stages left and both usage scripts' output lines.

Continue to the next phase only when the user says so; a user stop wins.

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
