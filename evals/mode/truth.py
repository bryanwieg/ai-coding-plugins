#!/usr/bin/env python3
"""Score each calibration case from its real change: the answer the estimate is compared with.

Usage: python3 evals/mode/truth.py [CASE_ID ...]

For each case in cases.json, the repository at `base` is exported to a
temporary folder; each part's files get their action and lines from the
real change (`head` commit, or an eval task's reference folder); the form
is scored with plan-mode.py against the base, so reach is searched the way
the estimate's would be. Prints one row per case and writes the forms and
summaries to truth.json next to this file.
"""

import difflib
import json
import os
import re
import subprocess
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
SCRIPT = os.path.join(ROOT, "plugins", "phased-delivery", "scripts", "plan-mode.py")
TESTY = re.compile(r"(^|/)tests?/|(^|/)test_")


def git(*args):
    return subprocess.run(["git", "-C", ROOT, *args], capture_output=True, text=True, check=True).stdout


def at(commit, path):
    try:
        return git("show", f"{commit}:{path}")
    except subprocess.CalledProcessError:
        return None


def after(case, path):
    if "head" in case:
        return at(case["head"], path)
    ref = os.path.join(ROOT, "evals", "tasks", case["reference"])
    deleted = os.path.join(ref, "reference-delete.txt")
    if os.path.exists(deleted) and path in open(deleted).read().split():
        return None
    p = os.path.join(ref, "reference", path)
    return open(p).read() if os.path.exists(p) else at(case["base"], path)


def changed_lines(old, new):
    diff = difflib.unified_diff((old or "").splitlines(), (new or "").splitlines(), lineterm="", n=0)
    return sum(1 for d in diff if d[:1] in "+-" and not d.startswith(("+++", "---")))


def bucket(n):
    return "under 30" if n < 30 else "30-150" if n <= 150 else "over 150"


def form_for(case):
    parts = []
    for p in case["parts"]:
        files, lines = [], 0
        for f in p["files"]:
            old, new = at(case["base"], f), after(case, f)
            files.append({"path": f, "action": "create" if old is None else "delete" if new is None else "edit"})
            if not TESTY.search(f):
                lines += changed_lines(old, new)
        part = {"title": p["title"], "kind": p["kind"], "files": files, "lines": bucket(lines), "changes": p["changes"]}
        if "existing_data" in p:
            part["existing_data"] = p["existing_data"]
        parts.append(part)
    return {"request": case["request"], "opened": [], "parts": parts, "unresolved": [], "open_questions": []}


def main(ids):
    cases = json.load(open(os.path.join(HERE, "cases.json")))
    out = {}
    for case in cases:
        if ids and case["id"] not in ids:
            continue
        form = form_for(case)
        with tempfile.TemporaryDirectory() as tmp:
            subprocess.run(f"git -C {ROOT} archive {case['base']} | tar -x -C {tmp}", shell=True, check=True)
            subprocess.run(["git", "init", "-q", tmp], check=True)  # so the search lists files as git would
            fpath = os.path.join(tmp, "..", f"form-{case['id']}.json")
            with open(fpath, "w") as fh:
                json.dump(form, fh)
            p = subprocess.run([sys.executable, SCRIPT, "score", fpath, "--repo", tmp], capture_output=True, text=True)
            os.remove(fpath)
        rows = [json.loads(x) for x in p.stdout.splitlines()]
        s = rows[-1]["summary"]
        problems = [r for r in rows[:-1] if r["level"] == "error"]
        out[case["id"]] = {"form": form, "summary": s, "problems": problems}
        mark = "" if s["mode"] == case["expected"] else "  <- expected " + case["expected"]
        print(f"{case['id']:20} {str(s['total']):>5} {str(s['mode']):7}{mark}"
              + "".join(f"\n{'':22}{x['title']}: {x['weight']}x{x['size']}x{x['reach']} reach {x['reach_files']}"
                        for x in s["parts"])
              + "".join(f"\n{'':22}ERROR {x['msg']}" for x in problems))
    with open(os.path.join(HERE, "truth.json"), "w") as fh:
        json.dump(out, fh, indent=1)


if __name__ == "__main__":
    main(sys.argv[1:])
