# Phase 02: Route by usage

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md); Codex
builders in [models-codex.md](models-codex.md).
Status: planned
Before: phase 01 built `scripts/claude-usage.py` (exit 0 on pace, 1 ahead
of pace, 2 nearly out, 3 no data, 4 bad arguments) and the status line
capture. Routing sends only narrow stages (F = 0, R = 0) to Codex.
After: the skills route stages by both tools' usage on the scale below,
stop the phase when both are nearly out, and the README and
`docs/model-routing.md` describe it. Plugin version 0.5.0.

## The routing rule (contract for both stages)

Checked before **every** stage dispatch and before the phase review, only
when the plan has `models-codex.md` and the session is not Codex. Run
`scripts/claude-usage.py` (Claude level) and `scripts/codex-usage.py`
(Codex room: exit 0 means room; any other exit means no room).

| Claude level (exit) | Codex has room | Codex has no room |
| --- | --- | --- |
| on pace (0) or no data (3) | narrow stages (F = 0, R = 0) to Codex | build in session |
| ahead of pace (1) | stages with F <= 1 and R <= 1 to Codex | build in session |
| nearly out (2) | every build stage **and** the phase review to Codex | stop and report |

- Codex builds use the tier's candidate in `models-codex.md`; a Codex review
  uses its `top` candidate, through `scripts/codex-build.sh` with
  phase-reviewer.md as the prompt file.
- **Stop and report:** finish and commit the stage in progress, update the
  phase status line and Notes, commit them, and stop. Report the stages
  done and left and both scripts' output lines (usage and reset times).
  When the stop comes at the check before the phase review, set
  `Status: in progress (stages done: all; review pending)`; resuming
  starts with the review, after checking the rule again.
- **Codex sign-in lapsed** (`codex-build.sh` exits 3, which arrives after
  dispatch): tell the user to run `codex login` again and build that stage
  in the session. At level 0 or 1, carry on as usual. At level 2, after
  committing that stage, stop and report as above, including the login
  message.
- Planning, plan revision, plan-review rounds and the orchestrator's own
  work stay in the session at every level; only stage builds and the phase
  review are routed. A stage that must write outside the repository stays
  in the session at every level (`codex-build.sh` can write only the
  repository and /tmp).
- Without `models-codex.md` (no Codex), nothing changes from today.
- When the level changes during a phase, record it in the phase's Notes
  with both scripts' output lines.

