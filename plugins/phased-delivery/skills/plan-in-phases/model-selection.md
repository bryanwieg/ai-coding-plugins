# Choosing a model and effort

Used by plan-in-phases, which scores every stage and records a tier and
effort, and by implement-in-phases, which re-scores each stage and maps its
tier to a model through the plan's `models.md` when it dispatches a
subagent. Score from the brief and the code as read now, not
from how small the task looks, from memory or from habit.

## Score the task

Score each measure 0, 1 or 2 using the observable criteria. When a measure
sits between two scores, take the higher. If you cannot score a measure
without guessing, you have not read enough: read the code, then score.

| Measure | 0 | 1 | 2 |
| --- | --- | --- | --- |
| **J: Judgment left** | Work names every change; the agent only writes it out | The agent chooses local details no other code sees: private helper names, loop structure, extra test cases | The agent chooses an approach, algorithm or data structure, or anything other code will see |
| **F: Files changed** (tests included) | 1–2 | 3–5 | 6 or more (also consider splitting the stage) |
| **R: Files to read** to change it safely (callers, callees, contracts, tests) | 3 or fewer | 4–10 | More than 10, spread across more than one component, or a data set too large to read whole |
| **C: Contracts** | Uses only settled contracts, unchanged | Implements a signature or format the plan already defines | Defines or changes a contract another stage or component uses |
| **K: Risk items** (count from the list below) | None | One | Two or more |
| **P: Pattern to follow** | A near-identical example exists; the brief names the file | Similar code exists but needs adapting | Nothing comparable in the repository |
| **V: Verification** of "Done when" | Fully by running tests, a build or the program | Partly by running, partly by reading | Only by reading code |
| **S: Sequencing** of the Work steps | Independent edits; no step depends on another's result | Ordered steps, but none depends on what a run shows | A step depends on what a run shows (run, look at the result, then act) |

Risk items for K: a trust boundary; security, authentication, permissions or
secrets; concurrency, async ordering or shared mutable state; persisted data,
file or wire formats, or migration; deleting data or retiring a code path;
touched code with no tests covering it.

## Pick the tier

Add the scores (0–16), then apply the overrides in order. Plans record the
tier, not a model name, so a plan written in one tool can be built in
another.

| Total | Tier |
| --- | --- |
| 0–3 | `small` |
| 4–8 | `middle` |
| 9–16 | `top` |

Overrides, which always win over the total:

1. **J = 2, C = 2 or K = 2: use `top`.** Open-ended design, shared
   contracts and stacked risk are where weaker models fail quietly.
2. **`small` only for mechanical stages:** J, C, K and S all 0, P = 0 (the
   brief names a near-identical example) and V = 0 (every "Done when" item
   is a command). Otherwise use at least `middle`, whatever the total. The
   cheapest candidates do well at writing out a precise change and poorly
   at following dependent steps, noticing what the brief leaves unsaid, or
   accounting accurately for their own actions; `small` work must need none
   of those, and its builder's report is never taken as evidence (see
   implement-in-phases).
3. **`middle` with any measure at 2: use `middle+`**, the next more capable
   candidate above the `middle` pick in `models.md`.

## Choose the model and thinking level: the plan's model table

Models, their names, their thinking levels and their behavior change often,
so this guide names none. A tier maps to a **candidate**: one model at one
thinking level (effort). The same model can be strong at one level and poor
at another, so candidates are compared as pairs, never as models alone.

The mapping is computed by code, not judged by reading tables:
`scripts/select-models.py` in this plugin (two directories above this
skill's directory) reads the plugin's `model-report.json`, refreshed daily
from Artificial Analysis, and writes the plan's `models.md`. Every phase
file links to `models.md`. Never write or edit it by hand.

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
- **Exit 3, report missing or older than 7 days:** fall back by hand and say
  so in `models.md`: rank models by the tool's own descriptions (fastest and
  cheapest to `small`, general-purpose to `middle`, most capable to `top`)
  and use effort low, medium and high for the three tiers, never above the
  thinking-level ceilings.
- **Exit 4, nothing selectable, or exit 2, bad input:** fix the input from
  what the script printed; if nothing is selectable, use the fallback.
- **No Python available:** use the fallback.

Before each phase, the implementer refreshes `models-available.json` from the
tool and reruns the selector. If the result changed, it records the change in
the phase's Notes. A plan built in a different tool from the one it was
planned in is redone the same way; briefs record tiers, so nothing else
changes.

When subagents must inherit the model, still set the candidate's effort
where the tool allows it, and say in the phase report which tier each stage
called for.

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
  update that test: J0 F1 R0 C0 K0 P0 V0 S2 = 3 -> override 2 -> `middle`.
