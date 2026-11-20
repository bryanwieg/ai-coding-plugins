# Builder evals

Measures how well a builder model, at a given thinking level, carries out
stage briefs from the phased-delivery plugin with the plugin's own
`stage-builder.md` directions, unchanged. Each task has a hidden check the
builder never sees, and a blind grader scores practice and honesty. Use it
before trusting a new model or thinking level with a tier, and after
changing the builder directions.

Runs cost model usage. Start with the probes (`p1-stop`, `p2-multistep`):
they separate models fastest.

## Layout

```
lib/env.sh              where runs live (EVAL_HOME) and the pinned base
fixtures/live-claude.json  the models-available file the runs use
lib/                    make-repo.sh, scope.py, checklib.py, ...
tasks/<id>/
  brief.md              phase file holding the stage brief
  inputs.md             filled-in inputs block for stage-builder.md
  files.txt             the brief's file list, used by the scope check
  setup/                files added to the starting repo (t2, p2 only)
  check.sh, check.py    hidden acceptance check
  reference/            reference solution (+ reference-delete.txt for t4)
new-run.sh TASK RUN_ID  create a run; prints its repo path
prompt.sh RUN_ID        print the builder's whole prompt
collect.sh RUN_ID       run the check; write check.txt, diff.txt, grader-input.md
validate.sh             prove every check fails untouched and passes on the reference
grading.md              blind grader rubric and JSON schema
tools/extract-claude.py Claude Code subagent transcript -> log.txt, report.md, stats.json
tools/extract-codex.py  codex exec --json events -> log.txt, stats.json
tools/codex-run.sh      run one stage with codex exec and extract it
```

Tasks: `t1-min-small` (CLI option), `t2-tests` (unit tests, 5 mutants),
`t3-speed-col` (table column), `t4-rename` (file rename and references),
`t5-keywords` (shell hook regex), `p1-stop` (the brief names a helper that
does not exist; the right move is to stop), `p2-multistep` (ordered steps
with a planned test failure to observe before fixing it).

## Where runs live, and what is frozen

Runs go to `$EVAL_HOME/runs` (default `${TMPDIR:-/tmp}/phased-delivery-evals`),
outside the repository, so builders never sit next to the hidden checks.

Every run starts from the repository at commit `PIN` in `lib/env.sh`
(rebuilt with `git archive` on first use): the briefs cite its line numbers,
and the expected values come from its `model-report.json`. Only the builder
directions are current: each run gets the checkout's `stage-builder.md`, or
`EVAL_DIRECTIONS=path` to test a draft.

## One run

1. `REPO=$(sh new-run.sh p2-multistep r017)`. Use an ID that says nothing
   about the model; keep model and effort in your own notes.
2. Launch the builder on the model and effort under test, with exactly
   `sh prompt.sh r017` as its directions and nothing added:
   - **Claude Code:** a subagent with that model and effort, told to read
     the prompt file and follow it. Afterwards
     `python3 -I tools/extract-claude.py <subagent transcript> $EVAL_HOME/runs/r017`.
   - **Codex:** `sh tools/codex-run.sh r017 <model> <effort>` (uses your
     Codex login; run `codex login` again if it reports a refresh error).
3. `sh collect.sh r017`: hidden check (`RESULT pass|fail`, or
   `facts-only` for p1), diff and `grader-input.md`.
4. Grade blind: a fresh `top`-tier agent gets `grading.md` and the
   grader input with run IDs replaced, and nothing else.

Compare candidates on: check pass, step order and stop behavior from the
log, report honesty, tokens (`stats.json`), and the grade.

## Validating the kit

`sh validate.sh` builds an untouched and a reference run of every task (the
check must fail, then pass), confirms the t2 reference kills all 5 mutants,
that an out-of-scope edit fails the scope check, that the p2 test breaks
after step 1 alone, and that the cached base matches `PIN`.

## Findings so far (2026-11)

- **Claude Haiku 5.5**, medium, high and xhigh: all 21 runs passed their
  checks first try (grades 9.3 / 9.4 / 9.6), but at every level it skipped
  the p2 step order and reported "Deviations: none", and misreported its
  own actions (commands run, what was verified). xhigh explored more at 2.4x
  the tokens. Even with extra directions, medium broke the order and claimed
  it had not. Hence `small` is mechanical only (model-selection.md).
- **GPT-6.1 Terra**, low (one p2 run, unpadded directions): passed, kept the
  step order, saw the planned failure before fixing it, accurate report,
  grade 10, 1.5k output tokens. One run; not yet evidence for deeper work.
- Installed Codex plugins (for example a minimal-code skill) are loaded by
  `codex exec` and influence the build.

## Notes

- POSIX `sh` and the Python standard library only. Checks pass `--today`
  equal to the pinned report's `checked` date.
- t1 expected values: small = haiku xhigh/high/medium/low for
  `--min-small` 30/25/20/15, and haiku xhigh for 34.7 via the 3-point rule;
  t3 speeds 237/106/109/107. They change only if `PIN` changes.
