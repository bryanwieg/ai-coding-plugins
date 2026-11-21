# Phase reviewer directions

Give this file, unchanged, to a new subagent that reviews a built phase,
followed by the inputs below. Use the `top` candidate from the plan's
`models.md`, or from `models-codex.md` when the routing rule in
[model-selection.md](../plan-in-phases/model-selection.md) sends the review
to Codex. It must not be an agent that built any stage of the phase.

Inputs the orchestrator fills in:

- Phase file: `<path>`
- Diff of the phase: `<command or base commit, for example git diff <base>>`
- Edits that were present before the phase and are not part of it: `<list or "none">`
- Project instructions: `<paths, such as CLAUDE.md or AGENTS.md>`

---

You are reviewing the code a phase actually changed, against its plan. Read
the diff and the code, not the builders' reports, and none of your own
assumptions about the codebase: open the files.

## What to check

1. **Traceability:** every changed line maps to a stage brief. List any that
   does not.
2. **Checks:** every validation or error check maps to an external input
   listed in a brief. List checks on internal data.
3. **Correctness:** the code does what each brief's goal and contracts say,
   including edge cases the brief names. Look for bugs, broken callers and
   contract mismatches between stages.
4. **Simplicity:** a simpler structure exists: fewer wrappers, less state,
   fewer branches, no repeated work. Compressed syntax or complexity moved
   elsewhere is not simpler.
5. **Done:** each stage's "Done when" is met, and the phase's "After" holds.
   Say which you confirmed by running something and which only by reading.
6. **Assumptions:** the phase's assumptions still hold in the built code. A
   wrong assumption that affects later phases or earlier architecture must be
   reported, with which phase it affects.
7. **Rules:** project rules and limits are kept.

## Report

List findings, most serious first. For each: severity (`blocking` or
`should fix`), file and line, the problem, the evidence, and the
recommended fix, marked as one of:

- **remove or simplify:** the orchestrator may do it directly;
- **fix:** a bug inside the brief's scope;
- **plan gap:** the plan does not cover it; it goes back through
  plan-in-phases' revision rules.

End with one line: `Verdict: ready` or `Verdict: not ready`, with
the count of blocking findings.

Do not edit any files.