- Fill in the body of a planned parser function against a defined signature,
  reading a config file another tool writes, with tests: J1 F1 R1 C1 K1 P1 V0
  S0 = 6 -> `middle`.
- Same parser, but the input format must be inferred from samples and the
  brief leaves the error-handling approach open: J2 ... -> override 1 ->
  `top`. Better still, the planner should settle the approach and
  re-score.
- Replace the session store with a new one, migrating stored sessions and
  retiring the old path: J1 F2 R2 C2 K2 P2 V1 S1 = 13 -> `top`.

A high score can also mean the stage is too big: before accepting F = 2 or
R = 2, check whether the stage should be split.

## Fixed choices

- **Reviews use the `top` candidate**, of `models-codex.md` when the
  routing rule sends the review to Codex, whatever the tier of the work
  under review. A review exists to catch what the author missed, including bad
  assumptions; a weaker reviewer defeats the point.
- **Planning and plan revision** use `top`.
- Never dispatch below the tier the scores give without a written reason in
  the phase's Notes.

## Builders in another tool

When the session is not Codex and Codex is on (see below), stages may be
built there with `scripts/codex-build.sh`. Codex runs on its own plan, so
this spares the session's quota, and Codex models follow a brief closely
when it is narrow. How much goes to Codex depends on both tools' usage.

### Codex availability

Codex is **off** for the rest of the session when any of these holds, and
**on** otherwise:

| Cause | Detected by | Action |
| --- | --- | --- |
| `AI_CODEX=off` in the environment | `codex-usage.py` exit 3 | off, no prompt |
| `codex` not installed | `codex-usage.py` exit 3 | off, no prompt |
| not signed in | `codex-usage.py` exit 4 | ask the user: sign in (`! codex login --device-auth`), then check again; or skip, which turns it off |
| Codex cannot be used (expired subscription, account error) | `codex-build.sh` exit 6 | off |
| Codex's sandbox cannot start here | `codex-build.sh` exit 5 | off; tell the user to set `CODEX_BUILD_SANDBOX=danger-full-access` only if the session already runs in a sandbox container (the ai-coding sandbox sets it already) |
| sign-in lapsed during a build | `codex-build.sh` exit 3 | ask the user: sign in again (`! codex logout && codex login --device-auth`, the command the script prints) or skip; a second exit 3 in the session turns it off |

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
- **After a failed build:** exit 3 and the user signs in again
  (`codex-usage.py` no longer exits 4): rerun the stage on Codex as the
  next attempt. Otherwise (exit 3 skipped or repeated, 5, 6, 7) the stage
  is built by the routing rule as if Codex had no room.
- **Exit 7, Codex out of quota during a build**, is not "off": it is "no
  room" for this dispatch (see the routing rule).
- **When:** at the start of each phase, before refreshing
  `models-available-codex.json` and `models-codex.md`, and whenever a
  dispatch result above turns it off. Only when the plan has
  `models-codex.md` and the session is not Codex.
- **Off means not loaded:** no refresh of the Codex model files, no usage
  scripts, no routing table; the phase runs as it would without Codex.
  Record `Codex off this session: <cause and the script's line>` in the
  phase's Notes and in the phase report.
- **Session scope:** off lasts until the session ends; a new session (or a
  resume in one) checks again. The Notes line is history, not a switch.
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
exit 3 or 4 is handled by the availability table first). No usage data
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
- Codex builds use the tier's candidate in `models-codex.md`; a Codex review
  uses its `top` candidate, through `scripts/codex-build.sh` with
  phase-reviewer.md as the prompt file.
- **Stop and report:** finish and commit the stage in progress, update the
  phase status line and Notes, commit them, and stop. Report the stages
  done and left and both scripts' output lines (usage and reset times).
  When the stop comes at the check before the phase review, set
  `Status: in progress (stages done: all; review pending)`; resuming
  starts with the review, after checking availability and the rule again.
- At level 2, Codex turning off or failing a build (exit 3 that is
  skipped or repeated, 5, 6 or 7) means "Codex has no room": the failed
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
  is. If the tier changes, update `Model basis` and record why in the Notes.
- If a subagent fails its "Done when", stops because the stage was harder
  than its scores showed, or produces work the review rejects for reasoning
  errors, rerun it one tier higher instead of retrying the same tier, and
  note which measure was under-scored. Where the model is inherited, move to
  the next higher effort the report benchmarked for that model (never above
  its thinking-level ceiling), or build the stage directly. If `top` also
  fails, the brief or the plan is the problem: go back to planning.
- If a subagent stops because the brief is wrong, a higher tier is not the
  fix; revise the plan.
