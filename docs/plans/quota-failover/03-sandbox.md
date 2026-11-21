# Phase 03: Sandbox support

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md); Codex
builders in [models-codex.md](models-codex.md).
Status: built fe9a71b (ai-coding-sandbox)
Before: phase 02 makes the plugin read `AI_CODEX` and Claude's saved
status line JSON. In the ai-coding sandbox, each user sets the status
line capture by hand (phase 01 stage 01.2), and a Claude session always
sets up Codex too.
After: the sandbox sets the status line capture itself at every start
when the user has none, and `AI_CODEX=off` in `.sandbox/agent.env` makes a
Claude session skip Codex's setup. The sandbox's README and session guide
describe both.

**Repository:** every path below is in `ai-coding-sandbox`
(`/workspace/ai-coding/ai-coding-sandbox`), not in this plan's
repository. Build it from the plan's own session, where both repositories
are mounted, on a new branch `ai-codex-statusline` from `origin/main`;
record its base commit in Notes. Follow that repository's `AGENTS.md`
(ShellCheck, `sandbox/bin/check-sandbox`, `git diff --check`, clean
tree). Its image tests (`test-session-agent-launch.sh`) build the agent
image, which needs the npm registry this session's proxy blocks; they run
in the repository's pull request CI (`.github/workflows/sandbox-image.yml`),
which is their verification here. Host tests run locally. Stage commits
and their trailers go in the sandbox repository; `Plan:` points to this
file; plan status and Notes are committed here. The work report runs
`stage-stats.sh` in both repositories (each from its own start commit)
and puts both tables in `work-report.md`. Stages are Codex-eligible as
scored; a Codex build passes the sandbox checkout as `codex-build.sh`'s
REPO, so its writes stay inside one repository. Stages are accepted on
their local checks. Route and build them by phase 02's rules as built
on the `quota-failover` branch: follow that checkout's
`model-selection.md` and run its `plugins/phased-delivery/scripts/`
(`codex-usage.py`, `claude-usage.py`, `codex-build.sh`), not the
installed plugin, which is still 0.4.0.

The user asked (2026-11-21) for the work to end with pull requests up and
CI passing. In order, after the phase review: push the sandbox branch and
open its pull request; wait for CI and fix failures with `Fixes-Stage`
commits until it passes; set the status to `built <final commit>` and
record the CI result in Notes; write the work report; then push the
plugin repository's `quota-failover` again (its pull request was opened
after phase 02). That repository has no pull request CI, so "CI passing"
applies to the sandbox pull request. No Dockerfile, Compose, proxy
or session-rules change is planned; one needed means stop and ask the
user (its "Changes to the security boundary").

## Contracts (for all stages)

- `AI_CODEX`: the user's switch, set in `.sandbox/agent.env` (passed to
  both agents and their commands unchanged). `off` means Codex is not
  used; unset or any other value changes nothing. The plugin reads the
  same variable (phase 02).
- Status line capture, the `statusLine` the sandbox writes:

  ```sh
  d="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; t="$d/claude-usage.json.$$"; find "$d" -maxdepth 1 -name 'claude-usage.json.*' -mmin +1 -delete 2>/dev/null; cat > "$t"; p="$d/ponytail-statusline.sh"; [ -f "$p" ] || p="$d/plugins/marketplaces/ponytail/hooks/ponytail-statusline.sh"; if [ -f "$p" ]; then bash "$p" < "$t"; fi; if grep -q '"rate_limits"' "$t"; then mv "$t" "$d/claude-usage.json"; else rm -f "$t"; fi
  ```

  It is phase 01's command (01-claude-usage.md, 01.2 Contracts) with the
  ponytail call run only when a script exists, since not every user has
  ponytail: the user-folder copy, else ponytail's marketplace clone.
  The fallback is needed because ponytail's session hook copies its
  script into the folder only when it nudges (no `statusLine` at all) or
  a copy already exists; with this `statusLine` set before the first
  start, a new user never gets the copy. As JSON: `{"type": "command", "command": "<the line>"}`.

## Assumptions
- Verified: `sandbox/image/sandbox-start` runs
  `"$libexec_dir"/init.d/*`, then `"$libexec_dir/$agent"/init.d/*`, then
  `"$libexec_dir/$other"/init.d/*`, with `other=codex` when
  `SANDBOX_AGENT=claude`. Codex's init steps are
  `sandbox/codex/init.d/10-context7-config` and `20-plugins`.
- Verified: `sandbox/image/init.d/01-login` checks only the launched
  agent's sign-in (`sandbox-auth status`); a Claude session never prompts
  for Codex's, so skipping Codex's init steps is all "off" needs.
- Verified: `sandbox/claude/init.d/20-settings` rewrites
  `${CLAUDE_CONFIG_DIR:-$HOME/.claude}/settings.json` at each start with
  one `jq -s '(.[0] // {}) | ...'` through a temporary file and `mv`,
  keeping other keys, and warns instead of failing when `jq` fails.
