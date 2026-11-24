#!/usr/bin/env python3
"""Run one phase of a plan end to end: revise, build each stage, review, finish.

Usage:
  run-phase.py PHASE_DIR [--repo DIR] [--profiles PATH] [--work DIR]
               [--instructions PATH]... [--subject-suffix TEXT]
               [--extra-trailer LINE]...

PHASE_DIR is a plan's phase folder NN-name, holding phase.json and one stage
file per stage. The driver prints a report: each stage and its result, the
review findings, the questions, the halt if any, and that Codex is off.

When a step cannot go on, the driver writes a halt into phase.json's record,
{step, stage, reason, detail, next}, re-renders the plan and stops. `next`
says what the session does before rerunning; a rerun clears the halt and
resumes from the records.

In this version the review is a mock and the phase is not finished: the
driver revises, starts and builds the stages.

Exit codes: 0 built; 10 halted (the halt is in phase.json's record); 2 usage.
"""

import argparse
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("plan_check", os.path.join(HERE, "plan-check.py"))
plan_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_check)
_spec = importlib.util.spec_from_file_location("build_check", os.path.join(HERE, "build-check.py"))
build_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(build_check)

# What the session does about each halt before rerunning the driver.
NEXT = {
    "revise-failed": "Read the detail (the reviser's report and plan-check.py's errors, or build-check.py "
                     "start's refusal), correct the stage files by revising.md "
                     "or clean the working tree, then rerun.",
    "escalated": "The reviser says the problem is above this phase: settle it with the user in the spec, the "
                 "design or the plan, revise the stage files to match, then rerun.",
    "revise-capped": "The stage was revised twice for failures in this run, or the reviser found nothing to "
                     "change after a used-up ladder: go through its attempts and its brief with the user, revise "
                     "the brief and raise its revision, then rerun.",
    "builder-stopped": "Read the builder's report: correct the brief it could not build and raise its "
                       "revision, then rerun.",
    "brief-changed": "A brief changed without a higher revision: raise the stage's revision or restore the "
                     "brief, then rerun.",
    "record-changed": "A model call changed a record, which only the scripts write; the driver has already "
                      "restored it. Check that step's directions, named in the detail, with the user, then rerun.",
    "models-stale": "Refresh the model profiles as model-selection.md says, then rerun.",
    "session-only": "Build, record and commit the stage in the session before rerunning: a rerun restores "
                    "uncommitted stage files.",
    "build-error": "The build failed for a reason that is not the model's (sign-in, service): clear the "
                   "cause in the detail, then rerun.",
    "review-capped": "The review call stopped at its cost cap, so there is no usable review.json: tell the "
                     "user, and rerun when they agree; the review runs again.",
    "review-invalid": "review.json does not match review.schema.json: delete it, then rerun so the phase is "
                      "reviewed again.",
    "plan-gap": "A review finding is a gap in the plan: revise the stage files by revising.md to cover it, "
                "then rerun.",
    "question": "A review finding is a question: answer it with the user, revise the plan by revising.md "
                "if the answer needs it, then rerun; the driver marks the finding answered.",
    "fix-failed": "The fix for a review finding failed: revise the stage's brief and raise its revision so "
                  "the driver rebuilds it, or settle the finding with the user, then rerun.",
}


def set_halt(pdir, plan_dir, halt):
    """Write the halt (None clears it) into phase.json's record and re-render the plan."""
    path = os.path.join(pdir, "phase.json")
    pj = plan_check.read_json(path)
    build_check.save(path, {**pj, "record": {**pj["record"], "halt": halt}})
    plan_check.render_plan(plan_dir)


SKILLS = os.path.join(os.path.dirname(HERE), "skills")
REVISE_GUIDE = os.path.join(SKILLS, "implement-in-phases", "revise-guide.md")
STAGE_BUILDER = os.path.join(SKILLS, "implement-in-phases", "stage-builder.md")
MAX_REVISIONS = 2  # failure-driven revisions of one stage in a run before the user is asked


class Halt(Exception):
    """A step cannot go on: the reason (a key of NEXT), the detail, and where it happened."""

    def __init__(self, reason, detail, step="revise", stage=None):
        super().__init__(reason, detail)
        self.reason, self.detail, self.step, self.stage = reason, detail, step, stage


# ---- tools

def sh(*cmd):
    return subprocess.run([str(x) for x in cmd], capture_output=True, text=True)


def py(script, *args):
    return sh(sys.executable, os.path.join(HERE, script), *args)


def last(text):
    lines = [x for x in text.splitlines() if x.strip()]
    return lines[-1].strip() if lines else ""


