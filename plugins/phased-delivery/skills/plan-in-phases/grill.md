# Grill the spec and design

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
concern is and the evidence (code you read, a concrete failure case). Then
ask why the user chose this approach. They may know something you do not, or
you may see something they missed. Discuss it together until the reason is
clear and you agree which way is better: theirs, yours, or a third option
neither started with. Change your view when their reasons hold; keep making
your case while they do not. The user makes the final call. Record the
concern, the reasoning and the outcome in the affected phase's Notes. Do not
raise concerns about taste or style.

Leave the grill with the change's purpose written as a few observable
outcomes: what a user can do or see afterwards that they could not before,
and what no longer goes wrong ("running X on Y writes Z", "a lapsed plan no
longer hangs the build"). Each outcome must be checkable by running the
program. One that cannot be turned into a test means the goal is not yet
understood: keep asking. These outcomes drive the tests (see
[test-planning.md](test-planning.md)).

Stop when no question or concern is left whose answer would change the plan.
A small change may need only a few questions; ask none just to fill the step.

Record each answer where planning will use it: as a decision in the Notes of
the phase it affects, or, if it changes the specification or design, in that
document with the user's agreement.
