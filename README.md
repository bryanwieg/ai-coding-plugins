# AI coding plugins

Personal plugins for coding agents, for Claude Code and Codex.

## Layout

```
.claude-plugin/marketplace.json     Marketplace: lists every plugin
plugins/<plugin>/
  .claude-plugin/plugin.json        Plugin manifest
  skills/<skill>/SKILL.md           Agent skills
  hooks/hooks.json                  Optional hooks, with their scripts
```

Each plugin directory is self-contained. Codex reads the same
`.claude-plugin` marketplace and manifests, so one copy serves both tools; a
separate `.codex-plugin/plugin.json` is only needed if a plugin must differ
in Codex.

## Plugins

| Plugin | Skills |
| --- | --- |
| `phased-delivery` | `plan-in-phases`, `implement-in-phases` |

### Automatic use of phased-delivery

The agent picks the skills on its own from their descriptions, and the
plugin's hooks encourage it further:

- **SessionStart** tells the agent when to use each skill, and lists
  unfinished phase files in the repository (found by the "Implement with the
  implement-in-phases skill" line every phase file carries).
- **UserPromptSubmit** adds a one-line reminder when a prompt asks to plan,
  build or change something (planning, phases, migrating, rewriting,
  refactoring, implementing, adding, building, creating, changing, updating,
  extending, replacing, supporting, integrating, features). The skill's capped
  estimate sends small changes back to direct work. It is silent otherwise,
  for example on questions and plain fixes.

The hooks are POSIX `sh` with only `git`, `grep`, `sed` and `awk`; no `jq`
or other install is needed. Both skills can
also be run directly as `/plan-in-phases` and `/implement-in-phases`.

To make phased delivery the rule in a particular project, add to its
`CLAUDE.md` (Claude Code) or `AGENTS.md` (Codex):

```
Plan any change that touches several files, a shared contract or the
architecture with the plan-in-phases skill before writing code, and build
phased plans only with the implement-in-phases skill.
```

### Models

The skills never name models. Each plan records tiers (`small`, `middle`,
`top`) and each stage's eight scores. The planner lists the models and
thinking levels the running tool offers in the plan's
`models-available.json`, and `plugins/phased-delivery/scripts/select-models.py`
turns that into the plan's `models.md`, the per-tier summary. The script,
not the agent, does the matching and the math: only benchmarked thinking
levels count, Codex models never run above `max` thinking and Claude models
never above `high` (Haiku up to `xhigh`), and each tier gets the cheapest
model and thinking level that scores close enough to the best available.

The script reads `plugins/phased-delivery/model-profiles.json`: one entry
per model and thinking level with its scores, prices, speed, a premium or
standard price class and what each step up in thinking level gains and
costs. `.github/workflows/model-report.yml` fetches the free
[Artificial Analysis](https://artificialanalysis.ai) API once a week
(`model-report.md` is the same data for people) and rebuilds and commits
the profiles only when the model list or a price changes; a change to
scores alone is ignored. The workflow needs the repository secret
`ARTIFICIAL_ANALYSIS_API_KEY`; run it by hand from the Actions tab to
create the first profiles. The selector uses the profiles at any age and
writes their fingerprint into `models.md`; at the start of each phase the
implementer runs `select-models.py check` and reruns the selector only when
the profiles changed. When the profiles are missing, or Python is
unavailable, the skills fall back to the tools' own model descriptions. The
scripts use only the Python standard library.

At each dispatch, `select-models.py route` picks one model and thinking
level for the stage from its scores: only pairs on the score/cost frontier,
no thinking step that gains under 2 points for more than 1.5 times the
cost, lower thinking for mechanical stages, a larger model at lower
thinking for design work, faster models for long or wide work and one step
up for risk. Claude stages and phase reviews are then built headless by
`plugins/phased-delivery/scripts/claude-build.sh` (`claude -p`), stopped at
a dollar cap: 150k tokens for `small`, 400k for `middle`, 1M for `top`, at
the pair's input price. A stage stopped at its cap is retried one step down
the frontier; one that fails its checks, one step up. Premium models
(output price of $30 or more per million tokens) are used below `top` only
when cheaper than the standard pick and as good, and get $10 per phase; past
that, builds use none. Reviews always run on `top`, and their cost counts
against that budget. The builder may edit files and runs only the commands
your project's permission rules allow; set
`CLAUDE_BUILD_PERMISSIONS=bypassPermissions` only when Claude Code already
runs in a sandbox container (the ai-coding sandbox image sets it). Every cap is at least $0.25, since a cheap
model's cap at its input price alone would round to a cent. The caps and
cutoffs are not yet calibrated.

### Planning mode

plan-in-phases starts with a quick estimate that decides how much planning a
change gets: **direct** (no plan; the change is made in context), **quick**
(one phase file checked by the script, no review subagent) or **full**. The
agent first sketches the parts from the request alone; `plugins/phased-delivery/scripts/plan-mode.py`
searches for the users of what changes and prints the lowest and highest
score the sketch allows, and when both give the same mode the estimate
stops there, before any file is read. Otherwise the agent lists up to 5
terms, the script finds the files that mention them, the agent reads at most 5 and fills a
form, and the script searches for the users of what changes and scores
kind × size × reach per part. A quick plan is re-scored from its `plan.json`
and can move up to full or down to direct. `evals/mode/` holds the
calibration cases and their results.

### Plan checks

plan-in-phases writes the plan as JSON in a `.plan/` folder while planning:
`plan.json` (outcomes, cross-phase decisions, a contract registry, outcome
tests, phases and stages) and one `NN.json` per phase. Field guides in the
skill say what goes in each field, down to the interface level and no
further. `plugins/phased-delivery/scripts/plan-check.py` checks what needs no
judgment (each contract listed by its provider and users, build order, files,
outcome coverage, tiers, spec and design quotes, code citations, no code in
briefs) and renders the `NN-name.md` phase files, which are the plan once it
is reported. The plan reviewer reports only a closed list of finding types.
It uses only the Python standard library; without Python, the planner writes
the phase files directly and checks by reading.

### Build checks

implement-in-phases follows the same pattern. Revising a phase ends in
`.build/NN-revision.json` (each stage's files, check commands and scores),
and `plugins/phased-delivery/scripts/build-check.py` does the bookkeeping:
it gates each build (no changed file outside the stage, every check
passes), refuses a model and thinking level already tried for the stage,
sums the premium spend for routing, and makes each stage, fix and phase
commit with its trailers. A ledger in `.build/` keeps every attempt, so a
resumed session picks up where it stopped. The phase reviewer writes
`.build/NN-review.json` with a closed list of finding types. SKILL.md is a
short outline; each step's directions are in its own guide.

Some tools, Codex among them, let subagents use a different model only when the
user asks. To allow it, add to the project's `AGENTS.md` or `CLAUDE.md`:

```
Use phased-delivery model selection to choose subagent models.
```

Without that line, subagents inherit the session's model and only the effort
level follows the tier. If your account lacks a model the tool lists, say so
in the project instructions (for example "Fable is not available on this
account") and the planner leaves it out.

`small` is only for mechanical stages (no judgment, no dependent steps,
checked by commands); the cheapest models copy precise changes well but
misreport their own actions, so the implementer checks `small` work itself.

### Building with Codex from Claude Code

Stages can be built with `codex exec` through `scripts/codex-build.sh`, on
your Codex plan instead of your Claude quota. Codex is used only when it is
installed, signed in and not turned off with `AI_CODEX=off`. Codex is
checked at most once a day: `scripts/codex-usage.py` caches the answer in
`~/.claude/codex-availability.json`, and every session started that day is
told at once when Codex is off. Off (not installed, not signed in, or a
build that cannot run: Codex's sandbox cannot start, a subscription or
account problem, or a lapsed sign-in) lasts the rest of the day, with no
prompt. After fixing it (for example `codex login --device-auth`), run
`scripts/codex-usage.py --recheck` to use Codex again the same day.
Codex also loads your installed Codex plugins, which can change how it
builds.

While Codex is on, how much goes there depends on both tools' usage, checked
before every stage and before the phase review:

- Claude on pace (or no usage data): narrow stages only (1–2 files changed,
  at most 3 to read).
- Claude ahead of pace: also stages one step wider or deeper.
- Claude nearly out: every build stage and the phase review.

Until Claude is nearly out, refactors and stages that must make sense of
large data stay in Claude. `scripts/claude-usage.py` reads Claude's level;
`scripts/codex-usage.py` reads Codex's remaining limits from its local
session logs (as of the last Codex request). When Codex has no room, stages
are built in Claude; when both are nearly out, the phase stops after the
stage in progress and reports both tools' usage and reset times, so you can
resume later.

Setup: Claude's usage is read from the status line's JSON, so the status
line must save it. In `~/.claude/settings.json`, set `statusLine` to
`{"type": "command", "command": ...}` with this command (as a JSON string,
quotes escaped):

```sh
d="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; t="$d/claude-usage.json.$$"; find "$d" -maxdepth 1 -name 'claude-usage.json.*' -mmin +1 -delete 2>/dev/null; cat > "$t"; bash "$d/ponytail-statusline.sh" < "$t"; if grep -q '"rate_limits"' "$t"; then mv "$t" "$d/claude-usage.json"; else rm -f "$t"; fi
```

`bash "$d/ponytail-statusline.sh" < "$t"` stands for your own status line
command, which then reads `< "$t"`; drop it if you have none. ai-coding
sandbox images with `AI_CODEX` support set this up themselves. The usage
data needs a Claude Pro, Max or Ultra plan; without it, routing stays
narrow-only. Set `CODEX_BUILD_SANDBOX=danger-full-access` only when Claude
Code itself runs in a sandbox container where Codex's own sandbox cannot
start (the ai-coding sandbox already sets it).

### Tracking which model did what

implement-in-phases commits each stage on its own (`build-check.py commit`), with trailers for the
stage, plan, tier, model, effort, attempt, token count and cost, and gives later
fixes to a stage their own commits marked `Fixes-Stage:`. When the plan is
done, it writes `work-report.md` in the plan directory: per model and
effort, the stages built, how many were right first time ("clean": accepted
on the first dispatch and never fixed), failed tries, fixes needed, tokens
spent and wasted, and a short reading of which models earned their tier.
The tables come from a script you can run on any range yourself:

```
sh plugins/phased-delivery/scripts/stage-stats.sh [rev-range]
```

## Use

In the AI coding sandbox, set the repository in `sandbox/.env`:

```
CLAUDE_DEV_PLUGIN_REPO=bryanwieg/ai-coding-plugins
```

Every Claude session then loads these plugins straight from a Git clone in its
state volume. The clone is fast-forwarded at launch when it has no local
changes, edits apply after `/reload-skills` or `/reload-plugins`, and pushing
is always an explicit step.

Outside the sandbox:

```
claude --plugin-dir plugins/phased-delivery
```

or add it as a marketplace:

```
claude plugin marketplace add bryanwieg/ai-coding-plugins
claude plugin install phased-delivery@ai-coding-plugins
```

### Codex

```
codex plugin marketplace add bryanwieg/ai-coding-plugins
codex plugin add phased-delivery@ai-coding-plugins
```

Codex lists the skills as `phased-delivery:plan-in-phases` and
`phased-delivery:implement-in-phases`. It runs a hook only after you approve
it, so approve the plugin's two hooks when Codex asks; until then the skills
work, only the reminders are missing. To update, refresh the marketplace
and add the plugin again, then start a new session:

```
codex plugin marketplace upgrade ai-coding-plugins
codex plugin add phased-delivery@ai-coding-plugins
```

## Design notes

[docs/model-routing.md](docs/model-routing.md): the goals behind model picking,
Codex/Claude routing and work reports, the evidence so far, and open
questions.

## Evals

`evals/` measures builder models on stage briefs with hidden checks and
blind grading, for Claude Code subagents and `codex exec`. See
[evals/README.md](evals/README.md).

## Adding a plugin

1. Create `plugins/<name>/.claude-plugin/plugin.json` and its `skills/`.
2. Add the plugin to `.claude-plugin/marketplace.json` with
   `"source": "./plugins/<name>"`.
3. Run `claude plugin validate .` before committing.
