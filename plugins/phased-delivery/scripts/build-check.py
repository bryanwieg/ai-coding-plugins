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
import subprocess
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


# ---- repository and ledger

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode:
        raise Usage(f"git {' '.join(args)}: {r.stderr.strip()}")
    return r.stdout


def toplevel(repo):
    return git(repo, "rev-parse", "--show-toplevel").strip()


def changed_paths(top):
    """Uncommitted paths against HEAD, untracked included and ignored files left out."""
    out = git(top, "status", "--porcelain", "-z", "--untracked-files=all").split("\0")
    found, i = [], 0
    while i < len(out):
        entry = out[i]
        i += 1
        if not entry:
            continue
        found.append(entry[3:])
        if entry[0] in "RC":
            i += 1  # the rename's source path follows
    return found


def is_cache(path):
    parts = path.split("/")
    return "__pycache__" in parts or ".pytest_cache" in parts or path.endswith(".pyc")


def load(path):
    return json.load(open(path))


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def stage_files(revision, stage):
    for s in revision["stages"]:
        if s["id"] == stage:
            return [f["path"] for f in s["files"]]
    raise Usage(f"stage {stage} is not in the revision")


def committed_stages(ledger):
    return {a["stage"] for a in ledger["attempts"] if a["result"] == "accepted" and a["commit"] and not a["fix"]}


def outside_paths(top, phase_file, revision, ledger, stage):
    plan_dir = os.path.relpath(os.path.dirname(os.path.abspath(phase_file)), top)
    done = committed_stages(ledger)
    allowed = set(stage_files(revision, stage)) | set(ledger["preexisting"])
    for s in revision["stages"]:
        if s["id"] not in done:
            allowed |= {f["path"] for f in s["files"]}
    return [p for p in changed_paths(top)
            if p not in allowed and not is_cache(p) and not (p + "/").startswith(plan_dir + "/")]


def run_checks(top, commands):
    return [{"cmd": c, "exit": subprocess.run(["sh", "-c", c], cwd=top, capture_output=True).returncode}
            for c in commands]


def amount(x):
    return "unknown" if x is None else f"{x:.2f}"


def count(x):
    return "unknown" if x is None else str(int(x))


# ---- subcommands

def cmd_start(a):
    f = paths(a.phase_file)
    revision, problems = load_checked(f["revision"], "revision.schema.json", "revision")
    if problems:
        return report(problems)
    if os.path.exists(f["ledger"]):
        return 0
    top = toplevel(a.repo)
    now = changed_paths(top)
    dirty = [{"file": "revision", "where": s["id"], "msg": f"stage file already modified: {p}"}
             for s in revision["stages"] for p in stage_files(revision, s["id"]) if p in now]
    if dirty:
        return report(dirty)
    save(f["ledger"], {"start_commit": git(top, "rev-parse", "HEAD").strip(), "preexisting": now, "attempts": []})
    return 0


def ledger_of(f):
    if not os.path.exists(f["ledger"]):
        raise Usage(f"missing {f['ledger']}: run start first")
    return load(f["ledger"])


def cmd_can_try(a):
    ledger = ledger_of(paths(a.phase_file))
    for x in ledger["attempts"]:
        if (x["stage"], x["model"], x["effort"]) == (a.stage, a.model, a.effort) and x["result"] not in ("error", "review"):
            print(json.dumps(x))
            return 1
    return 0


def cmd_record(a):
    f = paths(a.phase_file)
    ledger = ledger_of(f)
    attempt = {"stage": a.stage, "n": 0, "fix": a.fix, "tool": a.tool, "model": a.model, "effort": a.effort,
               "exit": a.exit_code, "tokens": a.tokens, "cost": a.cost, "cap": a.cap,
               "tool_calls": a.tool_calls, "premium": a.premium, "result": "review", "why": "", "commit": ""}
    outside, checks, code = [], [], 0
    if a.stage != "review":
        revision = load(f["revision"])
        top = toplevel(a.repo)
        same = [x for x in ledger["attempts"] if x["stage"] == a.stage and x["fix"] == a.fix and x["result"] != "error"]
        attempt["n"] = len(same) + 1
        outside = outside_paths(top, a.phase_file, revision, ledger, a.stage)
        if a.exit_code == 8:
            attempt.update(result="stopped", why="budget reached")
            code = 3
        elif a.exit_code != 0:
            attempt.update(result="error", why=f"build exit {a.exit_code}", n=0)
            code = 4
        elif outside:
            attempt.update(result="failed", why="changed files outside the stage")
            code = 1
        else:
            checks = run_checks(top, next(s["checks"] for s in revision["stages"] if s["id"] == a.stage))
            failed = any(c["exit"] for c in checks)
            attempt.update(result="failed" if failed else "accepted", why="check failed" if failed else "")
            code = 1 if failed else 0
    ledger["attempts"].append(attempt)
    save(f["ledger"], ledger)
    print(json.dumps({"stage": a.stage, "attempt": attempt["n"], "result": attempt["result"],
                      "outside": outside, "checks": checks}))
    return code


def cmd_reject(a):
    paths(a.phase_file)
    return 0


def cmd_commit(a):
    paths(a.phase_file)
    print("0000000")
    return 0


def cmd_spend(a):
    ledger = ledger_of(paths(a.phase_file))
    total = sum((x["cost"] if x["cost"] is not None else x["cap"] or 0) for x in ledger["attempts"] if x["premium"])
    print(f"{total:.2f}")
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
