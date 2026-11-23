# Phase 02: Per-stage routing

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: models.md maps four tiers to one pair each, and every stage of a tier gets that pair. Nothing stops a runaway build or limits premium spend.
After: `select-models.py route` prints one model and thinking level for a stage from its eight scores: only pairs on the score/cost frontier, no low-gain thinking steps, effort capped for mechanical and long or wide stages, larger models at lower thinking for design work, faster models for long work, and a token and dollar cap. `--down`, `--up`, `--premium-spent` and `--review` cover dropping a step, escalating, the premium budget and reviews.

## Assumptions
- Verified: plan-check.py's `tier` is importable by path and gives the tier with the model-selection overrides from the eight scores. (plugins/phased-delivery/scripts/plan-check.py:95-104 def tier; tests load scripts by path the same way (tests/test_plan_mode.py:9-12))
- Verified: Claude pairs above high are already excluded by the ceilings, so the high cap matters for Haiku and Codex pairs. (plugins/phased-delivery/scripts/select-models.py:49-53 CEILINGS)
- Open: The 2-point and 1.5x cutoffs, the stage caps and the 1.5x preference window pick well on real stages. (Only a paid eval run can show it; run it after phase 03 with the user's approval and adjust the constants.)

## Outcome tests
Budget: python3 -m pytest -q plugins/phased-delivery/tests runs in under a minute.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| `select-models.py route AVAILABLE.json --scores J1F1R0C0K0P0V0S0` prints one JSON line with `model`, `effort`, `tier`, `premium`, `cap_tokens` and `cap_usd`. The pair is the cheapest frontier pair meeting the tier's floor, never one beaten on both score and cost by another offered pair, and never a low-gain thinking step. | `plugins/phased-delivery/tests/test_select_models.py::test_route_frontier` | 02.1 | 02.1 |
| `route` caps a mechanical stage above the small tier at medium thinking while a small mechanical stage keeps the small model's higher level, caps S2, R2 or F2 stages at high and prefers the faster close pair, gives J2 or C2 stages a larger model at lower thinking when it costs at most 1.5 times more, and moves K of 1 or more one frontier pair up. | `plugins/phased-delivery/tests/test_select_models.py::test_route_stage_signals` | 02.1 | 02.2 |
| `route --down 1` prints the next cheaper pair on the frontier below the normal pick; `route --premium-spent 10` prints no premium pair for a build; `route --review --premium-spent 10` still prints the top pair. | `plugins/phased-delivery/tests/test_select_models.py::test_route_limits` | 02.1 | 02.1 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 02.1 | `select-models.py route` picks one pair per stage from the frontier of offered pairs, with tier floors, caps and the limit options. | top | first | planned |
| 02.2 | Route shapes the pick by what the stage's scores say: effort caps for mechanical and long or wide stages, larger models at lower thinking for design work, faster models for long work, a higher floor for risk. | middle | after 02.1 | planned |

## 02.1 route on the frontier with limits

Goal: `select-models.py route` picks one pair per stage from the frontier of offered pairs, with tier floors, caps and the limit options.

Context:
- Builds on 01.1: the model-profiles.json format with `low_gain` and `premium`
- Builds on 01.2: the selector reading profiles, with matching, ceilings and model lock unchanged
- `plugins/phased-delivery/scripts/plan-check.py:95-104`: Total and tier with overrides from a dict of the eight scores.
- `plugins/phased-delivery/scripts/select-models.py:36-41`: Tier floors as shares of the best score and the 3-point tie rule, reused by route.
- `plugins/phased-delivery/scripts/select-models.py:208-229`: Cheapest pair meeting the floor, then cheaper within 3 points; middle+ is the next pair above middle.
- `plugins/phased-delivery/scripts/select-models.py:96-99`: When subagents inherit the session model, only its levels are candidates.
- Design, Routing: "a pair another beats on both score and cost is never chosen"
- Design, Limits: "Tokens per stage: 150k for small, 400k for middle, 1M for top."
- Design, Limits: "Phase reviews always run on top."

Contracts:
- cli `select-models.py route` (provides; 02.2, 03.2): route AVAILABLE.json --scores J1F1R0C0K0P0V0S0 [--down N | --up N] [--premium-spent USD] [--review] [--profiles FILE]: one JSON line {model, effort, tier, premium, score, cap_tokens, cap_usd, why}; exit 0, 2 bad input, 3 no profiles, 4 none
- function `tier` (uses; plugins/phased-delivery/scripts/plan-check.py): tier(mb: dict of J F R C K P V S to 0-2) -> (total: int, tier: small|middle|middle+|top, why: str)
- format `model-profiles.json` (uses; 01.1): {"fingerprint": sha256 hex, "source_checked": "2026-11-21", "attribution": str, "pairs": [{"creator", "model", "effort", "name", "released", "intelligence", "engineering", "run_cost_usd", "price_in", "price_out", "speed", "premium": bool, "gain_from_lower": float|null, "cost_ratio_from_lower": float|null, "low_gain": bool}]}

Files:
- `plugins/phased-delivery/scripts/select-models.py` (edit): holds the `route` subcommand and the constants `CAP_TOKENS` and `PREMIUM_BUDGET_USD`
- `plugins/phased-delivery/tests/test_select_models.py` (edit): gains the route outcome tests
- `plugins/phased-delivery/tests/profiles_fixture.json` (create): a small hand-built profiles file whose pairs make each routing rule visible

Behaviour:
- Given an available file and profiles, when route runs, then the pool is the offered pairs after matching, ceilings and model lock as for models.md, less pairs with `low_gain` true or no score or run cost.
- Given the pool, when route picks, then only frontier pairs are chosen: a pair is dropped when another has score at least as high and cost at most as high, one of them strictly.
- Given the scores, when route picks, then `tier` gives the tier; the floor is that tier's share in `FLOORS` of the best score in the pool before any premium exclusion; the pick is the cheapest frontier pair meeting the floor, then the cheapest within `TIE_POINTS` of it; middle+ is the next frontier pair above the middle pick; with no pair meeting the floor, the highest-scoring pair.
- Given `--down N` or `--up N`, when route picks, then the result is N frontier pairs cheaper or dearer than the pick, stopping at the ends, and `why` says so.
- Given `--premium-spent` at or above `PREMIUM_BUDGET_USD` (10) without `--review`, when route picks, then premium pairs leave the pool and `why` names the budget.
- Given `--review`, when route picks, then the tier is top whatever the scores, and premium spend is ignored.
- Given the pick, when route prints, then `cap_tokens` is `CAP_TOKENS` for the tier (small 150000, middle and middle+ 400000, top 1000000) and `cap_usd` is cap_tokens times the pair's input price per million tokens divided by 1000000, rounded to cents.
- Given `--scores` not eight letters each followed by 0, 1 or 2, or a bad available file, when route runs, then it exits 2 with the reason.

External inputs:
- the `--scores` argument, typed by the orchestrator from a brief: exactly J F R C K P V S in order, each 0 to 2; on failure, exit 2 naming the expected form

Tests:
- writes `plugins/phased-delivery/tests/test_select_models.py::test_route_frontier` (outcome): `select-models.py route AVAILABLE.json --scores J1F1R0C0K0P0V0S0` prints one JSON line with `model`, `effort`, `tier`, `premium`, `cap_tokens` and `cap_usd`. The pair is the cheapest frontier pair meeting the tier's floor, never one beaten on both score and cost by another offered pair, and never a low-gain thinking step.
- writes `plugins/phased-delivery/tests/test_select_models.py::test_route_stage_signals` (outcome): `route` caps a mechanical stage above the small tier at medium thinking while a small mechanical stage keeps the small model's higher level, caps S2, R2 or F2 stages at high and prefers the faster close pair, gives J2 or C2 stages a larger model at lower thinking when it costs at most 1.5 times more, and moves K of 1 or more one frontier pair up.
- writes `plugins/phased-delivery/tests/test_select_models.py::test_route_limits` (outcome): `route --down 1` prints the next cheaper pair on the frontier below the normal pick; `route --premium-spent 10` prints no premium pair for a build; `route --review --premium-spent 10` still prints the top pair.

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests` passes, with `test_route_stage_signals` reported as expected-fail.

Out of scope:
- The stage-signal rules (02.2); write `test_route_stage_signals` now, marked `xfail(strict=True)`.
- models.md's content and the tier summary.
- The profiles format.

Model basis: J1 F1 R1 C2 K0 P1 V0 S0 = 6 -> top (override: J, C or K = 2)

## 02.2 stage signals shape the pick

Goal: Route shapes the pick by what the stage's scores say: effort caps for mechanical and long or wide stages, larger models at lower thinking for design work, faster models for long work, a higher floor for risk.

Context:
- Builds on 02.1: `select-models.py route` with its pool, frontier, floor and pick
- `plugins/phased-delivery/scripts/select-models.py:43-44`: The order used to compare thinking levels against the caps.
- Design, Routing: "Mechanical stages above the small tier run at medium thinking or below;"
- Design, Routing: "move up the model before the"
- Design, Routing: "Long or wide stages (S2, R2, F2) run at high thinking or below, and"
- Design, Routing: "Risk (K of 1 or more) raises the score floor."

Contracts:
- cli `select-models.py route` (uses; 02.1): route AVAILABLE.json --scores J1F1R0C0K0P0V0S0 [--down N | --up N] [--premium-spent USD] [--review] [--profiles FILE]: one JSON line {model, effort, tier, premium, score, cap_tokens, cap_usd, why}; exit 0, 2 bad input, 3 no profiles, 4 none

Files:
- `plugins/phased-delivery/scripts/select-models.py` (edit): route applies the stage-signal rules and the constant `PREFER_COST_RATIO`
- `plugins/phased-delivery/tests/test_select_models.py` (edit): `test_route_stage_signals` loses its expected-fail mark

Behaviour:
- Given J, P and V all 0 (mechanical) and a tier above small, when route picks, then pairs above medium leave the pool before the frontier is formed; a small-tier mechanical stage keeps every level up to `CEILINGS`, so on the committed profiles it still gets haiku high.
- Given S, R or F at 2, when route picks, then pairs above high leave the pool before the frontier is formed.
- Given the effort caps, when the floor is set, then it is still taken from the best score before the caps, so a cap never lowers the bar.
- Given K at 1 or more, when route picks, then the pick moves one frontier pair up after the tie rule.
- Given J or C at 2, when route picks, then among frontier pairs meeting the floor and costing at most `PREFER_COST_RATIO` (1.5) times the pick, the one with the lowest thinking level wins, higher score breaking ties.
- Given S, R or F at 2, when route picks, then among frontier pairs meeting the floor, within `TIE_POINTS` of the pick's score and at most 1.5 times its cost, the fastest wins.
- Given several rules apply, when route picks, then they apply in this order: caps, floor and pick, risk step, lower-thinking preference, speed preference, then `--down` or `--up`; `why` lists each rule that changed the result.

External inputs:
none

Tests:
- turns on `plugins/phased-delivery/tests/test_select_models.py::test_route_stage_signals` (outcome): `route` caps a mechanical stage above the small tier at medium thinking while a small mechanical stage keeps the small model's higher level, caps S2, R2 or F2 stages at high and prefers the faster close pair, gives J2 or C2 stages a larger model at lower thinking when it costs at most 1.5 times more, and moves K of 1 or more one frontier pair up.

Done when:
- `python3 -m pytest -q plugins/phased-delivery/tests` passes with no expected-fail left in test_select_models.py.

Out of scope:
- The limit options and caps from 02.1.
- Tier floors and `CEILINGS`.

Model basis: J1 F1 R0 C1 K0 P1 V0 S0 = 4 -> middle

## Notes
- Review round 1, 2026-11-23: the user exempted small-tier stages from the mechanical cap; O3 split so test_route_frontier covers only 02.1's rules and test_route_stage_signals (O6) the signals.
- `model-profiles.json` replaces `model-report.json` as the selector's input. The report stays as the raw fetched data and `model-report.md` for people. Reason: The profiles hold every field the selector reads plus the derived properties, so one cached file decides routing.
- A pair is premium when its output price is at least $30 per million tokens (`PREMIUM_PRICE_OUT` in select-models.py). Reason: An absolute price keeps the class stable across accounts and tool lists; today it marks Fable ($40-50) and GPT-6.x Astra ($40-50) premium, and Opus 5.5 ($20), Sonnet, Haiku, GPT-6.x Sol, Terra and Luna standard. Raised from $20 on 2026-11-23 at the user's request: Fable costs about twice Opus per token, and the budget should hold back Fable, not Opus.
- The thinking-level ceilings in `CEILINGS` stay; the low-gain rule and the stage caps apply within them. Reason: The ceilings were an earlier user decision and still hold.
- Once a phase's premium spend reaches $10, routing leaves premium pairs out of builds, falling to the best standard pair. Reason: One step down from a premium pair is often still premium; the user chose exclusion in the review round.
- Token caps per tier (small 150000, middle and middle+ 400000, top 1000000) are passed to claude -p as a dollar cap: cap tokens times the pair's input price per token. Reason: The user chose a dollar cap over watching tokens; `--max-budget-usd` is the hard stop claude -p offers, and the paid calibration run tunes it.
- `route` reads `models-available.json` and the plugin's profiles; `models.md` stays the per-tier summary and records the profiles fingerprint. Reason: Routing needs every offered pair, not only the four tier picks.
- Mechanical stages above the small tier are capped at medium thinking; small-tier stages keep the small model's higher levels within `CEILINGS`. Reason: Capping small stages would move them from Haiku high to Sonnet medium at 5.6 times the cost; the user chose the exemption in the review round.