## Assumptions
- Verified: routing lives in
  `plugins/phased-delivery/skills/plan-in-phases/model-selection.md`,
  section "Builders in another tool" (lines 186–210, ends before "Adjust
  while working"), and in
  `plugins/phased-delivery/skills/implement-in-phases/SKILL.md`, the
  paragraph starting "When the plan has `models-codex.md`" (lines 63–70);
  the review is in "### 3. Review the phase" (lines 114–125).
- Verified: `scripts/codex-build.sh REPO PROMPT MODEL EFFORT OUTDIR` takes any
  prompt file and runs Codex with workspace write access, so it can run a
  review unchanged; it prints `Tokens: N` and exits 3 on lapsed sign-in.
- Verified: `scripts/codex-usage.py` exits 0 room, 1 over its cutoffs, 2 no
  data; no data counts as no room. Phase 01 stage 01.3 makes it ignore
  windows that have reset, so a stale "over" cannot stop a phase for good.
- Verified: user-facing descriptions are README.md "### Building with Codex
  from Claude Code" (lines 88–98) and `docs/model-routing.md` "## Part 2"
  (lines 72–99) and the open question "Quota-aware failover" (in "## Open
  questions and next steps"); plugin version is in
  `plugins/phased-delivery/.claude-plugin/plugin.json` (`0.4.0`).
- Verified: copies under `evals/tasks/*/reference` and `.claude/worktrees/`
  are eval fixtures and other branches; they are not changed.
- Open: none.

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 02.1 | Skills route by usage per the rule above | middle+ | first | planned |
| 02.2 | README, routing doc and version describe it | middle+ | after 02.1 | planned |

## 02.1 Skill routing rules

Goal: model-selection.md and implement-in-phases/SKILL.md state the routing
rule above, and the implementer follows it before every dispatch and the
review.

Context: the routing rule section of this file is the whole decision; the
current text it replaces is cited in Assumptions. `claude-usage.py`'s
docstring (phase 01) lists its exit codes.

Contracts: the routing rule above, unchanged. Keep these existing rules:
Codex only when the session is not Codex and Codex is installed and signed
in; `models-codex.md` must have a candidate for the tier; plan-time
generation of `models-available-codex.json` and `models-codex.md`.

Files:
- `plugins/phased-delivery/skills/plan-in-phases/model-selection.md`
- `plugins/phased-delivery/skills/implement-in-phases/SKILL.md`
- `plugins/phased-delivery/skills/implement-in-phases/phase-reviewer.md`
  (orchestrator header only, above its `---`)

Work:
1. model-selection.md, "Builders in another tool": replace the "Send a stage
   to Codex only when all hold" list and the line after it with the routing
   table, its bullets, and one sentence on why width still caps routing
   until Claude is nearly out (Codex loses track across many files). Keep
   the plan-time bullet; replace the `codex-build.sh` exit 3 bullet with the
   rule's "Codex sign-in lapsed" bullet. Change the
   "Fixed choices" line "Reviews use the `top` candidate" to add: of
   `models-codex.md` when the routing rule sends the review to Codex.
2. SKILL.md, the paragraph "When the plan has `models-codex.md`": say both
   usage scripts run before each stage dispatch, then route by "Builders in
   another tool"; drop the restated narrow rule there (the table owns it).
   Keep the prompt-file and `codex-build.sh` instructions.
3. SKILL.md, "### 3. Review the phase": add that the review goes to Codex's
   `top` candidate through `codex-build.sh` when the routing rule says so.
4. SKILL.md, "### 4. Commit and stop": add that a stop from the routing rule
   reports both scripts' output lines and the stages left, and the
   review-pending status and resume rule.
5. phase-reviewer.md header: change "Use the `top` candidate from the plan's
   `models.md`" to add "or from `models-codex.md` when the routing rule in
   model-selection.md sends the review to Codex". Nothing below `---`
   changes.

External inputs: none.

Done when:
- Reading both files, every cell of the routing table and every bullet
  under it appears once, in model-selection.md, and SKILL.md points to it.
- `grep -rn 'F = 0 and R = 0' plugins/phased-delivery/skills/implement-in-phases`
  finds nothing (the narrow rule is no longer restated there).
- `grep -rln claude-usage.py plugins/phased-delivery/skills` lists both
  files.
- `grep -rn 'F <= 1' plugins/phased-delivery/skills/plan-in-phases/model-selection.md`
  finds the ahead-of-pace row (write the bound as `F <= 1 and R <= 1` or in
  the table cell as `F <= 1, R <= 1`).

Out of scope: scripts, README, docs, plan-in-phases/SKILL.md, eval copies.

Model basis: J1 F1 R1 C1 K0 P1 V2 S0 = 7 -> middle; override 3 (V = 2) ->
middle+. (F1: three files.)

## 02.2 Docs and version

Goal: README and `docs/model-routing.md` describe usage-based routing and
its setup, and the plugin version is 0.5.0.

Context: 02.1's text in model-selection.md is the rule to describe;
phase 01's 01.2 has the `statusLine` setting to document.

Contracts: the routing rule above; the `statusLine` command from
01-claude-usage.md stage 01.2.

Files:
- `README.md`
- `docs/model-routing.md`
- `plugins/phased-delivery/.claude-plugin/plugin.json`

Work:
1. README "### Building with Codex from Claude Code": describe the three
   levels in a few lines, the stop when both are nearly out, and the setup:
   the `statusLine` command from 01.2's Contracts (plain shell form), with
   a sentence that `bash "$d/ponytail-statusline.sh" < "$t"` stands for the
   user's own status line command, which reads `< "$t"`, or is dropped if
   they have none. Say it needs a Pro/Max/Ultra plan and that without it
   routing stays as before.
2. `docs/model-routing.md` Part 2, "How it works now": replace the bullets
   "A stage goes to Codex only when it is **narrow** ..." and "Planning and
   reviews stay in the session's tool on `top`." (lines 88–92) with the
   routing summary, and replace "Claude usage is not visible to
   the agent" with how it is read now (status line JSON, freshness as of the
   last refresh in any session) and summarize the routing table, citing
   `model-selection.md`. In "Open questions", replace "Quota-aware failover"
   with what remains: tuning the thresholds from work reports.
3. plugin.json: `"version": "0.5.0"`.

External inputs: none.

Done when:
- `jq -r .version plugins/phased-delivery/.claude-plugin/plugin.json`
  prints `0.5.0`.
- `grep -n 'not visible to the agent' docs/model-routing.md` finds nothing.
- `grep -n 'only when it is \*\*narrow\*\*' docs/model-routing.md` finds
  nothing.
- `grep -n claude-usage README.md docs/model-routing.md` finds both.

Out of scope: skills, scripts, eval copies, worktrees.

Model basis: J1 F1 R1 C0 K0 P1 V2 S0 = 6 -> middle; override 3 (V = 2) ->
middle+.

## Notes
- 2026-11-20: review round 3: stages writing outside the repository stay
  in the session.
- 2026-11-20: review round 2: review-pending stop status; plan reviews
  stay in session; phase-reviewer.md header added to 02.1; 02.2 names the
  stale Part 2 lines.
- 2026-11-20: review round 1: lapsed Codex sign-in rule made explicit;
  02.1 checks use `grep -r`; README setup uses 01.2's command.
- 2026-11-20: Codex "no data" (codex-usage.py exit 2) stays "no room", as
  today; a fresh Codex install never gets work until it has run once.