def must(r, what, ok=(0,)):
    """The finished command, or a halt: brief-changed for exit 5, build-error for any other exit not in OK."""
    if r.returncode == 5:
        raise Halt("brief-changed", r.stdout.strip() or last(r.stderr))
    if r.returncode not in ok:
        raise Halt("build-error", f"{what}: {last(r.stderr) or last(r.stdout)}")
    return r


def restore(c, paths=None):
    """Put PATHS back as HEAD has them; by default every uncommitted path but the plan's and the preexisting ones."""
    if paths is None:
        kept = plan_check.read_json(os.path.join(c.pdir, "phase.json"))["record"].get("preexisting", [])
        plan_rel = build_check.rel(c.top, c.plan_dir)
        paths = [p for p in build_check.changed_paths(c.top) if p not in kept
                 and not build_check.is_cache(p) and not build_check.in_dir(p, plan_rel)]
    for p in paths:
        if sh("git", "-C", c.top, "cat-file", "-e", f"HEAD:{p}").returncode == 0:
            build_check.git(c.top, "restore", "--source=HEAD", "--staged", "--worktree", "--", p)
        else:
            build_check.git(c.top, "rm", "-q", "--cached", "--ignore-unmatch", "--", p)
            if os.path.lexists(os.path.join(c.top, p)):
                os.remove(os.path.join(c.top, p))


def plan_docs(plan_dir):
    """{path: content} of every phase.json and stage file of the plan."""
    dirs = [os.path.join(plan_dir, ph["dir"]) for ph in plan_check.read_json(os.path.join(plan_dir, "plan.json"))["phases"]]
    return {os.path.join(d, n): plan_check.read_json(os.path.join(d, n))
            for d in dirs for n in ["phase.json"] + plan_check.stage_files(d)}


def guard(before, keep_briefs):
    """Undo what a model call may not change in the plan: (a record changed, a brief changed and was restored)."""
    def now(path):
        try:
            doc = plan_check.read_json(path)
        except (OSError, ValueError):
            return None
        return doc if isinstance(doc, dict) else None
    after = {p: now(p) for p in before}
    for p, old in before.items():
        new = after[p]
        right = old if new is None or keep_briefs else {**new, "record": old["record"]}
        if right != new:
            build_check.save(p, right)
    records = any(after[p] is None or after[p].get("record") != old["record"] for p, old in before.items())
    briefs = keep_briefs and any(after[p] is not None and after[p].get("brief") != old["brief"]
                                 for p, old in before.items())
    return records, briefs


def route(c, *options):
    r = must(py("select-models.py", "route", c.available, *c.profiles, *options), "route")
    return json.loads(r.stdout)


def call(c, label, guide, inputs, pair, keep_briefs):
    """One model call through claude-build.sh: {exit, tokens, cost, line (the report's last), stderr, edited}."""
    out = os.path.join(c.work, f"{len(os.listdir(c.work)) + 1:02d}-{label}")
    os.makedirs(out)
    prompt = os.path.join(out, "prompt.md")
    with open(guide) as g, open(prompt, "w") as f:
        f.write(g.read() + "\n## Inputs\n\n" + "\n".join(inputs) + "\n")
    before = plan_docs(c.plan_dir)
    r = sh("sh", os.path.join(HERE, "claude-build.sh"), c.top, prompt, pair["model"], pair["effort"],
           pair["cap_usd"], out)
    records, briefs = guard(before, keep_briefs)
    if records:
        raise Halt("record-changed", f"the {label} call changed a record; its directions: {guide}")
    printed = dict(re.findall(r"^(Tokens|Cost): (\S+)$", r.stdout, re.MULTILINE))
    report_path = os.path.join(out, "report.md")
    text = open(report_path).read() if os.path.isfile(report_path) else ""
    return {"exit": r.returncode, "tokens": printed.get("Tokens", "unknown"), "cost": printed.get("Cost", "unknown"),
            "line": last(text), "stderr": last(r.stderr), "edited": briefs}


def record(c, what, pair, res, *flags):
    return py("build-check.py", "record", c.pdir, what, "--tool", "claude-code", "--model", pair["model"],
              "--effort", pair["effort"], "--exit", res["exit"], "--tokens", res["tokens"], "--cost", res["cost"],
              "--cap", pair["cap_usd"], *(["--premium"] if pair["premium"] else []), *flags, "--repo", c.top)


# ---- steps. A step that cannot go on raises Halt.

def check_plan(c):
    number = next(ph["phase"] for ph in plan_check.read_json(os.path.join(c.plan_dir, "plan.json"))["phases"]
                  if ph["dir"] == os.path.basename(c.pdir))
    r = py("plan-check.py", c.plan_dir, "--repo", c.top, "--phase", number)
    if r.returncode:
        raise Halt("revise-failed", (r.stdout + r.stderr).strip())


