# Phase 01: Tier rule and premium ratio gate

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: `tier` makes any stage with J, C or K at 2 `top`, and `route` takes the premium pair above the standard pick whenever the standard pairs run out before a requested step up, so Fable high and Fable low are the usual picks.
After: `top` comes only from a total of 9 or more, and a premium step-up below `top` needs a score/cost ratio at least the standard pick's, except on a `--up` retry. model-selection.md and docs/model-routing.md describe both rules.

## Assumptions
- Verified: `select-models.py` takes its tier from plan-check.py's `tier` through `stage_tier`, so one change covers planning and routing. (plugins/phased-delivery/scripts/select-models.py:480-485)
- Verified: Each route candidate carries `score` and `cost` (the benchmark run cost), which the frontier already compares. (plugins/phased-delivery/scripts/select-models.py:488-493, frontier)

## Size

Quick plan:
- plan-mode.py sketch: quick, score 6.0
- tier rule (interface, plan_check.tier): 3.0
- premium step-up ratio gate (internal): 1
- docs and tests (internal): 2

## Outcome tests
Budget: The plugin suite stays under a minute.

| Outcome | Test | Written in | Passes from |
| --- | --- | --- | --- |
| `select-models.py route` for a stage scored J1F1R1C1K2P1V0S0 (total 7) prints tier `middle+`, not `top`; a stage totalling 9 or more still prints `top`. | `plugins/phased-delivery/tests/test_select_models.py::test_route_fable_limits` | 01.1 | 01.1 |
| When the standard pairs run out before a `middle+` or risk step, `route` prints the premium pair above the standard pick only when its score/cost ratio is at least the standard pick's, and otherwise the standard pick with the reason in `why`; with `--up 1` it still prints the premium pair. | `plugins/phased-delivery/tests/test_select_models.py::test_route_fable_limits` | 01.1 | 01.1 |

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | `tier` makes `top` only from a total of 9 or more, and `route` takes a premium step-up below `top` only when its score/cost ratio is at least the standard pick's or the step is a `--up` retry. | middle | first | planned |
| 01.2 | model-selection.md and docs/model-routing.md state the new tier rule and the ratio gate, with the measurement that led to them. | middle | after 01.1 | planned |

## 01.1 Tier rule, ratio gate and test

Goal: `tier` makes `top` only from a total of 9 or more, and `route` takes a premium step-up below `top` only when its score/cost ratio is at least the standard pick's or the step is a `--up` retry.

Context:
- `plugins/phased-delivery/scripts/plan-check.py:97-98`: The override that makes J, C or K at 2 `top`.
- `plugins/phased-delivery/scripts/select-models.py:619-622`: The step-up branch of the premium gate below top.
- `plugins/phased-delivery/tests/test_select_models.py:122`: The existing premium gate test and its edited-profiles pattern to follow.
- Design, Rules: "`top` comes only from a total of 9 or more."
- Design, Rules: "A `--up` retry after a failed build still steps up"

Contracts:
- function `tier` (provides; plugins/phased-delivery/scripts/select-models.py): tier(mb: dict of J F R C K P V S scores) -> (total, tier, why); top only when total >= 9

Files:
- `plugins/phased-delivery/scripts/plan-check.py` (edit): `tier` without the J, C or K = 2 override
- `plugins/phased-delivery/scripts/select-models.py` (edit): the premium gate's step-up branch checks the score/cost ratio unless `--up` was given
- `plugins/phased-delivery/tests/test_select_models.py` (edit): `test_route_fable_limits` and any expectations the tier change moves

Behaviour:
- Given scores totalling 8 or less with J, C or K at 2, when `tier` runs, then the tier is `middle+` (a measure at 2 on `middle`), not `top`.
- Given scores totalling 9 or more, when `tier` runs, then the tier is `top`, as before.
- Given a middle+ or risk step below top where the standard pairs run out and the premium pair above has a lower score/cost ratio than the standard pick, when `route` runs without `--up`, then it prints the standard pick, and `why` says the premium pair was left out for its score/cost ratio.
- Given the same stage, when `route` runs with `--up 1`, then it prints the premium pair above the standard pick, as before.
- Given a premium pair whose ratio is at least the standard pick's, when `route` runs, then the step up takes it, as before.

External inputs:
none

Tests:
- writes `plugins/phased-delivery/tests/test_select_models.py::test_route_fable_limits` (outcome): `select-models.py route` for a stage scored J1F1R1C1K2P1V0S0 (total 7) prints tier `middle+`, not `top`; a stage totalling 9 or more still prints `top`.
- writes `plugins/phased-delivery/tests/test_select_models.py::test_route_fable_limits` (outcome): When the standard pairs run out before a `middle+` or risk step, `route` prints the premium pair above the standard pick only when its score/cost ratio is at least the standard pick's, and otherwise the standard pick with the reason in `why`; with `--up 1` it still prints the premium pair.
- keeps passing `plugins/phased-delivery/tests/test_select_models.py::test_route_premium_below_top` (integration): the cost-and-score rule and the --up step still hold

Done when:
- `python3 -m pytest -q -p no:cacheprovider --basetemp=/cache/pytest-r plugins/phased-delivery/tests` passes

Out of scope:
- The floors, caps and other route rules
- The plan's recorded tiers in existing phase files

Model basis: J1 F1 R1 C1 K0 P1 V0 S0 = 5 -> middle

## 01.2 Docs for the new rules

Goal: model-selection.md and docs/model-routing.md state the new tier rule and the ratio gate, with the measurement that led to them.

Context:
- Builds on 01.1: the new tier rule and ratio gate to describe
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:46`: Override 1, which is removed.
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md:200`: The route table row the ratio rule joins.
- `docs/model-routing.md:94-95`: The routing notes' premium rule list.
- Design, Problem: "Fable at
medium thinking or above should be for the top 10% most complex tasks"

Contracts:
none

Files:
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md` (edit): overrides without J, C or K = 2 to top, examples re-scored, and the ratio rule in the route table
- `docs/model-routing.md` (edit): the rule change and the 38-stage measurement

Behaviour:
- Given a planner reading model-selection.md, when it picks a tier, then nothing tells it a single 2 means top.

External inputs:
none

Tests:
none

Done when:
- `grep -n 'K = 2: use' plugins/phased-delivery/skills/plan-in-phases/model-selection.md` finds nothing

Out of scope:
- implement-in-phases guides

Model basis: J1 F1 R0 C0 K0 P1 V1 S0 = 4 -> middle

## Notes
- 2026-11-24: measured before the change: 15 of 38 scored stages routed to Fable high, 10 to Fable low; with the override dropped, 2 to Fable high (5%).
- The ratio uses the profiles' `score` and benchmark run `cost` that `route` already compares; no new data. Reason: The selector's frontier already ranks pairs by those two numbers.
