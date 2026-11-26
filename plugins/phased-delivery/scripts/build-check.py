#!/usr/bin/env python3
"""Gate, record and commit the stages of a phase for implement-in-phases.

Usage:
  build-check.py start PHASE_DIR [--repo DIR]
  build-check.py can-try PHASE_DIR STAGE MODEL EFFORT
  build-check.py record PHASE_DIR STAGE|review|revise --tool T --model M
                 --effort E --exit N --tokens X --cost Y [--cap USD]
                 [--tool-calls N] [--premium] [--fix] [--repo DIR]
  build-check.py reject PHASE_DIR STAGE WHY
  build-check.py commit PHASE_DIR STAGE [--subject-suffix TEXT]
                 [--extra-trailer LINE]... [--repo DIR]
  build-check.py spend PHASE_DIR
  build-check.py finish PHASE_DIR [--stopped] [--extra-trailer LINE]...
                 [--repo DIR]

PHASE_DIR is a plan's phase folder NN-name: phase.json, one stage file
NN.n.json per stage (phase.schema.json and stage.schema.json in
skills/plan-in-phases) and review.json (written by the phase reviewer,
review.schema.json in skills/implement-in-phases). The script reads the
briefs and writes only the records: the start state, review and revise runs
and the built commit in phase.json, and each stage's revisions, attempts and
commit in its stage file. Status is never edited: phase.md and plan.md are
re-rendered from the records. --repo defaults to the current directory.

start     validates phase.json and the stage files and writes HEAD and the
          paths already modified into phase.json's record. On resume (HEAD
          already set) it adds the paths modified since, other than stage
          files and the plan's, so the driver never restores them. Exit 5
          when the only problem is a brief changed without a higher
          revision; exit 1 on other invalid JSON or, on the first start, a
          stage's file already modified.
can-try   exit 1 when the stage already has a non-error attempt on the pair
          at the brief's current revision.
record    logs an attempt and gates a build: no uncommitted path outside the
          scope rule, and every check command of the stage passes. Prints one
          JSON line {stage, attempt, result, outside, checks}. Exit 0
          accepted; 1 failed; 3 budget stop (build exit 8); 4 error (any
          other build exit: not a try of the pair). Exit 2, nothing logged,
          for --model orchestrator on a stage that is not session_only.
          Stages "review" and "revise" are logged for spend only. --live
          streams each check to stderr as it runs: "[check-<stage>] $ <cmd>",
          each output line (stdout and stderr merged) and "[check-<stage>]
          exit N".
reject    marks the stage's accepted, uncommitted attempt rejected.
commit    commits the stage's changed files with the stage trailers (an
          empty commit for a session-only or reopened stage with none),
          writes the commit into the stage's record and re-renders.
spend     prints the premium spend: costs of --premium attempts (cap when
          the cost is unknown), as a bare number.
finish    refuses while a stage has no commit or is reopened, validates the
          review, sets the record's built commit, re-renders and commits the
          plan directory with a Phase: trailer. --stopped only commits.

can-try and record store the hash of the stage's brief under its revision;
every subcommand but start exits 5, nothing changed, when a brief changed
since its revision was stored or the revision is lower than a stored one:
raise the revision. Every subcommand validates phase.json and the stage
files as start does; but for start, another problem is exit 2, one JSON
line each.
record exits 2, nothing logged, for a stage with a commit without --fix.

Exit codes not listed: 0 done; 1 refused (one JSON line per problem for
invalid JSON); 2 bad usage, a missing file, or start has not run.
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


class Invalid(Exception):
    """(problems, exit code): the phase failed validation; main prints the problems as JSON lines."""


def phase_paths(phase_dir):
    """(the phase folder, its plan directory), both real paths."""
    pdir = os.path.realpath(phase_dir)
    if not os.path.basename(pdir)[:2].isdigit():
        raise Usage(f"phase folder must be named NN-name: {phase_dir}")
    if not os.path.isfile(os.path.join(pdir, "phase.json")):
        raise Usage(f"missing {os.path.join(phase_dir, 'phase.json')}")
    return pdir, os.path.dirname(pdir)


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


def checked_phase(pdir):
    """(phase.json, {stage id: stage file}, problems): the schemas, then the revision check."""
    name, r = os.path.basename(pdir), plan_check.Report()
    pj = plan_check.load(os.path.join(pdir, "phase.json"), plan_check.schema_for("phase.schema.json"), r,
                         f"{name}/phase.json")
    schema = plan_check.schema_for("stage.schema.json")
    loaded = {n[:-5]: plan_check.load(os.path.join(pdir, n), schema, r, f"{name}/{n}")
              for n in plan_check.stage_files(pdir)}
    stages = {sid: s for sid, s in loaded.items() if s is not None}
    if not loaded:
        r.add(f"{name}/phase.json", "-", "missing", f"no stage files in {name}")
    for sid, s in stages.items():
        plan_check.check_revision(sid, {**s, "file": f"{name}/{sid}.json"}, r)
    return pj, stages, r.items


def report(problems):
    for p in problems:
        print(json.dumps(p))
    return 1 if problems else 0


# ---- repository and records

def git(repo, *args, check=True):
    r = subprocess.run(["git", "-C", repo, *args], capture_output=True, text=True)
    if check and r.returncode:
        raise Usage(f"git {' '.join(args)}: {(r.stderr + r.stdout).strip()}")
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
            found.append(out[i])  # the rename's source path: it changed too
            i += 1
    return found


def rel(top, path):
    return os.path.relpath(os.path.realpath(path), top)


def in_dir(path, directory):
    return directory == "." or (path + "/").startswith(directory + "/")


def is_cache(path):
    parts = path.split("/")
    return "__pycache__" in parts or ".pytest_cache" in parts or path.endswith(".pyc")


def save(path, data):
    with open(path, "w") as f:
        json.dump(data, f, indent=1)
        f.write("\n")


def read_phase(phase_dir):
    """(phase folder, plan directory, phase.json, {stage id: stage file}) of a started phase."""
    pdir, plan_dir = phase_paths(phase_dir)
    pj, stages, problems = checked_phase(pdir)
    if problems:
        # a brief edited without a higher revision keeps exit 5; any other problem is exit 2
        raise Invalid(problems, 5 if all(p["kind"] == "revision" for p in problems) else 2)
    if not pj["record"].get("start_commit"):
        raise Usage(f"{phase_dir} has no start_commit: run start first")
    return pdir, plan_dir, pj, stages


def stage_of(stages, sid):
    if sid not in stages:
        raise Usage(f"stage {sid} has no stage file")
    return stages[sid]


def with_record(doc, **fields):
    return {**doc, "record": {**doc["record"], **fields}}


def attempts_of(s):
    return s["record"].get("attempts", [])


def brief_files(s):
    return [f["path"] for f in s["brief"]["files"]]


def pinned(pdir, sid, s):
    """The stage with its brief's hash stored under its revision, saved; read_phase has run the revision check."""
    revs, rev = s["record"].get("revisions", {}), str(s["brief"]["revision"])
    if rev in revs:
        return s
    new = with_record(s, revisions={**revs, rev: plan_check.brief_hash(s["brief"])})
    save(os.path.join(pdir, f"{sid}.json"), new)
    return new


