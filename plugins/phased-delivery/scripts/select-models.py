#!/usr/bin/env python3
"""Map tiers (small, middle, middle+, top) to a model and thinking level.

Usage:
  select-models.py AVAILABLE.json [--profiles model-profiles.json]
                   [--out models.md] [--json models.json] [--today ignored]
  select-models.py check MODELS_MD [--profiles model-profiles.json]
  select-models.py profiles REPORT OUT_DIR
  select-models.py route AVAILABLE.json --scores J1F1R0C0K0P0V0S0
                   [--down N | --up N] [--premium-spent USD] [--review]
                   [--profiles model-profiles.json]

AVAILABLE.json is written by the planning agent from what the running tool
offers now:

  {
    "tool": "codex",                      # or "claude-code"
    "tool_version": "0.165.0",
    "looked_up_from": "codex debug models",
    "subagent_model_choice": "user-only", # or "allowed"
    "opted_in": false,
    "opt_in_where": "",
    "session_model": "gpt-6.1-sol",      # required when user-only and not opted in
    "models": [
      {"id": "gpt-6.1-sol", "efforts": ["low", "medium", "high", "max"],
       "match": "GPT-6.1 Sol"}            # optional: exact report model name
    ]
  }

Profiles default to the plugin's model-profiles.json and are used at any
age. Exit codes: 0 written; 2 bad input; 3 profiles missing (use the
fallback in model-selection.md); 4 no selectable candidate.

`check` compares the Profiles line of a models.md with the profiles'
fingerprint. Exit codes: 0 current; 1 differs or no Profiles line (rerun
the selector); 3 profiles missing.

`profiles` builds OUT_DIR/model-profiles.json from a model-report.json and
writes it only when the fingerprint of the model list and prices changed.
It prints the fingerprint and "changed" or "unchanged". Exit codes: 0
written; 1 unchanged, nothing written; 2 bad or unreadable report.

`route` prints one JSON line with the model and thinking level for a stage:
{model, effort, tier, premium, score, cap_tokens, cap_usd, why}. It picks
from the score/cost frontier of the offered pairs, leaving out low-gain
thinking steps. --down and --up move N frontier pairs cheaper or dearer;
--premium-spent at or above the phase budget leaves premium pairs out of
builds; --review runs on top and ignores premium spend. Exit codes: 0
printed; 2 bad input; 3 profiles missing; 4 no selectable pair.
"""

import argparse
import hashlib
import importlib.util
import json
import math
import os
import re
import sys

# Tier floors: a candidate qualifies if its score is at least this share of
# the best candidate's score; the cheapest qualifying candidate wins.
FLOORS = {"top": 0.97, "middle": 0.85, "small": 0.50}
# After a tier picks a candidate, any cheaper candidate scoring within this
# many index points (the index runs 0-100) of the pick is taken instead.
TIE_POINTS = 3.0
# Thinking levels from least to most.
EFFORT_ORDER = ["minimal", "low", "medium", "high", "xhigh", "max", "ultra"]
# Highest thinking level allowed, as (creator, model family word or None,
# ceiling); the first matching rule wins. Levels above the ceiling, and
# levels not in EFFORT_ORDER, are denied. In the Codex tool every model is
# treated as OpenAI.
CEILINGS = [
    ("openai", None, "max"),          # Codex output degrades badly above max
    ("anthropic", "haiku", "xhigh"),  # Haiku: xhigh keeps it a real small option
    ("anthropic", None, "high"),      # other Claude: xhigh and max cost far more
]
DEFAULT_EFFORT = "default"  # report row without a thinking-level suffix
# A pair is premium when its output price is at least this many dollars per
# million tokens.
PREMIUM_PRICE_OUT = 30
# A step up in thinking level is low gain when it adds fewer intelligence
# points than this for more than this multiple of the run cost.
LOW_GAIN_POINTS = 2
LOW_GAIN_COST_RATIO = 1.5
PROFILES_FILE = "model-profiles.json"
# Tokens a stage may spend, by tier; passed on as a dollar cap at the pair's
# input price.
CAP_TOKENS = {"small": 150000, "middle": 400000, "middle+": 400000, "top": 1000000}
# No build's dollar cap is lower than this: at the input price alone a cheap
# model's cap rounds to a cent, below what one headless run costs.
MIN_CAP_USD = 0.25
# Once a phase's premium spend reaches this many dollars, builds leave
# premium pairs out.
PREMIUM_BUDGET_USD = 10
# Design (J2, C2) and long or wide (S2, R2, F2) stages may take another
# frontier pair costing at most this multiple of the pick.
PREFER_COST_RATIO = 1.5
# A long or wide stage takes a faster pair only at this multiple of the pick's
# speed: thinking levels of one model differ by a few percent, which is noise.
SPEED_GAIN = 1.2
SCORES_FORM = "J F R C K P V S in that order, each followed by 0, 1 or 2, such as J1F1R0C0K0P0V0S0"

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_PROFILES = os.path.join(HERE, "..", PROFILES_FILE)


