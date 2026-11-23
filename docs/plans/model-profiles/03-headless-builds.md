# Phase 03: Headless builds and cutover

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: built 63de83b
Before: Claude stages are built by in-session subagents with no hard stop, and the skills map a stage to its tier's single pair from models.md, refreshed before every phase.
After: Claude stages and reviews are built headless by `claude-build.sh`, each stopped at its dollar cap. implement-in-phases routes every dispatch through `select-models.py route`, reruns the selector only when `check` says models.md is out of date, drops one step after a capped-out build, tracks premium spend per phase, and keeps reviews on top. The docs describe the weekly, change-only refresh.

## Assumptions
- Verified: `claude -p` accepts --model, --effort, --max-budget-usd, --settings as a JSON string, --permission-mode, --no-session-persistence and stream-json output. (claude --help (2.1.329) lists each flag and says --settings takes a file or a JSON string; evals/mode/estimate.py:52-56 runs the same flags with a settings file)
- Verified: A run stopped by the budget ends with a result event of subtype `error_max_budget_usd`. (the result schema in the installed claude 2.1.329 binary lists error_during_execution, error_max_turns, error_max_budget_usd)
- Open: `--max-budget-usd` stops runs signed in with a subscription, not only API-key runs, and `total_cost_usd` is reported there. (Needs one real run of a few cents; ask the user, then run claude-build.sh on a trivial prompt with a $0.01 cap after 03.1. If it does not stop, the cap needs a token watch on stream.jsonl instead, and the plan returns to 03.1.)
- Open: With acceptEdits, a headless builder can edit files and run the commands the project's settings allow, such as `python3 -m pytest` once allowed. (Checked on the same trivial run as the budget assumption, after 03.1 and with the user's approval; if edits are still refused, revise 03.1's default with the user.)

## Outcome tests
Budget: python3 -m pytest -q plugins/phased-delivery/tests runs in under a minute.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| `scripts/claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR` runs `claude -p` with that model, effort and `--max-budget-usd`, writes `report.md`, and prints `Tokens: N` and `Cost: X.XX`. A run stopped by the budget exits 8. | `plugins/phased-delivery/tests/test_claude_build.py::test_outcomes` | 03.1 | 03.1 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 03.1 | `claude-build.sh` builds one stage with `claude -p` at a given model, effort and dollar cap, and reports tokens, cost and a budget stop the way codex-build.sh reports its results. | top | first | done |
| 03.2 | The skills, README and routing notes use profiles, `check`, `route` and claude-build.sh, with the limits, and describe the weekly change-only refresh. | top | after 03.1 | done |

## 03.1 claude-build.sh

Goal: `claude-build.sh` builds one stage with `claude -p` at a given model, effort and dollar cap, and reports tokens, cost and a budget stop the way codex-build.sh reports its results.

Context:
- `plugins/phased-delivery/scripts/codex-build.sh:1-22`: The header and argument contract to mirror: prompt file outside REPO, OUTDIR with report.md, exit codes, never commits.
- `plugins/phased-delivery/scripts/codex-build.sh:24-31`: Usage check and an environment switch with two allowed values, exit 2 otherwise.
- `plugins/phased-delivery/scripts/codex-build.sh:40-59`: Reads the JSON events with an inline Python step and prints the token line.
- `evals/mode/estimate.py:52-56`: A working headless claude -p call with model, effort, settings, permission mode, budget and stream-json.
- `plugins/phased-delivery/tests/test_codex_build.py:16-29`: The test pattern: a stub CLI on PATH that prints canned events.
- Design, Limits: "Claude stage builds run headless through claude-build.sh with a budget"
- Design, Limits: "File edits are allowed and commands follow the project's own permission"

Contracts:
- cli `claude-build.sh` (provides; 03.2): claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR: writes OUTDIR/report.md, stream.jsonl, stderr.txt; prints 'Tokens: N' and 'Cost: X.XX' (or unknown); exit 0 built, 2 usage, 8 budget reached, else claude's status; never commits
- config `CLAUDE_BUILD_PERMISSIONS` (provides; user): environment variable read by claude-build.sh; unset: --permission-mode acceptEdits, commands follow the project's allow rules; bypassPermissions: passed as --permission-mode, for sessions already in a sandbox container; any other value: exit 2

Files:
- `plugins/phased-delivery/scripts/claude-build.sh` (create): the headless Claude builder
- `plugins/phased-delivery/tests/test_claude_build.py` (create): its outcome test with a stub `claude`

