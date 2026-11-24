# Phase 01: Schemas, script interface and outcome tests

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: built 4d47781
Before: implement-in-phases is one prose SKILL.md; the orchestrator writes commit trailers, tracks attempts and sums premium spend by hand. No build-check script or revision and review schemas exist.
After: `revision.schema.json` and `review.schema.json` exist; `scripts/build-check.py` accepts every subcommand with its arguments and exit codes, validates the revision and review JSON, and returns mock results. `tests/test_build_check.py` holds every outcome test, marked expected-fail.

## Assumptions
- Verified: plan-check.py's validate handles the schema features the new schemas need: type, required, enum, items, additionalProperties, pattern. (plugins/phased-delivery/scripts/plan-check.py:46, used by plan.schema.json and phase.schema.json)
- Verified: stage-stats.sh reads only trailers, so commits made by a script count exactly like hand-written ones. (plugins/phased-delivery/scripts/stage-stats.sh:20, git log --format with trailers)
- Verified: Check commands run with `sh -c` from the repository root in the session's environment. (decided here; the revise guide (03.1) tells the orchestrator to write checks that run from the repository root)

## Outcome tests
Budget: Under 10 s for test_build_check.py: each test makes one temporary git repository; the plugin's suite stays under a minute.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| After a build that changes only its stage's files and passes the stage's check commands, `build-check.py record` exits 0 and `build-check.py commit` makes one commit holding only that stage's changed files, with Stage, Plan, Tier, Tool, Model, Effort, Attempt, Tokens, Cost and Tool-Calls trailers that `stage-stats.sh` counts as one stage. | `plugins/phased-delivery/tests/test_build_check.py::test_accepted_stage_commit` | 01.3 | 02.2 |
| A build that changes a file outside its stage's files makes `record` exit 1 and print the file under `outside`; the stage is not accepted. | `plugins/phased-delivery/tests/test_build_check.py::test_outside_change_fails` | 01.3 | 02.1 |
| A build whose check command fails makes `record` exit 1; a second attempt on another pair that passes is accepted, and its commit has `Attempt: 2` and one `Earlier-Attempt:` trailer naming the first pair. | `plugins/phased-delivery/tests/test_build_check.py::test_failed_check_then_retry` | 01.3 | 02.2 |
| `build-check.py can-try` exits 1 for a model and effort already tried for the stage, and 0 for one not yet tried or whose only attempt ended in an error (the build never ran to a verdict). | `plugins/phased-delivery/tests/test_build_check.py::test_can_try_refuses_repeat` | 01.3 | 02.1 |
| `build-check.py spend` prints the phase's premium spend in dollars: the cost of every attempt and review recorded as premium, using its cap when the cost is unknown. | `plugins/phased-delivery/tests/test_build_check.py::test_premium_spend` | 01.3 | 02.1 |
| Files already modified when `start` runs are neither counted as outside changes nor included in any stage commit. | `plugins/phased-delivery/tests/test_build_check.py::test_preexisting_edits_left_alone` | 01.3 | 02.2 |
| `start` exits 1 when the revision JSON breaks its schema, and `finish` exits 1 when the review JSON breaks its schema, each printing a JSON line that names the field; nothing is written or committed. | `plugins/phased-delivery/tests/test_build_check.py::test_invalid_json_refused` | 01.3 | 01.3 |
| After every stage is committed and the review JSON is valid, `finish` sets the phase file's status line to `built <commit>`, marks each stage row done, and commits the phase file and the `.build` files with a `Phase:` trailer. | `plugins/phased-delivery/tests/test_build_check.py::test_finish_phase` | 01.3 | 02.2 |
| A fix recorded with `record --fix` for a committed stage is committed with a `Fixes-Stage:` trailer instead of `Stage:`, which `stage-stats.sh` counts as a fix needed for that stage's model. | `plugins/phased-delivery/tests/test_build_check.py::test_fix_commit` | 01.3 | 02.2 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | The revision and review JSON formats exist as schemas in the implement-in-phases skill directory, in the subset plan-check.py's validate understands. | top | first | done |
| 01.2 | `scripts/build-check.py` exists with every subcommand, argument, output line and exit code of its contracts; start and finish validate their JSON for real, the rest return mock results. | top | after 01.1 | done |
| 01.3 | `tests/test_build_check.py` holds every outcome test of the plan's script outcomes, each driving build-check.py in a temporary git repository and marked `xfail(strict=True)` against the mocks. | middle | after 01.2 | done |

## 01.1 Revision and review schemas

Goal: The revision and review JSON formats exist as schemas in the implement-in-phases skill directory, in the subset plan-check.py's validate understands.

