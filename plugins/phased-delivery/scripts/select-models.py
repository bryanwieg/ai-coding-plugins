#!/usr/bin/env python3
"""Map tiers (small, middle, middle+, top) to a model and thinking level.

Usage:
  select-models.py AVAILABLE.json [--profiles model-profiles.json]
                   [--out models.md] [--json models.json] [--today ignored]
  select-models.py check MODELS_MD [--profiles model-profiles.json]
  select-models.py profiles REPORT OUT_DIR

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
"""

import hashlib
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


def main(argv):
    if argv[1:2] == ["profiles"]:
        return profiles_main(argv[2:])
    if argv[1:2] == ["check"]:
        return check_main(argv[2:])
    options = parse_args(argv)
    try:
        with open(options["available"]) as source:
            available = json.load(source)
        if not available.get("models") or not available.get("tool"):
            raise ValueError("needs 'tool' and a non-empty 'models' list")
    except (OSError, ValueError) as error:
        print(f"bad available file: {error}", file=sys.stderr)
        return 2
    profiles = load_profiles(options["profiles"])
    if profiles is None:
        return 3
    candidates, excluded, matches = build_candidates(available, profiles)
    if model_locked(available):
        session = available.get("session_model")
        if not session:
            print("bad available file: subagents inherit the session model here, so"
                  " 'session_model' is required", file=sys.stderr)
            return 2
        excluded += [(c["tool_model"], c["effort"],
                      "model choice not allowed: subagents inherit the session model")
                     for c in candidates if c["tool_model"] != session]
        candidates = [c for c in candidates if c["tool_model"] == session]
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
