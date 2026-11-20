"""Hidden checks for t1-min-small (run by check.sh)."""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.environ["KIT"], "lib"))
from checklib import BASELINE, RUN, WORK, check, first_diff, select  # noqa: E402

# --min-small value -> expected small (model, effort). Computed from the
# fixture and model-report.json (checked 2026-11-19). 34.7 is the 3-point
# rule case: the absolute floor alone picks opus low (34.8, cost 979.66);
# haiku xhigh (34.6, cost 192.70) is cheaper and within 3 points, so it wins.
EXPECTED = {"30": ("haiku", "xhigh"), "25": ("haiku", "high"),
            "20": ("haiku", "medium"), "15": ("haiku", "low"),
            "34.7": ("haiku", "xhigh")}


def small_row(text):
    for line in text.splitlines():
        if line.startswith("| small |"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            return cells[1], cells[2]
    return None


def score_line(text):
    return next((l for l in text.splitlines() if l.startswith("Score:")), "")


base_json = os.path.join(WORK, "base.json")
code, base_out, err = select(BASELINE, "--json", base_json)
if code != 0:
    sys.exit(f"FAIL harness: base script failed: {err}")
with open(base_json) as source:
    base_tiers = json.load(source)

code, out, err = select(RUN)
check("no-flag-identical", code == 0 and out == base_out,
      f"exit {code}; " + (first_diff(out, base_out) if code == 0 else err.strip()[-300:]))

for value, (model, effort) in EXPECTED.items():
    name = f"min-small-{value}"
    json_path = os.path.join(WORK, f"run-{value}.json")
    code, out, err = select(RUN, "--min-small", value, "--json", json_path)
    if not check(f"{name} exit", code == 0, f"exit {code}: {err.strip()[-200:]}"):
        continue
    check(f"{name} table", small_row(out) == (model, effort),
          f"small row {small_row(out)}, expected {(model, effort)}")
    line = score_line(out)
    check(f"{name} score-line", f"small min {value}" in line and "small 50%" not in line
          and "top 97%" in line and "middle 85%" in line,
          f"got {line!r}")
    # Everything except the Score line and the small row matches base output.
    keep = lambda text: [l for l in text.splitlines()
                         if not l.startswith("Score:") and not l.startswith("| small |")]
    check(f"{name} other-lines", keep(out) == keep(base_out),
          first_diff("\n".join(keep(out)), "\n".join(keep(base_out))))
    try:
        with open(json_path) as source:
            tiers = json.load(source)
        small = (tiers["small"]["model"], tiers["small"]["effort"])
        others_same = all(tiers[t] == base_tiers[t] for t in base_tiers if t != "small")
        check(f"{name} json", small == (model, effort) and others_same
              and set(tiers) == set(base_tiers),
              f"json small {small}, other tiers unchanged: {others_same}")
    except (OSError, ValueError, KeyError, TypeError) as error:
        check(f"{name} json", False, f"{type(error).__name__}: {error}")

code, out, err = select(RUN, "--min-small", "abc")
check("bad-value exit 2", code == 2 and err.strip() != "",
      f"exit {code}, stderr {err.strip()[-200:]!r}")

# Usage: the script with no arguments prints its docstring.
script = os.path.join(RUN, "plugins", "phased-delivery", "scripts", "select-models.py")
usage = subprocess.run([sys.executable, "-B", script], capture_output=True, text=True)
check("usage-docstring", "--min-small" in usage.stderr + usage.stdout,
      "usage text does not mention --min-small")
