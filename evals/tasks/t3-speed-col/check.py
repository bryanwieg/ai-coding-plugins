"""Hidden checks for t3-speed-col (run by check.sh)."""
import json
import os
import sys

sys.path.insert(0, os.path.join(os.environ["KIT"], "lib"))
from checklib import BASELINE, REPORT, RUN, WORK, check, first_diff, select  # noqa: E402

HEADER = "| Tier | Model | Effort | Score | Cost | Speed | Report row |"
SEPARATOR = "| --- | --- | --- | --- | --- | --- | --- |"


def expected_output(base_out, report):
    """Base output with the Speed column inserted after Cost."""
    speeds = {r["name"]: r["output_tokens_per_second"] for r in report["rows"]}
    lines = []
    for line in base_out.splitlines():
        if line.startswith("| Tier |"):
            lines.append(HEADER)
        elif line.startswith("| --- |"):
            lines.append(SEPARATOR)
        elif line.startswith("| ") and line.split("|")[1].strip() in ("small", "middle", "middle+", "top"):
            cells = line.split(" | ")
            name = cells[-1].rstrip(" |")
            value = speeds[name]
            cells.insert(5, "n/a" if value is None else f"{value:.0f}")
            lines.append(" | ".join(cells))
        else:
            lines.append(line)
    return "\n".join(lines) + "\n"


def compare(label, report_path):
    with open(report_path) as source:
        report = json.load(source)
    code, base_out, err = select(BASELINE, report=report_path)
    if code != 0:
        sys.exit(f"FAIL harness: base script failed: {err}")
    want = expected_output(base_out, report)
    code, out, err = select(RUN, report=report_path)
    if not check(f"{label} exit", code == 0, f"exit {code}: {err.strip()[-200:]}"):
        return
    got_lines, want_lines = out.splitlines(), want.splitlines()
    table = lambda ls: [l for l in ls if l.startswith("| ")]
    got_table, want_table = table(got_lines), table(want_lines)
    check(f"{label} header", got_table[:1] == want_table[:1],
          f"got {got_table[:1]}")
    check(f"{label} separator", got_table[1:2] == want_table[1:2],
          f"got {got_table[1:2]}")
    check(f"{label} rows", got_table[2:] == want_table[2:],
          first_diff("\n".join(got_table[2:]), "\n".join(want_table[2:])))
    rest = lambda ls: [l for l in ls if not l.startswith("| ")]
    check(f"{label} other-lines", rest(got_lines) == rest(want_lines),
          first_diff("\n".join(rest(got_lines)), "\n".join(rest(want_lines))))


real_report = os.path.join(BASELINE, REPORT)
compare("fixture", real_report)

# Same, with the small tier's report row missing its speed: expect "n/a".
with open(real_report) as source:
    report = json.load(source)
for row in report["rows"]:
    if row["name"] == "Claude Haiku 5.5 (Xhigh)":
        row["output_tokens_per_second"] = None
missing = os.path.join(WORK, "report-missing-speed.json")
with open(missing, "w") as out:
    json.dump(report, out)
compare("missing-speed", missing)
