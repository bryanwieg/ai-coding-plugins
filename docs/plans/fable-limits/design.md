# Fable limits for implementation: design

Agreed with the user on 2026-11-24.

## Problem

Across the 38 stages scored in this repository's plans and eval tasks, `route`
sends 15 (39%) to Fable high and 10 more to Fable low. Ten of the fifteen
`top` stages reach it only through K = 2, with totals of 5 to 7. Fable at
medium thinking or above should be for the top 10% most complex tasks; picking
it this often means the implementation criteria are not tuned.

## Rules

- `top` comes only from a total of 9 or more. The override "J = 2, C = 2 or
  K = 2: use top" is dropped; a measure at 2 still raises `middle` to
  `middle+`.
- Fable low as a step up is fine as long as it beats Opus high in
  cost/performance ratio. Codified for any premium pair below `top`: when the
  standard pairs run out before a step up the stage asked for (`middle+` or
  risk), the premium pair above the standard pick is taken only when its score
  divided by its benchmark run cost is at least the standard pick's; otherwise
  the standard pick stays. A `--up` retry after a failed build still steps up,
  because the standard pick has already failed.
- Revised the same day: the user is "ok for now with letting fable low win
  if the cost is within an appropriate margin", since Fable should comprehend
  better and may need fewer tokens at low thinking. The premium pair's ratio
  may be up to 5% below the standard pick's (`PREMIUM_RATIO_MARGIN`); 5%
  rather than 10% because Fable has its own quota, and once it is used up
  builds fall back to Opus anyway.

## Check

On the 38 scored stages with the current profiles, Fable at medium or above is
picked for at most 10% of stages.
