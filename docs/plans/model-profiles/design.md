# Model profiles and per-stage routing: design

Agreed with the user on 2026-11-23. The plan in this folder builds it.

## Refresh

The model data is reassessed only when models change. A weekly job fetches
the Artificial Analysis report and rebuilds only when the Claude or OpenAI
model list or a price changes; a change to scores alone is ignored. The
assessment is cached in the plugin, keyed by a fingerprint of the model
list and prices, until the next change. This replaces the 7-day staleness
rule and the rerun of the selector before every phase.

## Profiles

Each model and thinking level gets stored properties in JSON, from the
Artificial Analysis fields only: intelligence and engineering scores,
benchmark run cost, input and output price, speed, a premium or standard
price class, and the score gained and cost multiplied by each step up in
thinking level. Context window is recorded when the data has it.

## Routing

The selector routes each stage from its J F R C K P V S scores, not from
the tier alone. Rules, from the research on thinking levels:

- Candidates are model and thinking-level pairs on the score/cost frontier:
  a pair another beats on both score and cost is never chosen.
- A thinking step that gains under 2 points for more than 1.5 times the
  cost is excluded.
- Mechanical stages above the small tier run at medium thinking or below;
  small stages keep the small model's higher levels.
- Design and shared-contract stages (J2, C2) move up the model before the
  thinking level.
- Long or wide stages (S2, R2, F2) run at high thinking or below, and
  prefer a clearly faster model (1.2 times the speed) when scores are close.
- Risk (K of 1 or more) raises the score floor.
- Below the top tier a premium pair is used only when it costs no more
  than the standard pick and scores at least as well, or when the standard
  pairs cannot give a step up the stage asked for; then the cheapest pair
  above the standard pick, the next model up at low thinking (added
  2026-11-23).
- Small models may use higher thinking levels, within their ceilings.

Tiers stay in plans as a summary, so a plan still moves between tools.

## Limits

- Premium models: $10 per phase.
- Tokens per stage: 150k for small, 400k for middle, 1M for top.
- The token cap is enforced as a dollar cap: the cap's tokens times the
  pair's input price.
- A stage that hits its cap is retried one step down the frontier, which
  may be a smaller model or a lower thinking level.
- Once premium spend reaches the phase budget, builds leave premium pairs
  out for the rest of the phase.
- Claude stage builds run headless through claude-build.sh with a budget
  cap, like codex-build.sh, so a runaway is stopped, not just counted.
  File edits are allowed and commands follow the project's own permission
  rules, unless CLAUDE_BUILD_PERMISSIONS says otherwise.
- Phase reviews always run on top. Their cost is counted against the
  premium budget, but they never drop a step.

## Outcomes

1. The weekly refresh changes the cached files only when the model list or
   a price changes.
2. The selector accepts cached profiles of any age, and models.md is reused
   while the model list is unchanged.
3. The selector returns one model and thinking level per stage from the
   frontier, without beaten pairs or low-gain thinking steps.
4. claude-build.sh builds a stage headless with a budget cap and stops a
   runaway with its own exit code.
5. After a stage hits its cap the next build goes one step down the
   frontier; once premium spend reaches the phase budget, builds use no
   premium pair. Reviews still run on top.
6. The stage's scores shape the pick: thinking caps for mechanical and long
   or wide stages, larger models at lower thinking for design work, faster
   models for long work, a higher floor for risk.
7. Codex availability is checked at most once a day; once found off, it is
   cached and Codex is not considered for the rest of the day.
8. Every session started that day tells the agent at once that Codex is
   off.

## Codex availability

Added 2026-11-23: check whether Codex is available once a day or at
session start, cache the result, and when it is off leave Codex out of
planning and building entirely for the rest of the session and day.
Not being signed in counts as off; after signing in, the user turns Codex
back on with `codex-usage.py --recheck`.

## Later

A paid eval run calibrates the 2-point and 1.5x cutoffs and the routing
table; ask the user before running it.
