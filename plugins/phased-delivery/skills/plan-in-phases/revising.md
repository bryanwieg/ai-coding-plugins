# Revising the plan

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