def outside_paths(top, plan_dir, pj, stages, sid):
    uncommitted = {p for s in stages.values() if not s["record"].get("commit") for p in brief_files(s)}
    allowed = set(brief_files(stages[sid])) | set(pj["record"]["preexisting"]) | uncommitted
    return [p for p in changed_paths(top)
            if p not in allowed and not is_cache(p) and not in_dir(p, rel(top, plan_dir))]


def run_live(top, stage, cmd):
    tag = f"[check-{stage}]"
    print(f"{tag} $ {cmd}", file=sys.stderr, flush=True)
    with subprocess.Popen(["sh", "-c", cmd], cwd=top, stdout=subprocess.PIPE, stderr=subprocess.STDOUT) as p:
        for raw in p.stdout:
            line = raw.decode(errors="replace").rstrip("\r\n")
            print(f"{tag} {line}", file=sys.stderr, flush=True)
    print(f"{tag} exit {p.returncode}", file=sys.stderr, flush=True)
    return p.returncode


def run_checks(top, commands, live_stage=None):
    return [{"cmd": c, "exit": run_live(top, live_stage, c) if live_stage
             else subprocess.run(["sh", "-c", c], cwd=top, capture_output=True).returncode}
            for c in commands]


def amount(x):
    return "unknown" if x is None else f"{x:.2f}"


