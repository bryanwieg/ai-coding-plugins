# Phase 03: Skill guides, closed review and validation

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: implement-in-phases is one 231-line prose SKILL.md; the orchestrator keeps attempts, trailers and premium spend by hand; the phase reviewer has an open list of checks and writes prose findings. build-check.py works but no skill uses it.
After: SKILL.md is short and sends each step to its guide (revise-guide.md, build-guide.md, phase-reviewer.md); the orchestrator writes the revision JSON, calls build-check.py for every gate, commit and spend, and the reviewer writes review JSON with closed finding types. A notes file records why, and the driver-script option as a todo. One paid run shows the skill builds a real phase.

## Assumptions
- Verified: Nothing outside the skill parses implement-in-phases SKILL.md headings; the hooks only name the skill. (plugins/phased-delivery/hooks/session-start.sh:27 and prompt-reminder.sh mention the skill by name only)
- Verified: The builder evals copy only stage-builder.md, so the restructure does not change them. (evals/lib/make-repo.sh:14 copies DIRECTIONS into stage-builder.md)
- Open: A headless session can load the branch's plugin with `claude --plugin-dir`. (checked at the start of 03.4 with `claude --help`; if it cannot, the run copies the branch's skill into the run repository's plugin directory instead)

## Outcome tests
Budget: The plugin suite stays under a minute; 03.4's paid run has a ceiling of about $8 (session $2.40 plus the stage and review caps) and runs once.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| An Opus session at medium thinking, given the restructured skill and the p2-multistep eval task as a one-phase plan in a git repository, builds it through build-check.py: the task's three files pass the hidden check and the stage commit carries the trailers. | `evals/tasks/p2-multistep/check.sh::run repo of 03.4` | 03.4 | 03.4 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 03.1 | SKILL.md is a short outline that sends revising to revise-guide.md and building, routing, failures and commits to build-guide.md, with every bookkeeping step done through build-check.py. | top | first | planned |
| 03.2 | phase-reviewer.md limits findings to the closed types and has the reviewer write the review JSON. | middle+ | parallel with 03.1 | planned |
| 03.3 | A notes file explains why implementation uses JSON, a script gate and closed review types, and records the driver script as a todo; the README and plugin version describe the change. | middle | after 03.1 | planned |
| 03.4 | One paid run of the restructured skill, built in this session, implements the p2-multistep eval task as a one-phase plan, and its result is recorded in the notes file. | middle+ | after 03.3 | planned |

## 03.1 Thin SKILL.md and step guides

Goal: SKILL.md is a short outline that sends revising to revise-guide.md and building, routing, failures and commits to build-guide.md, with every bookkeeping step done through build-check.py.

Context:
- Builds on 01.1: revision JSON format the revise guide tells the orchestrator to write
- Builds on 02.2: build-check.py with every subcommand working
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md:30-44`: The revision rules that move to revise-guide.md.
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md:46-116`: Routing, failure ladder, premium spend and Codex rules that move to build-guide.md.
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md:118-156`: Hand-written trailers, replaced by build-check.py commit.
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:218-225`: Describes the hand-kept Premium spend Notes line; becomes build-check.py spend.
- `plugins/phased-delivery/skills/plan-in-phases/SKILL.md:131-143`: The pattern to mirror: a short step that names the guide and the script.
- Design, What stays the same: "They move from
SKILL.md into guides or into the script, not into new rules."
- Design, Check gate: "The orchestrator cannot accept a
stage past a failing check; it may still reject one that passes."

Contracts:
- format `revision JSON` (uses; 01.1): as 01.1 defines it
- cli `build-check.py start` (uses; 01.2): as 01.2 defines it
- cli `build-check.py can-try` (uses; 01.2): as 01.2 defines it
- cli `build-check.py record` (uses; 01.2): as 01.2 defines it
- cli `build-check.py reject` (uses; 01.2): as 01.2 defines it
- cli `build-check.py commit` (uses; 01.2): as 01.2 defines it
- cli `build-check.py spend` (uses; 01.2): as 01.2 defines it
- cli `build-check.py finish` (uses; 01.2): as 01.2 defines it
- cli `select-models.py route` (uses; plugins/phased-delivery/scripts/select-models.py): route AVAILABLE.json --scores J1F1R0C0K0P0V0S0 [--down N | --up N] [--premium-spent USD] [--review]: one JSON line {model, effort, tier, premium, score, cap_tokens, cap_usd, why}
- cli `claude-build.sh` (uses; plugins/phased-delivery/scripts/claude-build.sh): claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR: prints `Tokens: N` and `Cost: X.XX`; exit 0 built, 2 usage, 8 budget reached

Files:
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md` (edit): the short outline: before the first phase, each phase's steps, the stop and report, the work report, corrections; each step names its guide and script
- `plugins/phased-delivery/skills/implement-in-phases/revise-guide.md` (create): how to revise the phase file against the repository and write the revision JSON, field by field
- `plugins/phased-delivery/skills/implement-in-phases/build-guide.md` (create): routing, dispatch, the failure ladder, Codex rules and the build-check.py calls for gate, reject, commit and spend
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md` (edit): its premium budget and Earlier-Attempt lines name build-check.py instead of hand-kept Notes

