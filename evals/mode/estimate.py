#!/usr/bin/env python3
"""Have a model make the quick estimate for each case, then compare it with truth.json.

Usage:
  python3 evals/mode/estimate.py run [CASE_ID ...]     # paid: one claude -p call per case
  python3 evals/mode/estimate.py compare

Each run exports the case's base commit to $MODE_RUNS/<id>/repo (default
/tmp/mode-runs), gives the model only the request and mode-guide.md, and
keeps its TERMS.json, FORM.json, the score output and the stream. Opus,
medium effort, plugins off, no Grep/Glob/Agent/web tools, a $1 cap and a
5-minute timeout per case. `compare` prints, per case, the estimate's mode
against the truth's, the files it opened, the shell commands it ran other
than plan-mode.py (searches the guide forbids), and the cost.
"""

import json
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
GUIDE = os.path.join(ROOT, "plugins", "phased-delivery", "skills", "plan-in-phases", "mode-guide.md")
SCRIPT = os.path.join(ROOT, "plugins", "phased-delivery", "scripts", "plan-mode.py")
RUNS = os.environ.get("MODE_RUNS", "/tmp/mode-runs")
OFF = os.environ.get("MODE_SETTINGS", "/tmp/plan-eval/off.json")

PROMPT = """Estimate how much planning this request needs. Do not plan it and do not change any code.

Request: {request}

Follow {guide} exactly: it is the whole procedure. The script is {script}; run it with
`python3 {script} locate|score FILE --repo .` from the repository (the current directory).
Write TERMS.json and FORM.json in {out}, not in the repository. Finish with the mode the
score step printed."""


def run(case):
    d = os.path.join(RUNS, case["id"])
    repo = os.path.join(d, "repo")
    subprocess.run(["rm", "-rf", d], check=True)
    os.makedirs(repo)
    subprocess.run(f"git -C {ROOT} archive {case['base']} | tar -x -C {repo}", shell=True, check=True)
    subprocess.run("git init -q && git add -A && git -c user.name=eval -c user.email=eval@localhost "
                   "commit -qm base", shell=True, cwd=repo, check=True)
    prompt = PROMPT.format(request=case["request"], guide=GUIDE, script=SCRIPT, out=d)
    with open(os.path.join(d, "stream.jsonl"), "w") as out:
        subprocess.run(["timeout", "300", "claude", "-p", prompt, "--model", "opus", "--effort", "medium",
                        "--settings", OFF, "--permission-mode", "bypassPermissions",
                        "--disallowedTools", "Grep,Glob,Agent,WebSearch,WebFetch,Skill",
                        "--no-session-persistence", "--max-budget-usd", "1",
                        "--output-format", "stream-json", "--verbose"],
                       cwd=repo, stdout=out, stderr=subprocess.DEVNULL)


def calls(d):
    reads, shell, cost = [], [], None
    for line in open(os.path.join(d, "stream.jsonl")):
        e = json.loads(line)
        if e.get("type") == "assistant":
            for c in e["message"]["content"]:
                if c.get("type") != "tool_use":
                    continue
                if c["name"] == "Read":
                    reads.append(os.path.relpath(c["input"]["file_path"], os.path.join(d, "repo")))
                elif c["name"] == "Bash" and "plan-mode.py" not in c["input"]["command"]:
                    shell.append(c["input"]["command"][:80])
        if e.get("type") == "result":
            cost = e.get("total_cost_usd")
    return [r for r in reads if not r.startswith("..")], shell, cost


def compare():
    truth = json.load(open(os.path.join(HERE, "truth.json")))
    total, hits = 0.0, 0
    for case in json.load(open(os.path.join(HERE, "cases.json"))):
        d = os.path.join(RUNS, case["id"])
        if not os.path.exists(os.path.join(d, "stream.jsonl")):
            continue
        reads, shell, cost = calls(d)
        total += cost or 0
        p = subprocess.run([sys.executable, SCRIPT, "score", os.path.join(d, "FORM.json"), "--repo",
                            os.path.join(d, "repo")], capture_output=True, text=True)
        try:
            s = json.loads(p.stdout.splitlines()[-1])["summary"]
        except (IndexError, ValueError):
            s = {"mode": None, "total": None, "parts": []}
        t = truth[case["id"]]["summary"]
        hits += s["mode"] == t["mode"]
        print(f"{case['id']:20} est {str(s['mode']):7}{str(s['total']):>6}  truth {t['mode']:7}{t['total']:>6}"
              f"  read {len(reads)}  shell {len(shell)}  ${cost or 0:.2f}"
              + "".join(f"\n{'':22}{x['title']}: {x['weight']}x{x['size']}x{x['reach']}" for x in s["parts"])
              + "".join(f"\n{'':22}SHELL {c}" for c in shell))
    print(f"\nmodes matching truth: {hits}; cost ${total:.2f}")


def main(argv):
    cases = json.load(open(os.path.join(HERE, "cases.json")))
    if argv[:1] == ["run"]:
        for case in cases:
            if len(argv) == 1 or case["id"] in argv[1:]:
                run(case)
        return 0
    if argv[:1] == ["compare"]:
        compare()
        return 0
    print(__doc__, file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
