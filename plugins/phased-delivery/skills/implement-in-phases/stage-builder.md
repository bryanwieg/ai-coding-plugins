# Stage builder directions

Give this file, unchanged, to each builder of a stage, followed by the
inputs below: through `scripts/claude-build.sh` or `scripts/codex-build.sh`,
at the model and thinking level `select-models.py route` prints (see "Route
each stage" in [model-selection.md](../plan-in-phases/model-selection.md)). The orchestrator
follows these rules too when it builds a stage directly.

Inputs the orchestrator fills in:

- Phase file: `<path>`
- Stage: `<NN.n>`
- Project instructions: `<paths, such as CLAUDE.md or AGENTS.md>`
- Anything else the brief links to: `<paths>`

---

You are building one stage of a phased plan. The stage brief in the phase
file is your whole assignment. The structure and contracts are decided; how
the code works inside the brief is yours.

## Before writing code

1. Read the project instructions, the whole phase file, your stage brief and
   everything the brief links to.
2. Read the code the brief names in Context, Contracts and Files, as it is
   now. Earlier stages may have changed it. Do not rely on memory or on the
   brief's description of the code; check it.
3. If the code disagrees with the brief, stop and report (see below).

## Rules

- Change only the brief's files, and only for the brief's goal. A listed
  file is not permission to tidy the rest of it.
- Write the minimum readable code. Check only the brief's external inputs,
  once where they enter, failing clearly. No speculative options, fallbacks
  or retries without a stated requirement. Prefer tools that fail on their
  own.
- Code style: prefer immutable internals. Assign a value once, give a new
  value a new name, produce new values instead of modifying existing ones,
  and keep side effects visible. This is a coding style only; releases,
  artifacts, branches and procedures follow their own requirements.
- Write the tests the brief's Tests line names, and remove the
  expected-fail marks it says to. Add no others: if the goal seems to need
  another test, stop and report. Keep tests deterministic and within the
  phase file's Outcome tests budget.
- Follow the project's rules for testing, size limits and what may be run.
  Writing code gives no permission to run it.
- Do not commit; the orchestrator commits each stage.

## Stop and report instead of proceeding when

- a contract, another stage's work or anything outside the brief must
  change;
- the brief seems wrong, contradicts the code, or needs a design choice it
  does not make;
- a project limit would be exceeded (simplify, do not compress);
- something new is needed: a dependency, tool, component or custom helper.

Describe the problem, give options and a recommendation. Do not work around
it.

## Report

- Files changed, one line each on what changed.
- Each "Done when" item: met or not, and how you know.
- What you verified by running something versus only by reading code, and
  what you could not verify.
- Deviations from the brief, or "none".
- Stops and questions, or "none".
