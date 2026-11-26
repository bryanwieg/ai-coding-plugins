# phase.json and the stage files: field guide

Each phase is a folder `<plan>/NN-name/` holding `phase.json` in
[phase.schema.json](phase.schema.json) and one stage file per stage,
`NN.n.json` in [stage.schema.json](stage.schema.json).
`scripts/plan-check.py` checks them against this guide and against
`plan.json`, and renders the folder's `phase.md` in the layout of
[phase-file-template.md](phase-file-template.md). The JSON is the plan for
its whole life: it is kept, and `phase.md` is never edited by hand. Each
fact has one home: the cross-phase decisions and the existing interfaces
are in `plan.json`, and a stage's order, files, contracts and tests are in
its stage file only. Each field below has its directions, its limit and an
example. The examples use an unrelated feature (login rate limiting in a
web app) so they show form, not content.

**Both kinds of file have two parts, `brief` and `record`.** Planning and
revising write only `brief`. The planner never writes `record`: it leaves
it `{}`, and only the build scripts fill it (see "record" at the end).

**The one rule behind every field:** the plan names a thing only if
something outside its stage uses it: another stage, a test, existing code,
the user, or a file on disk. Those things are given exactly. Anything only
the stage's own code uses (private functions, local variables, branches,
loops, the order of statements inside a function) has no field and does not
appear anywhere. The builder writes it. Write decisions, not instructions
to decide: "decide how X works" is unfinished planning when X is seen
outside the stage; when X is seen only inside it, leave it out entirely.

The rendered phase file stands alone: never cite the decision ids
`plan.json` uses (D3); name the decision instead. Cite the repository's
code, spec and design.

No string holds code: no code blocks, and no expressions such as
`a.get(b) or c`, `if x is None`, `return foo(bar)`. Names, signatures,
routes, keys and literal values in backticks are fine. `checks` holds
commands and a contract's `shape` holds signatures; both are exempt.

# phase.json: brief

## role, why, how
One or two sentences each. `role`: the phase's part in the plan, what it
adds to the phases before it. `why`: why the plan needs this phase, and
why here in the order. `how`: the approach in outline, as the stages take
it; no internals.

## before / after
What exists when the phase starts and ends, as things the user can inspect.
At most 6 sentences each.
- Good: "After: with auth on, five failed logins from one address within a
  minute get 429 for the rest of that minute; the counter is in memory."
- Bad: listing which functions call which, or how the counter is stored
  line by line.

## assumptions
`text`: one sentence each. `status` `verified`: `evidence` is the
file:line or symbol read. `status` `open`: `evidence` says why it cannot
be checked yet, how and when to check it, and what changes if it is wrong.

## test_budget
The project's test time budget for this phase (see test-planning.md).

## notes
Decisions and adjustments that affect only this phase, one line each, with
the reason and the date. Cross-phase decisions live in `plan.json` and are
added to every phase they name when rendered.

# Stage file: brief

One file per stage, named by the stage's id: `NN.n.json` in the folder of
phase NN, numbered from 1 in build order. `--outline` checks the first
seven fields below (`revision` to `uses`) before the rest is written.

## revision
A number. Planning starts every stage at 1. Every later change to a
brief, prose alone included, raises it by one; the script keeps a hash of
each brief that was built and reports a brief that changed without a
higher `revision`.

## title
A few words; it heads the stage's brief in `phase.md`.

## order
`first`, `after NN.n` or `parallel with NN.n`, naming a stage that comes
before it. Order a stage after the stage it depends on, not after the
previous one by habit; the script warns when a stage is ordered after one
it uses nothing from and shares no file with.

## lines
Your estimate of lines added plus removed in the stage's non-test files:
`under 30`, `30-150` or `over 150`. A quick plan is re-scored from these
(mode-guide.md, "Re-scoring").

## files
Every path the stage may change, with `action` `create`, `edit` or
`delete`. Edit and delete paths must exist (or be created by an earlier
stage); create paths must not. Stages that run in parallel share no file.
`role` is one sentence naming the contracts the file holds afterwards.
- Good: `{"path": "app/ratelimit.py", "action": "create", "role":
  "holds check_rate and the RateLimited error"}`
- Bad: a role listing the edits inside the file step by step.

## provides
Every interface, format or name this stage builds that something outside
it uses. The contract lives here, with its provider, and nowhere else; the
script builds the registry in `plan.md` and each brief's Contracts lines
from these lists. `shape` is the exact outside view, nothing more:

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

One contract per `name`: `A / B` is two contracts, and no two stages
provide the same name. `shape` limits, in characters: function, class,
error, test-helper 200; config, event, cli 300; format 400; route 500. A
shape that needs more is describing internals: move what others observe
into `behaviour`, and drop the rest. `other` is for a real interface no
kind fits; the checker reports every use.

