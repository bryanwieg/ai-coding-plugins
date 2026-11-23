# Phase 01: Cached model profiles

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: in progress (stages done: 01.1)
Before: The selector reads `model-report.json`, refuses it when older than 7 days, and is rerun before every phase. A workflow fetches the Artificial Analysis data daily and commits it when anything changed, or every 3 days as a heartbeat.
After: `model-profiles.json` sits in the plugin with one entry per model and thinking level, its derived properties and a fingerprint of the model list and prices. The selector reads it at any age, writes the fingerprint into models.md, and `select-models.py check models.md` says whether models.md is still current. The workflow runs weekly and commits only when the fingerprint changes.

## Assumptions
- Verified: Every report row has creator, model, effort, name, released, the two indexes, run cost, both prices and speed. (plugins/phased-delivery/scripts/fetch-model-report.py:61-75 rows.append)
- Verified: The selector's only age check is load_report against MAX_REPORT_AGE_DAYS. (plugins/phased-delivery/scripts/select-models.py:84-93 load_report)
- Verified: The evals run the selector from their own pinned base copy, so changing its options does not break them. (evals/lib/make-repo.sh:24 runs $BASE/plugins/phased-delivery/scripts/select-models.py)
- Open: The weekly workflow's commit path works with the new exit codes. (Workflows run only on GitHub; check with a workflow_dispatch run after merge. If it fails, fix the step's exit-code handling.)

## Outcome tests
Budget: python3 -m pytest -q plugins/phased-delivery/tests runs in under a minute.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| Running `select-models.py profiles REPORT plugins/phased-delivery` writes `model-profiles.json` and exits 0 when the report adds or drops a model row or changes a price, and exits 1 writing nothing when only scores or run costs changed. The weekly workflow commits only on exit 0. | `plugins/phased-delivery/tests/test_model_profiles.py::test_refresh_only_on_model_or_price_change` | 01.1 | 01.1 |
| `select-models.py AVAILABLE.json --out models.md` succeeds with profiles built from a report checked months ago, and models.md carries a `Profiles:` fingerprint line. `select-models.py check models.md` exits 0 while the plugin's profiles have that fingerprint and 1 once they change. | `plugins/phased-delivery/tests/test_select_models.py::test_any_age_and_check` | 01.2 | 01.2 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | `select-models.py profiles REPORT OUT_DIR` builds model-profiles.json with derived properties and a fingerprint, and writes it only when the fingerprint changed. | top | first | done |
| 01.2 | The selector reads model-profiles.json at any age, records its fingerprint in models.md, and `select-models.py check` tells whether models.md is current. | top | after 01.1 | planned |
| 01.3 | The model-report workflow runs weekly and commits the report and profiles only when `select-models.py profiles` says the fingerprint changed. | middle | after 01.1 | planned |

## 01.1 profiles subcommand

Goal: `select-models.py profiles REPORT OUT_DIR` builds model-profiles.json with derived properties and a fingerprint, and writes it only when the fingerprint changed.

Context:
- `plugins/phased-delivery/scripts/fetch-model-report.py:61-75`: The report rows the profiles are built from, with these field names.
- `plugins/phased-delivery/scripts/select-models.py:43-44`: Thinking levels from least to most; the step from the lower level uses this order.
- `plugins/phased-delivery/scripts/select-models.py:64-65`: Normalizes a row's effort; a row with none is the default level.
- `plugins/phased-delivery/scripts/select-models.py:68-81`: The existing argument parser: first argument is the available file, then flag and value pairs.
- Design, Profiles: "the score gained and cost multiplied by each step up in thinking level"
- Design, Refresh: "keyed by a fingerprint of the model list and prices"

Contracts:
- format `model-profiles.json` (provides; 01.2, 02.1, disk): {"fingerprint": sha256 hex, "source_checked": "2026-11-21", "attribution": str, "pairs": [{"creator", "model", "effort", "name", "released", "intelligence", "engineering", "run_cost_usd", "price_in", "price_out", "speed", "premium": bool, "gain_from_lower": float|null, "cost_ratio_from_lower": float|null, "low_gain": bool}]}
- cli `select-models.py profiles` (provides; 01.3): select-models.py profiles REPORT OUT_DIR: builds OUT_DIR/model-profiles.json from REPORT; exit 0 written (fingerprint new or file absent), 1 unchanged (nothing written), 2 bad or unreadable report; prints the fingerprint and changed or unchanged
- format `model-report.json` (uses; plugins/phased-delivery/scripts/fetch-model-report.py): {"checked": date, "attribution": str, "rows": [{"creator", "model", "effort", "name", "released", "intelligence_index", "engineering_index", "benchmark_run_cost_usd", "price_in_per_1m_usd", "price_out_per_1m_usd", "output_tokens_per_second"}]}

