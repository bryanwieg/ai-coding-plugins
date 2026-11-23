# Model routing: goals, design and evidence

A reference for iterating on how the phased-delivery plugin chooses models.
It records why things are the way they are, what we have measured, and what
is still open. The skills and scripts are the source of truth for behavior;
this explains the thinking behind them.

## The goal

Get good code for the least spend by giving each piece of work to the
cheapest model that can do it well, across every tool and plan the user
has, and measure whether that is working.

Three parts:

1. **Pick models dynamically.** Plans name tiers, never models. At plan and
   build time the plugin lists what the running tool offers and maps tiers
   to models from current benchmark data.
2. **Route between Codex and Claude.** Each tool runs on its own
   subscription. Sending suitable work to the other tool spares the
   session's quota and plays to each model family's strengths.
3. **Report results.** Every stage is committed with trailers recording who
   built it and what it cost, and every plan ends with a report judging
   each model by those numbers. The reports are the feedback loop for parts
   1 and 2.

## Principles

- **No hardcoded models.** Models, names and behavior change monthly.
  Guides name tiers and rules; the model table is computed at plan time
  (`models.md`, generated, never hand-edited).
- **Decisions in code, not judgment.** Score and cost math lives in
  `scripts/select-models.py`; reports come from `scripts/stage-stats.sh`.
  Agents run the scripts and act on their output.
- **Models must perform unpadded.** A model that needs extra or repeated
  directions to do the job is failing the job: the padding costs tokens
  and the result is still worse. When a cheap model fails, narrow the work
  it gets; never pad the directions to compensate.
- **Benchmarks pick candidates; behavior qualifies them.** Benchmark scores
  say how capable a model is in general. Whether it follows a brief, stops
  when the brief is wrong and reports honestly has to be observed (evals,
  then the work reports).
- **Never trust a builder's own account.** Tokens come from the tool's
  usage report; for the cheapest tier, the implementer reruns the checks
  itself. Reviews always use the `top` candidate.

## Part 1: dynamic model picking

How it works now:

- **Tiers:** `small`, `middle`, `middle+`, `top`. Each stage is scored on
  eight measures (judgment left, files changed, files to read, contracts,
  risk items, pattern to follow, verification, sequencing), 0–2 each, with
  overrides. See `skills/plan-in-phases/model-selection.md`.
- **Candidates are model + thinking level pairs.** The same model can be
  strong at one level and poor at another.
- **Data:** `model-profiles.json`, one entry per model and thinking level
  built from the Artificial Analysis report by a weekly GitHub workflow,
  rebuilt only when the model list or a price changes (a fingerprint of
  both; score changes alone are ignored). The selector uses it at any age;
  `models.md` records the fingerprint and `select-models.py check` says
  whether it is current, so the selector reruns only after a change.
  Score = Intelligence Index; cost = benchmark run cost (counts the tokens
  a thinking level spends, not just price).
- **Selection:** each tier takes the cheapest candidate within a share of
  the best score (`FLOORS`: top 0.97, middle 0.85, small 0.50); within 3
  points the cheaper one wins (`TIE_POINTS`). Thinking-level ceilings
  (`CEILINGS`): Claude at most `high`, Haiku at most `xhigh`, Codex models
  at most `max`.
- **Availability:** only what the running tool lists, minus what the
  user's account cannot use (stated in project instructions, or failed at
  dispatch). Example: Fable is listed by Claude Code but unavailable on
  this account.
- **`small` is mechanical only:** no judgment, contracts, risk or
  sequencing, a named example to copy, and every check a command.
