# Phase 02: Route by usage and availability

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md); Codex
builders in [models-codex.md](models-codex.md).
Status: planned
Before: phase 01 built `scripts/claude-usage.py` (exit 0 on pace, 1 ahead
of pace, 2 nearly out, 3 no data, 4 bad arguments) and the status line
capture. Routing sends only narrow stages (F = 0, R = 0) to Codex, and
nothing checks whether Codex can be used at all.
After: before each phase the skills check whether Codex is available and
leave it out of routing entirely when it is not; when it is, they route
stages by both tools' usage on the scale below and stop the phase when
both are nearly out. The README and `docs/model-routing.md` describe it.
Plugin version 0.5.0.

## Codex availability (contract for all stages)

Codex is **off** for the rest of the session when any of these holds, and
**on** otherwise:

| Cause | Detected by | Action |
| --- | --- | --- |
| `AI_CODEX=off` in the environment | `codex-usage.py` exit 3 | off, no prompt |
| `codex` not installed | `codex-usage.py` exit 3 | off, no prompt |
| not signed in | `codex-usage.py` exit 4 | ask the user: sign in (`! codex login --device-auth`), then check again; or skip, which turns it off |
| Codex cannot be used (expired subscription, account error) | `codex-build.sh` exit 6 | off |
| Codex's sandbox cannot start here | `codex-build.sh` exit 5 | off; tell the user about `CODEX_BUILD_SANDBOX` |
| sign-in lapsed during a build | `codex-build.sh` exit 3 | ask the user: sign in again (`! codex logout && codex login --device-auth`, the command the script prints) or skip; a second exit 3 in the session turns it off |

- **A failed Codex build** (exit 3, 5, 6 or 7) leaves no accepted work.
  Before each Codex dispatch, save `git status --porcelain` of the
  repository. On failure, before anything else, restore to `HEAD` every
  tracked path that changed since that snapshot and delete every untracked
  path that is new in it. If such a path already had edits in the
  snapshot, stop and ask the user instead of restoring it. Then the stage
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
- `AI_CODEX` is the user's switch, shared with the ai-coding sandbox
  (phase 03): `off` turns Codex off; unset or any other value leaves it to
  detection.

## The routing rule (contract for all stages)

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

- Codex builds use the tier's candidate in `models-codex.md`; a Codex review
  uses its `top` candidate, through `scripts/codex-build.sh` with
  phase-reviewer.md as the prompt file.
- **Stop and report:** finish and commit the stage in progress, update the
  phase status line and Notes, commit them, and stop. Report the stages
  done and left and both scripts' output lines (usage and reset times).
  When the stop comes at the check before the phase review, set
  `Status: in progress (stages done: all; review pending)`; resuming
  starts with the review, after checking availability and the rule again.
- At level 2, Codex turning off or failing a build (exit 3, 5, 6 or 7)
  means "Codex has no room": the failed stage is not rebuilt in the
  session; restore it as above, leave it `planned`, stop and report, with
  the cause.
- **Session-only stages** (those that must write outside the repository,
  or whose brief says it is built in the session or by the orchestrator)
  are built in the session at every level, including level 2; the rule
  never sends them to Codex.
- Planning, plan revision, plan-review rounds and the orchestrator's own
  work stay in the session at every level; only stage builds and the phase
  review are routed (`codex-build.sh` can write only the repository and
  /tmp, hence the session-only stages above).
- Without `models-codex.md` (no Codex at plan time), nothing changes from
  today.
- When the level changes during a phase, record it in the phase's Notes
  with both scripts' output lines.

## Assumptions
- Verified: routing lives in
  `plugins/phased-delivery/skills/plan-in-phases/model-selection.md`,
  section "Builders in another tool" (ends before "Adjust while working"),
  and in `plugins/phased-delivery/skills/implement-in-phases/SKILL.md`, the
  paragraph starting "When the plan has `models-codex.md`"; the review is
  in "### 3. Review the phase".
- Verified: `scripts/codex-build.sh REPO PROMPT MODEL EFFORT OUTDIR` takes any
  prompt file; it checks exit 3 (lapsed sign-in, `grep` of `stderr.txt`),
  then exit 5 (bwrap match in `events.jsonl`), prints `Tokens: N` from the
  last `turn.completed` event (`unknown` when there is none) and exits with
  Codex's status otherwise.
