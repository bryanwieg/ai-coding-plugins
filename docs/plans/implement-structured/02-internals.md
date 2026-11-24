# Phase 02: Check gate and bookkeeping

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: built 1e03273
Before: build-check.py validates the revision and review JSON; every other subcommand returns mock results, and the outcome tests are expected to fail.
After: build-check.py does the real work: it records attempts, gates each build on scope and check commands, refuses repeated pairs, sums premium spend, and makes the stage, fix and phase commits with stage-stats trailers. Every script outcome test passes with no expected-fail mark.

## Assumptions
- Verified: `git status --porcelain --untracked-files=all` lists modified and untracked paths and leaves out ignored ones, which is the baseline the scope check needs. (standard git behaviour; the scope rule is the plan decision on what counts as outside)
- Open: A check command that needs a long run (a full test suite) fits within the stage's test budget. (checked when 03.4 runs a real phase; if checks time out, the revision guide limits checks to the stage's own tests)

## Outcome tests
Budget: Under 10 s for test_build_check.py.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| After a build that changes only its stage's files and passes the stage's check commands, `build-check.py record` exits 0 and `build-check.py commit` makes one commit holding only that stage's changed files, with Stage, Plan, Tier, Tool, Model, Effort, Attempt, Tokens, Cost and Tool-Calls trailers that `stage-stats.sh` counts as one stage. | `plugins/phased-delivery/tests/test_build_check.py::test_accepted_stage_commit` | 01.3 | 02.2 |
| A build that changes a file outside its stage's files makes `record` exit 1 and print the file under `outside`; the stage is not accepted. | `plugins/phased-delivery/tests/test_build_check.py::test_outside_change_fails` | 01.3 | 02.1 |
| A build whose check command fails makes `record` exit 1; a second attempt on another pair that passes is accepted, and its commit has `Attempt: 2` and one `Earlier-Attempt:` trailer naming the first pair. | `plugins/phased-delivery/tests/test_build_check.py::test_failed_check_then_retry` | 01.3 | 02.2 |
| `build-check.py can-try` exits 1 for a model and effort already tried for the stage, and 0 for one not yet tried or whose only attempt ended in an error (the build never ran to a verdict). | `plugins/phased-delivery/tests/test_build_check.py::test_can_try_refuses_repeat` | 01.3 | 02.1 |
| `build-check.py spend` prints the phase's premium spend in dollars: the cost of every attempt and review recorded as premium, using its cap when the cost is unknown. | `plugins/phased-delivery/tests/test_build_check.py::test_premium_spend` | 01.3 | 02.1 |
| Files already modified when `start` runs are neither counted as outside changes nor included in any stage commit. | `plugins/phased-delivery/tests/test_build_check.py::test_preexisting_edits_left_alone` | 01.3 | 02.2 |
| After every stage is committed and the review JSON is valid, `finish` sets the phase file's status line to `built <commit>`, marks each stage row done, and commits the phase file and the `.build` files with a `Phase:` trailer. | `plugins/phased-delivery/tests/test_build_check.py::test_finish_phase` | 01.3 | 02.2 |
| A fix recorded with `record --fix` for a committed stage is committed with a `Fixes-Stage:` trailer instead of `Stage:`, which `stage-stats.sh` counts as a fix needed for that stage's model. | `plugins/phased-delivery/tests/test_build_check.py::test_fix_commit` | 01.3 | 02.2 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 02.1 | start records the real start state, record gates each attempt on scope and check commands, can-try refuses tried pairs and spend sums premium cost. | top | first | done |
| 02.2 | commit, reject and finish make the stage, fix and phase commits with the trailers stage-stats.sh reads, and update the phase file's stage table and status line. | top | after 02.1 | done |

## 02.1 Start, record, can-try and spend

Goal: start records the real start state, record gates each attempt on scope and check commands, can-try refuses tried pairs and spend sums premium cost.

