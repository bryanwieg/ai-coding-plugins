#!/usr/bin/env python3
"""Pick how much planning a change needs: direct, quick or full.

Usage:
  plan-mode.py FORM.json [--repo DIR]

The agent splits the request into parts and fills FORM.json per
skills/plan-in-phases/mode.schema.json, following mode-guide.md. This
script checks the evidence that can be checked (files exist, reach entries
exist and lie outside the part) and scores the form:

  part score = weight(kind) x size(lines) x reach(places outside the part)
  total      = sum of part scores + 1 per open question

Output: one JSON line per problem, {"where", "kind", "msg", "level"}, then a
summary line {"summary": {"mode", "total", "parts", "reasons"}}. level
"error" must be fixed before the mode counts; "warning" is for the agent
to judge. Exit codes: 0 no errors; 1 errors; 2 bad usage or an unreadable
file.
"""

import importlib.util
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.join(HERE, "..", "skills", "plan-in-phases", "mode.schema.json")
_spec = importlib.util.spec_from_file_location("plan_check", os.path.join(HERE, "plan-check.py"))
plan_check = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(plan_check)

WEIGHT = {"new": 0.5, "internal": 1, "interface": 2, "architecture": 3, "data": 3}
REACHES = {"interface", "architecture", "data"}
DIRECT_MAX, QUICK_MAX = 4, 15
MODES = ["direct", "quick", "full"]


def size(lines):
    return 1 if lines < 30 else 2 if lines <= 150 else 5


def reach(n):
    return 1 if n == 0 else 1.5 if n <= 3 else 2 if n <= 9 else 3


def place(entry):
    return entry.split(":")[0].strip()


def score(form):
    """Return (mode, total, per-part rows, reasons). No file checks."""
    rows, reasons, floor = [], [], 0
    for p in form["parts"]:
        places = {place(e) for e in p["reach"]} if p["kind"] in REACHES else set()
        r = {"title": p["title"], "weight": WEIGHT[p["kind"]], "size": size(p["lines"]),
             "reach": reach(len(places))}
        r["score"] = r["weight"] * r["size"] * r["reach"]
        rows.append(r)
        if p["kind"] == "data" and p.get("existing_data"):
            floor = 2
            reasons.append(f"{p['title']}: changes data that already exists -> full")
    total = sum(r["score"] for r in rows) + len(form["open_questions"])
    mode = 0 if total <= DIRECT_MAX else 1 if total <= QUICK_MAX else 2
    return MODES[max(mode, floor)], total, rows, reasons


def check(form, repo):
    out = []

    def add(where, kind, msg, level="error"):
        out.append({"where": where, "kind": kind, "msg": msg, "level": level})

    created = set()
    for i, p in enumerate(form["parts"]):
        w = f"/parts/{i}"
        own = {f["path"] for f in p["files"]}
        for f in p["files"]:
            exists = os.path.exists(os.path.join(repo, f["path"])) or f["path"] in created
            if f["action"] == "create" and exists:
                add(w, "files", f"{f['path']} exists; use edit")
            elif f["action"] != "create" and not exists:
                add(w, "files", f"{f['path']} does not exist")
        created |= {f["path"] for f in p["files"] if f["action"] == "create"}
        if p["kind"] in REACHES and not p["search"].strip():
            add(w, "search", "say what was searched to find the reach (an empty reach needs it too)")
        if p["kind"] == "data" and "existing_data" not in p:
            add(w, "schema", "a data part says whether data already exists (existing_data)")
        if p["kind"] not in REACHES and p["reach"]:
            add(w, "reach", f"reach is not counted for kind {p['kind']}", "warning")
        if p["kind"] == "new" and any(f["action"] != "create" for f in p["files"]):
            add(w, "kind", "a new part edits existing files; if existing code calls it, the edit is its own part",
                "warning")
        for e in p["reach"]:
            path = place(e)
            if path in own:
                add(w, "reach", f"{e} is one of the part's own files; reach is outside the part")
            elif not os.path.exists(os.path.join(repo, path)):
                add(w, "reach", f"{e} does not exist")
            elif ":" in e and e.split(":")[1].split("-")[0].isdigit():
                with open(os.path.join(repo, path), errors="replace") as fh:
                    n = sum(1 for _ in fh)
                if int(e.split(":")[1].split("-")[0]) > n:
                    add(w, "reach", f"{e}: the file has {n} lines")
    return out


def main(argv):
    args, repo, i = [], ".", 0
    while i < len(argv):
        if argv[i] == "--repo" and i + 1 < len(argv):
            repo, i = argv[i + 1], i + 2
        else:
            args, i = args + [argv[i]], i + 1
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    try:
        with open(args[0]) as fh:
            form = json.load(fh)
        with open(SCHEMA) as fh:
            schema = json.load(fh)
    except (OSError, ValueError) as e:
        print(f"cannot read: {e}", file=sys.stderr)
        return 2
    problems = [{"where": w, "kind": "schema", "msg": m, "level": "error"}
                for w, m in plan_check.validate(form, schema)]
    if not problems:
        problems = check(form, repo)
    for p in problems:
        print(json.dumps(p))
    errors = any(p["level"] == "error" for p in problems)
    summary = {"mode": None, "total": None, "parts": [], "reasons": []}
    if not errors:
        mode, total, rows, reasons = score(form)
        summary = {"mode": mode, "total": total, "parts": rows, "reasons": reasons}
    print(json.dumps({"summary": summary}))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
