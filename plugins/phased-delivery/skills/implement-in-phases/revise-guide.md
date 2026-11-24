# Revise the phase: guide

Directions for revising one phase of a plan, before it is built or after a
problem in it. The session follows them itself, or gives this file,
unchanged, to a headless reviser, followed by the inputs below.

Inputs:

- Phase folder: `<plan>/NN-name`
- Problem: `<the failed stage and what failed, the review finding, or "none" before the phase is built>`
- Project instructions: `<paths, such as CLAUDE.md or AGENTS.md>`

---

You are revising one phase of a phased plan. The plan is its JSON: the phase
folder holds `phase.json` and one stage file `NN.n.json` per stage, each
with a `brief` and a `record`. The revision rules are plan-in-phases'
[revising.md](../plan-in-phases/revising.md); apply them, within the limits
below. The field guides beside it say what goes in each field.

## What you may change

- The `brief` of this phase's stage files, and in this phase's `phase.json`
  the `notes` and the status and evidence of its `assumptions`.
- Never a `record`: only the build scripts write those.
- Never `phase.md` or `plan.md`: `plan-check.py` renders them.
- Nothing in another phase, `plan.json`, the specification or the design,
  and no code. When the fix needs one of those, escalate (below).
- No revision JSON or other side file: the stage files are what
  `build-check.py` gates and routes from.

## Check the phase against the repository

Earlier phases and stages may have changed names, paths or details. Read
the code each stage still to build touches as it is now, and update those
briefs (context, contracts, files, behaviour, `checks`) so each stage is
correct for the repository as it is. With a problem, start from it: find
which brief is wrong, and separate the missing definition from any proposed
code fix.

- `files`: exactly the paths the stage may change, with `create`, `edit` or
  `delete`. The gate fails any other changed path.
- `checks`: shell commands that show the brief's `done_when` holds. Each
  runs with `sh -c` from the repository root and must exit 0. A brief whose
  `done_when` can only be confirmed by reading gets an empty list.
- `model_basis`: re-score the measures when the brief or the code it
  touches changed (model-selection.md, "Pick the tier").

Check each open assumption of the phase against the code now: mark it
verified with where it was checked. A wrong assumption is a problem to
revise for, like any other.

For a quick plan (`plan.json`'s `size` says so), check that the revision
keeps it one phase of at most 3 stages and adds no contract that existing
code, the user or disk uses; if not, escalate: the plan must become a full
plan first.

## Built stages

Rework of built code is planned by revising the built stage's brief in
place, not by a cleanup stage: a committed stage whose brief has a higher
`revision` than it was built at is reopened and rebuilt against the new
brief as a fix. Raise the revision of every built stage the change affects,
after bringing its brief in line with the change. Add a stage file only for
work that belongs to no existing stage, numbered after the phase's existing
ones.

## Raise revisions and check

1. Raise `revision` by one in the brief of every stage whose brief you
   changed, whatever the change, prose included. A changed brief with an
   unchanged revision is an error from `plan-check.py` and `build-check.py`;
   a raised one lets every model pair be tried again.
2. Record each change and its reason in `phase.json`'s `notes`.
3. Run `scripts/plan-check.py <plan dir> --repo <repo> --phase NN` and fix
   every error, until it is clean. A headless reviser runs it when the
   project's rules allow it to; the driver runs it after the reviser anyway,
   and a revision that fails it is not built.

## Escalate instead of changing anything

Change nothing, and say why, when:

- the fix is above the phase: another phase, `plan.json` (a contract other
  phases use, an outcome, the architecture);
- the fix contradicts the approved specification or design, or is work the
  design lacks.

In the session, the first goes through revising.md on the whole plan and the
second to the user. A headless reviser only reports it.

## In the session, then

Before building the phase, run `build-check.py start <phase dir>`. Fix each
problem it prints (one JSON line each) and rerun until it exits 0. It also
refuses to start when a stage's file already has uncommitted edits: commit
or set them aside first, so they are not mistaken for the stage's work. On
resume, `start` keeps the existing record.

## Report

- Each stage file changed or added: what changed and why, and its new
  revision.
- Assumptions checked, with the evidence.
- Whether `plan-check.py` ran, and its summary line.

End the report with exactly one of these as its last line; a missing line
counts as escalate:

- `Result: revised`: stage files edited, revisions raised, `plan-check.py`
  clean (or not run, and said so above).
- `Result: unchanged`: nothing needed to change.
- `Result: escalate <phase|spec|design>: <why>`: nothing was changed;
  `phase` means the fix is above this phase.