Files:
- `plugins/phased-delivery/scripts/select-models.py` (edit): gains the `profiles` subcommand and the constants `PREMIUM_PRICE_OUT`, `LOW_GAIN_POINTS` and `LOW_GAIN_COST_RATIO`
- `plugins/phased-delivery/model-profiles.json` (create): the profiles built from the committed model-report.json
- `plugins/phased-delivery/tests/test_model_profiles.py` (create): the outcome test for the refresh rule

Behaviour:
- Given a report row, when profiles are built, then there is one pair per row, with the row's fields under the format's names and `effort` normalized by `normalize_effort`.
- Given a model with rows at several thinking levels, when profiles are built, then each level's `gain_from_lower` and `cost_ratio_from_lower` compare it with the next lower benchmarked level of that model by `EFFORT_ORDER`; the lowest level, a level outside `EFFORT_ORDER`, or either side missing a score or run cost gets null.
- Given a pair gaining under `LOW_GAIN_POINTS` (2) intelligence points for over `LOW_GAIN_COST_RATIO` (1.5) times the run cost, when profiles are built, then its `low_gain` is true; otherwise false.
- Given a pair with output price at least `PREMIUM_PRICE_OUT` (30), when profiles are built, then its `premium` is true; a missing price is not premium.
- Given two reports differing only in scores or run costs, when both are fingerprinted, then the fingerprints are equal; a row added or removed, a changed input or output price, or a row gaining its first intelligence score or run cost changes it.
- Given OUT_DIR holds a model-profiles.json with the same fingerprint, when the subcommand runs, then it writes nothing, prints the fingerprint and `unchanged`, and exits 1.
- Given no file there or a different fingerprint, when the subcommand runs, then it writes the file, prints the fingerprint and `changed`, and exits 0.
- Given the committed model-report.json, when built today, then Fable 5.2 xhigh and Haiku 5.5 max are low_gain, Opus 5.5 xhigh is not, Fable and GPT-6.2 Astra pairs are premium, and Opus 5.5 pairs are not.

External inputs:
- REPORT, written by fetch-model-report.py from the Artificial Analysis API: valid JSON with a `rows` list whose items have creator, model and name; on failure, print what is wrong and exit 2, writing nothing

Tests:
- writes `plugins/phased-delivery/tests/test_model_profiles.py::test_refresh_only_on_model_or_price_change` (outcome): Running `select-models.py profiles REPORT plugins/phased-delivery` writes `model-profiles.json` and exits 0 when the report adds or drops a model row or changes a price, and exits 1 writing nothing when only scores or run costs changed. The weekly workflow commits only on exit 0.
- writes `plugins/phased-delivery/tests/test_model_profiles.py::test_derived_properties` (unit): gain, cost ratio, low_gain and premium for a fixture model with four levels, including a missing score (unit because: the edge cases of the step comparison need hand-built rows a refresh run would not produce)

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.
- `python3 plugins/phased-delivery/scripts/select-models.py profiles plugins/phased-delivery/model-report.json plugins/phased-delivery` exits 1 after the committed model-profiles.json was built by it.

Out of scope:
- How the selector picks models; it still reads model-report.json until 01.2.
- fetch-model-report.py's fetching and row format.

Model basis: J1 F1 R0 C1 K2 P1 V0 S0 = 6 -> top (override: J, C or K = 2)

## 01.2 selector reads profiles

Goal: The selector reads model-profiles.json at any age, records its fingerprint in models.md, and `select-models.py check` tells whether models.md is current.

