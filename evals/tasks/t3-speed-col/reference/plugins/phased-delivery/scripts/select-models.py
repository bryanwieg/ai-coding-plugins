#!/usr/bin/env python3
"""Map tiers (small, middle, middle+, top) to a model and thinking level.

Usage:
  select-models.py AVAILABLE.json [--report model-report.json]
                   [--out models.md] [--json models.json] [--today YYYY-MM-DD]

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

Exit codes: 0 written; 2 bad input; 3 report missing or stale (use the
fallback in model-selection.md); 4 no selectable candidate.
"""

import datetime
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
MAX_REPORT_AGE_DAYS = 7
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

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_REPORT = os.path.join(HERE, "..", "model-report.json")


def normalize(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def normalize_effort(effort):
    return re.sub(r"[^a-z0-9]+", "", effort.lower()) if effort else DEFAULT_EFFORT


def parse_args(argv):
    if len(argv) < 2 or argv[1].startswith("-"):
        raise SystemExit(__doc__)
    options = {"available": argv[1], "report": DEFAULT_REPORT, "out": None,
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


def load_report(path, today):
    if not os.path.exists(path):
        return None, f"report not found: {path}"
    with open(path) as source:
        report = json.load(source)
    checked = datetime.date.fromisoformat(report["checked"])
    age = (today - checked).days
    if age > MAX_REPORT_AGE_DAYS:
        return None, f"report is stale: checked {checked}, {age} days old (limit {MAX_REPORT_AGE_DAYS})"
    return report, None


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


def build_candidates(available, report):
    rows_by_base = {}
    for row in report["rows"]:
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
            effort = normalize_effort(row["effort"])
            label = f"{entry['id']} at {effort}"
            if effort not in offered:
                excluded.append((entry["id"], effort, "benchmarked but not offered by the tool"))
            elif effort_denial(effort, ceiling):
                excluded.append((entry["id"], effort, effort_denial(effort, ceiling)))
            else:
                candidates.append({"tool_model": entry["id"], "effort": effort,
                                   "label": label, "row": row})
        benchmarked = {normalize_effort(r["effort"]) for r in rows_by_base[base]}
        for effort in sorted(offered - benchmarked - {DEFAULT_EFFORT}):
            reason = effort_denial(effort, ceiling) or "offered but not benchmarked"
            excluded.append((entry["id"], effort, reason))
    return candidates, excluded, matches


def score_and_cost(candidates):
    # The Intelligence Index is 25% coding (FrontierCode, Terminal-Bench) plus
    # reasoning-heavy science and HLE-Diamond. The free tier has no coding
    # index, and its "engineering" index is mostly engineering domain
    # knowledge with only 15% coding, so it is not used for ranking.
    metric = "intelligence_index"
    unscored = [(c["tool_model"], c["effort"], f"no {metric}")
                for c in candidates if c["row"][metric] is None]
    with_score = [c for c in candidates if c["row"][metric] is not None]
    # Benchmark run cost counts the tokens each thinking level spends, so it
    # is the only cost that separates levels of one model. Candidates without
    # it are excluded; price per token is used only if no candidate has it.
    if any(c["row"]["benchmark_run_cost_usd"] is not None for c in with_score):
        cost_field = "benchmark_run_cost_usd"
        unscored += [(c["tool_model"], c["effort"], "no benchmark run cost")
                     for c in with_score if c["row"][cost_field] is None]
        with_score = [c for c in with_score if c["row"][cost_field] is not None]
    else:
        cost_field = "price_out_per_1m_usd"
    scored = []
    for c in with_score:
        cost = c["row"][cost_field]
        speed = c["row"]["output_tokens_per_second"] or 0
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


def tokens_per_second(value):
    return "n/a" if value is None else f"{value:.0f}"


def render(available, report, metric, cost_field, best, tiers, scored, excluded, matches):
    lines = [
        "# Models",
        "",
        "Generated by `scripts/select-models.py` from `models-available.json` and",
        "the plugin's `model-report.json`; rerun it rather than editing this file.",
        "",
        f"Looked up: {available.get('tool')} {available.get('tool_version', '')}, "
        f"from {available.get('looked_up_from', 'unspecified')}",
        f"Report: checked {report['checked']}; {report['attribution']}",
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
        "| Tier | Model | Effort | Score | Cost | Speed | Report row |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for tier in ["small", "middle", "middle+", "top"]:
        c = tiers[tier]
        lines.append(f"| {tier} | {c['tool_model']} | {c['effort']} | {c['score']:.1f}"
                     f" | {money(c['cost'])}"
                     f" | {tokens_per_second(c['row']['output_tokens_per_second'])}"
                     f" | {c['row']['name']} |")
    lines += ["", "Matches (tool model -> report model):"]
    lines += [f"- {tool} -> {base or 'none'} ({how})" for tool, base, how in matches]
    lines += ["", "Candidates considered:"]
    lines += [f"- {c['label']}: score {c['score']:.1f}, cost {money(c['cost'])}"
              for c in sorted(scored, key=lambda c: (-c["score"], c["cost"]))]
    lines += ["", "Excluded:"]
    lines += [f"- {model} at {effort}: {reason}" for model, effort, reason in excluded] or ["- none"]
    return "\n".join(lines) + "\n"


def main(argv):
    options = parse_args(argv)
    today = (datetime.date.fromisoformat(options["today"]) if options["today"]
             else datetime.datetime.now(datetime.timezone.utc).date())
    try:
        with open(options["available"]) as source:
            available = json.load(source)
        if not available.get("models") or not available.get("tool"):
            raise ValueError("needs 'tool' and a non-empty 'models' list")
    except (OSError, ValueError) as error:
        print(f"bad available file: {error}", file=sys.stderr)
        return 2
    report, problem = load_report(options["report"], today)
    if report is None:
        print(f"{problem}; use the fallback in model-selection.md", file=sys.stderr)
        return 3
    candidates, excluded, matches = build_candidates(available, report)
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
    text = render(available, report, metric, cost_field, best, tiers, scored, excluded, matches)
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
