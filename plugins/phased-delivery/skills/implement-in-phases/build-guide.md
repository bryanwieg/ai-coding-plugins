# What the driver does: reference

`scripts/run-phase.py` builds one phase. This file describes what it does
at each step, so a halt can be understood; it gives the session nothing to
do. What the session does is in [SKILL.md](SKILL.md): run the driver,
answer its halts, and build a `session_only` stage. The routing rules are in
[model-selection.md](../plan-in-phases/model-selection.md).

```
run-phase.py PHASE_DIR [--repo DIR] [--profiles PATH] [--work DIR]
             [--instructions PATH]... [--subject-suffix TEXT] [--extra-trailer LINE]...
```

Exit 0: built. Exit 10: halted, with `{step, stage, reason, detail, next}`
in `record.halt` of the phase's `phase.json`. Exit 2: bad usage. Each run
prints a report: every stage and its status, the review findings and their
outcome, the halt, that Codex is off and, for a built phase,
`stage-stats.sh`'s table. `--work` keeps each call's prompt, output and
`report.md` in a numbered folder (a temporary directory otherwise). While a
call runs, the driver prints its feed to stderr, each line tagged with the
call (`[build-01.2]`): its thinking summaries, messages, tool calls, failed
tool results and result.

## The parts

- The driver reads each stage's brief from its stage file
  (`<phase dir>/NN.n.json`) and resumes from the records alone: a rerun
  clears the halt and continues with the first step not yet recorded. A
  phase already built is only reported.
- Every model call is a headless `claude` through `scripts/claude-build.sh`,
  at the model, thinking level and cost cap `select-models.py route`
  prints. Version 1 builds with Claude only, as if Codex were off.
- `scripts/build-check.py` keeps the attempts, gates each build, sums the
  premium spend and makes the commits, so nothing is counted or written by
  hand.
- After every model call the driver restores what the call may not change
  in the plan: any `record` (halt `record-changed`), and for a builder or
  fixer also the briefs and any file it added to the plan folder. Only the
  reviser may edit briefs.

`CLAUDE_BUILD_PERMISSIONS` unset gives each call `acceptEdits`: file edits,
and commands the project's allow rules permit. A session already in a
sandbox container may set it to `bypassPermissions` (the ai-coding sandbox
sets it already).

## Revise and start

On a phase with no revise run recorded, the driver:

1. runs `build-check.py start`, which validates the phase and writes
   `start_commit` and the paths already modified (`preexisting`); a refusal
   halts `revise-failed`;
2. runs `select-models.py check <plan>/models.md`; a stale table halts
   `models-stale`;
3. gives [revise-guide.md](revise-guide.md) to a headless reviser at the
   review pair (`route --review`), with "none" as the problem, and records
   the run. A report without `Result: revised` or `Result: unchanged` halts
   `escalated`; a revised plan that fails `plan-check.py` halts
   `revise-failed`.

On a rerun before any stage has an attempt it only runs `plan-check.py`.

## Build each stage

The stages not done are built one at a time in id order; a stage marked
parallel is not built in parallel. For each:

1. A `session_only` stage halts `session-only`: the session builds it
   (SKILL.md, "A session-only stage").
2. **Route.** `route` with the brief's `model_basis` scores and
   `build-check.py spend` as `--premium-spent`, moved `--up` one step per
   failed or rejected attempt at the brief's current revision, or `--down`
   one step per budget stop. From $10 of premium spend, builds get no
   premium pair (route does this).
3. **`can-try`.** A pair already tried at this revision, or a stage that has
   both failed and hit its cap, is not dispatched: the stage is revised
   (below).
