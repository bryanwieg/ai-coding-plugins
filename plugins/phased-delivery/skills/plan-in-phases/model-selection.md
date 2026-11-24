# Choosing a model and effort

Used by plan-in-phases, which scores every stage and records a tier and
effort, and by implement-in-phases, which re-scores each stage and routes
it to a model and thinking level with `select-models.py route` when it
dispatches a builder. Score from the brief and the code as read now, not
from how small the task looks, from memory or from habit.

## Score the task

Score each measure 0, 1 or 2 using the observable criteria. When a measure
sits between two scores, take the higher. If you cannot score a measure
without guessing, you have not read enough: read the code, then score.

| Measure | 0 | 1 | 2 |
| --- | --- | --- | --- |
| **J: Judgment left** | The brief names a near-identical example and every change follows it; the agent only writes it out | The agent chooses local details no other code sees: private helper names, loop structure | The agent chooses an approach, algorithm or data structure, or anything other code will see |
| **F: Files changed** (tests included) | 1–2 | 3–5 | 6 or more (also consider splitting the stage) |
| **R: Files to read** to change it safely (callers, callees, contracts, tests) | 3 or fewer | 4–10 | More than 10, spread across more than one component, or a data set too large to read whole |
| **C: Contracts** | Uses only settled contracts, unchanged | Implements a signature or format the plan already defines | Defines or changes a contract another stage or component uses |
| **K: Risk items** (count from the list below) | None | One | Two or more |
| **P: Pattern to follow** | A near-identical example exists; the brief names the file | Similar code exists but needs adapting | Nothing comparable in the repository |
| **V: Verification** of "Done when" | Fully by running tests, a build or the program | Partly by running, partly by reading | Only by reading code |
| **S: Sequencing** of the changes | Independent edits; no step depends on another's result | Ordered steps, but none depends on what a run shows | A step depends on what a run shows (run, look at the result, then act) |

Risk items for K: a trust boundary; security, authentication, permissions or
secrets; concurrency, async ordering or shared mutable state; persisted data,
file or wire formats, or migration; deleting data or retiring a code path;
touched code with no tests covering it.

## Pick the tier

Add the scores (0–16), then apply the overrides in order. Plans record the
tier, not a model name, so a plan written in one tool can be built in
another. Tiers stay in plans as a summary: at dispatch, `route` picks the
stage's pair from its eight scores (see "Route each stage").

| Total | Tier |
| --- | --- |
| 0–3 | `small` |
| 4–8 | `middle` |
| 9–16 | `top` |

A single measure at 2 does not make a stage `top`: only a total of 9 or
more does. (Changed 2026-11-24: the old override, any of J, C or K at 2
means `top`, sent 39% of stages to the most expensive pair.) A measure at 2
raises `middle` to `middle+` (override 2).

Overrides, which always win over the total:

1. **`small` only for mechanical stages:** J, C, K and S all 0, P = 0 (the
   brief names a near-identical example) and V = 0 (every "Done when" item
   is a command). Otherwise use at least `middle`, whatever the total. The
   cheapest candidates do well at writing out a precise change and poorly
   at following dependent steps, noticing what the brief leaves unsaid, or
   accounting accurately for their own actions; `small` work must need none
   of those, and its builder's report is never taken as evidence (see
   implement-in-phases).
2. **`middle` with any measure at 2: use `middle+`**, the next more capable
   candidate above the `middle` pick in `models.md`.

## Choose the model and thinking level: the plan's model table

Models, their names, their thinking levels and their behavior change often,
so this guide names none. A tier maps to a **candidate**: one model at one
thinking level (effort). The same model can be strong at one level and poor
at another, so candidates are compared as pairs, never as models alone.

