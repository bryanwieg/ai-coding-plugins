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
- **UserPromptSubmit** adds a one-line reminder when a prompt mentions
  planning, phases, migrating, rewriting, refactoring or implementing. It is
  silent otherwise.

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
`top`). The planner lists the models and thinking levels the running tool
offers in the plan's `models-available.json`, and
`plugins/phased-delivery/scripts/select-models.py` turns that into the plan's
`models.md`; the implementer reruns it before each phase. The script, not the
agent, does the matching and the math: only benchmarked thinking levels count,
Codex models never run above `max` thinking and Claude models never above
`high` (Haiku up to `xhigh`), and each tier gets the cheapest model and
thinking level that scores close enough to the best available.

The script reads `plugins/phased-delivery/model-report.json`, refreshed daily
by `.github/workflows/model-report.yml` from the free
[Artificial Analysis](https://artificialanalysis.ai) API (`model-report.md`
is the same data for people). The workflow needs the repository secret
`ARTIFICIAL_ANALYSIS_API_KEY`; run it by hand from the Actions tab to create
the first report. When the report is missing or more than 7 days old, or
Python is unavailable, the skills fall back to the tools' own model
descriptions. Both scripts use only the Python standard library.

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
installed, signed in and not turned off with `AI_CODEX=off`; this is checked
at the start of each phase. If Codex is not signed in, you are asked to sign
in or skip; skipping turns Codex off for the rest of the session. A build
that cannot run (Codex's sandbox cannot start, a subscription or account
problem, or a sign-in that lapses twice) also turns it off for the session.
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

implement-in-phases commits each stage on its own, with trailers for the
stage, plan, tier, model, effort, attempt and token count, and gives later
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
