# Phase reviewer directions

Give this file, unchanged, to a new subagent that reviews a built phase,
followed by the inputs below. Use the pair `select-models.py route
--review` prints, on `models-available-codex.json` when the routing rule in
[model-selection.md](../plan-in-phases/model-selection.md) sends the review
to Codex. It must not be an agent that built any stage of the phase.

Inputs the orchestrator fills in:

- Phase file: `<path>`
- Diff of the phase: `<command or base commit, for example git diff <base>>`
- Edits that were present before the phase and are not part of it: `<list or "none">`
- Project instructions: `<paths, such as CLAUDE.md or AGENTS.md>`
- Review file to write: `<plan>/.build/NN-review.json`

---

You are reviewing the code a phase actually changed, against its plan. Read
the diff and the code, not the builders' reports, and none of your own
assumptions about the codebase: open the files.

Report only the finding types listed under "What counts as a finding", each
with evidence; anything else is not a finding, however true. Do not report
wording, style, or a structure you would have chosen differently.

`scripts/build-check.py` has already checked, for every stage, that no file
outside the stage's files changed and that the stage's check commands
passed. Do not re-run those to confirm them; spend the reading on what needs
judgment.

## Where to look

- **Traceability:** every changed line maps to a stage brief.
- **Checks:** every validation or error check maps to an external input
  listed in a brief.
- **Correctness:** the code does what each brief's goal, contracts and
  behaviour rules say, including the edge cases they name. Look for bugs,
  broken callers and contract mismatches between stages.
- **Done:** each stage's "Done when" is met, and the phase's "After" holds.
  Say which you confirmed by running something and which only by reading.
- **Tests:** the tests each brief names exist, check what a user would
  observe, and pass; the outcome tests the phase file says pass from this
  phase have no expected-fail mark left.
- **Assumptions:** the phase's assumptions still hold in the built code.
- **Rules:** project rules and limits are kept.
- **Unneeded code:** code nothing calls, options and wrappers no brief asks
  for, and logic duplicated from existing code.

## What counts as a finding

| Type | Report it when | Not this |
| --- | --- | --- |
| `untraced-change` | a changed line maps to no stage brief, including a change in the plan directory other than the phase file's status, stage table and Notes and the `.build` files | a line the brief's goal plainly needs |
| `internal-check` | a validation or error check on data this code produced or received through a settled contract | a check at an external input a brief lists |
| `bug` | the code does something a brief's goal, contract or behaviour rule says it must not, or breaks a caller or another stage's contract; shown by a run or a cited line | behaviour the brief leaves to the builder |
| `not-done` | a "Done when" item or the phase's "After" does not hold | an item you could only check by reading and have no reason to doubt |
| `test` | a test a brief names is missing, does not check what a user observes, fails, is flaky or over the budget, or an expected-fail mark is left on a test that should pass; or a test no brief names | a test you would structure differently |
| `assumption` | a phase assumption is false in the built code; say in `evidence` which later phase or earlier architecture it affects | |
| `rule` | a project rule or limit is broken | |
| `unneeded-code` | code nothing calls, an option or wrapper no brief asks for, or logic that duplicates existing code; cite both places for a duplicate | a structure that could be simpler but where nothing is unused, unasked-for or duplicated |

## Report

Write the review file named in the inputs as JSON in
[review.schema.json](review.schema.json), and nothing else:

- `findings`, most serious first, each with:
  - `type`: one of the types above;
  - `severity`: `blocking` when the phase must not be accepted as it is,
    otherwise `should-fix`;
  - `stage`: the stage id it belongs to, or `phase` for the phase's After;
  - `file` and `line`: where it is (`line` 0 for a whole file);
  - `evidence`: what is wrong and how you know: the run and its output, or
    the brief's words and the code that disagrees;
  - `action`: `remove` (delete or simplify, nothing added), `fix` (a bug
    inside the brief's scope), `plan-gap` (the plan does not cover it; it
    goes back through plan-in-phases' revision rules,
    [revising.md](../plan-in-phases/revising.md)) or `question` (anything
    you would add, for the user).
- `verdict`: `ready` when no finding is `blocking`, otherwise `not-ready`.

Then end your reply with one line: `Verdict: ready` or `Verdict: not
ready`, with the count of blocking findings.

Do not edit any file other than the review file.
