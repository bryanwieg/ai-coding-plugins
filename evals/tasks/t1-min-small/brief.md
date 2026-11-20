# Phase 01: Absolute floor for the small tier

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: `select-models.py` sets every tier's floor as a share of the best
candidate's score (`FLOORS`).
After: `select-models.py --min-small SCORE` sets the small tier's floor to
an absolute Intelligence Index score; without the option nothing changes.

## Assumptions
- Verified: options are parsed generically from `--name value` pairs; a
  flag's key is the flag without leading dashes, and only keys already in
  the `options` dict are accepted (checked in `parse_args`,
  `plugins/phased-delivery/scripts/select-models.py`).
- Verified: tiers are picked in `assign_tiers` by
  `cheapest([c for c in scored if c["score"] >= floor * best])`, then
  `prefer_cheaper(pick, scored)` applies the 3-point rule (checked in
  `assign_tiers` and `prefer_cheaper`).
- Verified: the floors appear in `models.md` only on the `Score:` line built
  in `render` (checked in `render`).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Add `--min-small` to select-models.py | small | first | planned |

## 01.1 Add `--min-small`

Goal:            `select-models.py` accepts `--min-small SCORE`, which makes
                 the small tier's floor that absolute score; output without
                 the option is unchanged byte for byte.
Context:         All in `plugins/phased-delivery/scripts/select-models.py`,
                 read while planning:
                 - Module docstring, "Usage:" block (lines 4-6) lists the
                   options.
                 - `FLOORS = {"top": 0.97, "middle": 0.85, "small": 0.50}`
                   (line 38).
                 - `parse_args(argv)` (lines 68-81) builds
                   `options = {"available": ..., "report": DEFAULT_REPORT,
                   "out": None, "json": None, "today": None}` and fills it
                   from `--key value` pairs; `key = flag.lstrip("-")`.
                 - `assign_tiers(scored)` (lines 217-229) loops
                   `for tier, floor in FLOORS.items():` and picks
                   `cheapest([c for c in scored if c["score"] >= floor * best])`,
                   then `tiers[tier] = prefer_cheaper(pick, scored)`.
                 - `render(...)` (lines 236-270) writes the line
                   `floors: " + ", ".join(f"{t} {int(f * 100)}%" for t, f in FLOORS.items())`.
                 - `main(argv)` (lines 273-320) converts `options["today"]`
                   right after `parse_args`, prints input errors to stderr
                   and returns 2 (see "bad available file").
Contracts:       - New option `--min-small SCORE`. Its key in `options` is
                   `"min-small"`, default `None`.
                 - `assign_tiers(scored, min_small)`: `min_small` is a float
                   or `None`. When it is a float, the small tier's pick is
                   `cheapest([c for c in scored if c["score"] >= min_small])`
                   instead of using `FLOORS["small"] * best`; the result
                   still goes through `prefer_cheaper(pick, scored)`
                   exactly as now. Other tiers are unchanged.
                 - `render(...)` gets `min_small` as a new last parameter.
                   On the `Score:` line, when `min_small` is not `None`, the
                   small entry reads `small min {min_small:g}` (for example
                   `small min 30`, `small min 27.5`) instead of
                   `small 50%`; the other entries and their order are
                   unchanged. When it is `None` the line is unchanged.
                 - A value that `float()` rejects: print
                   `bad --min-small value: <value>` to stderr and return 2
                   from `main`.
Files:           plugins/phased-delivery/scripts/select-models.py
Work:            1. In the docstring's Usage block, add `[--min-small SCORE]`
                    to the option list (wrap the lines to match the
                    existing indentation), and add this paragraph right
                    before "Exit codes:":
                    `--min-small SCORE sets the small tier's floor to that
                    Intelligence Index score instead of 50% of the best.`
                 2. In `parse_args`, add `"min-small": None` to `options`.
                 3. In `main`, right after `today` is computed, convert
                    `options["min-small"]` with `float()` when it is not
                    `None` into a new name `min_small` (else `None`); on
                    `ValueError` print the error above and return 2.
                 4. Change `assign_tiers` to the contract above and pass
                    `min_small` from `main`.
                 5. Change `render` to the contract above and pass
                    `min_small` from `main`.
External inputs: the `--min-small` command-line value: check once in `main`
                 that `float()` accepts it.
Done when:       - With `plan/models-available.json` and `--today
                   2026-11-19`, output without `--min-small` is identical to
                   the output before the change.
                 - `--min-small 30` puts `haiku` at `xhigh` in the small row,
                   `--min-small 25` puts `haiku` at `high`, and
                   `--min-small 20` puts `haiku` at `medium`; the `Score:`
                   line shows `small min 30` (25, 20); `--json` gives the
                   same small model and effort as the table.
                 - `--min-small abc` prints the error to stderr and exits 2.
                 - Running the script with no arguments prints the usage,
                   which mentions `--min-small`.
Out of scope:    `FLOORS`, `TIE_POINTS`, the middle, middle+ and top tiers,
                 `model-selection.md`, the README and every other file.
Model basis:     J0 F0 R0 C0 K0 P0 V0 = 0 -> small

## Notes
- 2026-11-19: Absolute floor requested so small can be pinned to a score
  instead of a share of a moving best score.
