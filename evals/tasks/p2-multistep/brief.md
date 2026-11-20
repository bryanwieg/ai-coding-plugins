# Phase 01: Accept "thinking" in effort names

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: `normalize_effort("high-thinking")` gives `"highthinking"`, which
matches no thinking level, so a tool that lists efforts as "High thinking"
gets every level excluded.
After: a trailing word "thinking" is dropped, so `"high-thinking"` gives
`"high"`; the guide and the tests say so.

## Assumptions
- Verified: `normalize_effort(effort)` is
  `return re.sub(r"[^a-z0-9]+", "", effort.lower()) if effort else DEFAULT_EFFORT`
  and has no docstring or comment (checked in
  `plugins/phased-delivery/scripts/select-models.py`, lines 64-65).
- Verified: `normalize_effort` is used only in `build_candidates`, for the
  tool's offered efforts and the report rows' efforts, which are `null` or
  plain level names such as `high` (checked in `build_candidates` and
  `model-report.json`), so output for the current report and
  `plan/models-available.json` does not change.
- Verified: `plugins/phased-delivery/tests/test_effort.py` loads the script
  by path and tests `normalize_effort`; `test_thinking_suffix` asserts the
  current behavior for `"high-thinking"` (checked in `test_effort.py`).
- Verified: `model-selection.md` describes the `efforts` field in the
  `models` bullet of "### 1. List what the running tool offers" (checked in
  `plugins/phased-delivery/skills/plan-in-phases/model-selection.md`).

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Drop a trailing "thinking" in effort names | small | first | planned |

## 01.1 Drop a trailing "thinking" in effort names

Goal:            `normalize_effort` drops a trailing word "thinking", its
                 docstring and the guide say so, and the tests in
                 `test_effort.py` cover it and pass.
Context:         Read while planning:
                 - `plugins/phased-delivery/scripts/select-models.py`
                   lines 64-65, `normalize_effort` (quoted in Assumptions);
                   `DEFAULT_EFFORT = "default"`.
                 - `plugins/phased-delivery/tests/test_effort.py`: class
                   `NormalizeEffortTest` with `test_lowercases`,
                   `test_removes_punctuation`, `test_empty_is_default` and
                   `test_thinking_suffix`.
                 - `plugins/phased-delivery/skills/plan-in-phases/model-selection.md`,
                   section "### 1. List what the running tool offers", the
                   bullet (lines 79-81) "- `models`: each model's `id` as
                   the tool names it and the `efforts` it accepts. Add
                   `match` with the report's model name only when the
                   script reports a name it could not match."
Contracts:       `normalize_effort(effort)`:
                 - empty or `None` gives `DEFAULT_EFFORT` (unchanged);
                 - otherwise: lowercase; then remove a trailing word
                   `thinking` that is separated from the text before it by
                   one or more non-alphanumeric characters; then remove
                   every non-alphanumeric character (unchanged).
                 - Examples: `"high-thinking"` -> `"high"`,
                   `"xhigh thinking"` -> `"xhigh"`, `"High_Thinking"` ->
                   `"high"`, `"x-high"` -> `"xhigh"`, `"highthinking"` ->
                   `"highthinking"` (no separator, so not a word).
Files:           plugins/phased-delivery/scripts/select-models.py
                 plugins/phased-delivery/skills/plan-in-phases/model-selection.md
                 plugins/phased-delivery/tests/test_effort.py
Work:            Do these steps in order.
                 1. Change `normalize_effort` to the contract above.
                 2. Give `normalize_effort` this docstring:
                    `"""Lowercase a thinking level, drop a trailing word "thinking" and all punctuation; empty gives DEFAULT_EFFORT."""`
                 3. In `model-selection.md`, in the `models` bullet named in
                    Context, insert this sentence directly after "the
                    `efforts` it accepts." and before "Add `match` ...",
                    rewrapping only that bullet like the lines around it and
                    changing nothing else:

                        Effort names are compared ignoring case and
                        punctuation, and a trailing word "thinking" is
                        dropped, so `High thinking` counts as `high`.

                 4. Run the tests from the repository root:
                    `python3 -m unittest discover -s plugins/phased-delivery/tests`.
                 5. Update the assertion in `test_thinking_suffix` that
                    encodes the old `"high-thinking"` behavior so that it
                    expects the new result.
                 6. Add one test method `test_xhigh_thinking` to
                    `NormalizeEffortTest` asserting that `"xhigh thinking"`
                    gives `"xhigh"`, then run the tests again.
External inputs: none
Done when:       - `normalize_effort` gives the results in Contracts.
                 - The docstring and the `model-selection.md` sentence are
                   in place.
                 - `test_effort.py` has the four existing tests (with
                   `test_thinking_suffix` updated) plus
                   `test_xhigh_thinking`, and the command in step 4 passes.
                 - `select-models.py plan/models-available.json --today
                   2026-11-19` prints the same output as before.
Out of scope:    `normalize`, `build_candidates`, `EFFORT_ORDER`, other
                 sections of `model-selection.md`, the README.
Model basis:     J0 F1 R0 C0 K0 P0 V0 = 1 -> small

## Notes
- 2026-11-19: Some tools list efforts as "High thinking"; without this they
  are all excluded.
