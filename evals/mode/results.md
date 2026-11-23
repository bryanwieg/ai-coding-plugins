# Estimate runs

## 2026-11-23, run 1 (Opus medium, 19 cases, $2.78): 12 of 19 modes match

```
gitignore            est direct    0.5  truth direct      1  read 0  searches 0  $0.08
                      add root .gitignore: 0.5x1x1
test-exit-codes      est quick     0.5  truth direct    0.5  read 5  searches 1  $0.16
                      codex-build.sh exit-code tests with a stub codex: 0.5x1x1
sandbox-env          est direct    3.0  truth direct    3.0  read 1  searches 1  $0.12
                      sandbox mode from CODEX_BUILD_SANDBOX: 2x1x1.5
hook-trust           est direct      1  truth direct      1  read 1  searches 1  $0.11
                      pass hook-trust bypass in danger-full-access: 1x1x1
grill-step           est quick       3  truth direct      2  read 1  searches 1  $0.11
                      grill step and one push-back in plan-in-phases procedure: 1x2x1
grill-collab         est direct      1  truth direct      1  read 1  searches 1  $0.11
                      rewrite grill concerns paragraph: 1x1x1
claude-usage         est quick     1.0  truth direct    1.0  read 2  searches 0  $0.14
                      claude-usage script with tests: 0.5x2x1
codex-reset          est direct      1  truth direct      1  read 1  searches 1  $0.12
                      skip windows whose resets_at has passed: 1x1x1
codex-off            est quick     8.0  truth direct    3.0  read 2  searches 1  $0.13
                      detect Codex off / signed out and report it with its own message and exit code: 2x2x1.5
                      document the new state where callers read the exit code: 1x1x1
exit-codes           est quick       6  truth quick       8  read 3  searches 2  $0.16
                      codex-build.sh detects quota/unusable and exits 7/6: 2x1x2
                      callers fall back on exit 6/7: 1x1x1
outcome-tests        est quick       6  truth quick       6  read 4  searches 1  $0.16
                      grill ends with outcomes; phase file layout gains Outcome tests section: 2x2x1
                      reviewers check outcome tests and unit-test reasons: 1x1x1
                      implementer writes expected-fail tests early and turns them on: 1x1x1
split-skill          est full     17.5  truth quick       6  read 1  searches 1  $0.13
                      five step files: 0.5x5x1
                      SKILL.md sections become pointers: 2x5x1.5
structured-planning  est full     15.5  truth full     26.5  read 3  searches 3  $0.19
                      plan schema, checker and renderer script: 0.5x5x1
                      skill writes plan.json and renders phase files: 3x2x1
                      plan review reports closed finding types: 2x2x1.5
quota-failover       est full     22.0  truth full     39.5  read 4  searches 2  $0.20
                      Claude plan usage reader: 0.5x2x1
                      codex-usage reports out-of-quota / unusable: 2x2x1.5
                      route stages to the tool with room: 3x2x1.5
                      Codex off switch honored by codex-build and sandbox: 2x1x2
t1-min-small         est quick       8  truth direct      4  read 2  searches 1  $0.12
                      --min-small option sets absolute small floor: 2x2x2
t3-speed-col         est direct      4  truth direct      4  read 1  searches 1  $0.11
                      Speed column in rendered tier table: 2x1x2
t4-rename            est direct      2  truth direct      4  read 2  searches 0  $0.14
                      rename reviewer file and update its link: 2x1x1
t5-keywords          est direct      1  truth direct      1  read 2  searches 0  $0.18
                      add words to reminder regex: 1x1x1
p2-thinking          est quick       2  truth direct      1  read 2  searches 1  $0.14
                      normalize_effort drops trailing thinking: 1x1x1
                      guide notes effort normalization: 1x1x1

modes matching truth: 12; cost $2.60
```

Misses: 4 from the unresolved floor on builder details (API, test file, fixture); split-skill scored a verbatim move as interface; codex-off and t1 guessed 30-150 lines for under 30. Fixed in mode-guide: unresolved is only a part that cannot be placed; a move is internal.

## 2026-11-23, run 2 (8 reruns after the fixes, $1.06): 17 of 19 modes match