Behaviour:
- Given six arguments, when it runs, then it runs `claude -p` in REPO with PROMPT's text as the prompt, `--model`, `--effort`, `--max-budget-usd` BUDGET_USD, `--settings` turning `phased-delivery@ai-coding-plugins` off, `--no-session-persistence` and `--output-format stream-json --verbose`; stdin is empty.
- Given any other argument count, when it runs, then it prints its header and exits 2.
- Given CLAUDE_BUILD_PERMISSIONS unset, when it runs, then `--permission-mode acceptEdits` is passed; set to `bypassPermissions`, that mode is passed instead; any other value exits 2 before running claude.
- Given the run's result event, when it finishes, then report.md holds the result text, and it prints `Tokens: N` (input, output, cache read and cache creation tokens summed) and `Cost: X.XX` from `total_cost_usd`, each `unknown` when absent.
- Given a result of subtype `error_max_budget_usd`, when it finishes, then it prints that the budget was reached and exits 8.
- Given no result event, when it finishes, then it prints the last stderr line and exits with claude's status, or 1 if that was 0.

External inputs:
- claude's stream-json output: lines that are not JSON objects are skipped; the last `result` event decides; on failure, missing fields print `unknown`

Tests:
- writes `plugins/phased-delivery/tests/test_claude_build.py::test_outcomes` (outcome): `scripts/claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR` runs `claude -p` with that model, effort and `--max-budget-usd`, writes `report.md`, and prints `Tokens: N` and `Cost: X.XX`. A run stopped by the budget exits 8.

Done when:
- `sh -n plugins/phased-delivery/scripts/claude-build.sh` passes.
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.

Out of scope:
- codex-build.sh.
- Committing, routing or retrying; the orchestrator does those.

Model basis: J1 F1 R1 C1 K2 P0 V0 S0 = 6 -> top (override: J, C or K = 2)

## 03.2 skills and docs switch to routing

Goal: The skills, README and routing notes use profiles, `check`, `route` and claude-build.sh, with the limits, and describe the weekly change-only refresh.

