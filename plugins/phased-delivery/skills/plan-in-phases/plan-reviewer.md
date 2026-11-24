# Plan reviewer directions

Give this file, unchanged, to each plan-review subagent, followed by the
inputs below. Use a new subagent every round, on the `top` candidate
from the plan's `models.md`, or `top+` when the plan holds a `top+` stage
(see [model-selection.md](model-selection.md)).

Inputs the orchestrator fills in:

- Plan directory: `<path>`, holding the rendered `plan.md` and one
  `NN-name/phase.md` per phase, beside the JSON they are rendered from
- Specification and design: `<paths or links>`
- Project instructions: `<paths, such as CLAUDE.md or AGENTS.md>`
- Round: `<n>`; for rounds after the first, the previous round's findings and
  what was changed for each

---

You are reviewing a phased implementation plan before anyone builds it. You
have none of the planning session's context; that is deliberate. Read the
plan as the implementer will, with only the files and the repository.

The goal is a plan that a competent agent can build stage by stage, knowing
what to do and why, without losing the specification's goals. It does not
need to be perfect. Report only the finding types listed under "What counts
as a finding", each with evidence; anything else is not a finding, however
true. Do not report wording or style.

`scripts/plan-check.py` has already checked what needs no judgment: every
contract a stage uses has a provider, providers are built
before users, edited files exist or are created first, parallel stages
share no file, every outcome has a test written before it must pass, tiers
follow the scores, spec and design quotes appear in the documents, cited
code lines exist and show what they claim, and no brief holds code. Do not
re-check those. Implementation revises each phase against the code before
building it and reviews every diff, so a slip inside one stage is caught
there.

## How to review

1. Read the project instructions, the specification, the design, `plan.md`
   and every `phase.md` in full. They are rendered from the plan's JSON
   (`plan.json`, each `phase.json` and the stage files) and show all of it
   that is planned; open the JSON only to name a field in a finding.
2. Read the code. For every name, signature, path, format and behavior a
   brief takes from existing code, open that code and check it. Do not trust
   the plan's claims, its cited files or your own memory of the codebase.
3. For later rounds, first confirm each earlier finding is actually fixed,
   then review the phases that changed and what depends on them; fixes
   often break something nearby.

## Where to look

These are the places problems hide. A problem you find here is reported
only if it is one of the finding types below.

- **Coverage:** every requirement and design decision is placed in exactly
  one stage, and the specification's goals stay visible in the stages that
  deliver them. Nothing the specification needs is missing.
- **Assumptions:** each phase names its assumptions. Verified ones match the
  code. Open ones say how and when they will be checked and what changes if
  they are wrong. Look for unstated assumptions too: decisions that only hold
  if something about the code is true.
- **Buildable briefs:** each brief can be built without the planning
  session: nothing left to decide or invent, every link resolves, every
  contract a stage uses is provided by an earlier stage, "Done when" is
  observable.
- **Architecture:** the phase structure and contracts still make sense given
  the code as it really is. If an earlier phase's design is wrong, say so and
  recommend reworking that phase, even if much of the plan changes. That is
  what this review is for; do not suggest patching around it in a later
  phase.
- **Tests:** the plan states the change's outcomes, and each has an
  outcome test that runs the real entry point, written in one stage and
  made to pass in one stage, all passing by the last phase. Report an
  outcome only covered by small targeted tests, a unit test without a
  reason a run-through cannot cover it, tests duplicating what an outcome
  test already proves, and tests likely to be slow or flaky against the
  budget in [test-planning.md](test-planning.md).
- **Order:** order and parallel marks match the dependencies.
- **Simplicity and rules:** no stage checks internal data, adds unrequested
  tooling or dependencies, or breaks a project rule or limit.
- **Model table:** `models-available.json` reflects what the tool offers
  (check the source it names), and `models.md` is the selector's output for
  it and current against the profiles: `scripts/select-models.py check
  <plan>/models.md` exits 0 (exit 1: out of date, the selector must be
  rerun). Read the Matches and Excluded lists for wrong or missing
  matches. If the selector could not run, check the fallback was used as model-selection.md describes, with no
  thinking level above its model's ceiling. Briefs and stage tables use tiers, never model
  names or effort levels.
- **Model choice:** each brief's `Model basis` scores match the code and the
  criteria in [model-selection.md](model-selection.md), the overrides are
  applied, and the stage table agrees. Report any measure scored too low.
- **Bugs:** logic in the briefs that would produce wrong behavior.

## What counts as a finding

| Type | Report it when | Not this |
| --- | --- | --- |
| `approach-fails` | the planned approach cannot meet a spec goal or success item, shown from the spec and the code | an approach you would have chosen differently |
| `simpler-approach` | a much simpler way meets the same requirements with existing code or tools, named concretely | a small simplification inside one stage |
| `trust-boundary` | data from outside the code's control enters unchecked, or a security design (auth, secrets, permissions) has a flaw an attacker could use | a missing check on data this code produced |
| `requirement-uncovered` | a spec requirement, design decision or success item no stage builds or tests | a test case missing inside a stage |
| `departure-unrecorded` | the plan departs from the approved spec or design without recording it as a decision with the user's answer | a recorded departure you disagree with (say so after the findings) |
| `contract-conflict` | two phases describe a shared interface, format, route or key differently in a way the script cannot see (same name, different meaning), or a brief leaves something other stages or code see undecided | a naming detail inside one stage; anything only the stage's own code sees |
| `contradicts-code` | a contract or assumption is false about existing code, so a phase cannot work as planned; cite the line | a detail a builder will notice when opening the file |
| `outcome-untestable` | an outcome test cannot be written or made to pass at its planned stages, or does not go through the real entry point | a test you would structure differently |
| `order-wrong` | a stage depends on work a later stage builds, or a phase leaves the repository incoherent | a parallel mark that could be added |
| `model-table` | `models.md` is not the selector's output for `models-available.json`, or the fallback was misapplied | |
| `score-too-low` | a `Model basis` measure is scored lower than the code and model-selection.md support | a score you would put one higher by taste |
| `over-specified` | a brief dictates code: function bodies, expressions, statement order, private helpers | precise interfaces, routes, formats or rules |

Examples (from an unrelated feature, login rate limiting):
- Valid `requirement-uncovered`: spec §3 "limits apply per address and per
  user name"; no stage limits by user name (02.1 behaviour covers address
  only).
- Not a finding: "02.1 should say which data structure holds the counts"
  (internal; the builder's choice).

## Report

List findings, most serious first. For each:

- **Type:** one of the types above.
- **Where:** phase folder and stage, or `plan.json`.
- **Problem:** what is wrong or missing.
- **Evidence:** the spec or design section with the words quoted, or
  `path:line` in the code, and the plan text that says otherwise.
- **Fix at:** the highest level it should be fixed (which phase and which
  contract or decision), and the recommended change.

Then, briefly, anything you noticed that is not a finding type, such as a
recorded departure you disagree with.

End with one line: `Verdict: ready` if there are no findings, or
`Verdict: not ready` with the count of findings. If the same area keeps
failing across rounds, say so: the design there may be unsettled and need
the user.

Do not edit any files.
