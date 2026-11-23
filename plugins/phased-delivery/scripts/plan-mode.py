#!/usr/bin/env python3
"""Estimate how much planning a change needs: direct, quick or full.

Usage:
  plan-mode.py locate TERMS.json [--repo DIR]
  plan-mode.py score FORM.json [--repo DIR]

A quick estimate with hard limits, in two calls (see
skills/plan-in-phases/mode-guide.md). The agent does no searching itself:

1. The agent lists up to 5 terms from the request (TERMS.json, see
   mode.schema.json "terms"); `locate` searches the repository for each and
   prints the files that mention it (at most 10 per term).
2. The agent opens at most 5 of those files and writes FORM.json
   (mode.schema.json "form"): the parts of the change, and for each part
   that others see, the names that change. `score` checks the form, searches
   for the users of every changed name outside the part's files (the
   reach), and scores:

     part score = weight(kind) x size(lines) x reach(files using its names)
     total      = sum of part scores + 1 per open question

   direct up to 4, quick up to 15, full above. A part that changes data
   already written is always full; anything the estimate could not find
   (unresolved) makes it at least quick.

Output: one JSON line per problem, {"where", "kind", "msg", "level"}, then a
summary line. level "error" must be fixed; "warning" is for the agent to
judge. Exit codes: 0 no errors; 1 errors; 2 bad usage or an unreadable file.
"""

import importlib.util
import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "skills", "plan-in-phases", "mode.schema.json")
_spec = importlib.util.spec_from_file_location("plan_check", os.path.join(HERE, "plan-check.py"))
plan_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_check)

WEIGHT = {"new": 0.5, "internal": 1, "interface": 2, "architecture": 3, "data": 3}
SIZE = {"under 30": 1, "30-150": 2, "over 150": 5}
REACHES = {"interface", "architecture", "data"}
DIRECT_MAX, QUICK_MAX = 4, 15
MODES = ["direct", "quick", "full"]
MAX_TERMS, MAX_FILES_PER_TERM, MAX_OPENED = 5, 10, 5
SKIP_DIRS = {".git", "node_modules", ".venv", "venv", "__pycache__", "dist", "build", ".plan"}
MAX_BYTES = 1_000_000
PHASE_MARK = "Implement with the implement-in-phases skill"


def reach(n):
    return 1 if n == 0 else 1.5 if n <= 3 else 2 if n <= 9 else 3


def score(parts, open_questions, unresolved):
    """parts: dicts with kind, lines, reach_files (a count). Returns (mode, total, rows, reasons)."""
    rows, reasons, floor = [], [], 0
    for p in parts:
        r = {"title": p["title"], "weight": WEIGHT[p["kind"]], "size": SIZE[p["lines"]],
             "reach": reach(p["reach_files"]) if p["kind"] in REACHES else 1}
        r["score"] = r["weight"] * r["size"] * r["reach"]
        rows.append(r)
        if p["kind"] == "data" and p.get("existing_data"):
            floor = 2
            reasons.append(f"{p['title']}: changes data already written -> full")
    if unresolved and floor < 1:
        floor = 1
        reasons.append(f"{len(unresolved)} unresolved -> at least quick")
    total = sum(r["score"] for r in rows) + len(open_questions)
    mode = 0 if total <= DIRECT_MAX else 1 if total <= QUICK_MAX else 2
    return MODES[max(mode, floor)], total, rows, reasons


# ---- searching (the agent never searches during the estimate; these do)

def repo_files(repo):
    try:
        out = subprocess.run(["git", "-C", repo, "ls-files", "-co", "--exclude-standard"],
                             capture_output=True, text=True, check=True).stdout.splitlines()
        return sorted(f for f in out if not set(f.split("/")) & SKIP_DIRS)
    except (OSError, subprocess.CalledProcessError):
        files = []
        for root, dirs, names in os.walk(repo):
            dirs[:] = [d for d in dirs if d not in SKIP_DIRS]
            files += [os.path.relpath(os.path.join(root, n), repo) for n in names]
        return sorted(files)


def texts(repo, skip=None):
    """Text files of the repository, except the input file and plan folders (phase files and
    their model tables mention every name and are not users of it)."""
    out, plan_dirs = [], set()
    for f in repo_files(repo):
        p = os.path.join(repo, f)
        if skip and os.path.abspath(p) == skip:
            continue
        try:
            if os.path.getsize(p) > MAX_BYTES:
                continue
            with open(p, "rb") as fh:
                data = fh.read()
        except OSError:
            continue
        if b"\0" in data:
            continue
        text = data.decode("utf-8", "replace")
        if text.startswith("# Phase ") and PHASE_MARK in text[:500]:
            plan_dirs.add(os.path.dirname(f))
        out.append((f, text))
    return [(f, t) for f, t in out if os.path.dirname(f) not in plan_dirs]


