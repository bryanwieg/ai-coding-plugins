# plan.json: field guide

The plan's shared layer is written as `<plan>/.plan/plan.json` in
[plan.schema.json](plan.schema.json): the outcomes from the grill, the
decisions that span phases, the contract registry, the outcome tests, and
the phases with their stages. `scripts/plan-check.py` checks it before any
phase JSON is written (`--outline`), and again with every phase. Examples
use an unrelated feature (login rate limiting) to show form, not content.

**The rule behind every field** is the same as for phase files: the plan
names a thing only if something outside the stage that builds it uses it:
another stage, existing code, the user, or a file on disk. Those things are
given exactly. Internals (private functions, branches, statement order)
appear nowhere. No string holds code; names, signatures, routes, keys and
literal values in backticks are fine.

## size
`verdict` full or small per SKILL.md "Size the plan from the code";
`evidence` one line per criterion that decides it, citing the files and
users found.

## outcomes
The outcomes the grill settled (see grill.md), O1.. in order.
- `observable`: what a user can do or see afterwards, through which entry
  point (a command, a route, a page, a file), with the concrete values that
  show it. At most 3 sentences.
- `how_to_check`: the run that shows it: the command, request or test
  client call and what its result must contain. If you cannot write it,
  the goal is not understood yet: go back to the grill.
- `sources`: the spec or design lines it comes from: `doc`, `section`, and
  `quote`, the words copied exactly; the script looks for them.
- Good: observable "six failed logins from one address within 60 s get
  HTTP 429 on the sixth"; how_to_check "test client POSTs /login six times
  with a wrong password from 10.0.0.1; the sixth answer is 429".
- Bad: "rate limiting works well"; "the limiter uses a deque".

## decisions
Every decision that spans phases, D1.. in order: `text` the decision,
`reason` why, `phases` the phase numbers it affects (or `all`); it is
added to those phases' Notes when rendered. A departure from the spec or
design names the words it departs from in `departs_from` and sets
`user_answer`: `given` when the user agreed in the grill, `assumed` when
the user could not be asked. A decision that affects one phase only goes in
that phase's `notes`.

## contracts
The registry: every interface one stage provides and another stage or
existing code uses, and every existing interface a stage relies on.
- `id` C1.., `kind` as in [phase-guide.md](phase-guide.md), `name` one
  contract per name.
- `shape`: the exact outside view. Limits in characters: function, class,
  error, test-helper 200; config, event, cli 300; format 400; route 500.
  A longer shape is describing internals.
- `provided_by`: the stage id that builds it, or `existing:<path>` for code
  already in the repository (the path must exist).
- `used_by`: stage ids, existing non-test files, `user` or `disk`. Tests do
  not count, except for `test-helper`. Every stage listed here must list
  the contract in its `uses`, and the other way round; the script checks
  both directions and the build order (a provider stage comes before every
  user).
- Good: `{"id": "C4", "kind": "function", "name": "check_rate", "shape":
  "check_rate(addr: str, now: float) -> bool; True when allowed",
  "provided_by": "02.1", "used_by": ["03.1"]}`
- Bad: a contract for a private helper; `used_by` naming only a test file.

## outcome_tests
Every outcome with at least one row: `test` as `path::name` (see
test-planning.md), `written_in` and `passes_from` stage ids. A test is
written once and made to pass once; `written_in` is not after
`passes_from`. The rendered phase files list these rows; stage briefs do
not repeat them.

## phases
In build order, numbered 01.. . `file` `NN-short-name.md`, `kind` per
phase-kinds.md (`behaviour` for a phase that is one behavior target).

## phases[].stages
In build order within the phase.
- `id` NN.n, `title` a few words.
- `files`: every path the stage may change, with `create`, `edit` or
  `delete`. Edit and delete paths must exist (or be created by an earlier
  stage); create paths must not. Stages that run in parallel share no
  file.
- `provides` / `uses`: contract ids, matching the registry.
- `order`: `first`, `after NN.n` or `parallel with NN.n`, naming a stage
  listed before it. Order a stage after the stage it depends on, not after
  the previous one by habit; the script warns when a stage is ordered
  after one it uses nothing from.