```
gitignore            est direct    0.5  truth direct      1  read 0  searches 0  $0.08
                      add root .gitignore: 0.5x1x1
test-exit-codes      est direct    2.0  truth direct    0.5  read 2  searches 2  $0.14
                      codex-build.sh exit-code test with fake codex: 0.5x2x1
sandbox-env          est direct    3.0  truth direct    3.0  read 1  searches 1  $0.12
                      sandbox mode from CODEX_BUILD_SANDBOX: 2x1x1.5
hook-trust           est direct      1  truth direct      1  read 1  searches 1  $0.11
                      pass hook-trust bypass in danger-full-access: 1x1x1
grill-step           est quick      14  truth direct      2  read 1  searches 1  $0.12
                      grill step before planning: 2x2x3
                      planner pushes back once on security/architecture: 1x1x1
grill-collab         est direct      1  truth direct      1  read 1  searches 1  $0.11
                      rewrite grill concerns paragraph: 1x1x1
claude-usage         est direct    1.0  truth direct    1.0  read 1  searches 0  $0.12
                      claude-usage script with tests: 0.5x2x1
codex-reset          est direct      1  truth direct      1  read 1  searches 1  $0.12
                      skip windows whose resets_at has passed: 1x1x1
codex-off            est quick     8.0  truth direct    3.0  read 2  searches 1  $0.13
                      detect and report Codex off or signed out: 2x2x1.5
                      document the new state for callers: 1x1x1
exit-codes           est quick       6  truth quick       8  read 3  searches 2  $0.16
                      codex-build.sh detects quota/unusable and exits 7/6: 2x1x2
                      callers fall back on exit 6/7: 1x1x1
outcome-tests        est quick       6  truth quick       6  read 4  searches 1  $0.16
                      grill ends with outcomes; phase file layout gains Outcome tests section: 2x2x1
                      reviewers check outcome tests and unit-test reasons: 1x1x1
                      implementer writes expected-fail tests early and turns them on: 1x1x1
split-skill          est quick       5  truth quick       6  read 1  searches 1  $0.11
                      move five sections to step files with pointers: 1x5x1
structured-planning  est full     24.5  truth full     26.5  read 1  searches 2  $0.17
                      plan schema and check/render script: 0.5x5x1
                      planning writes plan.json, phase files rendered: 3x5x1
                      plan review with closed finding types: 2x2x1.5
quota-failover       est full     22.0  truth full     39.5  read 4  searches 2  $0.20
                      Claude plan usage reader: 0.5x2x1
                      codex-usage reports out-of-quota / unusable: 2x2x1.5
                      route stages to the tool with room: 3x2x1.5
                      Codex off switch honored by codex-build and sandbox: 2x1x2
t1-min-small         est direct      4  truth direct      4  read 2  searches 1  $0.11
                      --min-small option sets absolute small floor: 2x1x2
t3-speed-col         est direct      4  truth direct      4  read 1  searches 1  $0.11
                      Speed column in rendered tier table: 2x1x2
t4-rename            est direct      2  truth direct      4  read 2  searches 0  $0.14
                      rename reviewer file and update its link: 2x1x1
t5-keywords          est direct      1  truth direct      1  read 2  searches 0  $0.18
                      add words to reminder regex: 1x1x1
p2-thinking          est direct      3  truth direct      1  read 0  searches 1  $0.10
                      normalize_effort drops trailing thinking: 2x1x1
                      guide notes the normalization: 1x1x1

modes matching truth: 17; cost $2.48

```

Unresolved is now empty in every rerun; real questions moved to open_questions. Misses: grill-step listed the skill's name as the thing added to (reach 10+, score 14); fixed in mode-guide: only additions users must handle count the container. codex-off again guessed 30-150 lines for 14; left alone (errs upward, moves only to quick).

## 2026-11-23, run 3 (4 reruns after the container rule, $0.50): 17 of 19

grill-step now direct (2.0). structured-planning fell to quick (13.5): the workflow change was called interface 30-150 this time, architecture over 150 in run 2 (24.5) and architecture 30-150 in run 1 (15.5). Its estimate swings across the quick/full line between runs; the quick plan's re-score is the net for it. codex-off still guesses lines high.

## 2026-11-23, quick plan re-score test ($0.58)

