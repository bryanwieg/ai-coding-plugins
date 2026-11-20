# Project rules

- You may read any file in this repository and run `python3` and `sh`
  commands in it, including the scripts and tests. Running them is how
  "Done when" items are verified.
- Do not use git. Do not install anything.
- Change only the files your stage brief lists. Put any scratch output
  (for example a generated `models.md` you want to look at) under `/tmp`,
  never in the repository.
- The `plan/` directory holds the plan; do not edit it.
- `plugins/phased-delivery/model-report.json` records the date it was
  checked in its `checked` field. When you run
  `plugins/phased-delivery/scripts/select-models.py`, pass `--today` with
  that date (currently `2026-11-19`), or it may refuse the report as stale.