Context:
- `plugins/phased-delivery/scripts/plan-check.py:46`: The plugin's stdlib JSON Schema subset; returns (where, msg) pairs.
- `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md:22-43`: The eight current review checks the closed finding types replace.
- Design, Revision: "for each stage, the files it may change,
the check commands that show its "Done when", and its re-scored measures"
- Design, Review: "untraced change, check on internal data, bug or contract
mismatch"

Contracts:
- format `revision JSON` (provides; 01.2, 02.1, 03.1, disk): `<plan>/.build/NN-revision.json` per `revision.schema.json`: {phase, stages: [{id, title, files: [{path, action}], checks: [shell command], scores: "J1F1R0C0K0P0V0S0", tier}], assumptions: [{text, verdict: verified|wrong, evidence}], adjustments: [string]}
- format `review JSON` (provides; 01.2, 02.2, 03.2, disk): `<plan>/.build/NN-review.json`: {findings: [{type: untraced-change|internal-check|bug|not-done|test|assumption|rule|unneeded-code, severity: blocking|should-fix, stage, file, line, evidence, action: remove|fix|plan-gap|question}], verdict: ready|not-ready}

Files:
- `plugins/phased-delivery/skills/implement-in-phases/revision.schema.json` (create): holds the revision JSON schema
- `plugins/phased-delivery/skills/implement-in-phases/review.schema.json` (create): holds the review JSON schema

Behaviour:
- Given a revision with every field filled and each stage's `checks` non-empty, when it is validated against revision.schema.json, then no errors are returned.
- Given a revision stage without a `checks` key, when it is validated against revision.schema.json, then an error names `checks`; an empty list is allowed for a stage verified only by reading.
- Given `scores` not matching eight letter-digit pairs in the order JFRCKPVS, or a `tier` other than small, middle, middle+ or top, when it is validated, then an error names the field.
- Given a review finding whose `type` or `action` is outside its enum, or a finding without `evidence`, when it is validated against review.schema.json, then an error names the field.
- Given any object with an unlisted key, when it is validated, then an error names the key (additionalProperties false everywhere).

External inputs:
none

Tests:
none

Done when:
- Both files parse as JSON and plan-check.py's validate accepts a valid example of each and rejects the cases in Behaviour; 01.3's tests exercise them.

Out of scope:
- phase.schema.json and plan.schema.json
- phase-reviewer.md text (03.2)

Model basis: J1 F1 R0 C2 K1 P1 V0 S0 = 6 -> top (override: J, C or K = 2)

## 01.2 build-check.py interface with mock bodies

Goal: `scripts/build-check.py` exists with every subcommand, argument, output line and exit code of its contracts; start and finish validate their JSON for real, the rest return mock results.

Context:
- Builds on 01.1: revision JSON and review JSON schemas
- `plugins/phased-delivery/scripts/plan-check.py:46`: The plugin's stdlib JSON Schema subset; returns (where, msg) pairs.
- `plugins/phased-delivery/scripts/plan-mode.py:61-63`: How a script loads plan-check.py by path to reuse it.
- `plugins/phased-delivery/scripts/plan-check.py:430-441`: Loads a JSON file and reports schema errors; the pattern for start and finish.
- `plugins/phased-delivery/scripts/plan-check.py:2-22`: Docstring-as-usage and the one-JSON-line-per-problem output to copy.
- Design, Bookkeeping: "The script owns the per-phase ledger"

Contracts:
- format `revision JSON` (uses; 01.1): as 01.1 defines it; read from `<plan>/.build/NN-revision.json`
- format `review JSON` (uses; 01.1): as 01.1 defines it; read from `<plan>/.build/NN-review.json`
- format `ledger JSON` (provides; 02.1, 02.2, disk): `<plan>/.build/NN-ledger.json`: {start_commit, preexisting: [path], attempts: [{stage (id or review), n, fix, tool, model, effort, exit, tokens, cost, cap, tool_calls, premium, result: accepted|failed|stopped|error|rejected, why, commit}]}
- cli `build-check.py start` (provides; 03.1, user): start PHASE_FILE [--repo DIR]: validates the revision; writes the ledger with HEAD and paths modified now, or keeps an existing one. Exit 0; 1 invalid revision or a stage file already modified, one JSON line each; 2 usage.
- cli `build-check.py can-try` (provides; 03.1, user): can-try PHASE_FILE STAGE MODEL EFFORT: exit 1, printing it, when the stage has a failed, stopped, rejected or accepted attempt on the pair; else 0. `error` attempts do not count.
- cli `build-check.py record` (provides; 03.1, user): record PHASE_FILE STAGE|review --tool T --model M --effort E --exit N --tokens X --cost Y [--cap USD] [--tool-calls N] [--premium] [--fix]: logs an attempt and gates it. Exit 0 accepted; 1 failed; 3 budget stop; 4 error.
- cli `build-check.py reject` (provides; 03.1, user): reject PHASE_FILE STAGE WHY: marks the stage's accepted, uncommitted attempt rejected with WHY. Exit 0; 1 no such attempt.
- cli `build-check.py commit` (provides; 03.1, user): commit PHASE_FILE STAGE [--subject-suffix TEXT] [--extra-trailer LINE]...: commits only the stage's changed files with the stage trailers, then marks the row done in the working tree. Prints the hash. Exit 0; 1 nothing accepted.
- cli `build-check.py spend` (provides; 03.1, user): spend PHASE_FILE: prints a bare number, two decimals: the cost of every attempt recorded with --premium (builds and reviews), its cap when the cost is unknown. Exit 0.
- cli `build-check.py finish` (provides; 03.1, user): finish PHASE_FILE [--stopped]: validates the review JSON; sets `Status: built <last stage commit>`; commits the phase file's directory with `Phase: <phase file>`. --stopped skips review and status. Exit 0; 1 invalid review or stage uncommitted; 2 usage.

