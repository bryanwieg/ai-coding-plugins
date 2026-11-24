# plan.json: field guide

The plan's shared layer is written as `<plan>/plan.json` in
[plan.schema.json](plan.schema.json): what the plan is for, the outcomes
from the grill, the decisions that span phases, the existing interfaces
the stages rely on, and the list of phases. Everything about a stage is in
its stage file ([phase-guide.md](phase-guide.md)), nowhere else.
`scripts/plan-check.py` checks plan.json together with the outline fields
of the stage files (`--outline`) before the rest is written, and again
with every phase; it renders `plan.md` from it. The JSON is the plan for
its whole life: it is kept, and `plan.md` is never edited by hand.
plan.json has no `record`. Examples use an unrelated feature (login rate
limiting) to show form, not content.

**The rule behind every field** is the same as for the stage files: the
plan names a thing only if something outside the stage that builds it uses
it: another stage, existing code, the user, or a file on disk. Those
things are given exactly. Internals (private functions, branches,
statement order) appear nowhere. No string holds code; names, signatures,
routes, keys and literal values in backticks are fine.

## description, goal, why
`description`: a few words naming the plan; it is `plan.md`'s title.
`goal`: one or two sentences on what exists when every phase is built.
`why`: one or two sentences on what the goal is for.

## size
`verdict` `quick` or `full`, the mode `scripts/plan-mode.py score`
printed (see mode-guide.md); `evidence` its total and one line per part
with its score, and any re-score.

## outcomes
The outcomes the grill settled (see grill.md), `id` O1.. in order.
- `title`: a few words naming the outcome.
- `observable`: what a user can do or see afterwards, through which entry
  point (a command, a route, a page, a file), with the concrete values that
  show it. At most 3 sentences.
- `how_to_check`: the run that shows it: the command, request or test
  client call and what its result must contain. If you cannot write it,
  the goal is not understood yet: go back to the grill.
- `sources`: the spec or design lines it comes from: `doc` (`spec` or
  `design`), `section`, and `quote`, the words copied exactly; the script
  looks for them.
- Good: observable "six failed logins from one address within 60 s get
  HTTP 429 on the sixth"; how_to_check "test client POSTs /login six times
  with a wrong password from 10.0.0.1; the sixth answer is 429".
- Bad: "rate limiting works well"; "the limiter uses a deque".

Every outcome needs at least one outcome test. The tests are not listed
here: the stage that writes one names the outcome in its `tests` (see
phase-guide.md), and the script builds the outcome-test tables from those.

## decisions
Every decision that spans phases, `id` D1.. in order: `text` the decision,
`reason` why, `phases` the phase numbers it affects (or `all`); it is
added to those phases' Notes when rendered. A departure from the spec or
design names the words it departs from in `departs_from` (`doc`,
`section`, `quote`, as in an outcome's sources) and sets `user_answer`:
`given` when the user agreed in the grill, `assumed` when the user could
not be asked. A decision that affects one phase only goes in that phase's
`notes`.

## existing
Every interface that is already in the repository and that a stage relies
on, listed once. Interfaces the plan builds are not listed here: the stage
that builds one holds it in its `provides`.
- `kind` as in [phase-guide.md](phase-guide.md), `name` one interface per
  name; no stage may provide the same name.
- `shape`: the exact outside view, within the limits phase-guide.md gives
  per kind.
- `path`: the file that holds it, optionally `path:line`; it must exist.
- A stage that relies on it names it in its `uses`.
- Good: `{"kind": "route", "name": "login", "shape": "POST /login form
  user, password; 302 to next on success, 401 on a wrong password",
  "path": "app/views.py:40"}`
- Bad: an entry for a private helper; an entry no stage uses.

## docs
The paths of the `spec` and the `design`, relative to the repository, when
they exist. The script checks every quote against them.

## phases
In build order: `phase` the number, 01.. ; `dir` the phase's folder,
`NN-short-name` in lower case, digits and hyphens, starting with that
number; `name` the phase's title; `kind` per phase-kinds.md (`behaviour`
for a phase that is one behavior target). Each folder holds the phase's
`phase.json` and one stage file per stage.