The mapping is computed by code, not judged by reading tables:
`scripts/select-models.py` in this plugin (two directories above this
skill's directory) reads the plugin's `model-profiles.json` and writes the
plan's `models.md`, the per-tier summary; its `route` subcommand picks each
stage's pair at dispatch. Every phase file links to `models.md`. Never
write or edit it by hand.

The profiles hold one entry per model and thinking level, from the
Artificial Analysis data: scores, benchmark run cost, prices, speed, a
premium or standard price class (premium: output price of $30 or more per
million tokens) and the points gained and cost multiplied by each step up
in thinking level. A weekly workflow rebuilds them only when the model list
or a price changes; a change to scores alone is ignored. The selector uses
them at any age and writes their fingerprint into `models.md` as a
`Profiles:` line.

### 1. List what the running tool offers

Write `models-available.json` in the plan directory from the tool itself,
never from memory: the subagent tool's own parameter description, the tool's
model list or catalog command, or the model list in the session's
instructions. Ignore models the tool marks hidden, legacy or deprecated, and
models the user's account cannot use: ones the user or the project
instructions say are unavailable, or that failed when dispatched. The
format is in the script's header:

- `tool` (`claude-code` or `codex`), `tool_version`, `looked_up_from`;
- `subagent_model_choice`: `allowed`, or `user-only` when the tool lets an
  agent set a subagent's model only if the user asks. Then record `opted_in`
  and `opt_in_where`: tiers may pick models only if the user or the project
  instructions (`AGENTS.md`, `CLAUDE.md`) ask for phased-delivery model
  selection. If not opted in, also record `session_model`, the model this
  session runs on; tiers then choose only that model's thinking level;
- `models`: each model's `id` as the tool names it and the `efforts` it
  accepts. Add `match` with the report's model name only when the script
  reports a name it could not match.

### 2. Run the selector

```
python3 scripts/select-models.py <plan>/models-available.json --out <plan>/models.md
```

What the code enforces, so the agent does not:

- It matches each tool model to a report model by name; a short name such as
  `opus` resolves to the newest version of that one family, and anything
  ambiguous is excluded with a reason.
- **Only thinking levels the report benchmarked** become candidates; offered
  levels without a benchmark row are excluded. No interpolation.
- **Thinking-level ceilings:** Codex models never run above `max`; Claude
  models never above `high`, except Haiku, which may use `xhigh`. Higher
  levels, and levels the script cannot place, are denied even if offered
  and charted. The ceilings are the `CEILINGS` table in the script.
- Each candidate is scored by the Artificial Analysis Intelligence Index
  (a quarter coding, plus reasoning-heavy science and HLE-Diamond; the free
  data has no separate coding or reasoning score) and costed by the benchmark run cost, which counts
  the tokens a thinking level spends, not only the price per token.
- Each tier takes the **cheapest candidate scoring close enough to the
  best** (the floors are constants at the top of the script). So a large
  model at low thinking beats a small model at high thinking when it scores
  as well for less. `middle+` is the next more capable candidate above
  `middle`.
- **Within 3 points, the cheaper candidate wins.** After a tier picks, any
  cheaper candidate scoring within 3 index points of the pick replaces it,
  even across a floor (for `middle+`, only candidates still above
  `middle`).

`models.md` lists the inputs, every match, every candidate with score and
cost, and every exclusion with its reason, so a reviewer can check it or
rerun the script.

### 3. Handle what the script reports

- **Exit 0:** done. Read the Matches and Excluded lists; if a model you
  expected is excluded for a name mismatch, add its `match` and rerun.
- **Exit 3, profiles missing:** fall back by hand and say
  so in `models.md`: rank models by the tool's own descriptions (fastest and
  cheapest to `small`, general-purpose to `middle`, most capable to `top`)
  and use effort low, medium and high for the three tiers, never above the
  thinking-level ceilings.
- **Exit 4, nothing selectable, or exit 2, bad input:** fix the input from
  what the script printed; if nothing is selectable, use the fallback.
- **No Python available:** use the fallback.

At the start of each phase, the implementer runs

```
python3 scripts/select-models.py check <plan>/models.md
```

Exit 0: `models.md` is current, reuse it. Exit 1: its Profiles line differs
or is missing; refresh `models-available.json` from the tool, rerun the
selector and record the change in the phase's Notes. Do the same when a
dispatch fails because a model is unavailable. Exit 3: profiles missing,
use the fallback. A plan built in a different tool from the one it was
planned in is redone the same way; briefs record tiers and scores, so
nothing else changes.