`used_by` names only the users outside the plan's stages: existing
non-test files, `user` or `disk`. Stages that use the contract are not
listed here; they name it in their `uses`, and the script derives them.
Tests do not count as users (except for `test-helper`): what a test
observes goes in `behaviour`, and the test in `tests`. A thing no stage
uses and nothing in `used_by` uses other than tests is internal: leave it
out. A function's decision rules are not a contract, even when tests check
them; they are `behaviour`.
- Good: `{"kind": "function", "name": "check_rate", "shape":
  "check_rate(addr: str, now: float) -> bool; True when the attempt is
  allowed", "used_by": ["app/views.py"]}`
- Bad: a contract for `_prune_old(window)`, a private helper only
  `check_rate` calls; or a shape that says how `check_rate` loops over the
  timestamps.

## uses
The names of the contracts this stage relies on: each is a name in an
earlier stage's `provides` or in `plan.json`'s `existing`. The provider
stage is built before every stage that uses it; the script checks both.

## goal
One sentence, at most 250 characters: what is true when done.

## context
- `builds_on`: what earlier stages or phases built that this one uses, one
  entry each: `source` the stage id, `what` a line naming the contract.
- `code_read`: existing code this stage relies on, read while planning.
  `where` is `path:line` or `path:start-end`; `shows` is a few words that
  appear on those lines (a name, a key, a signature fragment), so the
  script can confirm the citation; `fact` is one sentence of what is there
  that matters. At most 8.
- `design`: spec or design sections that apply: `doc` (`spec` or
  `design`), `section`, and `quote`, the words that matter copied exactly.
  The script looks for the quote in the document; a paraphrase is not a
  quote, so write it in `builds_on` or a behaviour rule instead. At most 4.

## behaviour
The behavior other code, tests or the user can observe, as `given` /
`when` / `then`, edge cases included. At most 8 items. Each item is a rule
a test could check, not a step of the code.
- Good: given 5 failed attempts from one address in the last 60 s, when a
  sixth arrives, then `check_rate` returns False and the login view answers
  429.
- Bad: "then iterate the deque, pop entries older than now - 60, compare
  len to 5".

## external_inputs
Trust boundaries this stage may check: data from something this code does
not control. `source`, the `check`, and what happens `on_failure`. An empty
list means no checks. Data from this code or a settled contract gets none.

## tests
Every test the stage writes, turns on, keeps passing or deletes: `test` as
`path::name` (see test-planning.md), `kind` (`outcome`, `integration`,
`unit`), `action` (`writes`, `turns on`, `keeps passing`, `deletes`) and
`proves`, what it proves. A unit test also says in `why_unit` why a
run-through cannot cover it.

An outcome test is written once and made to pass once. The stage that
writes it sets `outcome` to the id of the outcome in `plan.json` it shows.
When a later stage makes it pass, that stage lists the same `test` with
action `turns on`; otherwise it passes from the stage that writes it. The
script builds each phase's outcome-test table from these entries and
reports an outcome with no test.

## done_when
Observable properties of the changed files: commands that pass, behavior a
test shows. At most 6.

## checks
The commands that show the stage is done, one per entry, exactly as they
are run from the repository root. A command must exist in the project (a
make target, a script in the package file); cite where it is defined in
`code_read`. An empty list means nothing is run.

## out_of_scope
Nearby things the stage must not change. At most 5.

## model_basis
The scores `J`, `F`, `R`, `C`, `K`, `P`, `V` and `S`, each 0–2 per
model-selection.md; the script adds them up and picks the tier with its
overrides. For J in this format: internals are always the builder's, so J
is 1, unless the stage copies a near-identical example the context names
(0). A J of 2 means the brief leaves an approach or something other code
sees open: settle it in `provides` and `behaviour` instead.

## session_only
Optional. `true` for a stage that must be built in the session (see
"Session-only stages" in model-selection.md), such as one that must write
outside the repository. Leave it out otherwise.

# record

Never written by planning or revising: write `"record": {}` in
`phase.json` and in every stage file. The fields are listed here so that a
reader of a built plan knows them.

- `phase.json`: `start_commit`, the commit the build started from;
  `preexisting`, the paths with edits present before the build or added
  between runs; `runs`, the revise and review attempts; `findings`, the
  review's findings by `index` with a `status` (`open`, `fixed`, `asked`, `answered`); `halt`,
  why the build stopped, or null; `built`, the commit that finished the
  phase, or null.
- Stage file: `revisions`, the hash of the brief at each revision that was
  built; `attempts`, one entry per build attempt with its `revision`, its
  number `n`, whether it was a `fix`, the `tool`, `model` and `effort`,
  the `exit` code, `tokens`, `cost`, `cap`, `tool_calls`, whether it was
  `premium`, its `result` (`accepted`, `failed`, `stopped`, `error`,
  `rejected`) and `why`, and its `commit`; `commit`, the latest accepted
  commit of the stage.
