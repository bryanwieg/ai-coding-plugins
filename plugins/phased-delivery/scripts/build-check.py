#!/usr/bin/env python3
"""Gate, record and commit the stages of a phase for implement-in-phases.

Usage:
  build-check.py start PHASE_FILE [--repo DIR]
  build-check.py can-try PHASE_FILE STAGE MODEL EFFORT
  build-check.py record PHASE_FILE STAGE|review --tool T --model M --effort E
                 --exit N --tokens X --cost Y [--cap USD] [--tool-calls N]
                 [--premium] [--fix] [--repo DIR]
  build-check.py reject PHASE_FILE STAGE WHY
  build-check.py commit PHASE_FILE STAGE [--subject-suffix TEXT]
                 [--extra-trailer LINE]... [--repo DIR]
  build-check.py spend PHASE_FILE
  build-check.py finish PHASE_FILE [--stopped] [--repo DIR]

PHASE_FILE is a plan's NN-name.md. The script keeps its files next to it in
.build/: NN-revision.json (written by the orchestrator, revision.schema.json
in skills/implement-in-phases), NN-review.json (written by the phase
reviewer, review.schema.json) and NN-ledger.json (written here: the start
state and every attempt). --repo defaults to the current directory.

start     validates the revision and writes the ledger with HEAD and the
          paths already modified (kept as is when it exists: resume). Exit 1
          on an invalid revision or a stage file already modified.
can-try   exit 1 when the stage already has a non-error attempt on the pair.
record    logs an attempt and gates a build: no uncommitted path outside the
          scope rule, and every check command of the stage passes. Prints one
          JSON line {stage, attempt, result, outside, checks}. Exit 0
          accepted; 1 failed; 3 budget stop (build exit 8); 4 error (any
          other build exit: not a try of the pair). Stage "review" is logged
          for spend only.
reject    marks the stage's accepted, uncommitted attempt rejected.
commit    commits the stage's changed files with the stage trailers and
          marks the stage done in the phase file (working tree only).
spend     prints the premium spend: costs of --premium attempts (cap when
          the cost is unknown), as a bare number.
finish    validates the review, sets "Status: built <commit>" and commits
          the phase file's directory with a Phase: trailer. --stopped skips
          the review and status and only commits the directory.

Exit codes not listed: 0 done; 1 refused (one JSON line per problem for
invalid JSON); 2 bad usage or a missing file.
"""

import argparse
import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SKILL = os.path.join(HERE, "..", "skills", "implement-in-phases")
_spec = importlib.util.spec_from_file_location("plan_check", os.path.join(HERE, "plan-check.py"))
plan_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_check)


class Usage(Exception):
    pass


def paths(phase_file):
    if not os.path.isfile(phase_file):
        raise Usage(f"no phase file: {phase_file}")
    num = os.path.basename(phase_file)[:2]
    if not num.isdigit():
        raise Usage(f"phase file must be named NN-name.md: {phase_file}")
    build = os.path.join(os.path.dirname(os.path.abspath(phase_file)), ".build")
    return {k: os.path.join(build, f"{num}-{k}.json") for k in ("revision", "review", "ledger")}


def load_checked(path, schema_name, label):
    """Return (data, problems); problems are printed as JSON lines by the caller."""
    if not os.path.isfile(path):
        raise Usage(f"missing {path}")
    try:
        data = json.load(open(path))
    except ValueError as e:
        return None, [{"file": label, "where": "/", "msg": f"not valid JSON: {e}"}]
    schema = json.load(open(os.path.join(SKILL, schema_name)))
    errs = plan_check.validate(data, schema)
    return (None if errs else data), [{"file": label, "where": w or "/", "msg": m} for w, m in errs]


def report(problems):
    for p in problems:
        print(json.dumps(p))
    return 1 if problems else 0


# ---- subcommands (mock bodies until phase 02)

def cmd_start(a):
    f = paths(a.phase_file)
    _, problems = load_checked(f["revision"], "revision.schema.json", "revision")
    if problems:
        return report(problems)
    os.makedirs(os.path.dirname(f["ledger"]), exist_ok=True)
    if not os.path.exists(f["ledger"]):
        json.dump({"start_commit": "", "preexisting": [], "attempts": []}, open(f["ledger"], "w"), indent=1)
    return 0


def cmd_can_try(a):
    paths(a.phase_file)
    return 0


def cmd_record(a):
    paths(a.phase_file)
    print(json.dumps({"stage": a.stage, "attempt": 1, "result": "accepted", "outside": [], "checks": []}))
    return 0


def cmd_reject(a):
    paths(a.phase_file)
    return 0


def cmd_commit(a):
    paths(a.phase_file)
    print("0000000")
    return 0


def cmd_spend(a):
    paths(a.phase_file)
    print("0.00")
    return 0


def cmd_finish(a):
    f = paths(a.phase_file)
    if not a.stopped:
        _, problems = load_checked(f["review"], "review.schema.json", "review")
        if problems:
            return report(problems)
    return 0


def number(text):
    if text == "unknown":
        return None
    try:
        return float(text)
    except ValueError:
        raise argparse.ArgumentTypeError(f"not a number or 'unknown': {text}")


def parse_args(argv):
    p = argparse.ArgumentParser(prog="build-check.py", description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("start")
    s.add_argument("phase_file")
    s.add_argument("--repo", default=".")
    s = sub.add_parser("can-try")
    for k in ("phase_file", "stage", "model", "effort"):
        s.add_argument(k)
    s = sub.add_parser("record")
    s.add_argument("phase_file")
    s.add_argument("stage")
    for k in ("--tool", "--model", "--effort"):
        s.add_argument(k, required=True)
    s.add_argument("--exit", type=int, required=True, dest="exit_code")
    s.add_argument("--tokens", type=number, required=True)
    s.add_argument("--cost", type=number, required=True)
    s.add_argument("--cap", type=number)
    s.add_argument("--tool-calls", type=number)
    s.add_argument("--premium", action="store_true")
    s.add_argument("--fix", action="store_true")
    s.add_argument("--repo", default=".")
    s = sub.add_parser("reject")
    for k in ("phase_file", "stage", "why"):
        s.add_argument(k)
    s = sub.add_parser("commit")
    s.add_argument("phase_file")
    s.add_argument("stage")
    s.add_argument("--subject-suffix", default="")
    s.add_argument("--extra-trailer", action="append", default=[])
    s.add_argument("--repo", default=".")
    s = sub.add_parser("spend")
    s.add_argument("phase_file")
    s = sub.add_parser("finish")
    s.add_argument("phase_file")
    s.add_argument("--stopped", action="store_true")
    s.add_argument("--repo", default=".")
    return p.parse_args(argv)


COMMANDS = {"start": cmd_start, "can-try": cmd_can_try, "record": cmd_record, "reject": cmd_reject,
            "commit": cmd_commit, "spend": cmd_spend, "finish": cmd_finish}


def main(argv):
    a = parse_args(argv)
    try:
        return COMMANDS[a.cmd](a)
    except Usage as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