When subagents must inherit the model, still set the candidate's effort
where the tool allows it, and say in the phase report which tier each stage
called for.

## Route each stage

Before every stage build and the phase review, the implementer runs

```
python3 scripts/select-models.py route <plan>/models-available.json --scores J1F1R1C1K0P0V1S0 [--down N | --up N] [--premium-spent USD] [--review]
```

`--scores` is the stage's `Model basis` scores, re-scored at dispatch,
written without spaces. It prints one JSON line: `model`, `effort`, `tier`,
`premium`, `score`, `cap_tokens`, `cap_usd` and `why` (the rules that
shaped the pick). Exit codes: 0 printed; 2 bad input (fix it from the
message); 3 profiles missing; 4 no selectable pair. On 3, or without
Python, dispatch the tier's pair from `models.md` (or the fallback) as an
in-session subagent with no cap, and say so in the phase's Notes. On 4,
stop and report to the user: falling back would get around the premium
budget and the cap.

What `route` does, in this order:

| Rule | Pick |
| --- | --- |
| Candidates | Offered pairs within the thinking-level ceilings that have a score and a benchmark run cost, minus low-gain thinking steps: a step up gaining under 2 points for more than 1.5 times the run cost of the level below. |
| Frontier | Only pairs on the score/cost frontier: a pair another beats on both score and cost is never chosen. |
| Tier | The tier from the scores with the overrides above; `--review` uses `top`. The pick is the cheapest frontier pair meeting the tier's floor, then any cheaper pair within 3 points; `middle+` is the next frontier pair above the `middle` pick. |
| Premium budget | With `--premium-spent` at or above $10, builds leave premium pairs out. |
| Mechanical (J, P and V all 0, tier above `small`) | Thinking at `medium` or below. `small` stages keep the small model's higher levels. |
| Long or wide (S, R or F = 2) | Thinking at `high` or below. |
| Risk (K of 1 or more) | One frontier pair up. |
| Design or contract (J = 2 or C = 2) | Among pairs meeting the floor that score at least the pick and cost at most 1.5 times it, the lowest thinking level: a larger model at lower thinking. |
| Long or wide (S, R or F = 2) | Among pairs meeting the floor within 3 points of the pick (with K of 1 or more, at least the risk step's score) and costing at most 1.5 times it, the fastest, if at least 1.2 times the pick's speed (thinking levels of one model differ by a few percent). |
| Premium below `top` | A premium pick below `top` is routed again without premium pairs; the premium pair stays only if it costs no more than that standard pick and scores at least as well. When the standard pairs run out before a step up the stage asked for (`middle+`, risk, `--up`), the cheapest pair scoring above the standard pick is taken instead (the next model up at low thinking, not more thinking on a smaller model), but only when its score divided by its benchmark run cost is at least the standard pick's; otherwise the standard pick stays. A `--up` retry after a failed build takes it regardless. |
| `--down N`, `--up N` | Move N frontier pairs cheaper or dearer from the pick, stopping at either end. N is 0 or more; not both at once. |
| `--review` | `top`, ignoring premium spend and the stage's scores (no caps, risk step or preferences). |

The constants (`LOW_GAIN_POINTS`, `LOW_GAIN_COST_RATIO`, `FLOORS`,
`TIE_POINTS`, `PREMIUM_BUDGET_USD`, `PREFER_COST_RATIO`, `SPEED_GAIN`, `CAP_TOKENS`) are
at the top of the script.

### Limits

- **Stage caps:** `cap_tokens` is 150000 for `small`, 400000 for `middle`
  and `middle+`, 1000000 for `top`. `cap_usd` is that many tokens at the
  pair's input price, rounded to cents, and never below $0.25
  (`MIN_CAP_USD`): at the input price alone a `small` stage on Haiku would
  get $0.01, below one headless run. `claude-build.sh` stops the build
  there. A paid calibration run is still to set the caps.
- **Budget stop:** a build that `claude-build.sh` stops at its cap (exit 8)
  is retried one step down the frontier (see "Adjust while working").
- **Premium budget, $10 per phase:** the implementer keeps a
  `Premium spend: $X of $10` line in the phase's Notes. After each
  `claude-build.sh` run of a pair `route` printed with `"premium": true`,
  and after every phase review it runs, it adds the run's `Cost:` (its
  `cap_usd` when the cost is `unknown`) and passes X to `route` as
  `--premium-spent`. Once X reaches $10, builds get no premium pair for
  the rest of the phase.
