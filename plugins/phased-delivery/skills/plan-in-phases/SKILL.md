---
name: plan-in-phases
description: "Turn an approved specification and design into a complete phased implementation plan: one self-contained NN-name.md file per phase, each split into stage briefs a fresh agent can build without further decisions. Planning only; writes no code. Use whenever the user asks to plan, break down, phase, stage or sequence a feature, migration, rewrite or other multi-step change (\"plan this\", \"break this into phases\", \"write the implementation plan\", \"how should we build this in stages\"), or to review, fix or rework an existing phased plan or revise a phase after implementation finds gaps. Use proactively, without being asked, before writing code for any change that touches several files, a shared contract or the architecture; it measures from the code whether a small plan is enough, so do not skip it because a change seems small. Not for one-file edits that change no contract, and not for building the plan; that is implement-in-phases."
---

# Plan in phases

Turn the approved specification and design into the complete plan in one pass:
one file per phase, every stage detailed enough to build. This skill writes
documents only; [implement-in-phases](../implement-in-phases/SKILL.md) builds them.
Anyone implementing the plan, agent or person, must use the
implement-in-phases skill; every phase file says so in its header.

The user approves the specification and the design. Before planning, grill
the user on them (see Grill the spec and design); that is the time to ask.
After it, settle every remaining decision with the context at hand and write
it down. Ask the user again only when planning, review or implementation
shows the specification or design is wrong, incomplete or contradictory, or
that the work needs something the design lacks (a new component, dependency,
tool or external system). Give options and a recommendation.

## Grill the spec and design

Before sizing or phasing anything, interview the user about the specification
and design until you both understand them the same way. Planning then rests
on what the user means, not on what the documents happen to say.

- Walk the design's decision tree branch by branch. Resolve the decisions
  other decisions depend on first.
- Ask one question at a time. Give your recommended answer and why, with the
  options when there are real alternatives.
- If reading the code can answer a question, read the code instead of
  asking. Ask only what the code cannot settle: intent, priorities, scope,
  trade-offs, and behavior the documents leave open.
- Push on the weak spots: vague requirements, unstated edge cases and
  failure behavior, what is out of scope, how success is judged, what
  existing behavior and data must keep working, and anything the code shows
  differs from the design.
- Do not ask about what the planner decides (file layout, stage split,
  internal structure) unless the spec or design constrains it.

Raise your own concerns too, not only questions. If you see a security
problem, a fundamental architectural flaw, an approach that will not meet the
spec's goals, or a much simpler way to meet them, say so plainly: what the
concern is, the evidence (code you read, a concrete failure case), and what
you would do instead. Push back once, clearly, then let the user decide. If
they keep their approach, plan it as they decided and record the concern and
their decision in the affected phase's Notes. Do not raise concerns about
taste or style, and do not re-argue a settled point unless new evidence
appears.

Stop when no question or concern is left whose answer would change the plan.
A small change may need only a few questions; ask none just to fill the step.

Record each answer where planning will use it: as a decision in the Notes of
the phase it affects, or, if it changes the specification or design, in that
document with the user's agreement.

## Read the code before deciding

Base every planning decision on the repository as it is now, read during this
planning session. Memory, earlier conversations, summaries, READMEs,
architecture overviews and the design document's description of existing code
may all be stale or wrong. Use them to know where to look, never as the basis
for a decision.

- Before planning a phase, read the components it touches: the files it will
  change, the code that calls them, the code they call, and the existing
  interfaces, data formats, configuration and tests it depends on.
- Before writing a contract that uses existing code, open that code and copy
  the real names, signatures, paths and formats. Do not write them from memory
  or guess them from naming conventions.
- Do this for every phase, not once at the start. Later phases often touch
  components the early reading never opened.
- When the code disagrees with the design, memory or an overview, the code is
  the truth. If the disagreement changes the design, ask the user (see above).
- If a decision cannot be checked because the code does not exist yet, it must
  rest on a contract defined earlier in this plan. Say which one.
- Write down what you verified: in each stage's Context, cite the files and
  symbols you read, so the implementer and the reviewer can see the decision
  rests on real code.

## Size the plan from the code

Every plan starts as a full plan. A plan may be small only after reading the
code proves it, never because the change feels small or familiar. Measure
first:

1. List every file the change will create or edit, tests included.
2. For every function, type, format or setting it changes, search for all
   its users and list them. Do not reason about who "probably" uses it.
3. Write down each assumption the change rests on and check it in the code.

The plan is small only if every one of these holds, each with evidence from
that reading:

- About five files or fewer change, inside one component or module.
- No contract used outside those files changes: no public or shared
  signature, data or file format, schema, configuration key, command-line
  interface, event, or persisted data.
