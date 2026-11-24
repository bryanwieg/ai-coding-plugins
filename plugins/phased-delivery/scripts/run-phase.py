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

In this version every step is a mock that returns a fixed result: nothing is
built, reviewed or committed.

Exit codes: 0 built; 10 halted (the halt is in phase.json's record); 2 usage.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("plan_check", os.path.join(HERE, "plan-check.py"))
plan_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_check)

# What the session does about each halt before rerunning the driver.
NEXT = {
    "revise-failed": "Read the reviser's report and plan-check.py's errors, correct the stage files by "
                     "revising.md until plan-check.py passes, then rerun.",
    "escalated": "The reviser says the problem is above this phase: settle it with the user in the spec, the "
                 "design or the plan, revise the stage files to match, then rerun.",
    "revise-capped": "The stage failed after two revisions: go through its attempts and its brief with the "
                     "user, revise the brief and raise its revision, then rerun.",
    "builder-stopped": "Read the builder's report: correct the brief it could not build and raise its "
                       "revision, then rerun.",
    "brief-changed": "A brief changed without a higher revision: raise the stage's revision or restore the "
                     "brief, then rerun.",
    "record-changed": "A model call changed a record, which only the scripts write: restore the record from "
                      "git, then rerun.",
    "models-stale": "Refresh the model profiles as model-selection.md says, then rerun.",
    "session-only": "Build, record and commit the stage in the session before rerunning: a rerun restores "
                    "uncommitted stage files.",
    "build-error": "The build failed for a reason that is not the model's (sign-in, service): clear the "
                   "cause in the detail, then rerun.",
    "review-capped": "The review still has findings after its last round: decide each with the user, fix or "
                     "revise, then rerun.",
    "review-invalid": "review.json does not match review.schema.json: delete it, then rerun so the phase is "
                      "reviewed again.",
    "plan-gap": "A review finding is a gap in the plan: revise the stage files by revising.md to cover it, "
                "then rerun.",
    "question": "A review finding is a question: answer it with the user and set the finding's status to "
                "answered in phase.json's record, then rerun.",
    "fix-failed": "The fix for a review finding failed: fix the finding in the session or revise the stage, "
                  "then rerun.",
}


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def set_halt(pdir, plan_dir, halt):
    """Write the halt (None clears it) into phase.json's record and re-render the plan."""
    path = os.path.join(pdir, "phase.json")
    pj = plan_check.read_json(path)
    save(path, {**pj, "record": {**pj["record"], "halt": halt}})
    plan_check.render_plan(plan_dir)


# ---- steps: mocks, each returning a fixed result. A step that cannot go on returns
# {"halt": reason, "detail": text} instead.

def revise(a, pdir, sid):
    return {"result": "mock"}


def build(a, pdir, sid):
    return {"result": "mock"}


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
    steps = ([("revise", None, revise)]
             + [("build", n[:-5], build) for n in plan_check.stage_files(pdir)]
             + [("review", None, review)])
    done, halt = [], None
    for step, sid, fn in steps:
        result = fn(a, pdir, sid)
        done = done + [(step, sid, result)]
        if "halt" in result:
            halt = {"step": step, "stage": sid, "reason": result["halt"], "detail": result["detail"],
                    "next": NEXT[result["halt"]]}
            set_halt(pdir, plan_dir, halt)
            break
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