- **Reviews** use `route --review`: always `top`, their cost counted
  against the premium budget when built by `claude-build.sh`, never a step
  down. A review stopped at its
  cap is reported to the user, not retried lower.
- **Codex runs** add nothing to the premium spend and their `route` calls
  pass no `--premium-spent`: Codex runs on its own quota.
- **Codex builds** have no cap: `codex exec` has no budget option, and
  Codex runs on its own quota (see "Builders in another tool").

### claude-build.sh

Claude stages and reviews are built headless, so a runaway is stopped, not
just counted:

```
scripts/claude-build.sh REPO PROMPT MODEL EFFORT BUDGET_USD OUTDIR
```

PROMPT is a file outside REPO holding stage-builder.md (or
phase-reviewer.md) and its inputs; its text is passed to `claude -p`, which
works in REPO with the phased-delivery plugin off and
`--max-budget-usd BUDGET_USD`. MODEL, EFFORT and BUDGET_USD are route's
`model`, `effort` and `cap_usd`. OUTDIR receives `report.md` (the final
message), `stream.jsonl` and `stderr.txt`. It prints `Tokens: N` and
`Cost: X.XX` (each `unknown` when claude reports none). Exit: 0 built; 2
usage; 8 the budget was reached; other non-zero: claude's exit status.
Never commits.

`CLAUDE_BUILD_PERMISSIONS` sets the permission mode. Unset:
`acceptEdits`, so file edits work and commands follow the project's own
allow rules (a command they do not allow cannot run). `bypassPermissions`:
only for a session already in a sandbox container (the ai-coding sandbox
sets it already). Any other value exits 2.

## Record the score

Write the scores in each stage brief's `Model basis` line, for example
`J1 F1 R1 C1 K0 P0 V1 S0 = 5 -> middle`, and name any override applied.
Reviewers check the scores against the code; the implementer re-scores at
dispatch.

## Examples

- Register a new command in an existing dispatch table, following the
  neighboring entry the brief names, and add one test: J0 F1 R0 C0 K0 P0 V0
  S0 = 1 -> `small`.
- Change a function, run its tests, expect one named test to fail, then
  update that test: J0 F1 R0 C0 K0 P0 V0 S2 = 3 -> override 1 -> `middle`.
- Fill in the body of a planned parser function against a defined signature,
  reading a config file another tool writes, with tests: J1 F1 R1 C1 K1 P1 V0
  S0 = 6 -> `middle`.
- Same parser, but the input format must be inferred from samples and the
  brief leaves the error-handling approach open: J2 F1 R1 C1 K1 P1 V0 S0
  = 7 -> override 2 -> `middle+`. Better still, the planner should settle
  the approach and re-score.
- Replace the session store with a new one, migrating stored sessions and
  retiring the old path: J1 F2 R2 C2 K2 P2 V1 S1 = 13 -> `top`.

A high score can also mean the stage is too big: before accepting F = 2 or
R = 2, check whether the stage should be split.

## Fixed choices

- **Reviews run on `top`** through `route --review` (on
  `models-available-codex.json` when the routing rule sends the review to
  Codex), whatever the tier of the work under review. A review exists to
  catch what the author missed, including bad assumptions; a weaker
  reviewer defeats the point. Its cost counts against the premium budget,
  but it never drops a step.
- **Planning and plan revision** use `top`.
- Never dispatch a pair below the one `route` prints for the stage's scores
  without a written reason in the phase's Notes; a `--down` retry after a
  budget stop is recorded by its Earlier-Attempt trailer.

## Builders in another tool

When the session is not Codex and Codex is on (see below), stages may be
built there with `scripts/codex-build.sh`. Codex runs on its own plan, so
this spares the session's quota, and Codex models follow a brief closely
when it is narrow. How much goes to Codex depends on both tools' usage.