- Verified (2026-11-21): ponytail ships with the sandbox
  (`sandbox/claude/plugins.txt`, `ponytail@ponytail`); its hook
  (`hooks/ponytail-activate.js`, the `nudge` and `fs.existsSync(scriptPath)`
  lines) copies `ponytail-statusline.sh` into the config folder only when
  nudging or when a copy exists; the script is also at
  `~/.claude/plugins/marketplaces/ponytail/hooks/ponytail-statusline.sh`
  (unversioned path).
- Verified: the user's current `statusLine.command` is exactly phase
  01's command (`jq .statusLine ~/.claude/settings.json`, 2026-11-21).
- Verified: `sandbox/tests/test-session-agent-launch.sh` (the
  "sandbox-start runs the shared init scripts and both agents'" block)
  runs `sandbox-start --probe` in the image with stub CLIs and checks
  `/tmp/calls` and `ls /tmp`, where `/tmp/codex` exists only after
  Codex's init ran; `sandbox/tests/test-plugin-sync.sh` is the host-test
  pattern for one init script (`run` sets the state variable and runs
  the hook with `sh`). Both are in `.github/workflows/sandbox-image.yml`;
  host tests are at lines 56–66.
- Verified: docs to update are `sandbox/README.md` "## Claude Code
  settings" and the paragraph starting "Both agents run without their own
  bubblewrap sandboxes" (it names `CODEX_BUILD_SANDBOX`), and
  `sandbox/image/session-guide.md` "### `agent.env`" (checked on
  `origin/main` by the plan reviewer).
- Verified: `shellcheck sandbox/image/sandbox-start` already reports
  SC2015 (info) on `origin/main`; the repository has no `.shellcheckrc` and
  CI runs no ShellCheck, so checks use `shellcheck -S warning`.
- Verified (2026-11-21): branch `ai-codex-statusline` created from
  `origin/main` (ffb401a); `sandbox-start`'s loop, `20-settings`'s `jq`
  line, both README sections, the session guide section and the
  `test-plugin-sync.sh` workflow line are there.

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 03.1 | `AI_CODEX=off` skips Codex's setup in Claude sessions | middle | first, parallel with 03.2 | done |
| 03.2 | The sandbox sets the status line capture when there is none | top | first, parallel with 03.1 | done |
| 03.3 | README and session guide describe both | middle | after 03.1 and 03.2 | done |

## 03.1 Skip Codex's setup when off

Goal: with `AI_CODEX=off`, `sandbox-start` in a Claude session runs no
Codex init step; everything else is unchanged.

Context: the `sandbox-start` loop and the launch test cited in
Assumptions.

Contracts: `AI_CODEX` above. Only the other agent's steps are skipped,
and only when that agent is Codex; a Codex session runs as today
(launching Codex with it off is the user's choice).

Files:
- `sandbox/image/sandbox-start`
- `sandbox/tests/test-session-agent-launch.sh`

Work:
1. Before the init loop, set the other agent's init directory to a path
   that does not exist when `other=codex` and `${AI_CODEX:-} = off`, so the
   loop's `[ -f ... ]` skips it; add a one-line comment why. Update the
   header comment's sentence on the other agent.
2. In the test, after the existing loop, run the Claude case once more
   with `-e AI_CODEX=off` and check that `ls /tmp` lists `claude` and not
   `codex`, and that the launcher still ran (`claude ... --probe`).

External inputs: the `AI_CODEX` environment variable (compared to `off`
only).

Done when:
- `shellcheck -S warning sandbox/image/sandbox-start sandbox/tests/test-session-agent-launch.sh`
  passes.
- Checked after the push: the pull
  request's "Session image tests" CI step passes, including the new case
  (the image cannot be built in this session).

Out of scope: `01-login`, Codex's own init scripts, Compose, the
Dockerfile.

Model basis: J1 F0 R0 C1 K0 P0 V0 S0 = 2 -> override 2 (J, C not 0) ->
middle.

## 03.2 Status line capture by default

Goal: at each start, `20-settings` sets the capture `statusLine` when
`settings.json` has none or has exactly phase 01's command, and leaves
any other status line alone.

Context: `sandbox/claude/init.d/20-settings` and `test-plugin-sync.sh`'s
host-test pattern, cited in Assumptions. Phase 01's command is in
01-claude-usage.md, stage 01.2 Contracts (the JSON form); the new one is
in this phase's Contracts.

Contracts:
- In the same `jq` call, after setting `skipDangerousModePermissionPrompt`:
  when `.statusLine` is absent or `.statusLine.command` equals phase 01's
  command exactly, set `.statusLine` to the capture above; otherwise keep
  it. Pass both commands to `jq` with `--arg`, never by string pasting.
- No output on start. A user status line that is kept means no usage
  capture; the README says so (03.3).

Files:
- `sandbox/claude/init.d/20-settings`
- `sandbox/tests/test-claude-settings.sh` (new host test)
- `.github/workflows/sandbox-image.yml` (add the test to the host-test
  list next to `test-plugin-sync.sh`)

Work:
1. Read the two commands into shell variables from quoted heredocs
   (`capture=$(cat <<'EOF'` ... `EOF` `)`), since both contain `'`, `"`
   and `$`, which must stay literal; phase 01's is byte for byte the
   `command` value of 01.2's JSON, decoded. Add the `jq` condition.
2. Write the test in `test-plugin-sync.sh`'s style (`pass`, `fail`, temp
   dir, `CLAUDE_CONFIG_DIR` set, the hook run with `sh`): no settings file
   -> capture set and `skipDangerousModePermissionPrompt` true; other keys
   kept; phase 01's command (the test's own copy, written into the
   settings with `jq --arg`, never the hook's variable) -> replaced; a different command -> kept;
   running twice changes nothing. Then run the written command itself
   with `sh -c`, in a temp `CLAUDE_CONFIG_DIR`: input with `rate_limits`
   -> `claude-usage.json` written, no `claude-usage.json.*` left; input
   without -> file unchanged; with a stub `ponytail-statusline.sh` that
   prints `pt` -> `pt` printed; with only a stub at
   `plugins/marketplaces/ponytail/hooks/ponytail-statusline.sh` -> its
   output printed; with neither -> nothing printed, exit 0.