Context:
- Builds on 01.1: model-profiles.json and its fingerprint (the model-profiles.json format)
- `plugins/phased-delivery/scripts/select-models.py:84-93`: Loads the report and refuses it past MAX_REPORT_AGE_DAYS; this check goes.
- `plugins/phased-delivery/scripts/select-models.py:147-177`: Groups rows by model, matches tool names and applies offered levels and ceilings; it reads report field names.
- `plugins/phased-delivery/scripts/select-models.py:180-205`: Scores by intelligence index and costs by benchmark run cost, excluding pairs without them.
- `plugins/phased-delivery/scripts/select-models.py:236-254`: Writes the models.md header, including the `Report: checked` line.
- `plugins/phased-delivery/scripts/select-models.py:68-81`: Accepts `--report`, `--out`, `--json` and `--today`.
- Design, Refresh: "This replaces the 7-day staleness rule and the rerun of the selector before every phase."

Contracts:
- format `model-profiles.json` (uses; 01.1): {"fingerprint": sha256 hex, "source_checked": "2026-11-21", "attribution": str, "pairs": [{"creator", "model", "effort", "name", "released", "intelligence", "engineering", "run_cost_usd", "price_in", "price_out", "speed", "premium": bool, "gain_from_lower": float|null, "cost_ratio_from_lower": float|null, "low_gain": bool}]}
- cli `select-models.py` (provides; 03.2, user): select-models.py AVAILABLE.json [--profiles FILE] [--out models.md] [--json FILE] [--today ignored]; models.md gains a 'Profiles: <fingerprint>' line; exit 0 written, 2 bad input, 3 profiles missing, 4 nothing selectable; no age check
- cli `select-models.py check` (provides; 03.2): select-models.py check MODELS_MD [--profiles FILE]: exit 0 when the Profiles line matches the profiles' fingerprint, 1 when it differs or is missing (rerun the selector), 3 profiles missing

Files:
- `plugins/phased-delivery/scripts/select-models.py` (edit): reads profiles by default from the plugin's model-profiles.json and holds the `check` subcommand
- `plugins/phased-delivery/tests/test_select_models.py` (create): the selector's outcome tests

Behaviour:
- Given profiles whose `source_checked` is 2020-01-01, when the selector runs on a valid available file, then it writes models.md and exits 0.
- Given the committed profiles and the plan fixture `docs/plans/model-profiles/models-available.json`, when the selector runs, then the tier table equals the one the report-based selector gave: small haiku high, middle opus medium, middle+ and top opus high.
- Given any run, when models.md is written, then it has a line `Profiles: <fingerprint> (data checked <source_checked>)` in place of the `Report: checked` line, with the attribution kept.
- Given `--today` is passed, when the selector runs, then it is accepted and has no effect.
- Given no profiles file at the given or default path, when the selector or `check` runs, then it says so on stderr and exits 3.
- Given models.md with a Profiles line matching the profiles, when `check` runs, then exit 0; after the profiles change fingerprint, or with no Profiles line, exit 1.

External inputs:
none