- **Per-stage routing:** tiers stay in plans as a summary; at dispatch
  `select-models.py route` picks one pair from the stage's eight scores.
  The rules (table in `model-selection.md`, "Route each stage"):
  - only pairs on the score/cost frontier; a pair beaten on both is never
    chosen;
  - a thinking step gaining under 2 points for more than 1.5 times the run
    cost is left out (`LOW_GAIN_POINTS`, `LOW_GAIN_COST_RATIO`): on the
    current data that drops, among others, Fable 5.2 xhigh, Opus 5.5 max
    and Haiku 5.5 max;
  - mechanical stages (J, P, V all 0) above `small` run at `medium` or
    below; `small` stages keep Haiku's higher levels, since capping them
    would move them to Sonnet medium at 5.6 times the cost;
  - long or wide stages (S2, R2, F2) run at `high` or below and take the
    fastest pair within 3 points and 1.5 times the cost, if it is at least
    1.2 times as fast (`SPEED_GAIN`);
  - design and contract stages (J2, C2) take a larger model at lower
    thinking within 1.5 times the cost (`PREFER_COST_RATIO`);
  - risk (K of 1 or more) moves one frontier pair up;
  - below `top`, a premium pair is kept only if it costs no more than the
    pick without premium pairs and scores at least as well (the user's rule:
    Fable low may stand in for Opus when it is cheaper and as good); when
    the standard pairs cannot give a step up the stage asked for (`middle+`,
    risk, `--up`), the cheapest pair above the standard pick is taken. The
    user's view, from practice: more thinking scores well on benchmarks but
    can do worse on real work, so the next model up at low thinking beats a
    smaller model above high. Hence Opus stays capped at `high`;
  - reviews (`--review`) run on `top` and ignore the stage's scores.
- **Rule sweep, 2026-11-23** (free: all 6,561 score combinations through
  `route` on the live profiles):
  - Before the premium gate, Fable was picked for 98% of combinations,
    `middle` included: by benchmark run cost Fable 5.2 low ($2,862) is
    barely dearer than Opus 5.5 high ($2,716) and scores 53.9 to 51.8, and
    the mechanical cap pushed `middle` from Opus high to Fable medium. With
    the gate, every stage below `top` runs on Opus, Sonnet or Haiku.
  - The speed preference switched Fable low to Fable medium over 108 vs
    110 tokens a second, raising thinking on long stages; `SPEED_GAIN` 1.2
    stops that.
  - With the gate alone, `middle+` and the risk step on `middle` landed on
    Opus high, the same as `middle`. With the step-up rule they take Fable
    low: plain `middle` stays on Opus high, mechanical `middle` on Opus
    medium.
  - The J2/C2 preference never fires: no pair scores at least Fable high
    at a lower thinking level. It waits for a larger model.
- **Limits:** a token cap per stage (150k `small`, 400k `middle` and
  `middle+`, 1M `top`) passed to `claude -p` as a dollar cap at the pair's
  input price, since `--max-budget-usd` is the hard stop it offers. A build
  stopped at its cap retries with `route --down 1`; one that fails its
  checks with `route --up 1`. Premium pairs (output price of $30 or more
  per million tokens; among current models, Fable and GPT-6.x Astra) built
  by `claude-build.sh` share $10 per phase; past that, Claude builds leave
  them out, since one step down from a premium pair is often still premium.
  Reviews count against it but never drop a step. Codex runs use their own
  quota and neither add to nor read the budget.
- **Headless Claude builds:** `scripts/claude-build.sh` runs a stage with
  `claude -p` at route's model, effort and `cap_usd`, the phased-delivery
  plugin off (its hooks would pull the builder away from its brief), in
  `acceptEdits` mode so commands follow the project's allow rules
  (`CLAUDE_BUILD_PERMISSIONS=bypassPermissions` in sandbox containers). It
  prints tokens and cost and exits 8 when the budget stopped the run.

## Part 2: routing between Codex and Claude

Observed strengths (from use and the evals below):

- **Claude Opus:** reliable across depth and breadth; plans, reviews and
  wide work.
- **Codex models (Sol, Terra):** follow a narrow brief closely and report
  honestly, but lose track across many files or large amounts of data
  (refactors, making sense of large data sets).
- **Claude Haiku:** writes out precise changes well, but skips dependent
  steps and misreports its own actions at every thinking level.

How it works now (`model-selection.md`, "Builders in another tool"):

- Planning also writes `models-available-codex.json` and `models-codex.md`
  when Codex is on (installed, signed in, not `AI_CODEX=off`).
- Availability: `scripts/codex-usage.py` checks at most once a day and
  caches the answer for the local day in `codex-availability.json`; the
  SessionStart hook tells every session that day when Codex is off. Off
  (`codex` not installed or not signed in, or recorded with `--record-off`
  after a build that cannot run) lasts the day with no prompt, until
  `codex-usage.py --recheck` finds Codex usable; `AI_CODEX=off` is read
  every time and never cached. A check that times out (exit 5) is off for
  that check only. While off, the phase runs as it would without Codex.
