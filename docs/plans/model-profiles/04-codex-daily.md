# Phase 04: Codex checked once a day

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: in progress (stages done: all; review pending)
Before: codex-usage.py runs `codex login status` every time it is called, at the start of every phase. Codex found off stays off only until the session ends; the next session checks again from scratch.
After: Codex availability is checked at most once a day. Once Codex is found off (not installed, not signed in, or a build showing it unusable), the result is cached for the day: codex-usage.py answers from the cache without running codex, and every session that day starts by telling the agent Codex is off and must not be considered. `codex-usage.py --recheck` checks again after the user fixes it.

## Assumptions
- Verified: codex-usage.py already decides off (exit 3) and not signed in (exit 4) before reading usage. (plugins/phased-delivery/scripts/codex-usage.py:73-81 AI_CODEX, shutil.which, codex login status)
- Verified: The plugin already keeps per-user state in $CLAUDE_CONFIG_DIR or ~/.claude, which is writable in the sandbox. (plugins/phased-delivery/scripts/claude-usage.py:34-35 claude-usage.json)
- Verified: The SessionStart hook can add context and has a 10-second timeout. (plugins/phased-delivery/hooks/hooks.json SessionStart timeout 10; hooks/session-start.sh prints additionalContext)
- Open: `codex login status` answers within a few seconds at session start. (Check by timing it once when Codex is installed again; codex-usage.py stops waiting after 5 seconds, so a slow answer only means no cached result that session.)

## Outcome tests
Budget: python3 -m pytest -q plugins/phased-delivery/tests runs in under a minute.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| After Codex is found off once in a day (not installed, not signed in, or recorded off after a failed build), `codex-usage.py` exits 3 from `~/.claude/codex-availability.json` without running codex; `codex-usage.py --recheck` checks again. | `plugins/phased-delivery/tests/test_codex_usage.py::test_daily_cache` | 04.1 | 04.1 |
| With Codex cached off for today, the SessionStart hook's JSON context contains `Codex is off today` and tells the agent not to consider Codex; with Codex on, it has no Codex line. | `plugins/phased-delivery/tests/test_session_start.py::test_codex_off_line` | 04.2 | 04.2 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 04.1 | codex-usage.py caches an off result for the day and answers from it without running codex, with `--recheck` and `--record-off CAUSE`. | top | first | done |
| 04.2 | The SessionStart hook checks Codex at most once a day through codex-usage.py and, when Codex is off, tells the agent not to consider it for the session. | middle | after 04.1 | done |
| 04.3 | The skills check Codex through the daily cache, record off with `--record-off`, and leave Codex out entirely while it is off. | middle+ | after 04.1 | done |

## 04.1 daily Codex cache

Goal: codex-usage.py caches an off result for the day and answers from it without running codex, with `--recheck` and `--record-off CAUSE`.

Context:
- `plugins/phased-delivery/scripts/codex-usage.py:66-81`: Parses flag and value pairs, then the off, not-installed and not-signed-in checks with exits 3 and 4.
- `plugins/phased-delivery/scripts/claude-usage.py:34-35`: Where the plugin keeps per-user state files.
- `plugins/phased-delivery/tests/test_codex_usage.py:14-30`: Tests run the script with a stub codex on PATH and CODEX_HOME in a temporary folder.

Contracts:
- cli `codex-usage.py` (provides; 04.2, 04.3): codex-usage.py [--max-window PCT] [--max-weekly PCT] [--recheck] [--record-off CAUSE]: exit 0 room, 1 over, 2 no data, 3 off (AI_CODEX=off, not installed, or cached off today), 4 not signed in (then cached off), 5 check timed out (off for this call, not cached)
- format `codex-availability.json` (provides; disk): file in $CLAUDE_CONFIG_DIR or ~/.claude: {"date": "2026-11-23" (local date), "on": false, "cause": "not signed in"}

Files:
- `plugins/phased-delivery/scripts/codex-usage.py` (edit): reads and writes codex-availability.json and accepts `--recheck` and `--record-off`
- `plugins/phased-delivery/tests/test_codex_usage.py` (edit): gains the daily-cache outcome test