- Verified (2026-11-21, strings in the installed Codex binary): Codex's
  JSON events include `turn.completed` and `turn.failed`, and its
  usage-limit errors all contain `hit your usage limit` (for example
  "You've hit your usage limit. Visit https://chatgpt.com/settings/usage
  ..."); the free plan's says `hit your usage limit. Upgrade to Plus to
  continue using Codex`, which is what a lapsed subscription reaching
  its free allowance shows. Not seen in a real run here.
- Verified: `scripts/codex-usage.py` exits 0 room, 1 over its cutoffs, 2 no
  data, and ignores windows that have reset (01.3). A bad flag raises
  `SystemExit(__doc__)`, which exits 1; left as is (no caller passes flags).
- Verified (2026-11-21): `codex login status` prints `Logged in using
  ChatGPT` and exits 0 when signed in; with an empty `CODEX_HOME` it prints
  `Not logged in` and exits 1; it runs locally in about 50 ms.
- Verified (2026-11-21): the session log's `rate_limits` carries
  `plan_type` (`plus` here). Not used: a free ChatGPT plan still gets some
  Codex use (third-party report), so an expired subscription cannot be
  told from `plan_type`; the build failure (exit 6) catches it instead.
- Verified: in this sandbox `CODEX_BUILD_SANDBOX=danger-full-access` is set
  by the image (`ai-coding-sandbox/sandbox/Dockerfile`, `ENV` block); the
  user need not set it there.
- Verified: user-facing descriptions are README.md "### Building with Codex
  from Claude Code" and `docs/model-routing.md` "## Part 2", "How it works
  now" bullets (after the 2026-11-21 rebase: "A stage goes to Codex only
  when it is **narrow**", "Planning and reviews stay ...", the
  `codex-build.sh` bullet, upstream's container bullet naming
  `CODEX_BUILD_SANDBOX`, and "Usage visibility"), and the open
  question "Quota-aware failover" in "## Open questions and next steps";
  plugin version is in `plugins/phased-delivery/.claude-plugin/plugin.json`
  (`0.4.0`).
- Verified: copies under `evals/tasks/*/reference` and `.claude/worktrees/`
  are eval fixtures and other branches; they are not changed.
- Open: the exact error Codex gives for an expired subscription is unknown
  and cannot be produced here. Exit 6 does not match it: any run that ends
  without a `turn.completed` event and without a usage-limit message
  counts as "cannot be used", and its error text is shown. If real failures
  show a transient cause (network) turning Codex off too often, narrow
  exit 6 to the observed messages.

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 02.1 | `codex-usage.py` reports Codex off or signed out, with tests | middle | first, parallel with 02.2 | planned |
| 02.2 | `codex-build.sh` reports out of quota (7) or unusable Codex (6) | top | first, parallel with 02.1 | planned |
| 02.3 | Skills check availability and route by usage | middle+ | after 02.1 and 02.2 | planned |
| 02.4 | README, routing doc and version describe it | middle+ | after 02.3 | planned |

## 02.1 codex-usage.py: availability

Goal: `scripts/codex-usage.py` exits 3 when Codex is off or not installed
and 4 when it is not signed in, before reading any usage.

Context: `plugins/phased-delivery/scripts/codex-usage.py`: `main(argv)`
parses flags, then calls `latest_limits()` and prints one line;
`plugins/phased-delivery/tests/test_codex_usage.py` (01.3) runs it with
`subprocess` and `CODEX_HOME=tmp_path`. `codex login status` behavior is in
Assumptions.

Contracts:
- New checks in `main()`, after flag parsing, in this order, each printing
  one line and returning:
  1. `os.environ.get("AI_CODEX") == "off"`: print
     `Codex is off (AI_CODEX=off)`, exit 3.
  2. `shutil.which("codex") is None`: print `Codex is not installed`,
     exit 3.
  3. `subprocess.run(["codex", "login", "status"], capture_output=True)`
     returns non-zero: print `Codex is not signed in; run: codex login
     --device-auth`, exit 4.
- Exits 0, 1, 2 and their output are unchanged. The docstring's exit
  paragraph lists 3 and 4.

Files:
- `plugins/phased-delivery/scripts/codex-usage.py`
- `plugins/phased-delivery/tests/test_codex_usage.py`

Work:
1. Add the three checks and the docstring lines.
2. Tests: put a stub `codex` (`#!/bin/sh`, exiting with `$STUB_STATUS`)
   in `tmp_path/bin` and run with `PATH` set to that directory only (the
   script runs through `sys.executable`), and with `AI_CODEX` removed from
   the copied environment unless a case sets it. Make the existing tests
   use the signed-in stub (exit 0). New cases: `AI_CODEX=off` -> 3; no `codex` on `PATH` -> 3; stub
   exits 1 -> 4; `AI_CODEX=on` with signed-in stub and a log under the
   maximums -> 0.

External inputs: the environment and `codex login status`'s exit status
(another tool); only the exit status is used.

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests/test_codex_usage.py`
  passes.
- `AI_CODEX=off python3 plugins/phased-delivery/scripts/codex-usage.py`
  prints one line and exits 3.

Out of scope: thresholds, log reading, `codex-build.sh`, skills.

Model basis: J1 F0 R0 C1 K1 P0 V0 S0 = 3 -> override 2 (J, C, K not 0) ->
middle (K: runs another tool's command; P0: 01.3's tests are the pattern).
Narrow (F0 R0).

## 02.2 codex-build.sh: failed builds

Goal: a Codex run that never completes a turn is reported as out of quota
(exit 7) or as Codex unusable (exit 6), with Codex's own error text, so the
orchestrator routes or turns Codex off instead of retrying.

Context: `plugins/phased-delivery/scripts/codex-build.sh` (01.4): after
`codex exec`, the exit 3 check greps `stderr.txt`, the exit 5 check greps
`events.jsonl`, then embedded Python reads `events.jsonl` and prints
`Tokens:` from the last `turn.completed` event. Codex strings are in
Assumptions.

Contracts:
- The embedded Python also writes `$OUT/error.txt`: the last error text in
  `events.jsonl`, taken from events whose `type` is `error` or
  `turn.failed`, from their `message` or `error.message` string; empty when
  there is none. It still prints only the `Tokens:` line on stdout.
- Exit 3 is unchanged and exits before the Python runs. Exit 5 wins
  over 6 and 7: the new checks run only when the exit 5 check did not
  match. Then, when `events.jsonl` has no line containing
  `"turn.completed"`:
  - `error.txt` or `stderr.txt` contains `Upgrade to Plus`: exit 6 as
    below (the free plan's limit: a lapsed subscription);
  - else `error.txt` or `stderr.txt` contains `hit your usage limit`: print to
    stderr `Codex is out of quota: <error.txt, or the last non-empty line
    of stderr.txt>` and exit 7;
  - otherwise print to stderr `Codex could not run a turn (subscription,
    account or service problem): <same text, or "no error text">` and
    exit 6.
- The `Tokens:` line is printed in the exit 6 and 7 cases too; exits 0, 3, 5 and other
  statuses are unchanged when a turn completed.
- The header's Exit line lists 6 and 7, and the `sed` usage range still
  covers the whole header.

Files: `plugins/phased-delivery/scripts/codex-build.sh`

Work:
1. Extend the embedded Python to write `error.txt`; run it before the new
   checks so they can read it.
2. Add the exit 7 and exit 6 checks after the exit 5 check.
3. Update the header.

External inputs: Codex's event log and stderr (another tool): parse each
line as JSON, skipping lines that fail; match a fixed string; show the
error text, never act on it otherwise.

Done when:
- `sh -n` and `shellcheck -S warning` pass on the script.
- With a stub `codex` first on `PATH` (`#!/bin/sh`, printing a chosen
  `events.jsonl` to stdout and a line to stderr, exiting 1), run in `/tmp`:
  a `turn.failed` event with message `You've hit your usage limit. Try
  again later.` -> exit 7 and that text; `You've hit your usage limit.
  Upgrade to Plus to continue using Codex` -> exit 6; an `error` event `account
  inactive` -> exit 6 and that text; no events -> exit 6 with the stderr
  line; a `turn.completed` event -> Codex's exit status, as before. Each
  prints `Tokens:`.
- `sed -n '2,NNp'` (the script's usage range) prints the whole header.

Out of scope: exits 3 and 5, the token count, skills.

Model basis: J1 F0 R0 C1 K1 P0 V0 S0 = 3 -> override 2 -> middle (K1:
another tool's output; no tests cover the script). Raised to top, by
written reason: the same script's exit 5 match was wrong on its first
build (Phase 01 Notes, 7728ad2), and a wrong exit 6 silently turns Codex
off. Built in the session: Codex would judge its own failure detection.

## 02.3 Skill routing rules

Goal: model-selection.md and implement-in-phases/SKILL.md state the
availability check and the routing rule above, and the implementer follows
them before every phase, dispatch and review.

Context: this file's two contract sections are the whole decision; the
current text they replace is cited in Assumptions. `claude-usage.py`'s and
`codex-usage.py`'s docstrings (01.1, 02.1) list their exit codes;
`codex-build.sh`'s header (01.4, 02.2) lists its exits.

Contracts: both contract sections above, unchanged. Keep these existing
rules: Codex only when the session is not Codex; `models-codex.md` must
have a candidate for the tier; plan-time generation of
`models-available-codex.json` and `models-codex.md`.

Files:
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md`
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md`
- `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md`
  (orchestrator header only, above its `---`)

Work:
1. model-selection.md, "Builders in another tool": open with the
   availability table and its bullets (before the plan-time bullet; plan
   time also skips Codex when it is off). Replace the "Send a stage to
   Codex only when all hold" list and the line after it with the routing
   table, its bullets, and one sentence on why width still caps routing
   until Claude is nearly out (Codex loses track across many files).
   Remove the `codex-build.sh` exit 3 bullet (the availability table now
   holds exits 3, 5, 6 and 7), and in the table's exit 5 row say to set
   `CODEX_BUILD_SANDBOX=danger-full-access` only if the session already
   runs in a sandbox container (the ai-coding sandbox sets it already).
   Change the "Fixed choices" line "Reviews use the `top` candidate" to
   add: of `models-codex.md` when the routing rule sends the review to
   Codex.
2. SKILL.md, the paragraph "When the plan has `models-codex.md`": first
   check availability by "Builders in another tool" (before the phase's
   first dispatch, ahead of refreshing `models-codex.md`); while Codex is
   on, run both usage scripts before each dispatch and route by the table
   there; drop the restated narrow rule (the table owns it). Keep the
   prompt-file and `codex-build.sh` instructions.
3. SKILL.md, "### 3. Review the phase": the review goes to Codex's `top`
   candidate through `codex-build.sh` when the routing rule says so.
4. SKILL.md, "### 4. Commit and stop": a stop from the routing rule
   reports both scripts' output lines and the stages left, with the
   review-pending status and resume rule; the report also names whether
   Codex was on or off and why.
5. phase-reviewer.md header: change "Use the `top` candidate from the
   plan's `models.md`" to add "or from `models-codex.md` when the routing
   rule in model-selection.md sends the review to Codex". Nothing below
   `---` changes.

External inputs: none.

Done when:
- Reading both files, every row and bullet of both contract sections
  appears once, in model-selection.md, and SKILL.md points to it.
- `grep -rn 'F = 0 and R = 0' plugins/phased-delivery/skills/implement-in-phases`
  finds nothing.
- `grep -rln claude-usage.py plugins/phased-delivery/skills` lists
  model-selection.md and implement-in-phases/SKILL.md.
- `grep -rn 'F <= 1' plugins/phased-delivery/skills/plan-in-phases/model-selection.md`
  finds the ahead-of-pace row.
- `grep -rn 'AI_CODEX' plugins/phased-delivery/skills/plan-in-phases/model-selection.md`
  and `grep -rn 'exit 7' plugins/phased-delivery/skills/plan-in-phases/model-selection.md`
  each find a line.

Out of scope: scripts, README, docs, plan-in-phases/SKILL.md, eval copies.

Model basis: J1 F1 R1 C1 K0 P1 V2 S0 = 7 -> middle; override 3 (V = 2) ->
middle+. (F1: three files.)

## 02.4 Docs and version

Goal: README and `docs/model-routing.md` describe the availability check,
usage-based routing and their setup, and the plugin version is 0.5.0.

Context: 02.3's text in model-selection.md is the rule to describe;
`codex-build.sh`'s header documents `CODEX_BUILD_SANDBOX` and exit 6;
phase 01's 01.2 has the `statusLine` setting to document; phase 03 makes
the ai-coding sandbox set it and honor `AI_CODEX`.

Contracts: both contract sections above; the `statusLine` command from
01-claude-usage.md stage 01.2.

Files:
- `README.md`
- `docs/model-routing.md`
- `plugins/phased-delivery/.claude-plugin/plugin.json`

Work:
1. README "### Building with Codex from Claude Code": say Codex is used
   only when installed, signed in and not turned off with `AI_CODEX=off`
   (asks to sign in or skip; skip lasts the session; a build that cannot
   run turns it off). Describe the three usage levels in a few lines and
   the stop when both are nearly out. Setup: the `statusLine` command from
   01.2's Contracts (plain shell form), with a sentence that
   `bash "$d/ponytail-statusline.sh" < "$t"` stands for the user's own
   status line command, which reads `< "$t"`, or is dropped if they have
   none; ai-coding sandbox images with `AI_CODEX` support set it up
   themselves. It needs a
   Pro/Max/Ultra plan; without it routing stays narrow-only. One sentence
   on `CODEX_BUILD_SANDBOX`: set it to `danger-full-access` only when Claude
   Code itself runs in a sandbox container where Codex's own sandbox
   cannot start (the ai-coding sandbox already sets it).
2. `docs/model-routing.md` Part 2, "How it works now": replace the
   "narrow" and "Planning and reviews stay" bullets with the availability
   check and the routing summary citing `model-selection.md`; in the
   `codex-build.sh` bullet add exits 5, 6 and 7; keep the container bullet
   unchanged; replace the "Usage visibility" bullet's Claude sentence with
   how Claude usage is read now (status line JSON, as fresh as the last
   refresh in any session). In "Open questions",
   replace "Quota-aware failover" with what remains: tuning the thresholds
   from work reports, and narrowing exit 6 once a real expired-plan error
   is seen.
3. plugin.json: `"version": "0.5.0"`.

External inputs: none.

Done when:
- `jq -r .version plugins/phased-delivery/.claude-plugin/plugin.json`
  prints `0.5.0`.
- `grep -n 'not visible to the agent' docs/model-routing.md` finds nothing.
- `grep -n 'only when it is \*\*narrow\*\*' docs/model-routing.md` finds
  nothing.
- `grep -n claude-usage README.md docs/model-routing.md` and
  `grep -n AI_CODEX README.md docs/model-routing.md` find both files.

Out of scope: skills, scripts, eval copies, worktrees, the sandbox repo.

Model basis: J1 F1 R1 C0 K0 P1 V2 S0 = 6 -> middle; override 3 (V = 2) ->
middle+.

## Notes
- 2026-11-21: rebased onto origin/main (upstream PR #1 had added
  `CODEX_BUILD_SANDBOX` validation and the hook-trust flag to
  `codex-build.sh`, without exit 5): kept upstream's script plus our exit 5
  check and widened its usage range; 02.4 now keeps upstream's container
  bullet. Plan start is now 6a000a1. Pull requests: the user asked
  (2026-11-21) to push and open them and see CI pass; this repository has
  no pull request CI.
- 2026-11-21: plan review round 2: "Upgrade to Plus" is exit 6; exit 5
  wins over 6/7; failed builds restore from a pre-dispatch `git status`
  snapshot; lapsed sign-in uses logout and login, a second lapse turns
  Codex off.
- 2026-11-21: plan review: exit 7 keeps an exhausted quota "no room";
  failed Codex builds are restored; exit 5 turns Codex off; level 2 never
  rebuilds a Codex failure in Claude; session-only stages stay in the
  session; tests drop the user's `AI_CODEX`.
- 2026-11-21: revised before building (user, 2026-11-21): Codex
  availability gate (`AI_CODEX`, not installed, not signed in with
  sign-in-or-skip for the session, exit 6 for unusable Codex); no quota
  stays per-dispatch "no room"; `CODEX_BUILD_SANDBOX` is already set by
  the sandbox image; added stages 02.1 and 02.2; old 02.1/02.2 became
  02.3/02.4; phase 03 added for the sandbox side.
- 2026-11-20: review round 3: stages writing outside the repository stay
  in the session.
- 2026-11-20: review round 2: review-pending stop status; plan reviews
  stay in session; phase-reviewer.md header added; docs stage names the
  stale Part 2 lines.
- 2026-11-20: review round 1: lapsed Codex sign-in rule made explicit;
  skill checks use `grep -r`; README setup uses 01.2's command.
- 2026-11-21: Codex "no data" (codex-usage.py exit 2) now counts as room:
  exit 7 catches a real limit at dispatch, and "no room" at level 2 would
  stop every phase on a Codex that has not run yet. (Replaces the
  2026-11-20 decision that kept it "no room".)