Files:
- `plugins/phased-delivery/scripts/build-check.py` (create): holds every build-check.py subcommand, the ledger format and the usage docstring

Behaviour:
- Given no arguments, an unknown subcommand or a missing PHASE_FILE, when the script runs, then it prints the usage to stderr and exits 2.
- Given a PHASE_FILE named `NN-name.md`, when any subcommand runs, then it reads and writes `.build/NN-*.json` in the phase file's directory.
- Given a revision that breaks the schema, when `start` runs, then it prints one JSON line per problem naming the field, writes no ledger and exits 1.
- Given a valid revision, when `start` runs, then it writes the ledger (mock: empty preexisting, current HEAD) and exits 0.
- Given a review that breaks the schema, when `finish` runs, then it prints one JSON line per problem and exits 1 without committing.
- Given valid input to record, can-try, reject, commit, spend or finish, when it runs, then it prints a fixed mock result in its contract's output shape and exits 0 (record's JSON line has result `accepted`).

External inputs:
- revision and review JSON written by the orchestrator LLM: schema validation with plan-check.py's validate; on failure, one JSON line per problem, exit 1
- command-line arguments: argparse types and choices; on failure, usage on stderr, exit 2

Tests:
none

Done when:
- `python3 plugins/phased-delivery/scripts/build-check.py --help` prints the usage and each subcommand's `--help` works
- `build-check.py` with no arguments exits 2

Out of scope:
- Real git work, scope checks and check commands (phase 02)
- select-models.py and claude-build.sh

Model basis: J1 F0 R1 C2 K2 P1 V0 S0 = 7 -> top (override: J, C or K = 2)

## 01.3 Outcome tests, expected to fail

Goal: `tests/test_build_check.py` holds every outcome test of the plan's script outcomes, each driving build-check.py in a temporary git repository and marked `xfail(strict=True)` against the mocks.

Context:
- Builds on 01.2: every build-check.py subcommand
- Builds on 01.1: revision JSON and review JSON formats for the fixtures
- `plugins/phased-delivery/tests/test_codex_build.py:6`: The plugin's tests are pytest files that run scripts with subprocess.
- `plugins/phased-delivery/tests/test_claude_build.py:23-38`: Pattern: a helper that builds a temporary directory and runs the script with subprocess.
- `plugins/phased-delivery/scripts/stage-stats.sh:1-5`: The work report the commits must feed; tests run it on the temporary repo.
- `plugins/phased-delivery/hooks/session-start.sh:17-20`: The session hook treats a phase as finished when its Status line starts with built or reviewed.
- Design, Validation: "Offline tests run the script against temporary git repositories with no
model calls."

Contracts:
none

Files:
- `plugins/phased-delivery/tests/test_build_check.py` (create): holds the outcome tests and a fixture that makes a temporary git repository with a plan directory, a phase file and a revision JSON

Behaviour:
- Given the mock script, when the suite runs, then the invalid-JSON test passes with no mark (01.2 validates for real); every other outcome test is xfail and none xpass.
- Given the fixture, when a test starts, then it has a git repository with one commit, a phase file in the rendered layout with one or two stages, and `.build/NN-revision.json` listing each stage's files and checks.

External inputs:
none

