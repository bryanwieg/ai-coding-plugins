#!/bin/sh
# fake-claude.sh: stands in for `claude` on PATH in the driver's tests.
#
# FAKE_CLAUDE_PLAN is a file holding a JSON list of steps; each call takes the
# next one, counted by the lines of "$FAKE_CLAUDE_PLAN.calls" (one line of the
# call's arguments, as JSON, is added per call). A step, every field optional:
#   {"files":  {PATH: TEXT},            files to write
#    "brief":  {STAGE_FILE: {FIELD: VALUE}},  fields to set in that stage
#                                       file's brief; its record is kept
#    "report": TEXT,                    the final message (report.md)
#    "sleep":  SECONDS,                 silence after the edits, before the result
#    "exit":   N,                       the exit status (default 0)
#    "cost":   USD}                     total_cost_usd (default 0.01)
# Paths are relative to the directory claude runs in, the repository. It
# prints one assistant event (a thinking summary and a tool call, for the
# driver's live feed) and the result event claude-build.sh parses. A call past the last step
# exits 1 with a message on stderr and nothing printed.
# claude-build.sh's probe for --thinking-display: answer as a claude that knows it, without taking a step
case " $* " in *" --version "*) echo "error: option '--thinking-display <display>' argument is invalid" >&2; exit 1;; esac
exec python3 - "$@" <<'PY'
import json, os, sys, time

plan = os.environ["FAKE_CLAUDE_PLAN"]
steps = json.load(open(plan))
with open(plan + ".calls", "a+") as calls:
    calls.seek(0)
    index = len(calls.readlines())
    calls.write(json.dumps(sys.argv[1:]) + "\n")
if index >= len(steps):
    sys.exit(f"fake claude: call {index + 1} but the plan has {len(steps)} steps")
step = steps[index]
for path, text in step.get("files", {}).items():
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as f:
        f.write(text)
for path, fields in step.get("brief", {}).items():
    stage = json.load(open(path))
    with open(path, "w") as f:
        json.dump({**stage, "brief": {**stage["brief"], **fields}}, f, indent=1)
        f.write("\n")
time.sleep(step.get("sleep", 0))
usage = {"input_tokens": 100, "output_tokens": 5, "cache_read_input_tokens": 1000,
         "cache_creation_input_tokens": 20}
print(json.dumps({"type": "assistant", "message": {"content": [
    {"type": "thinking", "thinking": "fake thinking"},
    {"type": "tool_use", "name": "Bash", "input": {"command": "true"}}]}}))
print(json.dumps({"type": "result", "subtype": "success", "result": step.get("report", ""), "usage": usage,
                  "total_cost_usd": step.get("cost", 0.01)}))
sys.exit(step.get("exit", 0))
PY
