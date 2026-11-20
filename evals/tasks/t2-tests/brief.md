# Phase 01: Unit tests for model matching and thinking levels

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: `plugins/phased-delivery/tests/` holds only `test_example.py`, which
tests `normalize`.
After: `test_select_models.py` tests `normalize_effort`, `match_model` and
`effort_denial`; all tests pass.

## Assumptions
- Verified: `select-models.py` cannot be imported by name because of the
  hyphen; `tests/test_example.py` loads it by path with
  `importlib.util.spec_from_file_location` (checked in `test_example.py`).
- Verified: importing the script runs no code beyond definitions; `main`
  runs only under `if __name__ == "__main__"` (checked in
  `select-models.py`).
- Verified: the signatures and return values below (checked in
  `normalize_effort`, `match_model`, `effort_denial`).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Add test_select_models.py | small | first | planned |

## 01.1 Add test_select_models.py

Goal:            `plugins/phased-delivery/tests/test_select_models.py` tests
                 the cases listed in Work for `normalize_effort`,
                 `match_model` and `effort_denial`, and
                 `python3 -m unittest discover -s plugins/phased-delivery/tests`
                 passes.
Context:         Read while planning:
                 - `plugins/phased-delivery/tests/test_example.py`: the
                   pattern to copy. It loads the script by path into a
                   module named `select_models`, and has one
                   `unittest.TestCase` class with one `test_` method per
                   case.
                 - `plugins/phased-delivery/scripts/select-models.py`:
                   `DEFAULT_EFFORT = "default"`; `EFFORT_ORDER` (least to
                   most: minimal, low, medium, high, xhigh, max, ultra);
                   `normalize_effort(effort)` (lowercases and removes every
                   non-alphanumeric character; empty or `None` gives
                   `DEFAULT_EFFORT`); `match_model(entry, bases)`;
                   `effort_denial(effort, ceiling)`.
Contracts:       Uses the existing functions unchanged:
                 - `match_model(entry, bases)`: `entry` is a dict with `"id"`
                   and optionally `"match"`; `bases` maps a report model
                   name to `{"released": "YYYY-MM-DD"}`. Returns
                   `(name, how)` on a match, or `(None, reason)`.
                 - `effort_denial(effort, ceiling)`: returns `None` when
                   allowed, otherwise a reason string starting `"denied: "`.
Files:           plugins/phased-delivery/tests/test_select_models.py (new)
Work:            1. Create the file with the same module docstring style and
                    the same loading code as `test_example.py`.
                 2. Class `NormalizeEffortTest`, one test each:
                    - `"High"` gives `"high"`;
                    - `"x-high"` gives `"xhigh"`;
                    - `""` gives `select_models.DEFAULT_EFFORT`;
                    - `None` gives `select_models.DEFAULT_EFFORT`.
                 3. Class `MatchModelTest`, one test each:
                    - explicit: entry `{"id": "x", "match": "Claude Opus 5"}`,
                      bases containing `"Claude Opus 5"` gives
                      `("Claude Opus 5", "explicit")`;
                    - explicit name missing: entry
                      `{"id": "x", "match": "Nope"}` gives `None` as the
                      name;
                    - exact name: entry `{"id": "claude-opus-5"}` with bases
                      `"Claude Opus 5"` and `"Claude Opus 5 Mini"` gives
                      `("Claude Opus 5", "exact name")`;
                    - alias: entry `{"id": "opus"}` with bases
                      `"Claude Opus 4"` (released `"2025-05-01"`) and
                      `"Claude Opus 5"` (released `"2026-05-01"`) gives
                      `("Claude Opus 5", "alias: newest release containing the name")`;
                    - ambiguous across families: entry `{"id": "claude"}`
                      with bases `"Claude Opus 5"` (`"2026-01-01"`) and
                      `"Claude Sonnet 5"` (`"2026-02-01"`) gives `None` as
                      the name and a reason starting `"ambiguous"`;
                    - no match: entry `{"id": "gemini"}` with bases
                      `"Claude Opus 5"` gives
                      `(None, "no report model matches the name")`.
                 4. Class `EffortDenialTest`, one test each:
                    - ceiling `None` allows anything: `("max", None)` gives
                      `None`;
                    - `DEFAULT_EFFORT` is always allowed:
                      `(select_models.DEFAULT_EFFORT, "low")` gives `None`;
                    - at the ceiling: `("high", "high")` gives `None`;
                    - below the ceiling: `("low", "high")` gives `None`;
                    - above the ceiling: `("xhigh", "high")` gives a string
                      containing `"above"`;
                    - unknown level: `("turbo", "high")` gives a string
                      containing `"unknown level"`.
                 5. Run the discover command in Goal from the repository
                    root.
External inputs: none
Done when:       - The file exists with the three classes and the cases in
                   Work.
                 - `python3 -m unittest discover -s plugins/phased-delivery/tests`
                   run from the repository root passes, including
                   `test_example.py`.
Out of scope:    `select-models.py` and `test_example.py` are not changed;
                 no other test files, no test runner configuration, no
                 `__init__.py`.
Model basis:     J0 F0 R0 C0 K0 P0 V0 = 0 -> small

## Notes
- 2026-11-19: Tests cover the matching and ceiling rules the tier
  selection depends on.
