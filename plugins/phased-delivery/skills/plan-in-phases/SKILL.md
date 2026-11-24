---
name: plan-in-phases
description: "Turn an approved specification and design into a complete phased implementation plan: JSON checked by a script and rendered to one self-contained phase.md per phase, each split into stage briefs a fresh agent can build without deciding anything other stages, code or the user see. Planning only; writes no code. Use whenever the user asks to plan, break down, phase, stage or sequence a feature, migration, rewrite or other multi-step change (\"plan this\", \"break this into phases\", \"write the implementation plan\", \"how should we build this in stages\"), or to review, fix or rework an existing phased plan or revise a phase after implementation finds gaps. Use proactively, without being asked, before writing code for any change that may touch several files, a shared contract or the architecture: its first step is a capped estimate (at most 5 files read) that sends small changes straight back to direct work, so starting it costs little. Not for one-file edits that change no contract, and not for building the plan; that is implement-in-phases."
---

# Plan in phases

Turn the approved specification and design into the complete plan in one pass:
one folder per phase, every stage detailed enough to build. This skill writes
the plan only; [implement-in-phases](../implement-in-phases/SKILL.md) builds it.
Anyone implementing the plan, agent or person, must use the
implement-in-phases skill; every rendered `phase.md` says so in its header.

The user approves the specification and the design. First estimate how much
planning the change needs (below); a change that needs no plan leaves this
skill there. Before planning, grill the user on them (see [grill.md](grill.md)); that is the time to ask.
After it, settle every remaining decision with the context at hand and write
it down. Ask the user again only when planning, review or implementation
shows the specification or design is wrong, incomplete or contradictory, or
that the work needs something the design lacks (a new component, dependency,
tool or external system). Give options and a recommendation.

## Estimate how much planning the change needs

Before grilling or reading further, make the quick estimate in
[mode-guide.md](mode-guide.md): sketch the change from the request and run
`scripts/plan-mode.py sketch`, which stops when the mode is already certain;
otherwise list the terms, run `scripts/plan-mode.py locate`, read at most 5
of the files it lists, write the form and run `scripts/plan-mode.py score`.
It has hard limits so that it stays an estimate; do not read more to
improve it. Follow the mode it
prints, unless the user asked for a particular one:

- **direct:** do not plan. Leave this skill and make the change in context:
  read the code it touches, make it, run the tests. When the work turns
  out bigger, re-score as mode-guide.md says.
- **quick:** grill, then write `plan.json` and one phase folder,
  `01-short-name/`, checked and rendered by `plan-check.py` as below, with
  `size` set to `quick` and the score in its evidence. It need not follow the
  skeleton-to-cutover progression. No review subagent: the script's checks
  stand in for it. When `plan.json` and the stage files pass `--outline`, run
  `scripts/plan-mode.py rescore` on the plan (mode-guide.md,
  "Re-scoring"): on full, continue as a full plan; on direct, stop
  planning and make the change.
- **full:** everything below, with `size` set to `full`.

Without Python, judge the mode from the tables in mode-guide.md by hand,
and say so in the evidence.

## Grill the spec and design

Read [grill.md](grill.md) now and follow all of it before phasing anything.

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
  rests on real code. Cite the lines with words they show (see
  [phase-guide.md](phase-guide.md)); the script checks them.

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

## Write every phase

The plan directory holds `plan.json` and one folder per phase, named
`NN-short-name` and numbered in build order:

```
<plan dir>/
  plan.json            the plan: goal, outcomes, decisions, phase list
  plan.md              rendered from plan.json
  models.md, models-available.json
  NN-short-name/
    phase.json         the phase: role, before and after, assumptions, notes
    NN.n.json          one per stage: its brief
    phase.md           rendered: the phase and every stage brief
```

The JSON is the plan for its whole life: planning writes it, revising and
building keep using it, and nothing deletes it. `plan.md` and each
`phase.md` are rendered from it for people and builders; never edit them by
hand. The shared files are `models.md`, the plan's model table, and the
`models-available.json` it is generated from. Write the plan top-down:

1. List the models the running tool offers now in `models-available.json`
   and generate `models.md` with the plugin's `scripts/select-models.py`
   (see [model-selection.md](model-selection.md)). Never write either from
   memory. When the session can also build with Codex, do the same for
   Codex in `models-available-codex.json` and `models-codex.md` (see
   "Builders in another tool" there).
2. Create every phase with its role and what exists before and after.
3. Define every stage of every phase by goal, files and contracts.
4. Fill in each stage brief completely.

Before each step, for each phase, read the current code that phase touches
(see Read the code before deciding).

At each step, define all related parts and their contracts before going deeper
into one of them, including callers and consumers in other phases.

### Write the plan as JSON and let the script check and render it

Steps 2 to 4 are written as JSON, and `scripts/plan-check.py` (in this
plugin, two directories above this skill's directory) checks it and renders
`plan.md` and each `phase.md`.

1. Steps 2 and 3: read [plan-guide.md](plan-guide.md) and write `plan.json`
   following it: the outcomes from the grill, the decisions that span
   phases, the existing interfaces the stages rely on, and the phase list.
   Read [phase-guide.md](phase-guide.md) and write one stage file,
   `NN-name/NN.n.json`, for every stage, with its outline fields: title,
   order, files, and the contracts it provides and uses. Run
   `python3 scripts/plan-check.py <plan dir> --outline --repo <repo>
   --spec <spec> --design <design>` and fix every error it reports before
   going on; judge each warning.
2. Step 4: following [phase-guide.md](phase-guide.md), write each phase's
   `phase.json` and fill in the rest of every stage file. Write only the
   `brief` part of each; `record` belongs to the build scripts. Run the
   script without `--outline`; it checks every file against its schema and
   the others, checks every spec and design quote and every code citation,
   and renders `plan.md` and each clean phase's `phase.md` in the layout of
   [phase-file-template.md](phase-file-template.md). Fix every error and
   rerun until it reports none.
3. Change the plan only by editing the JSON and rerunning the script, now
   and for as long as the plan lives. Never edit `plan.md` or a `phase.md`
   by hand: the next run overwrites them.

The script decides what can be checked without judgment: that every
contract a stage uses has a provider, the build order, that
files exist or are created first, outcome coverage, tiers from the scores,
quotes and citations, and the no-code and length rules. Do not re-check
those by hand; spend the reading on what needs judgment. If Python is not
available, write the JSON all the same, following the two guides for each
field, check each item above by reading, and tell the user that `plan.md`
and the `phase.md` files were not rendered.

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

Full plans only; a quick plan has no review subagent. When the whole plan is
written and the script reports no errors and has rendered every phase, review the plan, not any implementation. Use a fresh reviewing subagent each round,
since it reads the files as an implementer will, without the planning
session's context. Give it [plan-reviewer.md](plan-reviewer.md) unchanged,
with its inputs filled in; that file holds what counts as a finding, where
to look and the report format. Use the `top` candidate from the plan's
`models.md`.

The reviewer reports only the finding types plan-reviewer.md lists, each
with evidence, and may recommend going back to change earlier phases, even
their architecture. That is the point of the review: fix the problem at the
level it lives (see [revising.md](revising.md)), not with a patch in a later
phase. Before fixing any finding, read [revising.md](revising.md) now and
follow it for every fix.

Fix findings in the JSON and rerun the script. Repeat with a new reviewer
after each round of fixes until a round reports no findings; a later round
checks the previous findings and reviews only the phases that changed and
what depends on them. The plan does not have to be perfect; that is
impossible. It has to be enough that a competent agent can take over each
stage, know what to do and why, and not lose the spec's goals. If rounds
keep finding new problems in the same area, the design there is likely
unsettled: stop and ask the user. Why the review works this way is in
[structured-planning-notes.md](structured-planning-notes.md).

Then report the plan to the user, including any open assumptions.

## Revising the plan

Whenever a review, a later phase's planning or implementation shows an earlier
decision is wrong, or the user asks to review, fix or rework an existing plan,
read [revising.md](revising.md) and follow it.