Context:
- Builds on 01.2: build-check.py start, can-try, record and spend with mock bodies; the ledger JSON format
- Builds on 01.1: revision JSON: each stage's files and checks
- Builds on 01.3: the outcome tests to turn on
- `plugins/phased-delivery/scripts/claude-build.sh:14-19`: The build exit codes record receives; 8 is a budget stop.
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:218-225`: Premium spend counts each premium run's Cost, or its cap_usd when unknown, and every review.
- `plugins/phased-delivery/tests/test_codex_build.py:6`: The plugin's tests are pytest files run with pytest.
- Design, Check gate: "no file outside the stage's files changed (edits present before the phase do not count), and every
check command passes"

Contracts:
- format `revision JSON` (uses; 01.1): as 01.1 defines it
- format `ledger JSON` (uses; 01.2): as 01.2 defines it

Files:
- `plugins/phased-delivery/scripts/build-check.py` (edit): start, can-try, record and spend do their real work
- `plugins/phased-delivery/tests/test_build_check.py` (edit): the three outcome tests this stage makes pass lose their expected-fail marks

Behaviour:
- Given tracked or untracked paths already modified, when start writes a new ledger, then they are stored in `preexisting` with HEAD as `start_commit`, unless one is a stage's file, which makes start exit 1 naming it; an existing ledger is kept as it is.
- Given a build attempt with exit 0, when record runs, then each uncommitted path that is not allowed by the scope rule in the Notes is listed in `outside`; any listed path fails the attempt.
- Given a build attempt with exit 0 and no outside path, when record runs, then each of the stage's checks runs with `sh -c` in the repository root; any non-zero exit fails the attempt; the JSON line lists each command with its exit.
- Given build exit 8, or another non-zero exit, when record runs, then 8 is stored as `stopped` (why `budget reached`, exit 3) and any other as `error` (exit 4); no checks run, and `outside` still lists stray paths.
- Given stage `review`, when record runs, then it is stored for spend only; no scope check or checks run; exit 0.
- Given attempts on the stage, when can-try runs for a model and effort, then it exits 1 if a non-error attempt used that pair, else 0.
- Given attempts recorded with and without `--premium`, when spend runs, then it prints the sum over the `--premium` ones of the cost, or the cap when the cost is unknown, as a bare number with two decimals.

External inputs:
- --tokens and --cost values copied from the build script's output: a number or `unknown`; on failure, usage on stderr, exit 2

Tests:
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_outside_change_fails` (outcome): A build that changes a file outside its stage's files makes `record` exit 1 and print the file under `outside`; the stage is not accepted.
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_can_try_refuses_repeat` (outcome): `build-check.py can-try` exits 1 for a model and effort already tried for the stage, and 0 for one not yet tried or whose only attempt ended in an error (the build never ran to a verdict).
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_premium_spend` (outcome): `build-check.py spend` prints the phase's premium spend in dollars: the cost of every attempt and review recorded as premium, using its cap when the cost is unknown.

Done when:
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-bc plugins/phased-delivery/tests/test_build_check.py` passes, with the outcome tests for outside changes, repeated pairs and premium spend no longer expected to fail
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-bc plugins/phased-delivery/tests` passes

Out of scope:
- commit, reject and finish (02.2)
- select-models.py route

Model basis: J1 F1 R1 C1 K2 P1 V0 S0 = 7 -> top (override: J, C or K = 2)

## 02.2 Commit, reject and finish

Goal: commit, reject and finish make the stage, fix and phase commits with the trailers stage-stats.sh reads, and update the phase file's stage table and status line.