- No architecture changes: no new component, service, layer or dependency,
  and no responsibility moves between components.
- No migration, no data written by older versions to handle, and no existing
  path to retire or switch over.
- No trust boundary is added or changed.
- Every assumption is verified now; none is open.
- The work fits one phase of at most three stages.

If any item fails or cannot be shown, write a full plan. Being unable to list
the users of something, or needing words like "probably" or "should be fine",
means the measuring is not done.

A small plan is lighter in structure only:

- One phase file, `01-short-name.md`, with the usual layout. It need not
  follow the skeleton-to-cutover progression.
- It adds a `Size` section listing the files, the users searched for and
  found, and each criterion above with its evidence.
- Reading the code, the Assumptions section, complete stage briefs and the
  plan review are never skipped. The review uses a fresh subagent, who also
  re-measures the size: re-counts the files, re-searches the users and
  rechecks each criterion. A small plan often needs only one review round.

If the reviewer, later planning or implementation finds that any criterion
fails, the plan is no longer small: rewrite it as a full plan before building
further.

## Compose the phases from high level to narrow

Work starts broad and narrows. A useful progression for one system:

1. **Skeleton:** the files, entry points and wiring exist, inactive or stubbed.
2. **Roles and interfaces:** signatures, inputs and outputs, data formats and
   mock bodies, so the whole flow can be traced end to end.
3. **Internals:** the real logic, one behavior or component at a time.
4. **Integration and cutover:** switch the new work on, retire what it
   replaces, update documentation.

This is guidance, not a rule. When several systems must be built, give each its
progression and order or interleave them by dependency. A phase may instead be
one behavior target when that is the clearer unit. Choose phases by
responsibility and dependency, never to reach a count. Each phase leaves the
repository in a coherent state that the user can inspect at its end.

### Planning each kind of phase

Each kind of phase settles different decisions, reads different code and
rests on different assumptions. Name that phase's assumptions in its file,
check them against the code, and record what could not be checked yet (see
Assumptions and Notes in the phase file layout).

**Skeleton.**
- Settle: where every new file lives, how it is named, how it is registered
  or wired (entry points, routes, configuration, build and package files), and
  how it stays inactive until cutover (flag, unregistered, unreachable).
- Read: the project's layout and conventions, the registration and build
  files the new pieces join, and neighbors of the same kind to copy their
  pattern.
- Assumptions to check: where things belong, that the wiring point exists
  and works as believed, that inactive code really has no effect.
- Done when: the files exist and are wired, the project builds and its
  existing tests pass, and behavior is unchanged.

**Roles and interfaces.**
- Settle every contract here: signatures, inputs and outputs, data formats,
  error cases at trust boundaries, and which component owns what. Later phases
  consume these contracts; they do not invent new ones.
- Read: every existing interface the new code calls or is called by, the real
  data formats it reads or writes, and existing types it should reuse.
- Assumptions to check: what existing callers and callees actually accept and
  return, how data really looks (sample it where possible), that the
  responsibility split covers every requirement once.
- Done when: the whole flow traces end to end through mock bodies returning
  fixed or pass-through data, and the contracts are written in the code
  itself, not only in the plan.

**Internals.**
- Settle, per stage, one behavior behind a fixed contract: the algorithm or
  approach, the existing code it reuses, edge cases it handles, and the tests
  that prove it.
- Read: the contract and mock it replaces, the code it calls, existing
  helpers that already do part of the job, and the tests nearby.
- Assumptions to check: that the contract is sufficient for the real logic,
  that existing helpers behave as their names suggest, performance or data
  size limits that matter.
- Done when: the mock is replaced, the behavior's tests pass, and the
  contract is unchanged. If the real logic needs a different contract, that
  is a revision of the interfaces phase, not a local change.

**Integration and cutover.**
- Settle: how the new work is switched on, what old code, configuration and
  data it replaces and how those are retired or migrated, the order of
  switching so nothing is left half-working, how to undo it if required, and
  which documentation changes.
- Read: every caller of what is being replaced, configuration and deployment
  files, existing migrations, and the documentation that describes the old
  behavior.
- Assumptions to check: that every user of the old path is found, that data
  written by older versions is handled, that nothing outside the repository
  depends on what is removed.
- Done when: the new path is the only path, the old one is gone or
  deliberately kept with a reason, the full test suite passes, and the
  documentation matches.

## Write every phase file

Name the files `NN-short-name.md` in the plan directory, numbered in build
order. There is no separate index: each file stands alone and carries its own
status. The shared files are `models.md`, the plan's model table, and the
`models-available.json` it is generated from. Write
them top-down:

