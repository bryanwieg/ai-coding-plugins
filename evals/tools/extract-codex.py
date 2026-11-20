"""extract-codex.py RUN_DIR: codex-events.jsonl -> log.txt, stats.json (report.md comes from -o)."""
import json
import sys

d = sys.argv[1]
events = [json.loads(l) for l in open(f"{d}/codex-events.jsonl") if l.strip()]
lines, n, usage = [], 0, {}
for e in events:
    if e.get("type") == "turn.completed":
        usage = e.get("usage") or {}
    if e.get("type") != "item.completed":
        continue
    item = e["item"]
    kind = item.get("type")
    if kind == "command_execution":
        n += 1
        out = " ".join(str(item.get("aggregated_output", "")).split())[:240]
        lines.append(f"{n:3d}. Bash command={str(item.get('command', ''))[:300]}\n"
                     f"     -> exit {item.get('exit_code')} {out}")
    elif kind == "file_change":
        n += 1
        changes = ", ".join(f"{c.get('kind')} {c.get('path')}" for c in item.get("changes", []))
        lines.append(f"{n:3d}. Edit {changes}\n     -> {item.get('status')}")
    elif kind == "agent_message":
        lines.append(f"     (message) {' '.join(str(item.get('text', '')).split())[:240]}")
open(f"{d}/log.txt", "w").write("\n".join(lines) + "\n")
json.dump({"tool_calls": n, "output_tokens": usage.get("output_tokens", 0),
           "input_tokens_total": usage.get("input_tokens", 0), "usage": usage},
          open(f"{d}/stats.json", "w"))
print(f"{n} calls, usage {usage}")