Context:
- Builds on 02.1: the ledger filled with real attempts and results
- Builds on 01.1: review JSON schema
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md:118-150`: The stage commit trailers, the Attempt count and the Earlier-Attempt format the commits must carry.
- `plugins/phased-delivery/scripts/stage-stats.sh:20`: stage-stats.sh reads Stage, Fixes-Stage, Model, Effort, Attempt, Tokens, Earlier-Attempt and Tool trailers.
- `plugins/phased-delivery/hooks/session-start.sh:17-20`: A phase is finished for the session hook when its Status line starts with built or reviewed.
- `plugins/phased-delivery/skills/plan-in-phases/phase-file-template.md:8`: The Status line values the script writes.
- `plugins/phased-delivery/scripts/plan-check.py:386-388`: The rendered stage table whose last cell the script sets.
- Design, Bookkeeping: "makes each stage commit (staging only the stage's
files, with the trailers from the ledger)"

Contracts:
- format `review JSON` (uses; 01.1): as 01.1 defines it
- format `ledger JSON` (uses; 01.2): as 01.2 defines it
- format `stage commit trailers` (uses; plugins/phased-delivery/scripts/stage-stats.sh): Stage or Fixes-Stage, Plan, Tier, Tool, Model, Effort, Attempt, Tokens, Cost, Tool-Calls, and `Earlier-Attempt: <model> <effort> <tokens> <why>` per failed try

Files:
- `plugins/phased-delivery/scripts/build-check.py` (edit): commit, reject and finish do their real work
- `plugins/phased-delivery/tests/test_build_check.py` (edit): the remaining outcome tests lose their expected-fail marks

Behaviour:
- Given an accepted, uncommitted build attempt, when commit runs, then it stages only the stage's files that changed (minus preexisting) and commits with subject `NN.n <title>` plus any `--subject-suffix`, the trailers and any `--extra-trailer` lines; Attempt counts the stage's non-error attempts; each failed, stopped or rejected earlier one adds an Earlier-Attempt with its why.
- Given the commit is made, when the phase file is updated in the working tree, then the stage's row Status cell reads `done`, the Status line reads `in progress (stages done: <ids>)`, and the ledger stores the commit hash; neither file is committed here.
- Given an accepted fix attempt, when commit runs, then the trailer is `Fixes-Stage: NN.n` instead of `Stage:`, with that fix's Model, Effort and Tokens.
- Given no accepted, uncommitted attempt for the stage, when commit or reject runs, then it exits 1 and changes nothing.
- Given an accepted attempt the orchestrator rejects with a reason, when reject runs, then the attempt becomes `rejected` with that why and counts as an Earlier-Attempt.
- Given every stage committed and a valid review JSON, when finish runs, then the Status line reads `built <last stage commit short hash>` and one commit holds the phase file's directory with `Phase: <phase file>`; with `--stopped` it commits the directory without those checks or the status change.
- Given a stage without a commit or an invalid review, when finish runs, then it exits 1 and HEAD is unchanged.

External inputs:
- review JSON written by the reviewing agent: review.schema.json; on failure, one JSON line per problem, exit 1

Tests:
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_accepted_stage_commit` (outcome): After a build that changes only its stage's files and passes the stage's check commands, `build-check.py record` exits 0 and `build-check.py commit` makes one commit holding only that stage's changed files, with Stage, Plan, Tier, Tool, Model, Effort, Attempt, Tokens, Cost and Tool-Calls trailers that `stage-stats.sh` counts as one stage.
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_failed_check_then_retry` (outcome): A build whose check command fails makes `record` exit 1; a second attempt on another pair that passes is accepted, and its commit has `Attempt: 2` and one `Earlier-Attempt:` trailer naming the first pair.
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_preexisting_edits_left_alone` (outcome): Files already modified when `start` runs are neither counted as outside changes nor included in any stage commit.
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_finish_phase` (outcome): After every stage is committed and the review JSON is valid, `finish` sets the phase file's status line to `built <commit>`, marks each stage row done, and commits the phase file and the `.build` files with a `Phase:` trailer.
- turns on `plugins/phased-delivery/tests/test_build_check.py::test_fix_commit` (outcome): A fix recorded with `record --fix` for a committed stage is committed with a `Fixes-Stage:` trailer instead of `Stage:`, which `stage-stats.sh` counts as a fix needed for that stage's model.

Done when:
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-bc plugins/phased-delivery/tests/test_build_check.py` passes with no expected-fail mark left
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-bc plugins/phased-delivery/tests` passes
- `sh plugins/phased-delivery/scripts/stage-stats.sh` on a test repository counts the script's commits (shown by the accepted-stage and fix tests)

Out of scope:
- stage-stats.sh
- The skill text (phase 03)

Model basis: J1 F1 R1 C1 K2 P1 V0 S0 = 7 -> top (override: J, C or K = 2)

## Notes
- The script is `scripts/build-check.py`, standard library only, and every subcommand takes the phase file path; the plan directory and phase number come from it, the repository from `--repo` (default: the current directory). Reason: Matches plan-check.py and select-models.py; the phase file is what the orchestrator already holds.
- Revision, ledger and review files live in `<plan>/.build/` as `NN-revision.json`, `NN-ledger.json` and `NN-review.json` and are committed with the phase, so a resumed session reads them. Reason: Resume needs the ledger; keeping them next to the plan keeps them out of the code tree.
- Schemas are checked with plan-check.py's `validate`, loaded by path as plan-mode.py and select-models.py already do. Reason: One JSON Schema subset in the plugin; no new dependency.
- The scope check compares uncommitted changes against HEAD (git status, so ignored files are not seen). Not outside: the stage's files, files of other revision stages that have no commit yet, the phase file's whole directory, preexisting paths, and `__pycache__`, `*.pyc` and `.pytest_cache` paths. record lists outside paths on every build result, including a budget stop; the orchestrator restores them before a retry. start refuses (exit 1) when a stage's file is already modified. Reason: Parallel stages, plan regeneration mid-phase and test caches must not fail a stage; a committed stage's files must not change unseen; leftovers must not fail the next attempt.
- A build exit other than 0 and 8 is recorded as `error` (record exit 4): not a try of the pair (can-try ignores it) and no Earlier-Attempt. The orchestrator then applies today's rule for that tool and exit: claude-build.sh stops and reports; a failed Codex build is rebuilt by the routing rule. Reason: Bookkeeping must not blame the model for a build that never reached a verdict; each tool's failure rule keeps its current meaning.
- Stage commits hold only the stage's files; the phase file, `.build/` and any regenerated plan files are updated in the working tree and committed by `finish` (with `--stopped` at a routing stop, which skips the review and completeness checks and leaves the status in progress). Reason: Keeps the design's 'staging only the stage's files'; resume reads the working tree.
- A review is recorded as stage `review`; `spend` counts only attempts recorded with `--premium`, which the build guide sets for premium-pair builds and for every review run by claude-build.sh, never for Codex. Reason: Matches model-selection.md's premium budget rules.
- commit takes `--subject-suffix TEXT` for subject annotations such as `[skip ci]` and `--extra-trailer LINE` for added trailers such as `Co-Authored-By`. Reason: Project rules may require both; today the orchestrator adds them by hand.
- 2026-11-24: stages built directly by the orchestrator, as in phase 01.
- 2026-11-24: review of phases 01 and 02 together (fable high, in-session subagent): ready, 0 blocking, 12 should-fix. Fixed in 4312f37 (02.1: rename sources count as changed, attempt numbers skip committed tries, real paths and a root-level plan directory, script errors exit 2) and 1e03273 (02.2: reasons folded to one line in trailers, fix commits leave the status line alone, finish marks rows done and names the last stage commit by git order). Added tests for renames and for reject, budget stop and retry.
- 2026-11-24: contract additions from the review: the ledger's result may be `review`; finish takes `--extra-trailer LINE` like commit.
- 2026-11-24: open: check commands run with no timeout; kept until 03.4 shows whether long checks matter.
