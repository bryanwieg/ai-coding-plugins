# Phase 01: Read Claude's plan usage

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md); Codex
builders in [models-codex.md](models-codex.md).
Status: built 02825e2
Before: the agent cannot see Claude's plan usage. Codex usage is read by
`plugins/phased-delivery/scripts/codex-usage.py`. No `statusLine` is set in
`~/.claude/settings.json`.
After: the user's status line saves its JSON to
`~/.claude/claude-usage.json`, and `scripts/claude-usage.py` reads it and
reports Claude's usage level (normal, ahead of pace, nearly out, no data)
with tests. Routing does not use it yet (phase 02).

## Goal of the plan

Quota-aware failover between Claude and Codex in phased-delivery, scaled by
how fast Claude's plan is being used (approved by the user, 2026-11-20):

- Claude on pace: route as today (narrow stages to Codex when it has room).
- Claude ahead of pace: Codex also takes medium-width stages.
- Claude nearly out: Codex takes every build stage and the phase review.
- Claude nearly out and Codex has no room: finish the current stage, commit,
  stop and report both tools' usage.

## Assumptions
- Verified: the status line command receives JSON on stdin with
  `rate_limits.five_hour.used_percentage`, `rate_limits.five_hour.resets_at`,
  `rate_limits.seven_day.used_percentage`, `rate_limits.seven_day.resets_at`
  (percent 0–100, Unix epoch seconds). `rate_limits` appears only on
  claude.ai Pro/Max/Ultra plans after the session's first API response, each
  window may be absent, and a window is dropped once its `resets_at` passes
  (checked in code.claude.com/docs/en/statusline, "Available data").
- Verified: the status line runs at session start and on events (debounced
  300 ms), and Claude Code reloads a changed `statusLine` setting and runs it
  at once (same page, "How status lines work" and the setup walkthrough).
  Limits are account-wide, so any session's copy is valid. A new session's
  first runs have no `rate_limits`, so the capture keeps the last JSON that
  had them: the saved file is as fresh as the last refresh that carried
  `rate_limits`, in any session.
- Verified: no `statusLine` exists in `~/.claude/settings.json` or the
  project's `.claude/settings*.json`; the ponytail plugin's status line
  script is at `~/.claude/ponytail-statusline.sh` and reads its own flag
  file under `${CLAUDE_CONFIG_DIR:-$HOME/.claude}`. Ponytail's session hook
  (`ponytail-activate.js`) treats a `statusLine.command` containing a quoted
  `ponytail-statusline.sh` path as set up, so it will not nudge again; it
  checks that path only when it is absolute, so a `$d/...` form is left
  alone, and it refreshes the copy every session.
- Verified: `~/.claude/ponytail-statusline.sh` starts `#!/usr/bin/env bash`
  and ponytail's own setup runs it with `bash`; it does not read stdin and
  may exit at once, so piping into it can kill a `tee` (reproduced by the
  plan reviewer: 10 of 200 runs left an empty file).
- Verified: `scripts/codex-usage.py` reports the newest log's
  `rate_limits` (`primary`, `secondary`, each with `used_percent`,
  `window_minutes`, `resets_at`) without checking `resets_at`, so figures
  from before a reset still read as used.
- Verified: `scripts/codex-usage.py` is the pattern to copy: stdlib only,
  docstring as usage text, one printed line, exit code as the result.
- Verified: the plugin has no `tests/` directory yet; pytest is installed.
- Verified (2026-11-20, first dispatch of 01.1 and 01.3): inside a sandbox
  container that blocks user namespaces, `codex-build.sh`'s
  `--sandbox workspace-write` cannot start a shell. Codex exits 0, its
  report says it could not read the prompt, and `events.jsonl` contains
  `bwrap: No permissions to create a new namespace`.
- Verified (2026-11-20): the user's plan emits `rate_limits`; after 01.2's
  setting, `~/.claude/claude-usage.json` held `five_hour` and `seven_day`.

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.4 | `codex-build.sh` can skip Codex's sandbox and reports when it cannot start | top | first | done |
| 01.1 | `claude-usage.py` reports Claude's usage level, with tests | middle | after 01.4, parallel with 01.3 | done |
| 01.2 | User's status line saves its JSON for the script | top | after 01.1 | done |
| 01.3 | `codex-usage.py` ignores windows that have reset, with tests | top | after 01.4, parallel with 01.1 | done |

## 01.4 codex-build.sh: sandbox option

Goal: an orchestrator that already runs inside a sandbox can build with
Codex, and a Codex sandbox that cannot start is reported, not accepted.

