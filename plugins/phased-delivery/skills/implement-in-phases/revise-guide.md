# Revise the phase: guide

Before building a phase, check its file against what actually exists and
write the result as `<plan>/.build/NN-revision.json` in
[revision.schema.json](revision.schema.json). `scripts/build-check.py
start` checks it, and every later gate reads it: the files a stage may
change and the commands that show it is done come from this file, not
from the phase file's prose.

## Check the phase file against the repository

Earlier phases may have changed names, paths or details. Read the code each
stage touches as it is now, and update the phase file's context, contracts
and briefs so each stage is correct for the repository as it is. Record each
adjustment in the phase's Notes.

Check each open assumption in the phase's Assumptions section against the
code now: mark it verified with where it was checked, or, if it is wrong,
revise the plan through plan-in-phases' revision rules
([revising.md](../plan-in-phases/revising.md)) before building.

For a quick plan (its `Size` section says so), check that the revision keeps
it one phase of at most 3 stages and adds no contract that existing code,
the user or disk uses; if not, the plan must become a full plan first.

Planning-level changes inside the approved design need no approval. A change
to the specification or design, or work the design lacks, goes to the user
first.

## The revision JSON, field by field

### phase
The phase number, `NN`, as in the file name.

### stages
Every stage in the stage table, in its order.
- `id` and `title`: as in the phase file. The title becomes the stage
  commit's subject after the id.
- `files`: exactly the paths the revised brief's Files line allows, with
  `create`, `edit` or `delete`. The gate fails any other changed path,
  except the files of stages not yet committed, the plan directory,
  edits present before `start`, and Python caches.
- `checks`: shell commands that show the brief's "Done when" holds. Each
  runs with `sh -c` from the repository root and must exit 0. Use the
  commands the brief names; turn "the tests pass" into the command that
  runs them. A brief whose "Done when" can only be confirmed by reading
  gets an empty list; the orchestrator then reads the diff itself before
  committing.
- `scores`: the brief's `Model basis` measures re-scored against the
  revised brief and the code as it is now, written without spaces
  (`J1F1R0C0K0P0V0S0`). When a score changes, update the brief's Model
  basis and say why in the Notes.
- `tier`: the tier those scores give (model-selection.md, "Pick the tier").

### assumptions
Each open assumption checked: `verdict` `verified` or `wrong`, and
`evidence`, the file and symbol or the command that settled it.

### adjustments
One line per change made to the phase file, as recorded in its Notes.

## Then

Run `build-check.py start <phase file>`. Fix each problem it prints (one
JSON line each) and rerun until it exits 0. It also refuses to start when a
stage's file already has uncommitted edits: commit or set them aside first,
so they are not mistaken for the stage's work. On resume, `start` keeps the
existing ledger; edit the revision only for stages not yet committed.
