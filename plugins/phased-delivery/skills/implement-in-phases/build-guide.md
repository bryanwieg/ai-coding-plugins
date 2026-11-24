# Build the stages: guide

How to route, dispatch, gate and commit each stage of a phase. The routing
rules are in [model-selection.md](../plan-in-phases/model-selection.md);
`scripts/build-check.py` keeps the attempts, gates each build and makes the
commits, so nothing here is counted or written by hand.

## Order and builders

Follow the stage table's order. Hand each stage to a new builder with
[stage-builder.md](stage-builder.md) unchanged and its inputs filled in; run
stages marked parallel together. Small or tightly coupled stages may be
built directly, under the same directions; record that in the Notes.
Delegation keeps each agent's context focused on its brief.

## Models

Before the phase's first dispatch, run `scripts/select-models.py check
<plan>/models.md`. Only on exit 1, or when a dispatch fails because a model
is unavailable, refresh the plan's `models-available.json` from the running
tool, rerun the selector to regenerate `models.md` and note the change in
the phase's Notes; exit 3 means the fallback, as model-selection.md
describes.

## Route and dispatch each stage

1. Take the stage's `scores` from the revision JSON.
2. Run `scripts/select-models.py route <plan>/models-available.json
   --scores <scores> --premium-spent $(scripts/build-check.py spend <phase
   file>)` ("Route each stage" in model-selection.md).
3. Run `build-check.py can-try <phase file> <stage> <model> <effort>`. Exit
   1 means the pair was already tried for this stage: do not dispatch it;
   revise the plan (model-selection.md, "Adjust while working").
4. Build a Claude stage headless: write stage-builder.md and its filled-in
   inputs to a prompt file outside the repository and run
   `scripts/claude-build.sh <repo> <prompt> <model> <effort> <cap_usd>
   <outdir>` with route's `model`, `effort` and `cap_usd`. Read the
   builder's report from `<outdir>/report.md`; the script prints `Tokens:`
   and `Cost:`. Accept it exactly as a subagent's work.

`CLAUDE_BUILD_PERMISSIONS` unset gives the builder `acceptEdits`: file
edits, and commands the project's allow rules permit. A session already in
a sandbox container may set it to `bypassPermissions` (the ai-coding
sandbox sets it already).

## Gate each build

After every build, record it:

```
build-check.py record <phase file> <stage> --tool claude-code --model <m> --effort <e> \
  --exit <build exit> --tokens <Tokens> --cost <Cost> --cap <cap_usd> [--tool-calls N] [--premium]
```

Pass `--premium` when route printed `"premium": true`. `--tool-calls` comes
from the tool's own usage report (an in-session subagent's completion
notice); leave it out when there is none. Tokens and cost are `unknown`
when the tool gives none, never the builder's own claim.

It prints one JSON line and exits:

- **0, accepted:** no changed file outside the scope rule, and every check
  passed. Read the builder's report and the diff; when the work is wrong in
  a way the checks miss, run `build-check.py reject <phase file> <stage>
  "<why>"` and treat it as a failed "Done when". The orchestrator can
  reject a passing build, never accept a failing one.
- **1, failed:** a changed file outside the stage (`outside`) or a failing
  check (`checks`). Restore the `outside` paths (`git restore` them, or
  delete them when HEAD lacks them), then rerun with `route --up 1`, one
  step further on each further failure. When it fails because the brief is
  wrong, revise the plan instead.
- **3, budget reached** (build exit 8): restore the `outside` paths, then
  retry with `route --down 1`, one step further on each further stop.
- **4, error** (any other build exit): not a try of the pair. Apply that
  tool's rule: for `claude-build.sh` (2: bad arguments or permissions;
  otherwise claude's own status, such as a sign-in or service failure),
  report stderr's last line to the user and stop; for a failed Codex build,
  follow model-selection.md ("After a failed build").

A stage that has both hit its cap and failed its checks goes back to
planning; never net `--down` against `--up`.

For a `small` stage, never take the builder's report as evidence: the
checks are rerun by `record`, and read its diff before committing.

## Premium spend

`build-check.py spend <phase file>` prints the phase's premium spend: the
cost of every attempt recorded with `--premium`, its cap when the cost is
unknown. Pass `--premium` for every `claude-build.sh` run of a premium pair
and for every phase review run through `claude-build.sh`. From $10, builds
get no premium pair (route does this). Codex runs are never `--premium` and
their `route` calls pass no `--premium-spent`.

## Commit each stage

When a stage is accepted, run:

```
build-check.py commit <phase file> <stage> [--subject-suffix "[skip ci]"] [--extra-trailer "Co-Authored-By: ..."]
```

It commits only the stage's changed files, with the subject `NN.n <title>`
and the trailers `stage-stats.sh` reads (Stage, Plan, Tier, Tool, Model,
Effort, Attempt, Tokens, Cost, Tool-Calls, and an Earlier-Attempt per
failed, stopped or rejected try), and marks the stage done in the phase
file's table and status line (in the working tree; `finish` commits them).
Add the project's required subject annotations and trailers with the two
options. Stages built in parallel are committed one by one.

A stage built directly by the orchestrator is recorded with `--model
orchestrator --effort default --tokens unknown --cost unknown`.

A later change to fix a committed stage, from the phase review or later
work, is recorded with `record ... --fix` and committed the same way; its
commit carries `Fixes-Stage:` with the fixer's Model, Effort and Tokens.

## Codex

When the plan has `models-codex.md` and the session is not Codex, take
Codex availability from the daily check in "Builders in another tool" in
model-selection.md: off when the session was told at start that Codex is
off today, otherwise what `scripts/codex-usage.py` answers from its daily
cache before the phase's first dispatch. When Codex is off, skip the rest
of this section and record why in the Notes.

While Codex is on, refresh `models-codex.md` the same way as `models.md`,
then before each dispatch run `scripts/claude-usage.py` and
`scripts/codex-usage.py` and route the stage by the routing table there. A
Codex dispatch runs alone (stages marked parallel run one after another
when one goes to Codex) and starts with the snapshot of REPO; follow the
rules there for failed Codex builds. For a Codex build, write
stage-builder.md and its filled-in inputs to a prompt file outside the
repository and run `scripts/codex-build.sh <repo> <prompt> <model> <effort>
<outdir>`, with the model and effort `route` prints for
`models-available-codex.json` (Codex builds have no cap), and record it
with `--tool codex`. Read its report from `<outdir>/report.md`; it prints
the token count.

## Stopping mid-phase

When the routing rule stops the phase (both tools nearly out), commit the
stage in progress, then run `build-check.py finish <phase file> --stopped`
to commit the plan directory (phase file, Notes and `.build/`). A stop at
the check before the review first sets the phase file's status line to
`Status: in progress (stages done: all; review pending)`; resuming starts
with the review, after checking availability and the routing rule again.