Context: `plugins/phased-delivery/scripts/codex-build.sh` runs
`codex exec ... --sandbox workspace-write ...`, writes `events.jsonl` and
`stderr.txt` in OUTDIR, exits 3 on lapsed sign-in (a `grep` of
`stderr.txt`), otherwise prints `Tokens: N` and exits with Codex's status.
The failure this fixes is in this phase's Assumptions. The user chose this
option (2026-11-20) over running Codex unsandboxed ad hoc or building in
Claude.

Contracts:
- Environment variable `CODEX_BUILD_SANDBOX`: its value is passed to
  `codex exec --sandbox` unchanged; unset or empty means
  `workspace-write` (today's behavior). Meant to be set to
  `danger-full-access` only when the caller itself runs in a sandbox (a
  container) that is the security boundary. Codex rejects invalid values
  itself.
- New exit code 5: a command's output in `events.jsonl` starts with the
  error, matched as
  `"aggregated_output":"bwrap: No permissions to create a new namespace`
  (a file that merely quotes the error, such as this phase file, must not
  match). Print to stderr
  `Codex's sandbox cannot start here (no user namespaces); if this session
  already runs in a sandbox, set CODEX_BUILD_SANDBOX=danger-full-access`,
  still print the `Tokens:` line, and exit 5. Checked after the exit 3
  check.
- The header comment documents the variable and exit 5. Everything else
  is unchanged.

Files: `plugins/phased-delivery/scripts/codex-build.sh`

Work:
1. Use `"${CODEX_BUILD_SANDBOX:-workspace-write}"` for `--sandbox`.
2. Add the exit 5 check and header lines; keep the usage `sed` range
   covering the whole header.

External inputs: the environment variable (passed through; Codex
validates it) and Codex's event log (matched by a fixed string).

Done when:
- `sh -n plugins/phased-delivery/scripts/codex-build.sh` passes.
- The exit 5 match finds the reproduced failure in
  `/tmp/qf/out-fail/events.jsonl` and none of the successful runs'
  `events.jsonl` (`out-01.1`, `out-01.3`, `out-smoke`).
- With `CODEX_BUILD_SANDBOX=danger-full-access`, a Codex run that prints
  `ok` from a shell command in the repository succeeds.

Out of scope: the routing rule and docs (phase 02 covers mentioning the
variable), other scripts.

Model basis: J0 F0 R0 C1 K2 P0 V1 S1 = 5 -> override 1 (K = 2: turns off a
sandbox; no tests cover the script) -> top. Built directly by the
orchestrator: Codex cannot run here until this stage exists.

## 01.1 claude-usage.py

Goal: `plugins/phased-delivery/scripts/claude-usage.py` reads the saved
status line JSON and prints Claude's usage with one exit code per level.

Context: copy the shape of `plugins/phased-delivery/scripts/codex-usage.py`
(docstring is the usage text, `main(argv)`, `describe()` formats a window
with its UTC reset time, `sys.exit(main(sys.argv))`). Status line fields are
listed in this phase's Assumptions.

Contracts:
- Input file: `${CLAUDE_CONFIG_DIR:-~/.claude}/claude-usage.json`, the whole
  status line JSON. Only `rate_limits.five_hour` and `rate_limits.seven_day`
  are used, each `{"used_percentage": number, "resets_at": epoch seconds}`.
- Window lengths: `five_hour` 5 h, `seven_day` 7 days. Elapsed percent =
  `100 * (1 - (resets_at - now) / length)`, clamped to 0–100.
- A window whose `resets_at` is at or before now is ignored (it has reset;
  the saved figure is stale).
- Constants at the top of the script, no flags:
  `NEARLY_OUT = 90.0` (percent used, either window),
  `AHEAD_POINTS = 10.0` (weekly percent used minus weekly percent elapsed),
  `FIVE_HOUR_AHEAD = 80.0` (percent used of the 5 h window).
- Levels, first match wins, as exit codes:
  - `2` nearly out: either window's used percent >= `NEARLY_OUT`;
  - `1` ahead of pace: weekly used minus weekly elapsed >= `AHEAD_POINTS`,
    or 5 h used >= `FIVE_HOUR_AHEAD`;
  - `0` on pace;
  - `3` no data: file missing, not valid JSON, no `rate_limits`, or no
    window left after dropping reset ones.
- Output: exactly one line on stdout. With data: each present window as
  `5h window 12% used (resets 2026-11-20 18:00 UTC)` and
  `weekly 50% used, 29% of window elapsed (resets 2026-11-25 04:00 UTC)`,
  joined with `; `, then `; as of <file mtime, YYYY-MM-DD HH:MM UTC>`, then
  `; on pace` | `; ahead of pace` | `; nearly out`. No data: one line saying
  why, ending with `run any Claude Code request with a status line set up`.
- The script takes no arguments. Any argument prints the docstring to
  stderr and exits 4 (2 is already a level).

Files:
- `plugins/phased-delivery/scripts/claude-usage.py` (new, executable)
- `plugins/phased-delivery/tests/test_claude_usage.py` (new)

Work:
1. Write the script per the contracts; stdlib only (`json`, `os`, `time`,
   `datetime`, `sys`).
2. Write pytest tests that run the script with `subprocess` and
   `CLAUDE_CONFIG_DIR` set to `tmp_path`, building `resets_at` from
   `time.time()`. Cases: missing file -> 3; invalid JSON -> 3; no
   `rate_limits` -> 3; weekly 20% with 3.5 days left -> 0; weekly 50% with
   5 days left -> 1 (the user's example: 50% used, about 29% elapsed);
   5 h 85% -> 1; weekly 92% -> 2; 5 h 95% -> 2; weekly window with
   `resets_at` in the past and no other window -> 3; output is one line.

External inputs: the saved JSON is written by Claude Code (another system).
Treat missing file, bad JSON, missing keys or non-numeric values as no data
(exit 3); never raise a traceback.

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests/test_claude_usage.py`
  passes (only this stage's file: 01.3 writes its tests in parallel).
- `python3 plugins/phased-delivery/scripts/claude-usage.py` with no saved
  file prints one line and exits 3.

Out of scope: `codex-usage.py`, routing rules, the status line setting.

Model basis: J1 F0 R0 C1 K1 P1 V0 S0 = 4 -> middle (K: reads a file another
system writes). Narrow (F0 R0): Codex-eligible.

## 01.2 Status line capture

Goal: the user's Claude Code status line saves its JSON to
`~/.claude/claude-usage.json` and still shows the ponytail status line.

Context: the user approved this change to their own settings
(2026-11-20). `~/.claude/settings.json` is outside the repository: edit it
with the update-config skill, never commit it. Assumptions above cover the
ponytail script and its nudge check.

Contracts: add to `~/.claude/settings.json`, keeping every other key, this
`statusLine` (the command as plain shell first, then as JSON):

```sh
d="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"; t="$d/claude-usage.json.$$"; find "$d" -maxdepth 1 -name 'claude-usage.json.*' -mmin +1 -delete 2>/dev/null; cat > "$t"; bash "$d/ponytail-statusline.sh" < "$t"; if grep -q '"rate_limits"' "$t"; then mv "$t" "$d/claude-usage.json"; else rm -f "$t"; fi
```

It saves stdin to a per-process temporary file, shows ponytail from it,
and replaces `claude-usage.json` atomically only when the JSON has
`rate_limits`, so readers never see a partial file and new sessions never
erase good data. A run that Claude Code cancels mid-way can leave its
temporary file; each run first deletes such files older than a minute
(a trap cannot: `sh` defers it until the blocked `cat` returns, tested
2026-11-20). It exits 0 when it finishes.

```json
"statusLine": {
  "type": "command",
  "command": "d=\"${CLAUDE_CONFIG_DIR:-$HOME/.claude}\"; t=\"$d/claude-usage.json.$$\"; find \"$d\" -maxdepth 1 -name 'claude-usage.json.*' -mmin +1 -delete 2>/dev/null; cat > \"$t\"; bash \"$d/ponytail-statusline.sh\" < \"$t\"; if grep -q '\"rate_limits\"' \"$t\"; then mv \"$t\" \"$d/claude-usage.json\"; else rm -f \"$t\"; fi"
}
```

Files: `~/.claude/settings.json` only.

Work:
1. Read `~/.claude/settings.json`; if a `statusLine` exists by now, stop and
   ask the user how to combine them.
2. Add the `statusLine` above.
3. Run the command by hand with `CLAUDE_CONFIG_DIR` set to a temporary
   directory holding a copy of `ponytail-statusline.sh` and a
   `.ponytail-active` file containing `full`: once with a sample
   JSON that has `rate_limits` (file written, ponytail text printed, no
   `.json.<pid>` left), once without (file unchanged, no leftover), and
   a leftover `claude-usage.json.1` dated two minutes back
   (`touch -d '-2 min'`) is removed by the next run.

External inputs: none.

Done when:
- `jq .statusLine ~/.claude/settings.json` shows the entry.
- After the session's next API response, `claude-usage.json` exists and
  `scripts/claude-usage.py` exits 0, 1 or 2. If the file is still missing
  then (it is written only when `rate_limits` is present), record in Notes
  that this plan does not emit `rate_limits` and tell the user (the open
  assumption failed; routing stays as today).

Out of scope: README instructions (phase 02).

Model basis: J0 F0 R0 C0 K2 P0 V1 S2 = 5 -> override 1 (K = 2: edits the
user's settings and writes a new persisted file through an untested shell
command) -> top.
Built directly by the orchestrator (user settings, outside the repository);
record it in Notes instead of a stage commit.

## 01.3 codex-usage.py: ignore reset windows

Goal: `scripts/codex-usage.py` stops counting a window whose `resets_at`
has passed, so stale figures from before a reset never read as "no room".

Context: `plugins/phased-delivery/scripts/codex-usage.py`: `latest_limits()`
returns the newest log's `rate_limits`; `main()` reads
`found["primary"]` and `found.get("secondary")`, compares `used_percent`
to `--max-window` / `--max-weekly`; `describe()` formats a window. Phase 02
stops the phase when Claude is nearly out and Codex has no room, so a stale
"over" would stop it for good. Same rule as 01.1's reset handling.

Contracts:
- Exit codes and flags unchanged: 0 room, 1 at or over a maximum, 2 no
  usage data.
- A window (`primary` or `secondary`) whose `resets_at` is at or before
  now counts as 0% used and is shown as `<name> reset since last Codex
  request`.
- No `primary` at all is still exit 2.

Files:
- `plugins/phased-delivery/scripts/codex-usage.py`
- `plugins/phased-delivery/tests/test_codex_usage.py` (new)

Work:
1. In `main()`, treat a reset window as 0% used and describe it as above;
   update the docstring's exit-code paragraph with one sentence on it.
2. Write pytest tests that run the script with `subprocess` and
   `CODEX_HOME` set to `tmp_path`, writing a log at
   `sessions/2026/11/20/s.jsonl` with one line
   `{"payload": {"rate_limits": {"primary": {...}, "secondary": {...}}}}`
   (`used_percent`, `window_minutes`, `resets_at` from `time.time()`).
   Cases: no sessions -> 2; both under -> 0; primary 85 future -> 1;
   secondary 95 future -> 1; primary 100 with `resets_at` in the past and
   secondary 10 -> 0 and the line says "reset since last Codex request".

External inputs: Codex's session logs (another system); behavior for
missing keys is unchanged by this stage.

Done when: `python3 -m pytest -q plugins/phased-delivery/tests/test_codex_usage.py`
passes (only this stage's file: 01.1 writes its tests in parallel; the
phase review runs the whole directory).

Out of scope: `claude-usage.py`, thresholds, how logs are found.

Model basis: J1 F0 R0 C1 K2 P1 V0 S0 = 5 -> override 1 (K = 2) -> top
(C: the plan defines the "reset since last Codex request" output; K: reads
another system's logs, and changes code no test covers; P: no tests exist
yet to copy). Narrow (F0 R0): Codex-eligible.

## Notes
- Plan start: e0fbd56
- 2026-11-20: 01.2 done by the orchestrator: `statusLine` added to
  `~/.claude/settings.json` (other keys unchanged; backup was
  /tmp/qf/settings.backup.json); `claude-usage.py` exits 1 on live data.
  Work step 3 checks passed (rerun by the phase reviewer).
- 2026-11-20: 01.4's first match string also hit successful builds (Codex
  read this file, which quotes the error); fixed in 7728ad2 to match only a
  command output starting with it; contract and Done when updated.
- 2026-11-20: phase review: `claude-usage.py` treated usage above 100% as
  no data; fixed to keep it (nearly out); `codex-build.sh` header notes
  `CODEX_BUILD_SANDBOX`.
- 2026-11-20: first Codex dispatch of 01.1 (gpt-6.2-sol medium, 70869
  tokens) and 01.3 (gpt-6.2-astra high, 99410 tokens) failed: Codex's
  sandbox cannot start in this container. Added 01.4 (user's choice); both
  stages rerun after it. 01.2's settings were applied early (only its
  final check needs 01.1); the open `rate_limits` assumption is verified:
  the saved JSON has `five_hour` and `seven_day`.
- 2026-11-20: review round 3: 01.3 re-scored K2 -> top.
- 2026-11-20: review round 2: each status line run sweeps leftover temp
  files older than a minute (a trap was tested and does not fire while
  `cat` blocks);
  parallel stages test only their own files; 01.2 and 01.3 re-scored.
- 2026-11-20: review round 1: atomic status line capture that keeps the
  last `rate_limits` and runs ponytail with bash; added 01.3; 01.2 re-scored.
- 2026-11-20: plan written. Thresholds (90 nearly out, 10 points ahead of
  weekly pace, 80% of 5 h) are starting values; tune from work reports.