External inputs: the existing `settings.json` (user-owned; `jq` already
fails on invalid JSON and the script warns, unchanged).

Done when:
- `shellcheck -S warning` passes on both scripts.
- `sh sandbox/tests/test-claude-settings.sh` passes locally (and in CI
  after the push).

Out of scope: the plugin's README, ponytail's own setup, other settings.

Model basis: J1 F1 R0 C1 K2 P1 V0 S0 = 6 -> override 1 (K = 2: rewrites
user settings at every start; migrates a persisted value) -> top.

## 03.3 Sandbox docs

Goal: the sandbox's README and session guide describe `AI_CODEX` and the
status line capture.

Context: the sections cited in Assumptions; 03.1 and 03.2's contracts.

Contracts: this phase's Contracts.

Files:
- `sandbox/README.md`
- `sandbox/image/session-guide.md`

Work:
1. README "## Claude Code settings": one paragraph: `20-settings` also
   sets a status line that saves Claude's plan usage to
   `claude-usage.json` (read by phased-delivery's `claude-usage.py`) and
   shows ponytail's status line when installed; it replaces only phase
   01's hand-set command and leaves any other status line, which then
   captures no usage.
2. README Codex-builder paragraph: add that `AI_CODEX=off` in
   `.sandbox/agent.env` turns Codex off: Claude sessions skip its setup
   and phased-delivery builds nothing with it.
3. session-guide.md "### `agent.env`": name `AI_CODEX` (`off` turns Codex
   off for the agent and for phased-delivery) alongside the examples.

External inputs: none.

Done when:
- `grep -n AI_CODEX sandbox/README.md sandbox/image/session-guide.md`
  finds both files.
- `grep -n claude-usage.json sandbox/README.md` finds a line.
- `sandbox/bin/check-sandbox` and `git diff --check` pass.

Out of scope: root `README.md` (its contract is unchanged), session
rules, plugin docs.

Model basis: J1 F0 R1 C0 K0 P1 V1 S0 = 4 -> middle.

## Notes
- 2026-11-21: 03.2: the orchestrator added, before accepting, a guard so a
  `statusLine` that is not an object keeps the settings update working
  (bypass mode still set), with a test case.
- 2026-11-21: phase review (opus high): ready, 0 blocking, no fixes.
- 2026-11-21: sandbox PR bryanwieg/ai-coding-sandbox#15: CI passed (check
  12m11s, session 5m16s), including `AI_CODEX=off skips Codex setup in a
  Claude session` and `Claude settings checks passed.`
- Sandbox start: ffb401a (branch `ai-codex-statusline`); work report counts
  `ffb401a..HEAD` in ai-coding-sandbox.
- 2026-11-21: Codex off this session (sign-in token expired, `codex-build.sh`
  exit 3 pattern per 02.5); stages built in Claude.
- 2026-11-21: plan review round 4: push order ends with CI green before
  the work report; phase 03 uses the branch's phase 02 rules and scripts.
- 2026-11-21: plan review round 3: ponytail fallback to its marketplace
  clone; plugin repository push points.
- 2026-11-21: plan review round 2: push and PR on the user's request;
  CI-pending status; Codex builds use the sandbox checkout as REPO.
- 2026-11-21: plan review: built from the plan's session (a sandbox-repo
  session cannot read this plan); image tests verified by the PR's CI;
  heredoc quoting; `shellcheck -S warning`; sections cited by name.
- 2026-11-21: phase added (user, 2026-11-21): the sandbox ships the status
  line capture and honors `AI_CODEX`, chosen over sandbox-only or
  plugin-only names. Written from `20-settings` inline, so no Dockerfile
  change (which would need separate approval).