Tests:
- writes `plugins/phased-delivery/tests/test_select_models.py::test_any_age_and_check` (outcome): `select-models.py AVAILABLE.json --out models.md` succeeds with profiles built from a report checked months ago, and models.md carries a `Profiles:` fingerprint line. `select-models.py check models.md` exits 0 while the plugin's profiles have that fingerprint and 1 once they change.

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests` passes.

Out of scope:
- Tier floors, the tie rule, ceilings and matching rules.
- The `route` subcommand (phase 02).
- Skill and README text (03.2).

Model basis: J1 F1 R1 C1 K2 P1 V0 S0 = 7 -> top (override: J, C or K = 2)

## 01.3 weekly refresh on change

Goal: The model-report workflow runs weekly and commits the report and profiles only when `select-models.py profiles` says the fingerprint changed.

Context:
- Builds on 01.1: `select-models.py profiles` and its exit codes
- `.github/workflows/model-report.yml:10-11`: Runs daily at 06:17 UTC.
- `.github/workflows/model-report.yml:37-52`: Decides to commit on any data change or every 3 days, then copies the report files.
- `.github/workflows/model-report.yml:54-60`: Commits model-report.json and model-report.md.
- `plugins/phased-delivery/scripts/fetch-model-report.py:103-104`: The Markdown report's header says it is generated daily.
- Design, Refresh: "A weekly job fetches the Artificial Analysis report and rebuilds only when the Claude or OpenAI model list or a price changes"

Contracts:
- cli `select-models.py profiles` (uses; 01.1): select-models.py profiles REPORT OUT_DIR: builds OUT_DIR/model-profiles.json from REPORT; exit 0 written (fingerprint new or file absent), 1 unchanged (nothing written), 2 bad or unreadable report; prints the fingerprint and changed or unchanged

Files:
- `.github/workflows/model-report.yml` (edit): the weekly refresh that commits report and profiles only on a new fingerprint
- `plugins/phased-delivery/scripts/fetch-model-report.py` (edit): its Markdown header says the report is refreshed weekly when models or prices change
- `plugins/phased-delivery/model-report.md` (edit): its header says the report is refreshed weekly when models or prices change, matching the script

Behaviour:
- Given the schedule, when the workflow is read, then it runs once a week, Mondays at 06:17 UTC, and still on workflow_dispatch.
- Given a fetched report, when the profiles step exits 0, then model-report.json, model-report.md and model-profiles.json are copied into the plugin and committed with the message `model-report: refresh (models or prices changed)`.
- Given a fetched report, when the profiles step exits 1, then nothing is copied or committed and the job succeeds.
- Given a fetched report, when the profiles step exits 2, then the job fails.
- Given the header comment, when read, then it describes the weekly, change-only rule; the heartbeat and 7-day staleness text is gone.

External inputs:
none

Tests:
none

Done when:
- `python3 -c "import yaml,sys; yaml.safe_load(open(sys.argv[1]))" .github/workflows/model-report.yml` succeeds.
- `grep -c heartbeat .github/workflows/model-report.yml` prints 0.
- `grep -c 'Generated daily' plugins/phased-delivery/model-report.md plugins/phased-delivery/scripts/fetch-model-report.py` prints 0 for both.

Out of scope:
- The fetch logic and API key handling.
- The workflow's permissions and concurrency settings.

Model basis: J1 F1 R0 C0 K1 P1 V1 S0 = 5 -> middle

## Notes
- Plan start: b0c58e2
- 2026-11-23: in this sandbox /tmp is noexec, so tests that put stub commands in pytest's tmp_path fail; run the suite as `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-model-profiles plugins/phased-delivery/tests` (92 pass at plan start).
- 2026-11-23: models-available.json and models.md re-checked before the first dispatch: unchanged.
- Grill 2026-11-23: the user chose re-ranking on model and price changes only, data from Artificial Analysis fields only, and dropping a step on limits.
- Review round 1, 2026-11-23: K raised on 01.1 and 01.2 (persisted format, retired age check, select-models.py had no tests) and 01.3 (retired heartbeat path); fingerprint gains whether a run cost exists.
- `model-profiles.json` replaces `model-report.json` as the selector's input. The report stays as the raw fetched data and `model-report.md` for people. Reason: The profiles hold every field the selector reads plus the derived properties, so one cached file decides routing.
- The fingerprint is a sha256 over the sorted creator, model, effort, whether an intelligence score exists, whether a run cost exists, input price and output price of every report row. Score and run-cost values are not in it. Reason: The user chose to re-rank on model and price changes and ignore score-only revisions; a row gaining its first score or run cost becomes selectable, so it counts as a new model.
- A pair is premium when its output price is at least $30 per million tokens (`PREMIUM_PRICE_OUT` in select-models.py). Reason: An absolute price keeps the class stable across accounts and tool lists; today it marks Fable ($40-50) and GPT-6.x Astra ($40-50) premium, and Opus 5.5 ($20), Sonnet, Haiku, GPT-6.x Sol, Terra and Luna standard. Raised from $20 on 2026-11-23 at the user's request: Fable costs about twice Opus per token, and the budget should hold back Fable, not Opus.
- The thinking-level ceilings in `CEILINGS` stay; the low-gain rule and the stage caps apply within them. Reason: The ceilings were an earlier user decision and still hold.
- Profiles record no context window. Reason: The fetched Artificial Analysis fields have none (fetch-model-report.py rows_from); add it if the data gains one.
- `route` reads `models-available.json` and the plugin's profiles; `models.md` stays the per-tier summary and records the profiles fingerprint. Reason: Routing needs every offered pair, not only the four tier picks.
- Profiles are built by a `profiles` subcommand of select-models.py, not a separate script. Reason: Building them needs the selector's `EFFORT_ORDER` and `normalize_effort`; one file keeps those in one place.