1. List the models the running tool offers now in `models-available.json`
   and generate `models.md` with the plugin's `scripts/select-models.py`
   (see [model-selection.md](model-selection.md)). Never write either from
   memory. When the session can also build with Codex, do the same for
   Codex in `models-available-codex.json` and `models-codex.md` (see
   "Builders in another tool" there).
2. Create all phase files with their role and what exists before and after.
3. Define every stage of every phase by goal, files and contracts.
4. Fill in each stage brief completely.

Before each step, for each phase, read the current code that phase touches
(see Read the code before deciding).

At each step, define all related parts and their contracts before going deeper
into one of them, including callers and consumers in other phases.

### Phase file layout

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

### Stage brief

A stage is one focused piece of work that a fresh agent can complete with only
the phase file and the documents it links. Keep it small enough that an agent
holds all of it in mind: one purpose, a handful of files. Split a stage that
holds independent responsibilities.

```
Goal:            one sentence: what is true when done
Context:         what earlier phases and stages built that this uses, the
                 existing code it relies on (files and symbols read while
                 planning), and the design decisions that apply (link
                 spec/design sections; quote the few lines that matter)
Contracts:       interfaces, formats and names it must provide or use, exactly
Files:           exact paths it may create or change; nothing else
Work:            the concrete changes, in order
External inputs: trust boundaries it may check; "none" means no checks
Done when:       observable properties of the changed files
Out of scope:    nearby things it must not change
Model basis:     scores per model-selection.md, e.g.
                 J1 F1 R1 C1 K0 P0 V1 S0 = 5 -> middle
```

Write decisions, not instructions to decide: "Decide how X works" is unfinished
planning. Exact code bodies need not be in the brief, but everything an agent
would otherwise have to invent about structure or contracts must be.

## Plan for simple code

- Use existing code, standard libraries and tools already present before
  planning custom helpers, dependencies or new components.
- Do not plan tooling for a need nobody has shown. A requirement about *when*
  something happens does not decide *which tool* does it.
- Count the whole cost, not just code size: setup, downloads, extra machines,
  run time and maintenance.
- Plan checks only at **trust boundaries**: data entering from something this
  code does not control (user input, network or API responses, files or records
  written by other systems or older versions, external tool output,
  environment). Data produced by this code, or received through a settled
  contract, gets no checks. Validate once where data enters and fail clearly.
  Retries, fallbacks and recovery are behavior and need a stated requirement.
- Moving complexity elsewhere does not remove it.
- The project's own rules (testing, size limits, approvals, what may be run)
  apply to every stage. Splitting work never works around them.
- A document is a deliverable only when the user asked for it. Do not create
  phases whose only output is more planning.

## Review the written plan

When all files are written, review the plan, not any implementation. Use a
fresh reviewing subagent each round, since it reads the files as an
implementer will, without the planning session's context. Give it
[plan-reviewer.md](plan-reviewer.md) unchanged, with its inputs filled in;
that file holds the full checklist and report format. Use the `top`
candidate from the plan's `models.md`.

The reviewer reports gaps, omissions, bugs, contradictions and bad
assumptions, and may recommend going back to change earlier phases, even
their architecture. That is the point of the review: fix the problem at the
level it lives (see Revising the plan), not with a patch in a later phase.

Repeat with a new reviewer after each round of fixes until a round finds
nothing that would leave a competent implementer guessing, stuck or building
the wrong thing. The plan does not have to be perfect; that is impossible.
It has to be enough that a competent agent can take over each stage, know
what to do and why, and not lose the spec's goals. Do not keep reviewing for
wording or style once that bar is met. If rounds keep finding new problems in
the same area, the design there is likely unsettled: stop and ask the user.

Then report the plan to the user, including any open assumptions.

## Revising the plan

Plans are revised, not defended. A review, a later phase's planning or
implementation may show that an earlier decision, up to the architecture, is
wrong. Then change it, alter it or drop it, however much of the plan that
touches; do not build on a decision known to be wrong.

The implementer revises the next phase file before building it (see
implement-in-phases), rechecking that phase's open assumptions against the
code as it now is. When a review or implementation finds work the plan does
not cover or a decision that does not hold:

1. Re-read the code as it is now, including what earlier stages built, before
   changing anything in the plan.
2. Separate the missing definition from the proposed code fix.
3. Find the highest level affected and update the owning phase and its peers
   there; do not tack a cleanup stage onto the end when an earlier contract is
   what is wrong.
4. Recheck built stages the change affects, and plan the rework of built code
   as stages in the affected phases.
5. When the change touches architecture or a contract other phases use,
   review the affected phases again before building on them.
6. Never widen a stage to absorb the fix, or rewrite the plan to excuse
   unplanned edits.
7. If the change contradicts the approved spec or design, ask the user.

Replace text that is no longer true; record why in the phase's Notes. Git holds
the history.