### Codex availability

Codex is **off** for the rest of the day when any of these holds, and
**on** otherwise. `codex-usage.py` caches the answer for the local day in
`codex-availability.json` (beside `claude-usage.json`), so it runs `codex`
at most once a day; while the cache says off it exits 3 at once with
`Codex is off today: <cause>`. Off never prompts the user; after fixing
the cause, the user runs `codex-usage.py --recheck`.

| Cause | Detected by | Action |
| --- | --- | --- |
| `AI_CODEX=off` in the environment | `codex-usage.py` exit 3 | off while it is set (read every time, never cached); unset `AI_CODEX` to use Codex |
| `codex` not installed | `codex-usage.py` exit 3 | off for the day (cached) |
| found off earlier today | `codex-usage.py` exit 3 (`Codex is off today: ...`) | off for the day |
| not signed in | `codex-usage.py` exit 4 | off for the day (cached), no prompt; tell the user to sign in (`! codex login --device-auth`) and run `codex-usage.py --recheck` |
| availability check timed out | `codex-usage.py` exit 5 | off for this check only, never room; nothing is cached and the next check runs again |
| Codex cannot be used (expired subscription, account error) | `codex-build.sh` exit 6 | off for the day: run `codex-usage.py --record-off "<cause>"` |
| Codex's sandbox cannot start here | `codex-build.sh` exit 5 | off for the day: run `codex-usage.py --record-off "<cause>"`; tell the user to set `CODEX_BUILD_SANDBOX=danger-full-access` only if the session already runs in a sandbox container (the ai-coding sandbox sets it already) |
| sign-in lapsed during a build | `codex-build.sh` exit 3 | off for the day, no prompt: run `codex-usage.py --record-off "sign-in lapsed; run codex logout && codex login --device-auth"`; tell the user to sign in again and run `codex-usage.py --recheck` |

- **A Codex dispatch runs alone:** no other stage is built in the same
  checkout while it runs; stages marked parallel run one after another
  when one of them goes to Codex.
- **A failed Codex build** (exit 3, 5, 6 or 7) leaves no accepted work.
  Before each Codex dispatch, snapshot the checkout passed as REPO:
  every path `git status --porcelain --untracked-files=all` lists (both
  sides of a rename), with its `git hash-object` or `absent` when the file
  does not exist. On failure, before anything else, compare with the
  paths listed now: a path listed now but not in the snapshot is Codex's;
  restore it to `HEAD` (`git restore --source=HEAD --staged --worktree`),
  or delete it when `HEAD` lacks it. A path in the snapshot whose hash or
  `absent` state now differs: stop and ask the user instead of restoring
  it.
- **After a failed build** (exit 3, 5, 6 or 7), the stage is built by the
  routing rule as if Codex had no room; exits 3, 5 and 6 also record
  Codex off for the day as in the table.
- **Exit 7, Codex out of quota during a build**, is not "off": it is "no
  room" for this dispatch (see the routing rule).
- **When:** a session told at start that Codex is off today (exit 3 or
  4) treats it as off without checking again. Otherwise run
  `codex-usage.py` before a phase's first dispatch, ahead of refreshing
  `models-available-codex.json` and `models-codex.md`; it answers from
  the daily cache. When that check times out (exit 5), the phase starts
  without Codex and its Notes record `Codex check timed out`, not off;
  exit 5 at a check before a dispatch builds that stage in the session. Only when the plan has `models-codex.md` and the
  session is not Codex.
- **Off means not loaded:** no refresh of the Codex model files, no usage
  scripts, no routing table, nothing routed to Codex; the phase runs as it
  would without Codex. Record `Codex off today: <cause and the script's
  line>` in the phase's Notes and in the phase report.
- **Day scope:** off lasts the local day, in every session, until
  `codex-usage.py --recheck` finds Codex usable; the next day checks
  again. The Notes line is history, not a switch.
- **No quota is not "off":** it stays the per-dispatch "no room" in the
  routing rule (from `codex-usage.py` exit 1 or `codex-build.sh` exit 7),
  because Codex's windows reset within hours.