Context:
- Builds on 01.2: `select-models.py` reading profiles and `select-models.py check`
- Builds on 02.1: `select-models.py route` with `--down`, `--up`, `--premium-spent` and `--review`
- Builds on 03.1: `claude-build.sh` and `CLAUDE_BUILD_PERMISSIONS`
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:63-68`: Says the selector reads model-report.json, refreshed daily.
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:131-143`: The exit 3 fallback for a stale report, and the rerun before each phase.
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:296-309`: Escalation on failure, to become route --up 1.
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md:54-64`: Refreshes models-available.json and reruns the selector before every phase, then maps tiers to models.md.
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md:96-106`: The stage commit trailers.
- `plugins/phased-delivery/skills/plan-in-phases/plan-reviewer.md:79-81`: The reviewer reruns the selector to check models.md.
- `README.md:59-68`: Describes the daily refresh.
- `docs/model-routing.md:57`: Describes the daily refresh.
- Design, Limits: "Their cost is counted against the"
- Design, Routing: "Tiers stay in plans as a summary, so a plan still moves between tools."

Contracts:
- cli `select-models.py` (uses; 01.2): select-models.py AVAILABLE.json [--profiles FILE] [--out models.md] [--json FILE] [--today ignored]; models.md gains a 'Profiles: <fingerprint>' line; exit 0 written, 2 bad input, 3 profiles missing, 4 nothing selectable; no age check
- cli `select-models.py check` (uses; 01.2): select-models.py check MODELS_MD [--profiles FILE]: exit 0 when the Profiles line matches the profiles' fingerprint, 1 when it differs or is missing (rerun the selector), 3 profiles missing
- cli `select-models.py route` (uses; 02.1): route AVAILABLE.json --scores J1F1R0C0K0P0V0S0 [--down N | --up N] [--premium-spent USD] [--review] [--profiles FILE]: one JSON line {model, effort, tier, premium, score, cap_tokens, cap_usd, why}; exit 0, 2 bad input, 3 no profiles, 4 none
- cli `claude-build.sh` (uses; 03.1): claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR: writes OUTDIR/report.md, stream.jsonl, stderr.txt; prints 'Tokens: N' and 'Cost: X.XX' (or unknown); exit 0 built, 2 usage, 8 budget reached, else claude's status; never commits

Files:
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md` (edit): describes profiles, check, route, the routing rules, the limits and claude-build.sh
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md` (edit): dispatches every build and review through route and claude-build.sh, with the limits
- `plugins/phased-delivery/skills/plan-in-phases/plan-reviewer.md` (edit): checks models.md against the profiles with `check`
- `README.md` (edit): describes the weekly change-only refresh, profiles, routing and claude-build.sh
- `docs/model-routing.md` (edit): records the routing rules, the research behind them and the cutoffs still to calibrate
- `plugins/phased-delivery/.claude-plugin/plugin.json` (edit): version 0.10.0

Behaviour:
- Given the start of a phase, when the implementer follows SKILL.md, then it runs `select-models.py check` on models.md and refreshes models-available.json and reruns the selector only on exit 1, or when a dispatch fails because a model is unavailable.
- Given a stage to build, when the implementer dispatches it, then it runs `route` with the brief's Model basis and the phase's premium spend, and builds a Claude stage with `claude-build.sh` at the printed model, effort and `cap_usd`; Codex dispatch stays as it is, with route run on models-available-codex.json.
- Given claude-build.sh exits 8, when the stage is retried, then the next attempt uses `route --down 1` (counting further steps on further stops) and is recorded as an Earlier-Attempt.
- Given a build that fails its Done when or is harder than its tier, when it is retried, then the next attempt uses `route --up 1` instead of the next tier.
- Given each claude-build.sh run of a premium pair, and every review, when it finishes, then its Cost is added to a `Premium spend: $X of $10` line in the phase's Notes and passed to route as `--premium-spent`; once it reaches $10 builds get no premium pair; stage commits carry a `Cost:` trailer.
- Given the phase review, when dispatched, then it uses `route --review` and claude-build.sh with that cap, never dropping a step.
- Given model-selection.md, when read, then the 7-day rule and exit 3 fallback for age are gone; exit 3 means the profiles file is missing; Fixed choices, Adjust while working and the routing table match route's rules.
- Given plugin.json, when read, then its version is 0.10.0.

External inputs:
none

Tests:
- keeps passing `plugins/phased-delivery/tests` (integration): the docs change no behaviour

Done when:
- `grep -rn -i 'refreshed daily\|7 days\|reruns it before each phase' README.md docs/model-routing.md plugins/phased-delivery/skills` prints nothing.
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.

Out of scope:
- Plans in docs/plans/quota-failover, which record history.
- The evals and their pinned base copy.
- stage-stats.sh, which ignores the new Cost trailer.

Model basis: J1 F2 R2 C1 K0 P1 V2 S0 = 9 -> top

## Notes
- Review round 1, 2026-11-23: the user chose acceptEdits plus project rules as claude-build.sh's default and a dollar cap over a token watch; K raised on 03.1 (permissions and parsing claude's output).
- The thinking-level ceilings in `CEILINGS` stay; the low-gain rule and the stage caps apply within them. Reason: The ceilings were an earlier user decision and still hold.
- Once a phase's premium spend reaches $10, routing leaves premium pairs out of builds, falling to the best standard pair. Reason: One step down from a premium pair is often still premium; the user chose exclusion in the review round.
- Token caps per tier (small 150000, middle and middle+ 400000, top 1000000) are passed to claude -p as a dollar cap: cap tokens times the pair's input price per token. Reason: The user chose a dollar cap over watching tokens; `--max-budget-usd` is the hard stop claude -p offers, and the paid calibration run tunes it.
- Codex builds get no budget cap in this plan. Reason: codex exec has no budget option, and Codex runs on its own quota, already guarded by the routing rule and codex-build.sh exit 7.
- claude-build.sh turns the phased-delivery plugin off for the builder through `--settings`. Reason: The plugin's hooks tell every session to plan first, which would pull a builder away from its brief.
- `route` reads `models-available.json` and the plugin's profiles; `models.md` stays the per-tier summary and records the profiles fingerprint. Reason: Routing needs every offered pair, not only the four tier picks.
- claude-build.sh runs with `--permission-mode acceptEdits` by default, so file edits work and commands follow the project's allow rules; CLAUDE_BUILD_PERMISSIONS=bypassPermissions replaces it. The prompt is passed as the text of `-p`. Reason: claude -p refuses any tool needing approval, and many projects allow no edits; passing the prompt text avoids reading a file outside the repository.
- Revised before building, 2026-11-23: phase 02 added that `route --review` ignores the stage's scores and that --down/--up must be 0 or more; 03.2's docs say so. The small-tier `cap_usd` is $0.01 on the committed profiles (see 02's Notes): 03.2's docs name it as a known limit for the calibration run. The paid checks in the Assumptions stay open: the user asked to approve paid runs, so they go to the PR's test plan. Run tests with `--basetemp=/cache/...` (see 01's Notes).
- 2026-11-23, 03.1: the `--settings` value `{"enabledPlugins":{"phased-delivery@ai-coding-plugins":false}}` is the same key and plugin id the mode evals used to run with plugins off; an unreadable PROMPT exits 2.
- 2026-11-23, 03.2: the docs settle five points the brief left open: route exit 3 or 4 falls back to models.md in session with no cap; `Cost: unknown` counts the run's cap_usd as spent; a review stopped at its cap is reported, not retried lower; `moved 0 frontier pairs` means revise the plan; --down and --up are netted.
- Phase review 2026-11-23 (opus high): not ready, 1 blocking and 7 should-fix, all fixed by the orchestrator: the `moved 0` stop never fired after a clamped move (now: moved fewer than asked, or a pair already tried, goes back to planning; no netting of --down and --up); route exit 4 stops instead of falling back uncapped; Codex runs stay outside the premium budget; other claude-build.sh exits stop and report; an error result is never built (exit 1 or claude's status); stage-builder.md and phase-reviewer.md point at route; tests for permissions and flags.