def revise(c, problem):
    """Run the reviser on the phase and check its plan: 'revised' or 'unchanged'."""
    pair = route(c, "--scores", "J0F0R0C0K0P0V0S0", "--review")
    inputs = [f"- Phase folder: `{c.pdir}`", f"- Problem: {problem}", c.instructions,
              f"- The plugin's guides (absolute paths): `{os.path.join(SKILLS, 'plan-in-phases')}` holds "
              f"revising.md and the field guides; plan-check.py is `{os.path.join(HERE, 'plan-check.py')}`; "
              f"the repository is `{c.top}`"]
    res = call(c, "revise", REVISE_GUIDE, inputs, pair, False)
    if res["exit"] not in (0, 8):
        raise Halt("build-error", res["stderr"])
    must(record(c, "revise", pair, res), "record")
    word = re.fullmatch(r"Result: (revised|unchanged)", res["line"])
    if not word:  # an escalate line, or none
        raise Halt("escalated", res["line"] or "the reviser's report has no result line")
    check_plan(c)
    return word.group(1)


def pre_phase(c, stages):
    """Revise and start a phase not yet revised; check the plan while no stage has an attempt."""
    runs = plan_check.read_json(os.path.join(c.pdir, "phase.json"))["record"].get("runs", [])
    if not any(x["stage"] == "revise" for x in runs):
        started = py("build-check.py", "start", c.pdir, "--repo", c.top)
        if started.returncode:
            raise Halt("revise-failed", (started.stdout + started.stderr).strip())
        current = py("select-models.py", "check", os.path.join(c.plan_dir, "models.md"), *c.profiles)
        if current.returncode:
            raise Halt("models-stale", last(current.stdout + current.stderr))
        revise(c, "none")
    elif not any(s["record"].get("attempts") for s in stages.values()):
        check_plan(c)


def read_stages(pdir):
    return {n[:-5]: plan_check.read_json(os.path.join(pdir, n)) for n in plan_check.stage_files(pdir)}


def failed(c, sid, times, unchanged, why):
    """A stage that cannot be built on its revision: clean the tree and revise the phase for it."""
    restore(c)
    if times >= MAX_REVISIONS:
        raise Halt("revise-capped", f"stage {sid} was revised {times} times for failures in this run; then: {why}")
    if revise(c, f"stage {sid}: {why}") == "unchanged":
        raise Halt(unchanged, why)
    return "revised"


def build(c, sid, s, times):
    """One step on a stage, read from its record: a build ('built' or 'retry'), or a revision ('revised')."""
    brief, rec = s["brief"], s["record"]
    if brief.get("session_only"):
        raise Halt("session-only", f"stage {sid} is built in the session")
    tried = [x for x in rec.get("attempts", []) if x["revision"] == brief["revision"]]
    up = sum(x["result"] in ("failed", "rejected") for x in tried)
    down = sum(x["result"] == "stopped" for x in tried)
    if up and down:
        return failed(c, sid, times, "revise-capped", "its builds both failed and reached their budget")
    spent = must(py("build-check.py", "spend", c.pdir), "spend").stdout.strip()
    steps = ["--up", up] if up else ["--down", down] if down else []
    scores = "".join(f"{k}{brief['model_basis'][k]}" for k in "JFRCKPVS")
    pair = route(c, "--scores", scores, "--premium-spent", spent, *steps)
    # a ladder moved fewer steps than asked lands on a pair already tried, so can-try covers that too
    if must(py("build-check.py", "can-try", c.pdir, sid, pair["model"], pair["effort"]), "can-try", (0, 1)).returncode:
        return failed(c, sid, times, "revise-capped",
                      f"every model pair of its ladder was tried; the last attempt: {tried[-1]['why'] if tried else ''}")
    fix = bool(rec.get("commit"))  # reopened: rebuilt against the new brief as a fix
    earlier = [f"- Earlier commit: `{rec['commit']}` built this stage from an earlier brief; rebuild it "
               "against the brief in the packet"] if fix else []
    inputs = [c.instructions, "- Anything else the brief links to: none", *earlier, "- Stage packet:", "",
              plan_check.packet(c.plan_dir, sid)]
    res = call(c, f"build-{sid}", STAGE_BUILDER, inputs, pair, True)
    logged = record(c, sid, pair, res, *(["--fix"] if fix else []))
    if logged.returncode == 4:
        raise Halt("build-error", res["stderr"])
    accepted = must(logged, "record", (0, 1, 3)).returncode == 0
    stopped = re.match(r"Result: stopped:?\s*(.*)", res["line"])
    if stopped or (accepted and res["edited"]):
        why = "edited the plan" if not stopped else stopped.group(1) or "the builder stopped"
        if accepted:
            must(py("build-check.py", "reject", c.pdir, sid, why), "reject")
        return failed(c, sid, times, "builder-stopped", why) if stopped else "retry"
    if accepted:
        trailers = [x for line in c.a.extra_trailer for x in ("--extra-trailer", line)]
        must(py("build-check.py", "commit", c.pdir, sid, "--subject-suffix", c.a.subject_suffix, *trailers,
                "--repo", c.top), "commit")
        return "built"
    restore(c, json.loads(last(logged.stdout))["outside"])
    return "retry"