- `AI_CODEX` is the user's switch, shared with the ai-coding sandbox:
  `off` turns Codex off; unset or any other value leaves it to detection.
- **Plan time:** when the session is not Codex and Codex is on by the
  table above, also write `models-available-codex.json` (`tool`: `codex`, models and efforts from
  `codex debug models`, `subagent_model_choice`: `allowed`, since
  `codex-build.sh` sets the model) and generate `models-codex.md` from it
  with the selector. All tier rules and ceilings apply unchanged. When
  Codex is off, write neither.

### The routing rule

Only while Codex is on. Checked before **every** stage dispatch and before
the phase review. Run `scripts/claude-usage.py` (Claude level) and
`scripts/codex-usage.py` (exit 0 or 2 means room; exit 1 means no room;
exit 3, 4 or 5 is handled by the availability table first). No usage data
(exit 2: Codex has not run yet) counts as room, since a build that does
hit the limit reports exit 7.

| Claude level (exit) | Codex has room | Codex has no room |
| --- | --- | --- |
| on pace (0) or no data (3) | narrow stages (F = 0, R = 0) to Codex | build in session |
| ahead of pace (1) | stages with F <= 1 and R <= 1 to Codex | build in session |
| nearly out (2) | every build stage **and** the phase review to Codex | stop and report |

Width caps what goes to Codex until Claude is nearly out, because Codex
models lose track across many files and large amounts of data; only when
the session cannot continue does sparing its quota outweigh that.

- A stage goes to Codex only when `models-codex.md` has a candidate for
  its tier; otherwise it is built in the session.
- Codex builds use the pair `route` prints for
  `models-available-codex.json`, with no cap; a Codex review uses
  `route --review` on it, through `scripts/codex-build.sh` with
  phase-reviewer.md as the prompt file.
- **Stop and report:** finish and commit the stage in progress, update the
  phase status line and Notes, commit them, and stop. Report the stages
  done and left and both scripts' output lines (usage and reset times).
  When the stop comes at the check before the phase review, set
  `Status: in progress (stages done: all; review pending)`; resuming
  starts with the review, after checking availability and the rule again.
- At level 2, Codex turning off or failing a build (exit 3, 5, 6 or 7)
  means "Codex has no room": the failed
  stage is not rebuilt in the session; restore it as above, leave it
  `planned`, stop and report, with the cause.
- **Session-only stages** (those that must write outside the repository,
  or whose brief says it is built in the session or by the orchestrator)
  are built in the session at every level, including level 2; the rule
  never sends them to Codex.
- Planning, plan revision, plan-review rounds and the orchestrator's own
  work stay in the session at every level; only stage builds and the phase
  review are routed (`codex-build.sh` can write only the repository and
  /tmp, hence the session-only stages above).
- Without `models-codex.md` (no Codex at plan time), none of this
  applies: every stage and the review are built in the session.
- When the level changes during a phase, record it in the phase's Notes
  with both scripts' output lines.

## Adjust while working

- At dispatch, re-score against the brief as revised and the code as it now
  is. If a score changes, update `Model basis` and record why in the Notes;
  `route` reads the new scores.
- If `claude-build.sh` stops a build at its cap (exit 8), retry it with
  `route --down 1`, and one step further on each further stop (`--down 2`,
  and so on). Record each stopped attempt as an Earlier-Attempt. When
  `why` says it moved fewer pairs than asked, or `route` prints a pair
  already tried for this stage, the stage is too big for its cap: revise
  the plan.
- If a builder fails its "Done when", stops because the stage was harder
  than its scores showed, or produces work the review rejects for reasoning
  errors, rerun it with `route --up 1` instead of retrying the same pair
  (one step further on each further failure), and note which measure was
  under-scored. Where the model is inherited, `route` moves only its
  thinking level. When `why` says it moved fewer pairs than asked, or
  `route` prints a pair already tried for this stage, the brief or the
  plan is the problem: go back to planning. A stage that has both hit its
  cap and failed its checks also goes back to planning; never net `--down`
  against `--up`, which would re-dispatch a pair already tried.
- If a builder stops because the brief is wrong, a higher tier is not the
  fix; revise the plan.
