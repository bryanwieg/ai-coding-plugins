# Phase file layout

```
# Phase NN: <name>

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned | in progress (stages done: …) | built <commit> | reviewed by user
Before: what exists when this phase starts
After: what exists when it ends (what the user will inspect)

## Assumptions
- Verified: <assumption> (checked in <file/symbol>)
- Open: <assumption>, why it cannot be checked yet, how and when to check it,
  and what changes if it is wrong

## Outcome tests
Budget: <the project's, or ~1 min per stage, a few minutes for the suite>

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| <what a user can observe> | <test path::name> | NN.n | NN.n |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| NN.1 | … | middle | first | planned |
| NN.2 | … | small | parallel with NN.3 | planned |

## NN.1 <name>
<stage brief>

## Notes
- Decision or adjustment, one line each, with its reason and date.
```

`Tier` comes from scoring the stage with
[model-selection.md](model-selection.md); the brief's `Model basis` line
shows the scores. Plans record tiers, never model names or effort levels;
`models.md` maps each tier to a current model and thinking level, chosen
from the benchmark report. The implementer re-scores and makes the final
choice at dispatch. `Order` says what must come first and what may run in
parallel. The implementer updates the `Status`
columns and line; the planner keeps them `planned`.

## Stage brief

A stage is one focused piece of work that a fresh agent can complete with only
the phase file and the documents it links. Keep it small enough that an agent
holds all of it in mind: one purpose, a handful of files. Split a stage that
holds independent responsibilities.

```
Goal:            one sentence: what is true when done
Context:         what earlier phases and stages built that this uses, the
                 existing code it relies on (files and lines read while
                 planning), and the spec and design words that apply, quoted
Contracts:       every interface, format or name it provides to or uses from
                 something outside the stage, exactly, with who is on the
                 other side
Files:           exact paths it may create, change or delete, each with what
                 it holds afterwards; nothing else
Behaviour:       what other code, tests or the user can observe, as given /
                 when / then rules, edge cases included
External inputs: trust boundaries it may check; "none" means no checks
Tests:           the outcome tests it writes or turns on, then any other
                 tests it writes, keeps passing or deletes, each with its
                 kind (outcome, integration, unit) and what it proves; a
                 unit test also says why a run-through cannot cover it
Done when:       observable properties of the changed files
Out of scope:    nearby things it must not change
Model basis:     scores per model-selection.md, e.g.
                 J1 F1 R1 C1 K0 P0 V1 S0 = 5 -> middle
```

`scripts/plan-check.py` renders this layout from the plan's JSON (see
[plan-guide.md](plan-guide.md) and [phase-guide.md](phase-guide.md), which
say what goes in each field). Write decisions, not instructions to decide:
"Decide how X works" is unfinished planning when X is seen outside the
stage. The brief settles everything another stage, existing code or the
user sees; how the code works inside the stage is the builder's, and the
brief holds no code and no statement-level steps.