def stage_loop(c):
    """Build the stages not done, in id order: (the (step, stage, result) of each one built, the Halt or None)."""
    done, revisions = [], {}
    while True:
        stages = read_stages(c.pdir)
        todo = [sid for sid, s in stages.items() if plan_check.stage_status(s) != "done"]
        if not todo:
            return done, None
        sid = todo[0]
        try:
            result = build(c, sid, stages[sid], revisions.get(sid, 0))
        except Halt as h:
            restore(c)  # a rerun starts from a clean tree
            return done, Halt(h.reason, h.detail, "build", sid)
        if result == "built":
            done = done + [("build", sid, {"result": "built"})]
        if result == "revised":
            revisions = {**revisions, sid: revisions.get(sid, 0) + 1}


def review(a, pdir, sid):
    return {"result": "mock", "findings": [], "questions": []}


def report(name, done, halt):
    """The report's lines, from the (step, stage, result) of each step that ran."""
    listed = lambda items: [f"- {x}" for x in items] or ["none"]
    lines = [f"Phase {name}", "Stages:"]
    lines += listed(f"{sid}: {r['result']}" for step, sid, r in done if step == "build" and "halt" not in r)
    lines += ["Review findings:"] + listed(x for _, _, r in done for x in r.get("findings", []))
    lines += ["Questions:"] + listed(x for _, _, r in done for x in r.get("questions", []))
    if halt:
        lines += [f"Halt: {halt['reason']} at {halt['step']}" + (f" {halt['stage']}" if halt["stage"] else ""),
                  f"  {halt['detail']}", f"  Next: {halt['next']}"]
    else:
        lines += ["Halt: none"]
    return lines + ["Codex: off (driver version 1)"]


def run(a):
    pdir = os.path.realpath(a.phase_dir)
    plan_dir = os.path.dirname(pdir)
    # a rerun means the session has handled the halt; resuming reads the records only
    if plan_check.read_json(os.path.join(pdir, "phase.json"))["record"].get("halt"):
        set_halt(pdir, plan_dir, None)
    work = a.work or tempfile.mkdtemp(prefix="run-phase-")
    os.makedirs(work, exist_ok=True)
    c = SimpleNamespace(
        a=a, pdir=pdir, plan_dir=plan_dir, top=build_check.toplevel(a.repo), work=work,
        available=os.path.join(plan_dir, "models-available.json"),
        profiles=["--profiles", a.profiles] if a.profiles else [],
        instructions="- Project instructions: "
                     + (", ".join(f"`{os.path.abspath(p)}`" for p in a.instructions) or "none"))
    try:
        pre_phase(c, read_stages(pdir))
        done, stopped = stage_loop(c)
    except Halt as h:
        done, stopped = [], h
    halt = None
    if stopped:
        halt = {"step": stopped.step, "stage": stopped.stage, "reason": stopped.reason, "detail": stopped.detail,
                "next": NEXT[stopped.reason]}
        set_halt(pdir, plan_dir, halt)
    else:
        done = done + [("review", None, review(a, pdir, None))]
    print("\n".join(report(os.path.basename(pdir), done, halt)))
    return 10 if halt else 0


def parse_args(argv):
    p = argparse.ArgumentParser(prog="run-phase.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("phase_dir")
    p.add_argument("--repo", default=".")
    p.add_argument("--profiles")
    p.add_argument("--work")
    p.add_argument("--instructions", action="append", default=[])
    p.add_argument("--subject-suffix", default="")
    p.add_argument("--extra-trailer", action="append", default=[])
    a = p.parse_args(argv)
    if not os.path.isfile(os.path.join(a.phase_dir, "phase.json")):
        p.error(f"not a phase folder (no phase.json): {a.phase_dir}")
    return a


if __name__ == "__main__":
    sys.exit(run(parse_args(sys.argv[1:])))