- Routing by usage: before every stage dispatch and the phase review,
  `scripts/claude-usage.py` gives Claude's level and `codex-usage.py`
  whether Codex has room. Claude on pace (or no data): narrow stages
  (F = 0, R = 0) go to Codex; ahead of pace: F <= 1 and R <= 1; nearly
  out: every build stage and the phase review. Codex without room: build
  in the session, or stop and report when Claude is nearly out too.
  Planning, plan reviews and session-only stages stay in the session. The
  rule is in `model-selection.md`, "The routing rule".
- `scripts/codex-build.sh` runs the stage with `codex exec`
  (workspace-write sandbox), returns Codex's token count, and exits 3 when
  Codex's sign-in has lapsed, 5 when Codex's sandbox cannot start, 6 when
  Codex ran no turn (subscription, account or service problem) and 7 when
  Codex is out of quota, so the orchestrator reroutes the stage or turns
  Codex off. `codex exec` cannot ask the orchestrator anything mid-run: a
  builder that is stuck ends with its question as the report, and the
  stage brief is fixed and rerun.
- Inside a container that is itself the boundary (the ai-coding-sandbox
  agent image), Codex's bubblewrap sandbox cannot start, so the container
  sets `CODEX_BUILD_SANDBOX=danger-full-access` and Codex runs unsandboxed
  within it, with plugin hooks untrusted-but-enabled, as interactive
  sessions there already do. The builder uses Codex's own state (sign-in,
  memories, plugins), since the container mounts both agents' state.
- Usage visibility: Codex usage is readable from its session logs (as of
  the last request). Claude usage is read from the status line's JSON,
  which the status line saves to `claude-usage.json`; it is as fresh as
  the last status line refresh in any session.

## Part 3: reports

- **Per-stage commits** with trailers: `Stage`, `Plan`, `Tier`, `Tool`,
  `Model`, `Effort`, `Attempt`, `Tokens`, `Cost`, `Tool-Calls`,
  `Earlier-Attempt` (one per failed try), `Fixes-Stage` (on later fixes),
  `Phase` (phase status commits).
- **`scripts/stage-stats.sh <range>`** turns them into a Markdown report
  per model and effort: stages, first try, **clean** (first try and never
  fixed), failed tries, fixes needed, tokens spent, wasted, per stage, plus
  every rerun and fix.
- **`work-report.md`** at the end of each plan: those tables plus a Reading
  judging each candidate. Effectiveness = clean rate; cost = tokens per
  clean stage including waste and others' fixes.
- **Evals** (`evals/`): seven stage briefs from this repo with hidden
  checks and blind Opus grading, runnable on Claude Code subagents or
  `codex exec`. Use before trusting a new model or level with a tier.

## Evidence so far (2026-11)

| Candidate | Runs | Result |
| --- | --- | --- |
| Claude Haiku 5.5, medium / high / xhigh | 21 evals | All checks passed first try (grades 9.3 / 9.4 / 9.6), but at every level skipped the multi-step order and reported "Deviations: none", and misreported commands run. Higher thinking only widened what it checked, at up to 2.4x the tokens. Extra directions helped partly and were reverted under the "unpadded" principle. |
| GPT-6.1 Terra, low (Codex) | 1 eval (multi-step probe) | Passed, kept the step order, saw the planned failure before fixing it, accurate report; grade 10; 1.5k output tokens. |
| GPT-6.2 Sol, medium (Codex) | 1 real phase (`stage-stats` failed column) | Passed its checks first try, accurate report, 195k tokens (1.8k output). Opus review found one real bug (non-portable awk) the planned check missed. First try, not clean. |

### Routing calibration, 2026-11-23

15 headless runs of the builder evals through `claude-build.sh`, each at
the pair `route` picks and one step down, $0.57 in all. The eval briefs
are all scored mechanical, so this tested the small tier and one
re-scored stage (p2 with S2), not the J2/C2, risk or speed rules.

