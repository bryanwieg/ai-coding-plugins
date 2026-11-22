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
the user on them (see [grill.md](grill.md)); that is the time to ask.
After it, settle every remaining decision with the context at hand and write
it down. Ask the user again only when planning, review or implementation
shows the specification or design is wrong, incomplete or contradictory, or
that the work needs something the design lacks (a new component, dependency,
tool or external system). Give options and a recommendation.

## Grill the spec and design

Read [grill.md](grill.md) now and follow all of it before sizing or phasing
anything.

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
- Reading the code, the Assumptions section, the Outcome tests section,
  complete stage briefs and the plan review are never skipped. The review uses a fresh subagent, who also
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

Before planning each phase, read [phase-kinds.md](phase-kinds.md) and follow
its part for that kind of phase: what to settle, what to read, the
assumptions to check, and when it is done.

## Plan the tests

Read [test-planning.md](test-planning.md) and follow it before planning any
phase's tests or writing any stage brief's Tests line.

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

### Phase file layout and stage brief

Before writing any phase file, read
[phase-file-template.md](phase-file-template.md) and use its phase file layout
and stage brief exactly.

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
level it lives (see [revising.md](revising.md)), not with a patch in a later
phase.

Repeat with a new reviewer after each round of fixes until a round finds
nothing that would leave a competent implementer guessing, stuck or building
the wrong thing. The plan does not have to be perfect; that is impossible.
It has to be enough that a competent agent can take over each stage, know
what to do and why, and not lose the spec's goals. Do not keep reviewing for
wording or style once that bar is met. If rounds keep finding new problems in
the same area, the design there is likely unsettled: stop and ask the user.

Then report the plan to the user, including any open assumptions.

## Revising the plan

Whenever a review, a later phase's planning or implementation shows an earlier
decision is wrong, or the user asks to review, fix or rework an existing plan,
read [revising.md](revising.md) and follow it.