Tests:
- writes `plugins/phased-delivery/tests/test_build_check.py::test_accepted_stage_commit` (outcome): After a build that changes only its stage's files and passes the stage's check commands, `build-check.py record` exits 0 and `build-check.py commit` makes one commit holding only that stage's changed files, with Stage, Plan, Tier, Tool, Model, Effort, Attempt, Tokens, Cost and Tool-Calls trailers that `stage-stats.sh` counts as one stage.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_outside_change_fails` (outcome): A build that changes a file outside its stage's files makes `record` exit 1 and print the file under `outside`; the stage is not accepted.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_failed_check_then_retry` (outcome): A build whose check command fails makes `record` exit 1; a second attempt on another pair that passes is accepted, and its commit has `Attempt: 2` and one `Earlier-Attempt:` trailer naming the first pair.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_can_try_refuses_repeat` (outcome): `build-check.py can-try` exits 1 for a model and effort already tried for the stage, and 0 for one not yet tried or whose only attempt ended in an error (the build never ran to a verdict).
- writes `plugins/phased-delivery/tests/test_build_check.py::test_premium_spend` (outcome): `build-check.py spend` prints the phase's premium spend in dollars: the cost of every attempt and review recorded as premium, using its cap when the cost is unknown.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_preexisting_edits_left_alone` (outcome): Files already modified when `start` runs are neither counted as outside changes nor included in any stage commit.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_invalid_json_refused` (outcome): `start` exits 1 when the revision JSON breaks its schema, and `finish` exits 1 when the review JSON breaks its schema, each printing a JSON line that names the field; nothing is written or committed.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_finish_phase` (outcome): After every stage is committed and the review JSON is valid, `finish` sets the phase file's status line to `built <commit>`, marks each stage row done, and commits the phase file and the `.build` files with a `Phase:` trailer.
- writes `plugins/phased-delivery/tests/test_build_check.py::test_fix_commit` (outcome): A fix recorded with `record --fix` for a committed stage is committed with a `Fixes-Stage:` trailer instead of `Stage:`, which `stage-stats.sh` counts as a fix needed for that stage's model.

Done when:
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-bc plugins/phased-delivery/tests/test_build_check.py` exits 0 with one passed test and the rest xfailed
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-bc plugins/phased-delivery/tests` passes as before

Out of scope:
- Tests of select-models.py or claude-build.sh

Model basis: J1 F0 R1 C1 K0 P1 V0 S0 = 4 -> middle

## Notes
- The script is `scripts/build-check.py`, standard library only, and every subcommand takes the phase file path; the plan directory and phase number come from it, the repository from `--repo` (default: the current directory). Reason: Matches plan-check.py and select-models.py; the phase file is what the orchestrator already holds.
- Revision, ledger and review files live in `<plan>/.build/` as `NN-revision.json`, `NN-ledger.json` and `NN-review.json` and are committed with the phase, so a resumed session reads them. Reason: Resume needs the ledger; keeping them next to the plan keeps them out of the code tree.
- Schemas are checked with plan-check.py's `validate`, loaded by path as plan-mode.py and select-models.py already do. Reason: One JSON Schema subset in the plugin; no new dependency.
- The scope check compares uncommitted changes against HEAD (git status, so ignored files are not seen). Not outside: the stage's files, files of other revision stages that have no commit yet, the phase file's whole directory, preexisting paths, and `__pycache__`, `*.pyc` and `.pytest_cache` paths. record lists outside paths on every build result, including a budget stop; the orchestrator restores them before a retry. start refuses (exit 1) when a stage's file is already modified. Reason: Parallel stages, plan regeneration mid-phase and test caches must not fail a stage; a committed stage's files must not change unseen; leftovers must not fail the next attempt.
- A build exit other than 0 and 8 is recorded as `error` (record exit 4): not a try of the pair (can-try ignores it) and no Earlier-Attempt. The orchestrator then applies today's rule for that tool and exit: claude-build.sh stops and reports; a failed Codex build is rebuilt by the routing rule. Reason: Bookkeeping must not blame the model for a build that never reached a verdict; each tool's failure rule keeps its current meaning.
- Stage commits hold only the stage's files; the phase file, `.build/` and any regenerated plan files are updated in the working tree and committed by `finish` (with `--stopped` at a routing stop, which skips the review and completeness checks and leaves the status in progress). Reason: Keeps the design's 'staging only the stage's files'; resume reads the working tree.
- A review is recorded as stage `review`; `spend` counts only attempts recorded with `--premium`, which the build guide sets for premium-pair builds and for every review run by claude-build.sh, never for Codex. Reason: Matches model-selection.md's premium budget rules.
- commit takes `--subject-suffix TEXT` for subject annotations such as `[skip ci]` and `--extra-trailer LINE` for added trailers such as `Co-Authored-By`. Reason: Project rules may require both; today the orchestrator adds them by hand.
- Plan start: ae57d33.
- 2026-11-24: stages built directly by the orchestrator (one script, its schemas and tests; tightly coupled), so commits carry Model: orchestrator and no token counts.
- 2026-11-24: phase 01's review is folded into phase 02's: 01 holds mock bodies that 02 replaces, so reviewing them alone would cost a review for code about to change.