| Task | Pair | Check | Cost | Tokens |
| --- | --- | --- | --- | --- |
| t1-t5 (5 tasks) | Haiku high (route) | 5/5 pass | $0.006-0.018 | 105k-332k |
| t1-t5 (5 tasks) | Haiku medium (`--down 1`) | 5/5 pass | $0.006-0.014 | 106k-366k |
| p1-stop | Haiku high | stopped correctly, no changes | $0.007 | 118k |
| p1-stop | Haiku medium | did not stop: built the column with the wrong helper | $0.012 | 261k |
| p2-multistep, as S2 | Opus medium (route) | pass, step order kept | $0.215 | 128k |
| p2-multistep, as S2 | Opus low (`--down 1`) | pass, step order kept | $0.198 | 126k |
| p2-multistep | Haiku high (old small pick) | pass, step order kept | $0.012 | 249k |

- **Caps hold with room.** The dearest Haiku stage cost $0.018 against
  the $0.25 floor; Opus stages $0.21 against $1.60. Tokens run past
  `cap_tokens` (a small stage used up to 366k, mostly cache reads), so
  `cap_tokens` is nominal: the dollar cap is what stops a build.
- **One step down is not free.** Haiku medium passed every hidden check
  but failed the stop probe Haiku high passed, so dropping a step after a
  cap costs judgment, not only score. One run each.
- **Thinking level barely moved Opus cost here:** low and medium spent
  the same tokens on p2.
- **Haiku high kept the p2 step order** this time (earlier subagent runs
  skipped it), at a seventeenth of Opus medium's cost. One run is not
  enough to relax "small only for mechanical stages".
- Not tested: the 2-point/1.5x cutoffs (no low-gain pair was a route
  pick), J2/C2, risk and speed rules, and Sonnet (off the frontier).

Side observations:

- `codex exec` loads the user's installed Codex plugins and skills, which
  can steer the build (a minimal-code skill did in one run).
- Codex sign-in can lapse while `codex login status` still says logged in.
- Fixes made directly by the orchestrator have unknown token counts.

## Open questions and next steps

- **Calibrate routing further (paid run, ask first):** the first run
  (above) covered the small tier and the caps. The 2-point and 1.5x
  low-gain cutoffs, the 1.5x preference window and the J2/C2, risk and
  speed rules need eval tasks scored to trigger them. Every cap is at
  least `MIN_CAP_USD` ($0.25); at the input price alone a `small` stage
  on Haiku would get $0.01.
- **Headless build checks: done 2026-11-23** (two Haiku-high runs on a
  one-function stage, $0.006 together). On a subscription,
  `total_cost_usd` is reported and `--max-budget-usd` stops the run: a
  $0.001 cap stopped it after one turn at $0.002, exit 8, so a run can
  overshoot its cap by one turn. The uncapped run cost $0.0043 for 112,771
  tokens (98k of them cache reads) in 6 turns. Under `acceptEdits` the
  builder edited files and ran read-only commands, but `python3 -m pytest`
  was refused: a project must allow its test commands, or set
  `CLAUDE_BUILD_PERMISSIONS=bypassPermissions` in a sandbox; with the
  ai-coding sandbox image setting it, a third run ran pytest itself (2
  passed, no denials, $0.0034). A budget stop
  reports zero `usage`; `claude-build.sh` counts tokens from `modelUsage`.

- **More Codex evidence:** a few more probe runs and real phases before
  widening what goes to Codex; does a deeper stage (R = 1) work there?
- **Behavior qualification:** record per-candidate probe results
  (`model-behavior.json`) and have the selector cap failing candidates at
  `small`, so qualification is code, not memory.
- **Reverse routing:** when the session is Codex, should wide work go to
  Claude?
- **Routing thresholds:** tune the usage levels and width caps from
  `work-report.md` results.
- **Unusable Codex (exit 6):** narrow it to the observed messages once a
  real expired-plan error is seen, so a transient failure does not turn
  Codex off.
- **Close the loop:** feed `work-report.md` results back into selection
  (for example, demote a candidate whose clean rate stays low).
- **Clean Codex environment:** build with a dedicated `CODEX_HOME` so the
  user's own Codex plugins don't influence builds, if they prove harmful.
- **Orchestrator token counts:** find a way to record tokens for fixes the
  orchestrator makes itself.