def count(x):
    return "unknown" if x is None else str(int(x))


# ---- subcommands

def cmd_start(a):
    pdir, plan_dir = phase_paths(a.phase_dir)
    name = os.path.basename(pdir)
    pj, stages, problems = checked_phase(pdir)
    if problems:
        return 5 if report(problems) and all(p["kind"] == "revision" for p in problems) else 1
    top = toplevel(a.repo)
    now = changed_paths(top)
    if pj["record"].get("start_commit"):
        # resume: keep paths changed since the last run, so a restore never deletes or reverts them
        known = set(pj["record"]["preexisting"]) | {p for s in stages.values() for p in brief_files(s)}
        new = [p for p in now if p not in known and not is_cache(p) and not in_dir(p, rel(top, plan_dir))]
        if new:
            save(os.path.join(pdir, "phase.json"),
                 with_record(pj, preexisting=pj["record"]["preexisting"] + new))
        return 0
    dirty = [{"file": f"{name}/{sid}.json", "where": sid, "msg": f"stage file already modified: {p}"}
             for sid, s in stages.items() for p in brief_files(s) if p in now]
    if dirty:
        return report(dirty)
    save(os.path.join(pdir, "phase.json"),
         with_record(pj, start_commit=git(top, "rev-parse", "HEAD").strip(), preexisting=now))
    return 0


def cmd_can_try(a):
    pdir, _, _, stages = read_phase(a.phase_dir)
    s = pinned(pdir, a.stage, stage_of(stages, a.stage))
    for x in attempts_of(s):
        if ((x["model"], x["effort"], x["revision"]) == (a.model, a.effort, s["brief"]["revision"])
                and x["result"] != "error"):
            print(json.dumps(x))
            return 1
    return 0


def cmd_record(a):
    pdir, plan_dir, pj, stages = read_phase(a.phase_dir)
    base = {"n": 0, "fix": a.fix, "tool": a.tool, "model": a.model, "effort": a.effort,
            "exit": a.exit_code, "tokens": a.tokens, "cost": a.cost, "cap": a.cap,
            "tool_calls": a.tool_calls, "premium": a.premium, "why": "", "commit": ""}
    if a.stage in ("review", "revise"):
        run = {"stage": a.stage, **base, "result": a.stage}
        save(os.path.join(pdir, "phase.json"), with_record(pj, runs=pj["record"].get("runs", []) + [run]))
        print(json.dumps({"stage": a.stage, "attempt": 0, "result": a.stage, "outside": [], "checks": []}))
        return 0
    if a.model == "orchestrator" and not stage_of(stages, a.stage)["brief"].get("session_only"):
        print(f"stage {a.stage} is not session_only: the orchestrator may not build it", file=sys.stderr)
        return 2
    if stage_of(stages, a.stage)["record"].get("commit") and not a.fix:
        print(f"stage {a.stage} already has a commit: pass --fix to record its rebuild", file=sys.stderr)
        return 2
    s = pinned(pdir, a.stage, stages[a.stage])
    top = toplevel(a.repo)
    same = [x for x in attempts_of(s) if x["fix"] == a.fix and x["result"] != "error" and not x["commit"]]
    outside = outside_paths(top, plan_dir, pj, stages, a.stage)
    checks = [] if a.exit_code or outside else run_checks(top, s["brief"]["checks"], a.stage if a.live else None)
    if a.exit_code == 8:
        outcome, code = {"result": "stopped", "why": "budget reached"}, 3
    elif a.exit_code != 0:
        outcome, code = {"result": "error", "why": f"build exit {a.exit_code}", "n": 0}, 4
    elif outside:
        outcome, code = {"result": "failed", "why": "changed files outside the stage"}, 1
    elif any(c["exit"] for c in checks):
        outcome, code = {"result": "failed", "why": "check failed"}, 1
    else:
        outcome, code = {"result": "accepted"}, 0
    attempt = {"revision": s["brief"]["revision"], **base, "n": len(same) + 1, **outcome}
    save(os.path.join(pdir, f"{a.stage}.json"), with_record(s, attempts=attempts_of(s) + [attempt]))
    print(json.dumps({"stage": a.stage, "attempt": attempt["n"], "result": attempt["result"],
                      "outside": outside, "checks": checks}))
    return code


