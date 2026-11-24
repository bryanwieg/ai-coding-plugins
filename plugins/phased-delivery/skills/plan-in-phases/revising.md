# Revising the plan

Plans are revised, not defended. A review, a later phase's planning or
implementation may show that an earlier decision, up to the architecture, is
wrong. Then change it, alter it or drop it, however much of the plan that
touches; do not build on a decision known to be wrong.

The plan is its JSON: `plan.json`, each phase folder's `phase.json` and its
stage files. Every revision edits the `brief` parts of the JSON and reruns
`scripts/plan-check.py`, which checks the plan again against the code as it
now is and renders `plan.md` and each `phase.md`. Never edit the rendered
files, and never write a `record`; the build scripts own those.

The implementer revises the next phase before building it (see
implement-in-phases), rechecking that phase's open assumptions against the
code as it now is. When a review or implementation finds work the plan does
not cover or a decision that does not hold:

1. Re-read the code as it is now, including what earlier stages built, before
   changing anything in the plan.
2. Separate the missing definition from the proposed code fix.
3. Find the highest level affected and update the owning phase and its peers
   there; do not tack a cleanup stage onto the end when an earlier contract is
   what is wrong.
4. Recheck built stages the change affects. Plan the rework of built code
   by revising those stages' briefs in place, not by adding cleanup stages:
   a built stage whose brief has a higher `revision` than the one it was
   built at is reopened, and is rebuilt against the new brief as a fix. Add
   a stage file, numbered after the phase's existing ones, only for work
   that belongs to no existing stage.
5. Raise `revision` by one in the brief of every stage whose brief you
   changed, whatever the change, prose included: `plan-check.py` reports a
   brief that changed since it was built without a higher `revision`.
6. Rerun `plan-check.py <plan dir> --repo <repo>` (with `--phase NN` to
   limit the repository checks to the phase about to be built) and fix
   every error.
7. When the change touches architecture or a contract other phases use,
   review the affected phases again before building on them.
8. Never widen a stage to absorb the fix, or rewrite the plan to excuse
   unplanned edits.
9. If the change contradicts the approved spec or design, ask the user.

Replace text that is no longer true; record why in the phase's `notes`
(`phase.json`). Git holds the history.