Behaviour:
- Given codex-availability.json dated today with `on` false, when codex-usage.py runs without `--recheck`, then it prints `Codex is off today: <cause> (cached; run codex-usage.py --recheck after fixing it)` and exits 3 without running codex.
- Given no cache for today, Codex not installed or `codex login status` failing, when it runs, then it exits 3 or 4 as now and writes the cache with `on` false and a cause that keeps the fix, such as `not signed in; run codex login --device-auth`.
- Given no cache for today and Codex signed in, when it runs, then it writes the cache with `on` true and reports usage as now; a cache dated today with `on` true skips `codex login status`.
- Given a cache dated another day, when it runs, then it is ignored and the checks run again.
- Given `--record-off CAUSE`, when it runs, then it writes the cache off for today with that cause, prints it and exits 3.
- Given `--recheck`, when it runs, then it ignores the cache, checks again and writes the result.
- Given AI_CODEX=off, when it runs, then it exits 3 as now and writes no cache, since the switch is read every time.
- Given `codex login status` takes over 5 seconds, when it runs, then it stops waiting, prints that the check timed out, caches nothing and exits 5.

External inputs:
- codex-availability.json on disk, which a user or another version may have changed: a JSON object with a `date` string and an `on` boolean; on failure, treated as no cache

Tests:
- writes `plugins/phased-delivery/tests/test_codex_usage.py::test_daily_cache` (outcome): After Codex is found off once in a day (not installed, not signed in, or recorded off after a failed build), `codex-usage.py` exits 3 from `~/.claude/codex-availability.json` without running codex; `codex-usage.py --recheck` checks again.
- keeps passing `plugins/phased-delivery/tests/test_codex_usage.py` (outcome): the existing exits are unchanged; each existing test gets its own CLAUDE_CONFIG_DIR so no cache leaks between them

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.

Out of scope:
- Reading usage windows.
- codex-build.sh and its exit codes.

Model basis: J1 F1 R0 C1 K2 P1 V0 S0 = 6 -> top (override: J, C or K = 2)

## 04.2 session start announces Codex off

Goal: The SessionStart hook checks Codex at most once a day through codex-usage.py and, when Codex is off, tells the agent not to consider it for the session.

Context:
- Builds on 04.1: codex-usage.py answering exit 3 from the daily cache
- `plugins/phased-delivery/hooks/session-start.sh:26-38`: Builds the context text and prints it as the hook's JSON.
- `plugins/phased-delivery/hooks/hooks.json:6-11`: The SessionStart hook runs with a 10-second timeout.

Contracts:
- cli `codex-usage.py` (uses; 04.1): codex-usage.py [--max-window PCT] [--max-weekly PCT] [--recheck] [--record-off CAUSE]: exit 0 room, 1 over, 2 no data, 3 off (AI_CODEX=off, not installed, or cached off today), 4 not signed in (then cached off), 5 check timed out (off for this call, not cached)

Files:
- `plugins/phased-delivery/hooks/session-start.sh` (edit): adds the Codex-off line to the session context
- `plugins/phased-delivery/tests/test_session_start.py` (create): the hook's outcome test

Behaviour:
- Given codex-usage.py exits 3 or 4, when a session starts, then the context gains `Codex is off today (<its line>): do not consider Codex this session: no Codex model files, usage checks or Codex builds and reviews.`, then `Run codex-usage.py --recheck after fixing it.`, or for AI_CODEX=off `Unset AI_CODEX to use it.`.
- Given codex-usage.py exits 5 (the check timed out), when a session starts, then the context gains `Codex check timed out at session start; the skills check again before using Codex.` and nothing says Codex is off.
- Given any other exit or no python3, when a session starts, then the context has no Codex line and the hook still prints its JSON.

External inputs:
none

Tests:
- writes `plugins/phased-delivery/tests/test_session_start.py::test_codex_off_line` (outcome): With Codex cached off for today, the SessionStart hook's JSON context contains `Codex is off today` and tells the agent not to consider Codex; with Codex on, it has no Codex line.

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.
- `sh -n plugins/phased-delivery/hooks/session-start.sh` passes.

Out of scope:
- The unfinished-plans listing and the skill reminders.
- hooks.json.

Model basis: J1 F1 R0 C1 K1 P1 V0 S0 = 5 -> middle

## 04.3 skills use the daily check

Goal: The skills check Codex through the daily cache, record off with `--record-off`, and leave Codex out entirely while it is off.

Context:
- Builds on 04.1: codex-usage.py with `--recheck` and `--record-off`
- Builds on 03.2: model-selection.md and implement-in-phases as switched to routing
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:304-320` (moved by 03.2): The availability table: causes, detection and actions.
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:331-350` (moved by 03.2): When to check, off means not loaded, and off lasting until the session ends.