Behaviour:
- Given a phase to build, when the orchestrator follows SKILL.md, then it revises, writes `.build/NN-revision.json`, and runs `build-check.py start` before the first dispatch.
- Given a pair route prints, when the orchestrator dispatches, then it runs `can-try` first; on exit 1 it follows the existing rule for a pair already tried (revise the plan).
- Given a finished build, when the orchestrator checks it, then it runs `record`; exit 1 or 3 means restore the outside paths, then `route --up 1` or `route --down 1`; exit 4 means today's rule for that tool and exit; only exit 0 may be committed.
- Given `route` needs the premium spend, when the orchestrator calls it, then it passes `build-check.py spend` output as `--premium-spent`.
- Given SKILL.md, when it is read, then every rule it held before is in it or in a guide it links, with the same meaning; it holds no trailer list or spend arithmetic.
- Given a routing stop after every stage but before the review, when the orchestrator stops, then it sets the Status line to `in progress (stages done: all; review pending)` and runs `finish --stopped`; a capped review is judged by claude-build.sh's own exit, as today.

External inputs:
none

Tests:
none

Done when:
- `wc -l` shows SKILL.md under 110 lines
- Every relative link in SKILL.md, revise-guide.md and build-guide.md resolves to an existing file
- A side-by-side read of the old SKILL.md finds each of its rules in the new files (recorded in the phase Notes)

Out of scope:
- stage-builder.md (unchanged, the builder evals measure it)
- select-models.py and the routing rules' meaning
- phase-reviewer.md (03.2)

Model basis: J2 F1 R1 C1 K1 P1 V2 S0 = 9 -> top (override: J, C or K = 2)

## 03.2 Phase reviewer with closed finding types

Goal: phase-reviewer.md limits findings to the closed types and has the reviewer write the review JSON.

Context:
- Builds on 01.1: review JSON format and its finding types
- `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md:22-43`: The eight open checks to map onto the closed types; Simplicity is narrowed to unneeded code.
- `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md:45-60`: The prose report and remove/fix/plan-gap actions the JSON replaces.
- `plugins/phased-delivery/skills/plan-in-phases/plan-reviewer.md:20-24`: The plan reviewer's closed-type wording to mirror.
- Design, Review: "The open-ended
"a simpler structure exists" check is dropped."

Contracts:
- format `review JSON` (uses; 01.1): as 01.1 defines it

Files:
- `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md` (edit): closed finding types with what counts as evidence for each, where to look, and the review JSON as its only output

Behaviour:
- Given a reviewer following phase-reviewer.md, when it reports, then it writes `.build/NN-review.json` that passes review.schema.json, one finding per problem of a listed type, and nothing else.
- Given a structure the reviewer thinks could be simpler but no code is unused, unasked-for or duplicated, when it reviews, then it is not a finding.
- Given a finding needing something the plan lacks, when it is written, then its action is `plan-gap`, and anything the reviewer would add is a `question`.
- Given a change in the plan directory other than the phase file's status, table and Notes and the `.build` files, when the reviewer reads the diff, then it is an untraced change.

External inputs:
none

Tests:
none

Done when:
- Each of the eight types in review.schema.json is defined in phase-reviewer.md with its evidence
- The reviewer's inputs still name the phase file, diff, pre-existing edits and project instructions

Out of scope:
- The review routing (`route --review`) and who runs the review

Model basis: J1 F0 R1 C1 K0 P0 V2 S0 = 5 -> middle+ (override: middle with a measure at 2)

## 03.3 Notes, driver todo, README and version

Goal: A notes file explains why implementation uses JSON, a script gate and closed review types, and records the driver script as a todo; the README and plugin version describe the change.

Context:
- Builds on 03.1: the new guides and build-check.py usage to describe
- `plugins/phased-delivery/skills/plan-in-phases/structured-planning-notes.md:1-5`: The notes file to mirror for implementation.
- `README.md:195-200`: The README section describing how trailers are written today.
- `plugins/phased-delivery/.claude-plugin/plugin.json:3`: Version to raise to 0.11.0.
- Design, Later: "the draft on the `plan-phase-driver` branch) is recorded as a todo
for later investigation"

Contracts:
none

Files:
- `plugins/phased-delivery/skills/implement-in-phases/structured-implementation-notes.md` (create): why the restructure, what it replaced, and a Later section with the driver-script todo and its trade-offs, pointing at the plan-phase-driver branch
- `README.md` (edit): the phased-delivery section names build-check.py and the step guides
- `plugins/phased-delivery/.claude-plugin/plugin.json` (edit): version 0.11.0

Behaviour:
- Given a maintainer wondering whether to build the driver, when they read the notes file's Later section, then it names the plan-phase-driver branch, what the driver would add, what it would cost, and what to measure first.

External inputs:
none

Tests:
none

Done when:
- `grep -n plan-phase-driver` finds the todo in structured-implementation-notes.md
- plugin.json version is 0.11.0

Out of scope:
- Deleting or changing the plan-phase-driver branch

