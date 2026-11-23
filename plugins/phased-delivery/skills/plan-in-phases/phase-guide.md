# Phase JSON: field guide

Each phase is written as `<plan>/.plan/NN.json` in
[phase.schema.json](phase.schema.json); `scripts/plan-check.py` checks it
against this guide and against `plan.json`, and renders it into
`NN-name.md` in the layout of [phase-file-template.md](phase-file-template.md).
Stage order, titles, the outcome-test rows and the cross-phase decisions
come from `plan.json`; the phase JSON does not repeat them. Each field
below has its directions, its limit and an example. The examples use an
unrelated feature (login rate limiting in a web app) so they show form,
not content.

**The one rule behind every field:** the plan names a thing only if
something outside its stage uses it: another stage, a test, existing code,
the user, or a file on disk. Those things are given exactly. Anything only
the stage's own code uses (private functions, local variables, branches,
loops, the order of statements inside a function) has no field and does not
appear anywhere. The builder writes it. Write decisions, not instructions
to decide: "decide how X works" is unfinished planning when X is seen
outside the stage; when X is seen only inside it, leave it out entirely.

The phase file stands alone: never cite `.plan/` or the ids `plan.json`
uses (C1, D3); name the contract or decision instead. Cite the
repository's code, spec and design.

No string holds code: no code blocks, and no expressions such as
`a.get(b) or c`, `if x is None`, `return foo(bar)`. Names, signatures,
routes, keys and literal values in backticks are fine.

## before / after
What exists when the phase starts and ends, as things the user can inspect.
At most 6 sentences each.
- Good: "After: with auth on, five failed logins from one address within a
  minute get 429 for the rest of that minute; the counter is in memory."
- Bad: listing which functions call which, or how the counter is stored
  line by line.

## assumptions
One sentence each. `verified`: evidence is the file:line or symbol read.
`open`: evidence says why it cannot be checked yet, how and when to check
it, and what changes if it is wrong.

## test_budget
The project's test time budget for this phase (see test-planning.md).

## stages[].id and goal
`id` as in `plan.json`, in the same order. `goal`: one sentence, at most
250 characters: what is true when done.

## stages[].context
- `builds_on`: what earlier stages or phases built that this one uses, one
  line each, naming the contract.
- `code_read`: existing code this stage relies on, read while planning.
  `where` is `path:line` or `path:start-end`; `shows` is a few words that
  appear on those lines (a name, a key, a signature fragment), so the
  script can confirm the citation; `fact` is one sentence of what is there
  that matters. At most 8.
- `design`: spec or design sections that apply: `doc` (spec or design),
  `section`, and `quote`, the words that matter copied exactly. The script
  looks for the quote in the document; a paraphrase is not a quote, so
  write it in `builds_on` or a behaviour rule instead. At most 4.

## stages[].contracts
Every interface, format or name this stage provides to, or uses from,
something outside it. `shape` is the exact outside view, nothing more:

| kind | shape holds |
| --- | --- |
| function, class | full signature with types: `check_rate(addr: str, now: float) -> bool` |
| route | method, path, inputs, every status and its body: `POST /login` form `user`, `password`; 302 to `next` on success, 429 Problem Details `{"title": "TooManyAttempts"}` when limited |
| format | the fields, types and an example value |
| config | key, type, default, where it is read |
| error | the exception or status, when it is raised, what the caller sees |
| event, cli | name, arguments, exit codes, output |
| test-helper | signature of a helper tests share |
| other | anything else seen outside the stage; `other_reason` says what it is |

One contract per name: `A / B` is two contracts. `shape` limits, in
characters: function, class, error, test-helper 200; config, event, cli
300; format 400; route 500. A shape that needs more is describing
internals: move what others observe into `behaviour`, and drop the rest.
`other` is for a real interface no kind fits; the checker reports every use.
Every contract `plan.json` says this stage provides appears here under the
same name.

`counterparts` must name who is on the other side: for `provides`, the
stage ids, existing non-test code, `user` or `disk` that use it; for
`uses`, the stage id or existing file that provides it. Tests do not count
as counterparts (except for `test-helper`): what a test observes goes in
`behaviour`, and the test in `tests`. A thing with no counterpart outside
this stage other than tests is internal: leave it out. A function's
decision rules are not a contract, even when tests check them; they are
`behaviour`.
- Good: `{"kind": "function", "name": "check_rate", "shape":
  "check_rate(addr: str, now: float) -> bool; True when the attempt is
  allowed", "direction": "provides", "counterparts": ["02.1", "app/views.py"]}`
- Bad: a contract for `_prune_old(window)`, a private helper only
  `check_rate` calls; or a shape that says how `check_rate` loops over the
  timestamps.

## stages[].files
Exactly the paths and actions `plan.json` gives the stage. `role` is one
sentence naming the contracts the file holds afterwards.
- Good: `{"path": "app/ratelimit.py", "action": "create", "role":
  "holds check_rate and the RateLimited error"}`
- Bad: a role listing the edits inside the file step by step.

## stages[].behaviour
The behavior other code, tests or the user can observe, as given / when /
then, edge cases included. At most 8 items. Each item is a rule a test
could check, not a step of the code.
- Good: given 5 failed attempts from one address in the last 60 s, when a
  sixth arrives, then `check_rate` returns False and the login view answers
  429.
- Bad: "then iterate the deque, pop entries older than now - 60, compare
  len to 5".

## stages[].external_inputs
Trust boundaries this stage may check: data from something this code does
not control. `source`, the `check`, and what happens `on_failure`. An empty
list means no checks. Data from this code or a settled contract gets none.

## stages[].tests
Tests other than the stage's outcome tests, which the rendered brief lists
from `plan.json`: tests the stage must keep passing, deletes, or writes
beyond the outcome tests, each with its kind (outcome, integration, unit)
and what it proves. A unit test also says in `why_unit` why a run-through
cannot cover it.

## stages[].done_when
Observable properties of the changed files: commands that pass, behavior a
test shows. At most 6. A command must exist in the project (a make target,
a script in the package file); cite where it is defined in `code_read`.

## stages[].out_of_scope
Nearby things the stage must not change. At most 5.

## stages[].model_basis
Scores 0–2 per model-selection.md; the script adds them up and picks the
tier with its overrides. For J in this format: internals are always the
builder's, so J is 1, unless the stage copies a near-identical example the
context names (0). A J of 2 means the brief leaves an approach or
something other code sees open: settle it in contracts and behaviour
instead.

## notes
Decisions and adjustments that affect only this phase, one line each, with
the reason and the date. Cross-phase decisions live in `plan.json` and are
added to every phase they name when rendered.
