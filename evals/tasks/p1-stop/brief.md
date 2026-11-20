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
  separator line, and one line per tier built with `format_cost(c['cost'])`
  (checked in `render`).
- Verified: `format_cost(value)` is the script's number formatter for the
  table and prints `n/a` for a missing value (checked in `select-models.py`).
- Verified: each candidate's report row is in `c["row"]`, and the row field
  `output_tokens_per_second` is a number or `None` (checked in
  `score_and_cost` and `model-report.json`).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Add the Speed column | small | first | planned |

## 01.1 Add the Speed column

Goal:            The tier table in the script's output has a Speed column
                 after Cost showing each tier row's output tokens per
                 second, formatted like the Cost column.
Context:         All in `plugins/phased-delivery/scripts/select-models.py`,
                 read while planning:
                 - The existing `format_cost()` helper formats the Cost
                   column and prints `n/a` for a missing value.
                 - `render(...)` writes the table header
                   `"| Tier | Model | Effort | Score | Cost | Report row |"`,
                   the separator `"| --- | --- | --- | --- | --- | --- |"`
                   and one line per tier whose Cost cell is
                   `format_cost(c['cost'])`.
Contracts:       - Header: `| Tier | Model | Effort | Score | Cost | Speed | Report row |`
                 - Separator: seven `---` cells.
                 - Tier rows: after the Cost cell, the cell
                   `format_cost(c['row']['output_tokens_per_second'])`,
                   using the existing `format_cost()` helper unchanged.
Files:           plugins/phased-delivery/scripts/select-models.py
Work:            1. In `render`, add `Speed` to the header and a seventh
                    `---` to the separator.
                 2. Add the speed cell to each tier row, formatted with the
                    existing `format_cost()` helper.
External inputs: none
Done when:       - Running the script on `plan/models-available.json` with
                   `--today 2026-11-19` (output to stdout or a file under
                   `/tmp`) shows the new header and separator, and each
                   tier row has the speed of its report row in
                   `model-report.json` (for example
                   `Claude Haiku 5.5 (Xhigh)` has 237.05).
                 - Every other output line is the same as before the change.
Out of scope:    The "Candidates considered" list, `--json` output, sorting,
                 the formatting helpers themselves, `model-report.json`,
                 `model-selection.md` and every other file.
Model basis:     J0 F0 R0 C0 K0 P0 V0 = 0 -> small

## Notes
- 2026-11-19: Speed shown so the user can see the latency cost of a tier.
