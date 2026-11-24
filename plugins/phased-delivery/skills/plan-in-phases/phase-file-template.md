# Rendered plan layout

`scripts/plan-check.py` renders both files below from the plan's JSON:
`<plan>/plan.md` from `plan.json` and the stage files, and
`<plan>/NN-name/phase.md` from that folder's `phase.json` and stage files
(see [plan-guide.md](plan-guide.md) and [phase-guide.md](phase-guide.md),
which say what goes in each field). Neither is edited by hand: change the
JSON and run the script again.

## plan.md

```
# Plan: <description>

Rendered by plan-check.py from plan.json and the stage files; never edited by hand.

Goal: what exists when every phase is built
Why: what the goal is for

## Outcomes
- O1 <title>: <what a user can observe> Check: <the run that shows it>

## Decisions
- D1 (phases 01, 02): <decision> Reason: <why>

## Contracts
- <kind> `<name>` (provided by NN.n; used by NN.n, user): <shape>

## Existing interfaces
- <kind> `<name>` (`<path>`; used by NN.n): <shape>

## Phases

| Phase | Kind | Status |
| --- | --- | --- |
| [01 <name>](01-<name>/phase.md) | skeleton | planned |
```

## phase.md

```
# Phase NN: <name>

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](../models.md).
Status: planned | in progress (stages done: …) | halted: <reason> | built <commit>
Before: what exists when this phase starts
After: what exists when it ends (what the user will inspect)

Role: the phase's part in the plan
Why: why the plan needs it, and why here
How: the approach in outline

## Assumptions
- Verified: <assumption> (checked in <file/symbol>)
- Open: <assumption>, why it cannot be checked yet, how and when to check it,
  and what changes if it is wrong

## Size

Quick plan:
- <the score's evidence; this section appears in a quick plan only>

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

## NN.1 <title>
<stage brief>

## Notes
- Decision or adjustment, one line each, with its reason and date; then
  the plan's cross-phase decisions that name this phase.
```

`Tier` comes from scoring the stage with
[model-selection.md](model-selection.md); the brief's `Model basis` line
shows the scores. Plans record tiers, never model names or effort levels;
`models.md` maps each tier to a current model and thinking level, chosen
from the benchmark report. The implementer re-scores and makes the final
choice at dispatch. `Order` says what must come first and what may run in
parallel. The `Status` column and line come from each file's `record`,
which the build scripts write: a stage is `planned`, `in progress`, `done`
or `reopened` (its brief's `revision` was raised after it was built).

## Stage brief

A stage is one focused piece of work that a fresh agent can complete with only
`phase.md` and the documents it links. Keep it small enough that an agent
holds all of it in mind: one purpose, a handful of files. Split a stage that
holds independent responsibilities.

```
Goal:            one sentence: what is true when done
Context:         what earlier phases and stages built that this uses, the
                 existing code it relies on (files and lines read while
                 planning), and the spec and design words that apply, quoted
Contracts:       every interface, format or name it provides to or uses from
                 something outside the stage, exactly, with who is on the
                 other side: from its `provides` and `uses`, and the
                 providers' shapes
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
Checks:          the commands that show it is done
Out of scope:    nearby things it must not change
Model basis:     scores per model-selection.md, e.g.
                 J1 F1 R1 C1 K0 P0 V1 S0 = 5 -> middle
```

Write decisions, not instructions to decide:
"Decide how X works" is unfinished planning when X is seen outside the
stage. The brief settles everything another stage, existing code or the
user sees; how the code works inside the stage is the builder's, and the
brief holds no code and no statement-level steps.