def open_attempt(s):
    for x in reversed(attempts_of(s)):
        if x["result"] == "accepted" and not x["commit"]:
            return x
    return None


def replaced(s, marked, **fields):
    """The stage's attempts with `fields` set on the ones in `marked`."""
    return [{**y, **fields} if any(y is m for m in marked) else y for y in attempts_of(s)]


def cmd_reject(a):
    pdir, _, _, stages = read_phase(a.phase_dir)
    s = stage_of(stages, a.stage)
    x = open_attempt(s)
    if x is None:
        print(f"no accepted, uncommitted attempt for {a.stage}", file=sys.stderr)
        return 1
    save(os.path.join(pdir, f"{a.stage}.json"),
         with_record(s, attempts=replaced(s, [x], result="rejected", why=a.why)))
    return 0


def git_commit(top, files, subject, trailers):
    body = "\n".join(trailers)
    if files:
        # a deletion is left to commit's pathspec: git add fails on one already staged (git rm)
        present = [p for p in files if os.path.lexists(os.path.join(top, p))]
        if present:
            git(top, "add", "-A", "--", *present)
        git(top, "commit", "-q", "-m", subject, "-m", body, "--", *files)
    else:
        # an empty commit made from HEAD's tree, so that paths staged by someone else stay out of it
        new = git(top, "commit-tree", "HEAD^{tree}", "-p", "HEAD", "-m", subject, "-m", body).strip()
        git(top, "update-ref", "HEAD", new)
    return git(top, "rev-parse", "--short", "HEAD").strip()


def cmd_commit(a):
    pdir, plan_dir, pj, stages = read_phase(a.phase_dir)
    s = stage_of(stages, a.stage)
    x = open_attempt(s)
    if x is None:
        print(f"no accepted, uncommitted attempt for {a.stage}", file=sys.stderr)
        return 1
    top = toplevel(a.repo)
    now = set(changed_paths(top)) - set(pj["record"]["preexisting"])
    files = [p for p in brief_files(s) if p in now]
    if not files and not (s["brief"].get("session_only") or plan_check.stage_status(s) == "reopened"):
        print(f"no changed files for {a.stage}", file=sys.stderr)
        return 1
    earlier = [y for y in attempts_of(s) if y["fix"] == x["fix"]
               and y["result"] in ("failed", "stopped", "rejected") and not y["commit"]]
    trailers = [f"{'Fixes-Stage' if x['fix'] else 'Stage'}: {a.stage}",
                f"Plan: {rel(top, pdir)}",
                f"Tier: {plan_check.tier(s['brief']['model_basis'])[1]}", f"Tool: {x['tool']}",
                f"Model: {x['model']}", f"Effort: {x['effort']}", f"Attempt: {len(earlier) + 1}",
                f"Tokens: {count(x['tokens'])}", f"Cost: {amount(x['cost'])}",
                f"Tool-Calls: {count(x['tool_calls'])}"]
    earlier_lines = [f"Earlier-Attempt: {y['model']} {y['effort']} {count(y['tokens'])} {' '.join(y['why'].split())}"
                     for y in earlier]
    subject = f"{a.stage} {s['brief']['title']}" + (f" {a.subject_suffix}" if a.subject_suffix else "")
    sha = git_commit(top, files, subject, trailers + earlier_lines + a.extra_trailer)
    save(os.path.join(pdir, f"{a.stage}.json"),
         with_record(s, attempts=replaced(s, earlier + [x], commit=sha), commit=sha))
    plan_check.render_plan(plan_dir)
    print(sha)
    return 0


