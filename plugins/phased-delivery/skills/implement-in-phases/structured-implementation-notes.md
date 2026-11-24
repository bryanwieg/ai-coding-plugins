# Why implementation uses stage files, a script gate and closed review types

Background for maintainers of this skill; the orchestrator and the reviewer
do not need it. Changed 2026-11-24 (plugin 0.11.0). The plan that built it
is `docs/plans/implement-structured/`.

## What changed

Planning moved to JSON with a checking script and a closed list of review
finding types (see
[structured-planning-notes.md](../plan-in-phases/structured-planning-notes.md)):
judgment words were replaced by things that can be checked, and the review
stopped ratcheting. implement-in-phases now follows the same pattern:

- **Short SKILL.md, one guide per step.** The 231-line SKILL.md held every
  rule inline; it is now an outline that sends revising to
  revise-guide.md and building to build-guide.md. The rules kept their
  meaning; they moved.
- **Revision as JSON.** Revising a phase ends in `.build/NN-revision.json`:
  each stage's files, the commands that show it is done, and its scores.
  Older phase files differ in layout, and "Done when" is prose, so the
  script reads this file instead of parsing the phase file.
- **A gate the orchestrator cannot argue with.** `build-check.py record`
  fails a build that changed files outside its stage or whose checks fail;
  the orchestrator may still reject a passing build, never accept a
  failing one. Before, acceptance rested on the orchestrator's reading.
- **Bookkeeping in the script.** Attempt counts, Earlier-Attempt lines,
  pairs already tried and the premium spend were kept by hand in Notes
  lines and commit messages, where a slip changes routing (a wrong spend
  lets premium pairs through; a forgotten try gets re-dispatched) and the
  work report. The ledger holds them and `commit` writes the trailers in
  the format `stage-stats.sh` already read.
- **Closed review types.** The phase reviewer reports only untraced
  change, check on internal data, bug, not done, test, assumption, rule
  and unneeded code, as JSON. The open "a simpler structure exists" check
  was dropped: it is the kind of judgment finding that made plan review
  ask for more every round. Unneeded code (unused, unasked-for or
  duplicated) keeps the useful part.

## Why the revision JSON went away (0.12.0)

History: until 0.11.x a revised phase had three homes for a stage: the
`NN-name.md` phase file, the `.build/NN-revision.json` the revise step wrote
from it, and a ledger of attempts beside it in `.build/`. The planning JSON
was deleted once the plan was reported, so a revision edited prose and then
restated it as JSON, and the two could drift apart.

Now the plan's JSON is kept for its whole life (see
[structured-planning-notes.md](../plan-in-phases/structured-planning-notes.md)),
and `build-check.py` takes a phase folder and reads each stage file directly:

- **Revise is an edit of the JSON.** A stage's `files`, `checks` and
  `model_basis` are already in its brief, so the revision JSON and its
  schema had nothing left to say. The reviser edits briefs, raises their
  `revision` and reruns `plan-check.py`.
- **Records beside the briefs.** Each stage file is `{brief, record}`;
  attempts go into the stage's `record`, review and revise runs into
  `phase.json`'s. Only the scripts write a `record`, so two writers never
  share a part of a file, and status in `phase.md` is rendered from the
  records, never edited.
- **A brief's hash is kept per revision.** A brief edited without a higher
  `revision` is an error (exit 5), and the pairs already tried are counted
  per revision: a changed brief may be tried again on every pair.
- **A built stage can be reopened** by raising its brief's revision; it is
  rebuilt as a fix commit. Freezing built briefs left facts about later
  stages unmovable.
- **Only a `session_only` stage may be recorded as built by the
  orchestrator.** The 0.11.0 validation run below built a stage itself to
  save money; the script now refuses that.
- **One guide for every revision.** revise-guide.md takes the problem as an
  input (none before a phase) and ends in a result line, so a session and a
  headless reviser follow the same rules.

The sections above and below describe 0.11.0 where they name the revision
JSON or the ledger.

## Decisions worth keeping

- A build exit other than 0 and 8 is `error`, not a try: sign-in, service
  and Codex availability failures say nothing about the model, so they
  neither block the pair nor count against it in the work report.
- Stage commits hold only the stage's files; the plan directory (the JSON
  with its records, and the rendered files) is committed by `finish`, so
  plan edits mid-phase never fail a gate.
- Files of other stages count as in scope only until those stages are
  committed: parallel stages work, and a committed stage cannot change
  unseen.

## Later: a driver script

Investigate, not built. The `plan-phase-driver` branch holds an unreviewed
draft plan (2026-11-22) for a Python driver that owns the whole phase loop
and calls `claude -p` for each step (revise, build, review, triage), with
the orchestrator LLM only handling halts.

- **What it would add:** rules that hold every time (no step skipped), no
  orchestrator tokens, clean halts and resume on usage limits, and the
  whole loop testable offline with a fake `claude`.
- **What it would cost:** a larger build than this one; the draft predates
  `claude-build.sh`, `route`, the premium budget and this script, so it
  needs re-planning on top of `build-check.py`. While both paths exist,
  the loop's rules live in prose and Python. Codex routing was deferred in
  the draft, and every case the rules do not cover becomes a halt for the
  user.
- **What to measure first:** with this version in use, how often the
  orchestrator skips or misapplies a step the script does not gate, and
  how much of a phase's usage the orchestrator itself spends. If both are
  small, the driver is not worth it.

## Measured

One validation run, 2026-11-24: a headless Opus session at medium thinking
(`--max-budget-usd 2.40`, the branch's plugin only, Opus and Haiku offered)
implemented the builder eval task `p2-multistep` as a one-phase plan in a
git copy of the eval repository.

- **Result:** the task's files, copied onto a fresh eval repository, pass
  the hidden check (`RESULT pass`). Cost $0.84: $0.54 for the session (15
  turns) and $0.30 for the review on Opus high (248k tokens, no findings).
- **The script path was followed end to end:** the session wrote a
  revision JSON with five real check commands (the test suite, the
  behaviour cases, an unchanged selector output, the doc sentence, the new
  test), ran `start`, `record` (accepted), `commit` (stage trailers),
  recorded the review with `--premium`, and ran `finish` (`Status: built`)
  and the work report.
- **Where it bent the rules:** it built the `small` stage itself instead of
  dispatching the routed Opus medium build ($1.60 cap), and ran the review
  with a $1.50 cap instead of route's $4.00, both because its own $2.40
  session cap could not cover them. Both are recorded in the phase Notes.
  The lesson is about the run's setup, not the skill: a session capped
  below the caps it must pay for will economize. Nothing the script gates
  was skipped.
- **Not exercised:** `can-try` and a headless stage build (the session
  built the stage itself), a failing build, a retry or a budget stop (the
  stage passed first time), Codex, and check commands that run long; the open
  question on check timeouts stays open.