def mentions(corpus, needle, ignore_case):
    n = needle.lower() if ignore_case else needle
    return [f for f, t in corpus if n in (t.lower() if ignore_case else t)]


# ---- the two calls

def locate(terms, repo, skip=None):
    corpus = texts(repo, skip)
    out = []
    for t in terms["terms"]:
        found = sorted(set(mentions(corpus, t, True) + [f for f, _ in corpus if t.lower() in f.lower()]))
        out.append({"term": t, "files": found[:MAX_FILES_PER_TERM], "more": max(0, len(found) - MAX_FILES_PER_TERM)})
    return out


def check_form(form, repo):
    out = []

    def add(where, kind, msg, level="error"):
        out.append({"where": where, "kind": kind, "msg": msg, "level": level})

    if len(form["opened"]) > MAX_OPENED:
        add("/opened", "limit", f"{len(form['opened'])} files opened; the estimate reads at most {MAX_OPENED}")
    for f in form["opened"]:
        if not os.path.isfile(os.path.join(repo, f)):
            add("/opened", "files", f"{f} does not exist")
    created = set()
    for i, p in enumerate(form["parts"]):
        w = f"/parts/{i}"
        for f in p["files"]:
            exists = os.path.exists(os.path.join(repo, f["path"])) or f["path"] in created
            if f["action"] == "create" and exists:
                add(w, "files", f"{f['path']} exists; use edit")
            elif f["action"] != "create" and not exists:
                add(w, "files", f"{f['path']} does not exist")
        created |= {f["path"] for f in p["files"] if f["action"] == "create"}
        if p["kind"] in REACHES and not p["changes"]:
            add(w, "changes", f"a {p['kind']} part names what others see change (a key, signature, route, format)")
        for n in p["changes"]:
            if len(n) < 4:
                add(w, "changes", f"{n!r} is too short to search for; give the whole name", "warning")
        if p["kind"] not in REACHES and p["changes"]:
            add(w, "changes", f"changes are not counted for kind {p['kind']}", "warning")
        if p["kind"] == "data" and "existing_data" not in p:
            add(w, "schema", "a data part says whether data already exists (existing_data)")
        if p["kind"] == "new" and any(f["action"] != "create" for f in p["files"]):
            add(w, "kind", "a new part edits existing files; if existing code calls it, the edit is its own part",
                "warning")
    return out


def with_reach(form, repo, skip=None):
    """Add reach_files and reach (the user files) to each part by searching for its changed names."""
    corpus = None
    parts = []
    for p in form["parts"]:
        p = dict(p)
        users = set()
        if p["kind"] in REACHES and p["changes"]:
            corpus = corpus if corpus is not None else texts(repo, skip)
            own = {f["path"] for f in p["files"]}
            for name in p["changes"]:
                users |= set(mentions(corpus, name, False)) - own
        p["reach"], p["reach_files"] = sorted(users), len(users)
        parts.append(p)
    return parts


def main(argv):
    args, repo, i = [], ".", 0
    while i < len(argv):
        if argv[i] == "--repo" and i + 1 < len(argv):
            repo, i = argv[i + 1], i + 2
        else:
            args, i = args + [argv[i]], i + 1
    if len(args) != 2 or args[0] not in ("locate", "score"):
        print(__doc__, file=sys.stderr)
        return 2
    cmd, path = args
    try:
        with open(path) as fh:
            data = json.load(fh)
        with open(SCHEMA) as fh:
            schema = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read: {e}", file=sys.stderr)
        return 2
    part = "terms" if cmd == "locate" else "form"
    problems = [{"where": w, "kind": "schema", "msg": m, "level": "error"}
                for w, m in plan_check.validate(data, schema["definitions"][part], schema)]
    if cmd == "locate":
        if not problems and len(data["terms"]) > MAX_TERMS:
            problems.append({"where": "/terms", "kind": "limit", "msg": f"at most {MAX_TERMS} terms", "level": "error"})
        for p in problems:
            print(json.dumps(p))
        print(json.dumps({"summary": {"located": [] if problems else locate(data, repo, os.path.abspath(path))}}))
        return 1 if problems else 0
    if not problems:
        problems = check_form(data, repo)
    for p in problems:
        print(json.dumps(p))
    errors = any(p["level"] == "error" for p in problems)
    summary = {"mode": None, "total": None, "parts": [], "reasons": []}
    if not errors:
        parts = with_reach(data, repo, os.path.abspath(path))
        mode, total, rows, reasons = score(parts, data["open_questions"], data["unresolved"])
        for r, p in zip(rows, parts):
            r["reach_files"] = p["reach"][:MAX_FILES_PER_TERM]
        summary = {"mode": mode, "total": total, "parts": rows, "reasons": reasons}
    print(json.dumps({"summary": summary}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
