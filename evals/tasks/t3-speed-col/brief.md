# Phase 01: Speed column in models.md

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: the tier table in `models.md` has the columns Tier, Model, Effort,
Score, Cost and Report row.
After: it has a Speed column (output tokens per second) between Cost and
Report row; nothing else in the output changes.

## Assumptions
- Verified: the tier table is written only in `render` in
  `plugins/phased-delivery/scripts/select-models.py`: a header line, a
  separator line, and one line per tier built with `money(c['cost'])`
  (checked in `render`).
- Verified: each candidate's report row is in `c["row"]`, and the row field
  `output_tokens_per_second` is a number or `None` (checked in
  `score_and_cost` and `model-report.json`).
- Verified: `c["speed"]` is not usable for display: `score_and_cost` sets it
  to `output_tokens_per_second or 0`, so a missing value becomes 0 (checked
  in `score_and_cost`).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Add the Speed column | small | first | planned |

## 01.1 Add the Speed column

Goal:            The tier table in the script's output has a Speed column
                 after Cost showing each tier row's output tokens per second
                 as a whole number, or `n/a` when the report has no value.
Context:         All in `plugins/phased-delivery/scripts/select-models.py`,
                 read while planning:
                 - `money(value)` (lines 232-233) formats the Cost column:
                   `return "n/a" if value == math.inf else f"{value:.2f}"`.
                 - `render(...)` (lines 236-270) writes the table header
                   `"| Tier | Model | Effort | Score | Cost | Report row |"`,
                   the separator `"| --- | --- | --- | --- | --- | --- |"`
                   and, per tier, `f"| {tier} | {c['tool_model']} | {c['effort']} | {c['score']:.1f}"`
                   `f" | {money(c['cost'])} | {c['row']['name']} |"`.
                 - `score_and_cost` sets `c["speed"]` to
                   `c["row"]["output_tokens_per_second"] or 0` for sorting
                   only.
Contracts:       - New helper `tokens_per_second(value)` placed right after
                   `money`, same shape as `money`: returns `"n/a"` when
                   `value is None`, else `f"{value:.0f}"`.
                 - Header: `| Tier | Model | Effort | Score | Cost | Speed | Report row |`
                 - Separator: seven `---` cells.
                 - Tier rows: after the Cost cell, the cell
                   `tokens_per_second(c['row']['output_tokens_per_second'])`.
                   Use the row field, not `c['speed']`.
Files:           plugins/phased-delivery/scripts/select-models.py
Work:            1. Add `tokens_per_second` after `money`.
                 2. In `render`, add `Speed` to the header, a seventh `---`
                    to the separator, and the speed cell to each tier row.
External inputs: none
Done when:       - Running the script on `plan/models-available.json` with
                   `--today 2026-11-19` (output to stdout or a file under
                   `/tmp`) shows the new header and separator, and each
                   tier row has the speed of its report row in
                   `model-report.json`, rounded to a whole number (for
                   example `Claude Haiku 5.5 (Xhigh)` has 237.05, shown as
                   `237`).
                 - Every other output line is the same as before the change.
Out of scope:    The "Candidates considered" list, `--json` output, sorting,
                 `model-report.json`, `model-selection.md` and every other
                 file.
Model basis:     J0 F0 R0 C0 K0 P0 V0 = 0 -> small

## Notes
- 2026-11-19: Speed shown so the user can see the latency cost of a tier.