4. **Dispatch.** [stage-builder.md](stage-builder.md) unchanged, then the
   project instructions and the stage packet (`plan-check.py --packet`), the
   only plan text a builder is given. A reopened stage (committed, then its
   brief's revision raised) is rebuilt the same way as a fix, with its
   earlier commit named.
5. **Gate.** `build-check.py record` with the call's exit, tokens and cost:
   - accepted (no changed file outside the brief's `files`, every command
     in its `checks` passed): `build-check.py commit`;
   - failed or budget stop: the paths outside the stage are restored and
     the stage is routed again;
   - stalled (`claude-build.sh` exit 7: no output for `CLAUDE_BUILD_STALL`
     seconds): the call's edits are undone and it runs once more, not as a
     try of the pair; a second stall halts `stalled`. Each stalled call is
     recorded with exit 7 (for a stage, as an error attempt), so its cap
     counts in the premium spend; a stalled revise does not count as the
     phase's revise. This holds for every model call, not only builds;
   - error (a build exit other than 0, 7 and 8; not a try of the pair): halt
     `build-error`;
   - the builder's report ends `Result: stopped`: the attempt is rejected
     and the stage revised. A builder that edited the plan is rejected and
     the stage routed again.
6. **Commit.** Only the stage's changed files, with the subject `NN.n
   <title>` and the trailers `stage-stats.sh` reads (Stage, Plan, Tier,
   Tool, Model, Effort, Attempt, Tokens, Cost, Tool-Calls, and an
   Earlier-Attempt per failed, stopped or rejected try, over every
   revision), plus `--subject-suffix` and each `--extra-trailer`. The
   commit goes into the stage file's `record` and `phase.md` is
   re-rendered, where the stage then shows as done (in the working tree;
   `finish` commits the plan directory).

**Revising a stage that cannot be built.** The driver restores the working
tree and runs the reviser with the failure as the problem. `revised`: the
raised revision starts the pairs afresh and the stage is built again.
`unchanged`: halt `builder-stopped` when the builder stopped, otherwise
`revise-capped`. A stage revised twice for failures in one run halts
`revise-capped` instead of a third revision. A brief changed without a
higher revision (exit 5 of any `build-check.py` call) halts
`brief-changed`.

A halt during a build restores every uncommitted path but the plan's and
the preexisting ones, so a rerun starts from a clean tree. Any build puts
an earlier `review.json` aside as `review-N.json`, so the phase is reviewed
again.

## Review and fix

With every stage committed and no `review.json`, the driver gives
[phase-reviewer.md](phase-reviewer.md) to a new headless reviewer at the
review pair, with the phase's diff from `start_commit`, the preexisting
edits and the stages that have no check commands, and records the run. A
review stopped at its cap halts `review-capped`; a missing `review.json` or
one that does not match `review.schema.json` halts `review-invalid`.

Each finding's status is kept in `record.findings` of `phase.json`:

- `remove` and `fix` on a stage of the phase: one fix build of that stage
  at its routed pair, with the finding as the assignment (stage-builder.md,
  "Fixing one review finding"), recorded with `--fix` and committed with
  `Fixes-Stage:`. A fix that fails its gate, stops, edits the plan or
  changes none of the stage's files halts `fix-failed`.
- every other finding is marked `asked` and halts `plan-gap` (when one of
  them is a plan gap) or `question`; on the rerun they count as answered.
  A stage the session reopened to answer one is rebuilt first, and the
  phase reviewed again.

## Finish

`build-check.py finish` checks `review.json` and that every stage has a
commit and none is reopened, records the built commit, re-renders
`phase.md` and `plan.md` and commits the plan directory with a `Phase:`
trailer and each `--extra-trailer`; a plan directory git ignores (a plan
kept out of the repository) is left uncommitted. Its refusal halts
`build-error`.

## Premium spend

`build-check.py spend <phase dir>` prints the phase's premium spend: the
cost of every attempt recorded with `--premium`, its cap when the cost is
unknown. The driver passes `--premium` for every run of a pair route marks
premium, the revise and review runs included.

## Session-only stages

A `session_only` stage, built by the session, is recorded with `--model
orchestrator --effort default --tokens unknown --cost unknown`; `record`
exits 2 for that model on any other stage. When it changed no file in the
repository, `commit` makes an empty commit with its trailers.