Contracts:
- cli `codex-usage.py` (uses; 04.1): codex-usage.py [--max-window PCT] [--max-weekly PCT] [--recheck] [--record-off CAUSE]: exit 0 room, 1 over, 2 no data, 3 off (AI_CODEX=off, not installed, or cached off today), 4 not signed in (then cached off), 5 check timed out (off for this call, not cached)

Files:
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md` (edit): availability is checked once a day through the cache; off lasts the day
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md` (edit): drops the per-phase availability check in favour of the cached one
- `README.md` (edit): mentions the daily Codex check and `--recheck`
- `docs/model-routing.md` (edit): its Codex availability notes describe the daily check

Behaviour:
- Given a session told at start that Codex is off (exit 3 or 4), or codex-usage.py exiting 3 or 4, when planning or building, then the skills write no Codex model files, run no usage scripts and route nothing to Codex.
- Given codex-build.sh exits 3, 5 or 6, when the orchestrator handles it, then it runs `codex-usage.py --record-off "<cause>"` so the rest of the day skips Codex.
- Given a user who signed in or fixed Codex, when they want it back the same day, then the docs tell them to run `codex-usage.py --recheck`.
- Given codex-usage.py exits 4, when the skills handle it, then Codex is off for the day with no sign-in prompt; the not-signed-in row of the availability table says so and names `--recheck`.
- Given codex-usage.py exits 5, when the skills handle it, then Codex is off for that check only and is never room; the next check runs again. The availability table keeps it apart from codex-build.sh exit 5 (sandbox), and the routing rule's note on exits handled first names exit 5 too. The sign-in-again rerun after a failed build is removed.

External inputs:
none

Tests:
- keeps passing `plugins/phased-delivery/tests` (integration): the docs change no behaviour

Done when:
- `grep -n -i 'until the session ends\|off lasts the session\|for the rest of the session' plugins/phased-delivery/skills/plan-in-phases/model-selection.md docs/model-routing.md` prints nothing.
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.

Out of scope:
- Quota rules: exits 0, 1 and 2 keep their meaning.
- AI_CODEX's meaning.

Model basis: J1 F1 R1 C0 K0 P1 V2 S0 = 6 -> middle+ (override: middle with a measure at 2)

## Notes
- 2026-11-23: the user asked for Codex availability to be checked once a day or at session start, cached, and Codex left out entirely while off.
- Review round 2, 2026-11-23: O7 split so the hook line is O8 (04.2); K raised on 04.1 (new persisted file shared by every session) and 04.2 (untested hook); the login check is bounded inside codex-usage.py, since `timeout` is missing on macOS.
- Review round 3, 2026-11-23: a timed-out check gets exit 5 (off for that call, not room); a lapsed sign-in during a build is recorded off with no prompt, matching exit 4; the cached cause keeps the sign-in command; AI_CODEX=off gets its own advice.
- Review round 4, 2026-11-23: a timed-out check at session start gets its own line and does not turn Codex off for the session; only exits 3 and 4 do.
- The thinking-level ceilings in `CEILINGS` stay; the low-gain rule and the stage caps apply within them. Reason: The ceilings were an earlier user decision and still hold.
- Codex availability is cached per local day in `codex-availability.json` beside claude-usage.json; AI_CODEX=off is read every time and never cached. Reason: The user asked for a once-a-day check with Codex left out entirely while off; the switch is the user's and must take effect at once.
- User's answer, departs from the design (Codex availability: "Not being signed in counts as off"): Not being signed in to Codex counts as off for the day: no sign-in prompt; the session-start line and the docs tell the user to sign in and run `codex-usage.py --recheck`. Reason: The user asked that Codex, when not available, be cached off and not considered for the rest of the day; signed out is not available.
- Revised before building, 2026-11-23: 03.2 moved the availability text in model-selection.md (now lines 304-350, the routing note at 365); README.md:151 and docs/model-routing.md:124-127 also describe the per-session check and are in 04.3's files. Run tests with `--basetemp=/cache/...` (see 01's Notes); test_codex_usage.py's stub codex needs it.
- 2026-11-23, 04.1: bad arguments now exit 2 (argparse); no caller passes any. The 5-second timeout (exit 5) was checked by hand with a sleeping stub, not by a test.
- 2026-11-23, 04.2: the off line reads `Codex is off today, so do not consider Codex this session: ... Cause: <codex-usage.py's line>`, since the script's own line already starts with "Codex is off today" when cached. The exit 5 and no-python3 paths are checked by reading only.
