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

- **Reviews use the `top` candidate**, whatever the tier of the work under
  review. A review exists to catch what the author missed, including bad
  assumptions; a weaker reviewer defeats the point.
- **Planning and plan revision** use `top`.
- Never dispatch below the tier the scores give without a written reason in
  the phase's Notes.

## Builders in another tool

When the session is not Codex but Codex is installed and signed in
(`codex login status`), stages may be built there with
`scripts/codex-build.sh`. Codex runs on its own plan, so this spares the
session's quota, and Codex models follow a brief closely when it is narrow.
They lose track across many files and large amounts of data, so width
decides, not tier.

- **Plan time:** also write `models-available-codex.json` (`tool`: `codex`,
  models and efforts from `codex debug models`, `subagent_model_choice`:
  `allowed`, since `codex-build.sh` sets the model) and generate
  `models-codex.md` from it with the selector. All tier rules and ceilings
  apply unchanged.
- **Send a stage to Codex only when all hold:**
  - it is narrow: F = 0 and R = 0 (1–2 files changed, at most 3 to read).
    Refactors, renames across files and stages that must make sense of a
    large data set stay in the session's tool, whatever their tier;
  - `scripts/codex-usage.py` exits 0 (room left in the Codex plan);
  - `models-codex.md` has a candidate for the stage's tier.
- Otherwise build it in the session's tool. Planning and reviews stay in
  the session's tool on `top`.
- If `codex-build.sh` exits 3, tell the user Codex needs `codex login`
  again, and build the stage in the session's tool meanwhile.

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
