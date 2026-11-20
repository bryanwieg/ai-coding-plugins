"""Hidden checks for t5-keywords (run by check.sh)."""
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.environ["KIT"], "lib"))
from checklib import BASELINE, RUN, check, info, read  # noqa: E402

HOOK = os.path.join("plugins", "phased-delivery", "hooks", "prompt-reminder.sh")

# (name, hook stdin, expect reminder)
CASES = [
    ("roadmap", {"session_id": "s", "cwd": "/x", "prompt": "Let's draft a roadmap for Q3"}, True),
    ("milestone", {"cwd": "/x", "prompt": "what is the next milestone?"}, True),
    ("milestones", {"cwd": "/x", "prompt": "list the milestones please"}, True),
    ("case-insensitive", {"cwd": "/x", "prompt": "ROADMAP review"}, True),
    ("case-insensitive-2", {"cwd": "/x", "prompt": "Milestone 3 is late"}, True),
    ("after-newline", {"cwd": "/x", "prompt": "notes:\nmilestones\nthanks"}, True),
    ("old-word-plan", {"cwd": "/x", "prompt": "Plan the release"}, True),
    ("old-word-refactor", {"cwd": "/x", "prompt": "refactoring the parser"}, True),
    ("not-milestoned", {"cwd": "/x", "prompt": "the milestoned project shipped"}, False),
    ("not-roadmapping", {"cwd": "/x", "prompt": "a roadmapping session tomorrow"}, False),
    ("unrelated", {"cwd": "/x", "prompt": "fix the typo in the footer"}, False),
    ("cwd-not-prompt", {"cwd": "/x/plan", "transcript_path": "/x/roadmap/milestones.jsonl",
                        "prompt": "fix the typo in the footer"}, False),
]


def run_hook(shell, repo, payload):
    done = subprocess.run(shell + [os.path.join(repo, HOOK)], input=json.dumps(payload),
                          capture_output=True, text=True, timeout=20)
    return done.returncode, done.stdout, done.stderr


source = read(os.path.join(RUN, HOOK)) or ""
check("shebang", source.startswith("#!/bin/sh\n"), f"first line {source.splitlines()[:1]}")

code, reminder, _ = run_hook(["sh"], BASELINE, {"prompt": "plan this"})
if code != 0 or not reminder.strip():
    sys.exit("FAIL harness: base hook printed no reminder")

shells = [["sh"]]
for extra in (["dash"], ["busybox", "sh"], ["bash", "--posix"]):
    if shutil.which(extra[0]):
        shells.append(extra)
info("shells: " + ", ".join(" ".join(s) for s in shells))

for shell in shells:
    label = " ".join(shell)
    bad = []
    for name, payload, want in CASES:
        code, out, err = run_hook(shell, RUN, payload)
        expected = reminder if want else ""
        if code != 0 or out != expected or err:
            bad.append(f"{name} (exit {code}, {'reminder' if out else 'no output'}"
                       f"{', stderr ' + err.strip()[:80] if err else ''})")
    if shell == ["sh"]:
        # One line per case under the default shell.
        for name, payload, want in CASES:
            code, out, err = run_hook(shell, RUN, payload)
            check(f"{'positive' if want else 'negative'} {name}",
                  code == 0 and out == (reminder if want else "") and not err,
                  f"exit {code}, output {out.strip()[:60]!r}, stderr {err.strip()[:80]!r}")
    else:
        check(f"all cases under {label}", not bad, "; ".join(bad))