Model basis: J1 F1 R1 C0 K0 P0 V1 S0 = 4 -> middle

## 03.4 Paid end-to-end run on p2-multistep

Goal: One paid run of the restructured skill, built in this session, implements the p2-multistep eval task as a one-phase plan, and its result is recorded in the notes file.

Context:
- Builds on 03.1: the restructured skill
- Builds on 03.3: the notes file to record the result in
- `evals/new-run.sh:2-4`: Makes the run repository with the task's phase file in plan/.
- `evals/lib/make-repo.sh:18-19`: The phase file lands at plan/01-<task>.md.
- `evals/README.md:93-99`: Runs use EVAL_HOME in /cache because /tmp is noexec.
- `evals/lib/scope.py:9-16`: The hidden check fails on any file outside files.txt, so it runs on a copy holding only the task's files.
- Design, Validation: "it runs only after the user
confirms its cost"

Contracts:
none

Files:
- `plugins/phased-delivery/skills/implement-in-phases/structured-implementation-notes.md` (edit): a Measured section with the run's result, cost and what went wrong

Behaviour:
- Given the user's ceiling of about $8, when the run is set up, then `new-run.sh p2-multistep` makes the repository; it gets a models-available.json offering only opus and haiku, a models.md regenerated by the branch's selector (`check` exits 0), project rules that allow git and plan edits and say only opus and haiku are available, then `git init` and one commit.
- Given that repository, when the run starts, then a headless Opus session at medium thinking with `--plugin-dir` set to the branch's plugin, the installed phased-delivery turned off through `--settings`, and `--max-budget-usd 2.40` is asked to implement its plan, naming the branch's scripts by absolute path.
- Given the run ends, when it is checked, then the three files in the task's files.txt are copied onto a fresh `new-run.sh p2-multistep` repository and `sh collect.sh` runs there; the RESULT line, the commits and trailers in the built repository, the total cost and any skill rule the session skipped are recorded.

External inputs:
none

Tests:
- writes `evals/tasks/p2-multistep/check.sh::run repo of 03.4` (outcome): An Opus session at medium thinking, given the restructured skill and the p2-multistep eval task as a one-phase plan in a git repository, builds it through build-check.py: the task's three files pass the hidden check and the stage commit carries the trailers.

Done when:
- The notes file's Measured section records the run: check result, commits with trailers, cost
- The user has seen the result

Out of scope:
- Old-versus-new comparison runs
- Changing the eval tasks

Model basis: J1 F0 R1 C0 K0 P1 V1 S2 = 6 -> middle+ (override: middle with a measure at 2)

## Notes
- The script is `scripts/build-check.py`, standard library only, and every subcommand takes the phase file path; the plan directory and phase number come from it, the repository from `--repo` (default: the current directory). Reason: Matches plan-check.py and select-models.py; the phase file is what the orchestrator already holds.
- Revision, ledger and review files live in `<plan>/.build/` as `NN-revision.json`, `NN-ledger.json` and `NN-review.json` and are committed with the phase, so a resumed session reads them. Reason: Resume needs the ledger; keeping them next to the plan keeps them out of the code tree.
- stage-builder.md does not change. Reason: The builder evals measure it; changing it would break comparison with earlier runs.
- Routing, the retry ladder, caps, premium budget and Codex rules keep their meaning and move into build-guide.md; only who keeps the numbers changes. Reason: Agreed scope: restructure, not new rules.
- The scope check compares uncommitted changes against HEAD (git status, so ignored files are not seen). Not outside: the stage's files, files of other revision stages that have no commit yet, the phase file's whole directory, preexisting paths, and `__pycache__`, `*.pyc` and `.pytest_cache` paths. record lists outside paths on every build result, including a budget stop; the orchestrator restores them before a retry. start refuses (exit 1) when a stage's file is already modified. Reason: Parallel stages, plan regeneration mid-phase and test caches must not fail a stage; a committed stage's files must not change unseen; leftovers must not fail the next attempt.
- A build exit other than 0 and 8 is recorded as `error` (record exit 4): not a try of the pair (can-try ignores it) and no Earlier-Attempt. The orchestrator then applies today's rule for that tool and exit: claude-build.sh stops and reports; a failed Codex build is rebuilt by the routing rule. Reason: Bookkeeping must not blame the model for a build that never reached a verdict; each tool's failure rule keeps its current meaning.
- Stage commits hold only the stage's files; the phase file, `.build/` and any regenerated plan files are updated in the working tree and committed by `finish` (with `--stopped` at a routing stop, which skips the review and completeness checks and leaves the status in progress). Reason: Keeps the design's 'staging only the stage's files'; resume reads the working tree.
- A review is recorded as stage `review`; `spend` counts only attempts recorded with `--premium`, which the build guide sets for premium-pair builds and for every review run by claude-build.sh, never for Codex. Reason: Matches model-selection.md's premium budget rules.
- commit takes `--subject-suffix TEXT` for subject annotations such as `[skip ci]` and `--extra-trailer LINE` for added trailers such as `Co-Authored-By`. Reason: Project rules may require both; today the orchestrator adds them by hand.