def cmd_spend(a):
    _, _, pj, stages = read_phase(a.phase_dir)
    spent = pj["record"].get("runs", []) + [x for s in stages.values() for x in attempts_of(s)]
    total = sum((x["cost"] if x["cost"] is not None else x["cap"] or 0) for x in spent if x["premium"])
    print(f"{total:.2f}")
    return 0


def cmd_finish(a):
    pdir, plan_dir, pj, stages = read_phase(a.phase_dir)
    top = toplevel(a.repo)
    if not a.stopped:
        _, review_problems = load_checked(os.path.join(pdir, "review.json"), "review.schema.json", "review")
        states = {sid: plan_check.stage_status(s) for sid, s in stages.items()}
        unbuilt = [{"file": f"{sid}.json", "where": sid,
                    "msg": "stage is reopened" if state == "reopened" else "stage has no commit"}
                   for sid, state in states.items() if state != "done"]
        if review_problems or unbuilt:
            return report(review_problems + unbuilt)
        ours = {s["record"]["commit"] for s in stages.values()}
        log = git(top, "log", "--format=%h", "--abbrev=7", f"{pj['record']['start_commit']}..HEAD").split()
        last = next(h for h in log if any(c.startswith(h) or h.startswith(c) for c in ours))
        save(os.path.join(pdir, "phase.json"), with_record(pj, built=last))
        plan_check.render_plan(plan_dir)
    if subprocess.run(["git", "-C", top, "check-ignore", "-q", rel(top, plan_dir)]).returncode == 0:
        print("not committed: git ignores the plan directory")  # a plan kept out of the repository
        return 0
    subject = f"Phase {os.path.basename(pdir)[:2]} {'stopped' if a.stopped else 'built'}: status and notes"
    print(git_commit(top, [rel(top, plan_dir)], subject, [f"Phase: {rel(top, pdir)}"] + a.extra_trailer))
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
    s.add_argument("phase_dir")
    s.add_argument("--repo", default=".")
    s = sub.add_parser("can-try")
    for k in ("phase_dir", "stage", "model", "effort"):
        s.add_argument(k)
    s = sub.add_parser("record")
    s.add_argument("phase_dir")
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
    s.add_argument("--live", action="store_true")
    s.add_argument("--repo", default=".")
    s = sub.add_parser("reject")
    for k in ("phase_dir", "stage", "why"):
        s.add_argument(k)
    s = sub.add_parser("commit")
    s.add_argument("phase_dir")
    s.add_argument("stage")
    s.add_argument("--subject-suffix", default="")
    s.add_argument("--extra-trailer", action="append", default=[])
    s.add_argument("--repo", default=".")
    s = sub.add_parser("spend")
    s.add_argument("phase_dir")
    s = sub.add_parser("finish")
    s.add_argument("phase_dir")
    s.add_argument("--stopped", action="store_true")
    s.add_argument("--extra-trailer", action="append", default=[])
    s.add_argument("--repo", default=".")
    return p.parse_args(argv)


COMMANDS = {"start": cmd_start, "can-try": cmd_can_try, "record": cmd_record, "reject": cmd_reject,
            "commit": cmd_commit, "spend": cmd_spend, "finish": cmd_finish}


def main(argv):
    a = parse_args(argv)
    try:
        return COMMANDS[a.cmd](a)
    except Invalid as e:
        report(e.args[0])
        return e.args[1]
    except (Usage, OSError, ValueError) as e:
        print(e, file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