def normalize(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def normalize_effort(effort):
    return re.sub(r"[^a-z0-9]+", "", effort.lower()) if effort else DEFAULT_EFFORT


def parse_args(argv):
    if len(argv) < 2 or argv[1].startswith("-"):
        raise SystemExit(__doc__)
    options = {"available": argv[1], "profiles": DEFAULT_PROFILES, "out": None,
               "json": None, "today": None}
    rest = argv[2:]
    if len(rest) % 2:
        raise SystemExit(__doc__)
    for flag, value in zip(rest[::2], rest[1::2]):
        key = flag.lstrip("-")
        if key not in options or key == "available":
            raise SystemExit(f"unknown option {flag}\n{__doc__}")
        options[key] = value
    return options


def load_profiles(path):
    """The profiles, or None after saying on stderr that the file is missing."""
    if not os.path.exists(path):
        print(f"profiles not found: {path}; use the fallback in model-selection.md",
              file=sys.stderr)
        return None
    with open(path) as source:
        return json.load(source)


def model_locked(available):
    """True when subagents must inherit the session model."""
    return (available.get("subagent_model_choice") != "allowed"
            and not available.get("opted_in"))


def match_model(entry, bases):
    """Return (report base name, how matched) or (None, reason)."""
    if entry.get("match"):
        name = entry["match"]
        return (name, "explicit") if name in bases else (None, f"explicit match '{name}' not in report")
    wanted = normalize(entry["id"])
    exact = [b for b in bases if normalize(b) == wanted]
    if len(exact) == 1:
        return exact[0], "exact name"
    tokens = set(wanted.split("-"))
    partial = [b for b in bases if tokens <= set(normalize(b).split("-"))]
    if not partial:
        return None, "no report model matches the name"
    # A short name may only pick the newest version of one model family
    # ("opus" -> newest Opus); names spanning families are ambiguous.
    families = {tuple(t for t in normalize(b).split("-") if not t.isdigit()) for b in partial}
    if len(families) > 1:
        return None, "ambiguous: " + ", ".join(sorted(partial)) + "; add an explicit match"
    newest = max(bases[b]["released"] or "" for b in partial)
    latest = [b for b in partial if (bases[b]["released"] or "") == newest]
    if len(latest) > 1:
        return None, "ambiguous: " + ", ".join(sorted(latest)) + "; add an explicit match"
    return latest[0], "alias: newest release containing the name"


def ceiling_for(creator, base, codex_tool):
    creator = "openai" if codex_tool else creator.lower()
    words = set(normalize(base).split("-"))
    for rule_creator, family, ceiling in CEILINGS:
        if creator == rule_creator and (family is None or family in words):
            return ceiling
    return None


def effort_denial(effort, ceiling):
    """Reason a thinking level is denied under the ceiling, or None if allowed."""
    if ceiling is None or effort == DEFAULT_EFFORT:
        return None
    if effort not in EFFORT_ORDER:
        return f"denied: unknown level, cannot confirm it is at or below {ceiling}"
    if EFFORT_ORDER.index(effort) > EFFORT_ORDER.index(ceiling):
        return f"denied: above this model's {ceiling} ceiling"
    return None


def build_candidates(available, profiles):
    rows_by_base = {}
    for row in profiles["pairs"]:
        rows_by_base.setdefault(row["model"], []).append(row)
    bases = {name: {"released": max((r["released"] or "") for r in rows)}
             for name, rows in rows_by_base.items()}
    codex_tool = available["tool"].lower() == "codex"
    candidates, excluded, matches = [], [], []
    for entry in available["models"]:
        base, how = match_model(entry, bases)
        matches.append((entry["id"], base, how))
        offered = {normalize_effort(e) for e in entry.get("efforts", [])} | {DEFAULT_EFFORT}
        if base is None:
            excluded.append((entry["id"], "*", how))
            continue
        ceiling = ceiling_for(rows_by_base[base][0]["creator"], base, codex_tool)
        for row in rows_by_base[base]:
            effort = row["effort"]
            label = f"{entry['id']} at {effort}"
            if effort not in offered:
                excluded.append((entry["id"], effort, "benchmarked but not offered by the tool"))
            elif effort_denial(effort, ceiling):
                excluded.append((entry["id"], effort, effort_denial(effort, ceiling)))
            else:
                candidates.append({"tool_model": entry["id"], "effort": effort,
                                   "label": label, "row": row})
        benchmarked = {r["effort"] for r in rows_by_base[base]}
        for effort in sorted(offered - benchmarked - {DEFAULT_EFFORT}):
            reason = effort_denial(effort, ceiling) or "offered but not benchmarked"
            excluded.append((entry["id"], effort, reason))
    return candidates, excluded, matches


def load_offered(available_path, profiles_path):
    """(available, profiles, candidates, excluded, matches) after matching,
    ceilings and the model lock. Exits 2 on a bad available file and 3 when
    the profiles are missing."""
    try:
        with open(available_path) as source:
            available = json.load(source)
        if not isinstance(available, dict) or not available.get("models") \
                or not available.get("tool"):
            raise ValueError("needs 'tool' and a non-empty 'models' list")
    except (OSError, ValueError) as error:
        print(f"bad available file: {error}", file=sys.stderr)
        raise SystemExit(2)
    profiles = load_profiles(profiles_path)
    if profiles is None:
        raise SystemExit(3)
    candidates, excluded, matches = build_candidates(available, profiles)
    if not model_locked(available):
        return available, profiles, candidates, excluded, matches
    session = available.get("session_model")
    if not session:
        print("bad available file: subagents inherit the session model here, so"
              " 'session_model' is required", file=sys.stderr)
        raise SystemExit(2)
    locked_out = [(c["tool_model"], c["effort"],
                   "model choice not allowed: subagents inherit the session model")
                  for c in candidates if c["tool_model"] != session]
    return (available, profiles, [c for c in candidates if c["tool_model"] == session],
            excluded + locked_out, matches)


def score_and_cost(candidates):
    # The Intelligence Index is 25% coding (FrontierCode, Terminal-Bench) plus
    # reasoning-heavy science and HLE-Diamond. The free tier has no coding
    # index, and its "engineering" index is mostly engineering domain
    # knowledge with only 15% coding, so it is not used for ranking.
    metric = "intelligence"
    unscored = [(c["tool_model"], c["effort"], f"no {metric}")
                for c in candidates if c["row"][metric] is None]
    with_score = [c for c in candidates if c["row"][metric] is not None]
    # Benchmark run cost counts the tokens each thinking level spends, so it
    # is the only cost that separates levels of one model. Candidates without
    # it are excluded; price per token is used only if no candidate has it.
    if any(c["row"]["run_cost_usd"] is not None for c in with_score):
        cost_field = "run_cost_usd"
        unscored += [(c["tool_model"], c["effort"], "no benchmark run cost")
                     for c in with_score if c["row"][cost_field] is None]
        with_score = [c for c in with_score if c["row"][cost_field] is not None]
    else:
        cost_field = "price_out"
    scored = []
    for c in with_score:
        cost = c["row"][cost_field]
        speed = c["row"]["speed"] or 0
        scored.append({**c, "score": c["row"][metric],
                       "cost": math.inf if cost is None else cost, "speed": speed})
    return scored, unscored, metric, cost_field


def cheapest(pool):
    return min(pool, key=lambda c: (c["cost"], -c["score"], -c["speed"]))


def prefer_cheaper(pick, pool):
    """Within TIE_POINTS of the pick's score, the cheapest candidate wins."""
    return cheapest([c for c in pool if c["score"] >= pick["score"] - TIE_POINTS] + [pick])


def assign_tiers(scored):
    best = max(c["score"] for c in scored)
    tiers = {}
    for tier, floor in FLOORS.items():
        pick = cheapest([c for c in scored if c["score"] >= floor * best])
        tiers[tier] = prefer_cheaper(pick, scored)
    above = [c for c in scored if c["score"] > tiers["middle"]["score"]]
    if above:
        pick = min(above, key=lambda c: (c["score"], c["cost"]))
        tiers["middle+"] = prefer_cheaper(pick, above)
    else:
        tiers["middle+"] = tiers["top"]
    return best, tiers


def money(value):
    return "n/a" if value == math.inf else f"{value:.2f}"


def render(available, profiles, metric, cost_field, best, tiers, scored, excluded, matches):
    lines = [
        "# Models",
        "",
        "Generated by `scripts/select-models.py` from `models-available.json` and",
        "the plugin's `model-profiles.json`; rerun it rather than editing this file.",
        "",
        f"Looked up: {available.get('tool')} {available.get('tool_version', '')}, "
        f"from {available.get('looked_up_from', 'unspecified')}",
        f"Profiles: {profiles['fingerprint']} (data checked {profiles['source_checked']}); "
        f"{profiles['attribution']}",
        f"Subagent model choice: {available.get('subagent_model_choice', 'unspecified')}"
        + ("" if available.get("subagent_model_choice") == "allowed" else
           f" (opted in: {'yes' if available.get('opted_in') else 'no'}"
           f"{', ' + available['opt_in_where'] if available.get('opt_in_where') else ''})"),
        *([f"Subagents inherit the session model ({available.get('session_model')}); "
           "tiers choose only its thinking level."] if model_locked(available) else []),
        f"Score: {metric}; cost: {cost_field}; best score {best:.1f}; "
        f"floors: " + ", ".join(f"{t} {int(f * 100)}%" for t, f in FLOORS.items())
        + f"; cheaper within {TIE_POINTS:g} points wins",
        "",
        "| Tier | Model | Effort | Score | Cost | Report row |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for tier in ["small", "middle", "middle+", "top"]:
        c = tiers[tier]
        lines.append(f"| {tier} | {c['tool_model']} | {c['effort']} | {c['score']:.1f}"
                     f" | {money(c['cost'])} | {c['row']['name']} |")
    lines += ["", "Matches (tool model -> report model):"]
    lines += [f"- {tool} -> {base or 'none'} ({how})" for tool, base, how in matches]
    lines += ["", "Candidates considered:"]
    lines += [f"- {c['label']}: score {c['score']:.1f}, cost {money(c['cost'])}"
              for c in sorted(scored, key=lambda c: (-c["score"], c["cost"]))]
    lines += ["", "Excluded:"]
    lines += [f"- {model} at {effort}: {reason}" for model, effort, reason in excluded] or ["- none"]
    return "\n".join(lines) + "\n"


def fingerprint(rows):
    """sha256 over the model list and prices; score and run-cost values are left out."""
    keys = sorted(json.dumps([r["creator"], r["model"], normalize_effort(r.get("effort")),
                              r.get("intelligence_index") is not None,
                              r.get("benchmark_run_cost_usd") is not None,
                              r.get("price_in_per_1m_usd"), r.get("price_out_per_1m_usd")])
                  for r in rows)
    return hashlib.sha256("\n".join(keys).encode()).hexdigest()


def step_from_lower(pair, lower):
    """(gain, cost ratio) from the next lower level, or (None, None)."""
    if lower is None or None in (pair["intelligence"], pair["run_cost_usd"],
                                 lower["intelligence"], lower["run_cost_usd"]) \
            or not lower["run_cost_usd"]:
        return None, None
    return (round(pair["intelligence"] - lower["intelligence"], 2),
            round(pair["run_cost_usd"] / lower["run_cost_usd"], 3))


def build_pairs(rows):
    base_pairs = [{
        "creator": r["creator"], "model": r["model"],
        "effort": normalize_effort(r.get("effort")), "name": r["name"],
        "released": r.get("released"),
        "intelligence": r.get("intelligence_index"),
        "engineering": r.get("engineering_index"),
        "run_cost_usd": r.get("benchmark_run_cost_usd"),
        "price_in": r.get("price_in_per_1m_usd"),
        "price_out": r.get("price_out_per_1m_usd"),
        "speed": r.get("output_tokens_per_second"),
    } for r in rows]
    ordered = {}
    for p in base_pairs:
        if p["effort"] in EFFORT_ORDER:
            ordered.setdefault((p["creator"], p["model"]), []).append(p)

    def lower_of(pair):
        below = [p for p in ordered.get((pair["creator"], pair["model"]), [])
                 if EFFORT_ORDER.index(p["effort"]) < EFFORT_ORDER.index(pair["effort"])]
        return max(below, key=lambda p: EFFORT_ORDER.index(p["effort"]), default=None)

    pairs = []
    for p in base_pairs:
        gain, ratio = step_from_lower(p, lower_of(p)) if p["effort"] in EFFORT_ORDER else (None, None)
        pairs.append({**p,
                      "premium": p["price_out"] is not None and p["price_out"] >= PREMIUM_PRICE_OUT,
                      "gain_from_lower": gain, "cost_ratio_from_lower": ratio,
                      "low_gain": gain is not None and gain < LOW_GAIN_POINTS
                      and ratio > LOW_GAIN_COST_RATIO})
    return pairs


def load_profile_report(path):
    """The report, or raise ValueError saying what is wrong."""
    try:
        with open(path) as source:
            report = json.load(source)
    except OSError as error:
        raise ValueError(f"cannot read {path}: {error}")
    if not isinstance(report, dict) or not isinstance(report.get("rows"), list):
        raise ValueError("needs a 'rows' list")
    for key in ("checked", "attribution"):
        if key not in report:
            raise ValueError(f"needs '{key}'")
    for index, row in enumerate(report["rows"]):
        if not isinstance(row, dict) or not all(row.get(k) for k in ("creator", "model", "name")):
            raise ValueError(f"row {index} needs creator, model and name")
    return report


def profiles_main(args):
    if len(args) != 2:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        return build_profiles(*args)
    except Exception as error:  # any failure must exit 2: the workflow reads 1 as "unchanged"
        print(f"bad report or output: {error!r}", file=sys.stderr)
        return 2


def build_profiles(report_path, out_dir):
    try:
        report = load_profile_report(report_path)
    except ValueError as error:
        print(f"bad report: {error}", file=sys.stderr)
        return 2
    new_fingerprint = fingerprint(report["rows"])
    path = os.path.join(out_dir, PROFILES_FILE)
    try:
        with open(path) as source:
            old_fingerprint = json.load(source).get("fingerprint")
    except FileNotFoundError:
        old_fingerprint = None
    if old_fingerprint == new_fingerprint:
        print(f"{new_fingerprint} unchanged")
        return 1
    profiles = {"fingerprint": new_fingerprint, "source_checked": report["checked"],
                "attribution": report["attribution"], "pairs": build_pairs(report["rows"])}
    with open(path, "w") as out:
        json.dump(profiles, out, indent=2)
        out.write("\n")
    print(f"{new_fingerprint} changed")
    return 0


def check_main(args):
    if len(args) not in (1, 3) or args[1:2] not in ([], ["--profiles"]):
        print(__doc__, file=sys.stderr)
        return 2
    profiles = load_profiles(args[2] if len(args) == 3 else DEFAULT_PROFILES)
    if profiles is None:
        return 3
    with open(args[0]) as source:
        recorded = re.search(r"^Profiles: (\S+)", source.read(), re.MULTILINE)
    if recorded and recorded.group(1) == profiles["fingerprint"]:
        print(f"{args[0]} is current")
        return 0
    print(f"{args[0]} does not match profiles {profiles['fingerprint']}; rerun the selector")
    return 1


def parse_scores(text):
    if not re.fullmatch(r"J[012]F[012]R[012]C[012]K[012]P[012]V[012]S[012]", text):
        raise argparse.ArgumentTypeError(f"expected {SCORES_FORM}, got {text!r}")
    return {text[i]: int(text[i + 1]) for i in range(0, 16, 2)}


def stage_tier(scores):
    """plan-check.py's tier: (total, tier, why) with the model-selection overrides."""
    spec = importlib.util.spec_from_file_location("plan_check", os.path.join(HERE, "plan-check.py"))
    plan_check = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(plan_check)
    return plan_check.tier(scores)


def frontier(pool):
    """Pairs no other pair beats on score and cost, cheapest first."""
    def beaten(c):
        return any(o["score"] >= c["score"] and o["cost"] <= c["cost"]
                   and (o["score"], o["cost"]) != (c["score"], c["cost"]) for o in pool)
    return sorted((c for c in pool if not beaten(c)), key=lambda c: (c["cost"], c["score"]))


def meets_floor(front, tier, best):
    """Frontier pairs meeting the tier's floor; for middle+, those above the middle pick."""
    if tier == "middle+":
        bar = frontier_pick(front, "middle", best)["score"]
        return [c for c in front if c["score"] > bar]
    return [c for c in front if c["score"] >= FLOORS[tier] * best]


def effort_rank(effort):
    return EFFORT_ORDER.index(effort) if effort in EFFORT_ORDER else len(EFFORT_ORDER)


def frontier_pick(front, tier, best):
    """The tier's pair on the frontier: cheapest meeting the floor, then the tie rule."""
    if tier == "middle+":
        middle = front.index(frontier_pick(front, "middle", best))
        return front[min(middle + 1, len(front) - 1)]
    meeting = meets_floor(front, tier, best)
    if not meeting:
        return max(front, key=lambda c: c["score"])
    return prefer_cheaper(cheapest(meeting), front)


def steps_count(text):
    value = int(text)
    if value < 0:
        raise argparse.ArgumentTypeError("must be 0 or more")
    return value


def pick_pair(allowed, tier, best, scores, signals, up, down):
    """Route one stage within the allowed pairs: (choice, reasons), or (None, error)."""
    why = []
    mechanical = signals and tier != "small" and all(scores[m] == 0 for m in "JPV")
    long_wide = signals and any(scores[m] == 2 for m in "SRF")
    cap = "medium" if mechanical else "high" if long_wide else None
    capped = [c for c in allowed if not effort_denial(c["effort"], cap)]
    if not capped:
        return None, f"no selectable pair at {cap} thinking or below"
    front = frontier(capped)
    pick = frontier_pick(front, tier, best)
    if cap and pick is not frontier_pick(frontier(allowed), tier, best):
        why.append(f"{'mechanical' if mechanical else 'long or wide'} stage: thinking capped at {cap}")
    meeting = meets_floor(front, tier, best)
    if signals and scores["K"] >= 1:
        stepped = front[min(front.index(pick) + 1, len(front) - 1)]
        if stepped is not pick:
            why.append(f"risk K{scores['K']}: one frontier pair up from {pick['label']}")
        pick = stepped
    # The preferences never go below this score, so they cannot undo the risk step.
    least = pick["score"]
    if signals and (scores["J"] == 2 or scores["C"] == 2):
        lighter = min([pick] + [c for c in meeting if c["score"] >= least
                                and c["cost"] <= PREFER_COST_RATIO * pick["cost"]],
                      key=lambda c: (effort_rank(c["effort"]), -c["score"]))
        if lighter is not pick:
            why.append(f"J2 or C2: lower thinking within {PREFER_COST_RATIO}x the cost of {pick['label']}")
        pick = lighter
    if long_wide:
        close = least if scores["K"] >= 1 else pick["score"] - TIE_POINTS
        faster = max([pick] + [c for c in meeting if c["score"] >= close
                               and c["cost"] <= PREFER_COST_RATIO * pick["cost"]
                               and c["speed"] >= SPEED_GAIN * pick["speed"]],
                     key=lambda c: c["speed"])
        if faster is not pick:
            why.append(f"S2, R2 or F2: faster close pair than {pick['label']}")
        pick = faster
    index = front.index(pick)
    moved = max(0, min(len(front) - 1, index + up - down))
    if down or up:
        why.append(f"--{'down' if down else 'up'} {down or up}: moved "
                   f"{abs(moved - index)} frontier pairs from {pick['label']}")
    return front[moved], why


def route_main(args):
    parser = argparse.ArgumentParser(prog="select-models.py route")
    parser.add_argument("available")
    parser.add_argument("--scores", required=True, type=parse_scores)
    steps = parser.add_mutually_exclusive_group()
    steps.add_argument("--down", type=steps_count, default=0)
    steps.add_argument("--up", type=steps_count, default=0)
    parser.add_argument("--premium-spent", type=float, default=0.0)
    parser.add_argument("--review", action="store_true")
    parser.add_argument("--profiles", default=DEFAULT_PROFILES)
    options = parser.parse_args(args)
    _, _, candidates, _, _ = load_offered(options.available, options.profiles)
    usable = [c for c in candidates if not c["row"]["low_gain"]
              and c["row"]["intelligence"] is not None and c["row"]["run_cost_usd"] is not None]
    pool = score_and_cost(usable)[0]
    if not pool:
        print("no selectable pair", file=sys.stderr)
        return 4
    tier, tier_why = ("top", "phase reviews run on top") if options.review \
        else stage_tier(options.scores)[1:]
    best = max(c["score"] for c in pool)
    over_budget = not options.review and options.premium_spent >= PREMIUM_BUDGET_USD
    allowed = [c for c in pool if not c["row"]["premium"]] if over_budget else pool
    if not allowed:
        print("no selectable pair within the premium budget", file=sys.stderr)
        return 4
    why = [f"tier {tier}" + (f" ({tier_why})" if tier_why else "")]
    if over_budget:
        why.append(f"premium budget ${PREMIUM_BUDGET_USD} reached "
                   f"(${options.premium_spent:g} spent): premium pairs left out")
    scores = options.scores
    signals = not options.review  # a review runs on top as is: the stage's scores do not shape it
    steps = (options.up, options.down)
    choice, notes = pick_pair(allowed, tier, best, scores, signals, *steps)
    if choice is None:
        print(notes, file=sys.stderr)
        return 4
    standard = [c for c in allowed if not c["row"]["premium"]]
    if tier != "top" and choice["row"]["premium"] and standard:
        # Below top a premium pair must beat the standard pick on cost and score.
        other, other_notes = pick_pair(standard, tier, best, scores, signals, *steps)
        if other is not None and (choice["cost"] > other["cost"] or choice["score"] < other["score"]):
            notes = other_notes + [f"premium {choice['label']} left out below top: "
                                   f"{other['label']} costs less or scores at least as well"]
            choice = other
    why += notes
    row = choice["row"]
    cap_tokens = CAP_TOKENS[tier]
    print(json.dumps({"model": choice["tool_model"], "effort": choice["effort"], "tier": tier,
                      "premium": row["premium"], "score": choice["score"],
                      "cap_tokens": cap_tokens,
                      "cap_usd": max(MIN_CAP_USD, round(cap_tokens * row["price_in"] / 1000000, 2)),
                      "why": "; ".join(why)}))
    return 0


def main(argv):
    if argv[1:2] == ["route"]:
        return route_main(argv[2:])
    if argv[1:2] == ["profiles"]:
        return profiles_main(argv[2:])
    if argv[1:2] == ["check"]:
        return check_main(argv[2:])
    options = parse_args(argv)
    available, profiles, candidates, excluded, matches = load_offered(
        options["available"], options["profiles"])
    scored, unscored, metric, cost_field = score_and_cost(candidates)
    excluded += unscored
    if not scored:
        print("no selectable candidate; see the exclusions below", file=sys.stderr)
        for model, effort, reason in excluded:
            print(f"- {model} at {effort}: {reason}", file=sys.stderr)
        return 4
    best, tiers = assign_tiers(scored)
    text = render(available, profiles, metric, cost_field, best, tiers, scored, excluded, matches)
    if options["out"]:
        with open(options["out"], "w") as out:
            out.write(text)
    else:
        sys.stdout.write(text)
    if options["json"]:
        with open(options["json"], "w") as out:
            json.dump({tier: {"model": c["tool_model"], "effort": c["effort"],
                              "score": c["score"], "report_row": c["row"]["name"]}
                       for tier, c in tiers.items()}, out, indent=2)
            out.write("\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