plan-in-phases with the new wiring on the structured-planning request, forced to quick: estimate quick 10.5; the agent's own re-score of its form repeated it (quick 10.5), so the form re-score is not an independent check. Replaced by plan-mode.py rescore, computed from plan.json: quick 12.5 on the same plan (it found implement-in-phases as a reader of the edited template). The user agreed quick is right for that request as scoped (rendered layout unchanged); the case's truth now labels the workflow change internal (10.5, quick).

## 2026-11-23, final run (all 19 on the committed version, $2.51): 17 of 19

```
gitignore            est direct    0.5  truth direct      1  read 0  searches 0  $0.08
                      root .gitignore for caches: 0.5x1x1
test-exit-codes      est direct    1.5  truth direct    0.5  read 3  searches 0  $0.16
                      codex-build.sh exit-code test with captured fixture: 0.5x1x1
sandbox-env          est direct    3.0  truth direct    3.0  read 1  searches 1  $0.13
                      CODEX_BUILD_SANDBOX env var for codex-build.sh: 2x1x1.5
hook-trust           est direct      1  truth direct      1  read 1  searches 1  $0.11
                      pass hook-trust bypass in danger-full-access: 1x1x1
grill-step           est direct      4  truth direct      2  read 1  searches 1  $0.11
                      grill interview step in skill: 1x2x1
                      planner pushes back once: 1x1x1
grill-collab         est direct      1  truth direct      1  read 1  searches 1  $0.10
                      rewrite grill concerns paragraph as discussion: 1x1x1
claude-usage         est direct    1.0  truth direct    1.0  read 2  searches 0  $0.13
                      claude-usage script with tests: 0.5x2x1
codex-reset          est direct      1  truth direct      1  read 1  searches 1  $0.10
                      skip windows whose resets_at has passed: 1x1x1
codex-off            est quick     7.0  truth direct    3.0  read 2  searches 1  $0.12
                      report Codex off or signed out: 2x2x1.5
exit-codes           est quick       6  truth quick       8  read 1  searches 1  $0.15
                      codex-build.sh exits 7 on quota, 6 when unusable: 2x1x2
                      callers fall back on exit 6/7: 1x1x1
outcome-tests        est quick       6  truth quick       6  read 1  searches 2  $0.17
                      grill outcomes and test rules in planning: 1x2x1
                      phase file gains Outcome tests section: 2x1x1
                      reviewers check outcome tests: 1x1x1
                      implementation turns expected-fail tests on: 1x1x1
split-skill          est quick       5  truth quick       6  read 1  searches 1  $0.13
                      move sections verbatim into step files: 1x5x1
structured-planning  est full     21.5  truth quick    10.5  read 2  searches 1  $0.18
                      plan JSON schema and check/render script: 0.5x5x1
                      plan-in-phases writes plan.json and renders phase files: 2x2x3
                      plan review reports closed finding types: 2x2x1.5
quota-failover       est full     24.0  truth full     39.5  read 5  searches 2  $0.22
                      Claude plan usage reader: 0.5x2x1
                      Codex usage reports out-of-quota / unusable state: 2x2x1.5
                      Route stages to the tool with room, failing over both ways: 3x2x2
                      Codex-off switch honored by codex-build.sh: 2x1x2
t1-min-small         est direct      4  truth direct      4  read 2  searches 2  $0.13
                      --min-small option sets absolute small floor: 2x1x2
t3-speed-col         est direct      4  truth direct      4  read 2  searches 2  $0.13
                      Speed column in rendered tier table: 2x1x2
t4-rename            est direct      2  truth direct      4  read 1  searches 1  $0.10
                      rename reviewer directions file and its link: 2x1x1
t5-keywords          est direct      1  truth direct      1  read 2  searches 0  $0.12
                      add keywords to reminder regex: 1x1x1
p2-thinking          est direct      2  truth direct      1  read 1  searches 1  $0.13
                      normalize_effort strips trailing thinking, with tests: 1x1x1
                      guide notes the normalization: 1x1x1

modes matching truth: 17; cost $2.51

```

Both misses err upward, by one mode. codex-off: lines guessed 30-150 for 14 (every run). structured-planning: listed the skill's name 'plan-in-phases' as the thing added to (reach 10+), despite the rule that the container counts only when its users must handle the addition; it has scored 15.5, 24.5, 13.5 and 21.5 across runs. No change is reached by the estimate making a quick or full change direct.
