# Why planning uses JSON, checks and closed review types

Background for maintainers of this skill; the planner and the reviewer do
not need it. Changed 2026-11-23 (plugin 0.8.0). The measurements are in
`experiments/plan-pipeline/README.md` on the `plan-pipeline-poc` branch.

## What went wrong before

Planning a medium feature (built-in authentication for Fava) took up to 75
minutes and $60, and filled a whole usage window. Two things caused it:

1. **Briefs dictated code in prose.** Several directions each read as
   "settle everything": briefs a fresh agent can build "without further
   decisions"; "everything an agent would otherwise have to invent about
   structure or contracts must be" in the brief; "Work: the concrete
   changes, in order"; and a J score of 0 for "Work names every change".
   Together they left one way to comply: write the code as prose. A single
   phase reached 500 lines and 184 lines per brief before any review.
2. **The review ratcheted.** Its stop rule counted anything left for the
   builder as "guessing", so each round asked for more detail, and the next
   round checked that detail against the code: 50 to 96 turns per round,
   most of the run's cost.

Cutting those directions was not the answer: earlier cuts made the skill
plan worse. The fix replaces judgment words with things that can be
checked: fields with a fixed shape and a per-field guide (an outside view
only, no field for internals), a script that checks what needs no
judgment, and a closed list of review finding types.

## Measured effect

Same task, Opus at medium effort, blind grading out of 30:

| Version | Grade | Cost | Time |
| --- | --- | --- | --- |
| Prose plan, one session (Fable reviews) | 27 | $15 | 33 min |
| Prose plan, pipeline | 23 | $60 | ~75 min |
| JSON plan with checks and closed review, pipeline | 26 | $18 | ~25 min |

Review rounds fell to 1–2 minutes each and found only real problems. Every
remaining defect the grader found was one a script could catch; those
checks (quotes, citations, plan ids in phase files) were added.

## Replaced text, kept verbatim

The stage brief block and its last paragraph in phase-file-template.md:

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
Tests:           the exact tests it writes or turns on, each with its kind
                 (outcome, integration, unit) and what it proves; a unit
                 test also says why a run-through cannot cover it
Done when:       observable properties of the changed files
Out of scope:    nearby things it must not change
Model basis:     scores per model-selection.md, e.g.
                 J1 F1 R1 C1 K0 P0 V1 S0 = 5 -> middle
```

Write decisions, not instructions to decide: "Decide how X works" is unfinished
planning. Exact code bodies need not be in the brief, but everything an agent
would otherwise have to invent about structure or contracts must be.

The stop rule in SKILL.md, "Review the written plan":

Repeat with a new reviewer after each round of fixes until a round finds
nothing that would leave a competent implementer guessing, stuck or building
the wrong thing. The plan does not have to be perfect; that is impossible.
It has to be enough that a competent agent can take over each stage, know
what to do and why, and not lose the spec's goals. Do not keep reviewing for
wording or style once that bar is met. If rounds keep finding new problems in
the same area, the design there is likely unsettled: stop and ask the user.

The opening of plan-reviewer.md's directions:

The goal is a plan that a competent agent can build stage by stage, knowing
what to do and why, without losing the specification's goals. It does not
need to be perfect. Report what would leave an implementer guessing, stuck
or building the wrong thing. Do not report wording or style.

plan-reviewer.md's report section:

## Report

List findings, most serious first. For each:

- **Severity:** `blocking` (an implementer would guess, get stuck or build
  the wrong thing) or `should fix` (a real problem a competent implementer
  would likely get past).
- **Where:** phase file and stage.
- **Problem:** what is wrong or missing.
- **Evidence:** the file, symbol or plan text that shows it.
- **Fix at:** the highest level it should be fixed (which phase and which
  contract or decision), and the recommended change.

End with one line: `Verdict: ready` if there are no blocking findings, or
`Verdict: not ready` with the count of blocking findings. If the same area
keeps failing across rounds, say so: the design there may be unsettled and
need the user.

Do not edit any files.

In model-selection.md, J = 0 read "Work names every change; the agent only
writes it out", and S was "Sequencing of the Work steps".

And the sentence before it in SKILL.md: "The reviewer reports gaps,
omissions, bugs, contradictions and bad assumptions, and may recommend
going back to change earlier phases, even their architecture." Bugs inside
one stage are now left to implementation, which reviews every diff.

The skill's description said each phase is "split into stage briefs a fresh
agent can build without further decisions"; it now says "without deciding
anything other stages, code or the user see".
