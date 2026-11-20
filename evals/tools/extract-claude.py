"""extract-claude.py TRANSCRIPT.jsonl RUN_DIR: from a Claude Code subagent transcript, write log.txt, report.md (the hand-back message) and stats.json."""
import json
import sys

src, run_dir = sys.argv[1], sys.argv[2]
entries = [json.loads(line) for line in open(src) if line.strip()]

calls, results, last_text, handback = {}, {}, "", ""
order = []
out_tokens = in_tokens = 0
for e in entries:
    msg = e.get("message") or {}
    content = msg.get("content")
    if msg.get("role") == "assistant":
        usage = msg.get("usage") or {}
        out_tokens += usage.get("output_tokens", 0)
        in_tokens += (usage.get("input_tokens", 0) + usage.get("cache_read_input_tokens", 0)
                      + usage.get("cache_creation_input_tokens", 0))
        for block in content if isinstance(content, list) else []:
            if block.get("type") == "tool_use" and block.get("name") == "SubagentHandback":
                handback = block.get("input", {}).get("message", "")
            elif block.get("type") == "tool_use":
                if block["id"] not in calls:
                    order.append(block["id"])
                calls[block["id"]] = block
            elif block.get("type") == "text" and block.get("text", "").strip():
                last_text = block["text"]
    elif msg.get("role") == "user" and isinstance(content, list):
        for block in content:
            if block.get("type") == "tool_result":
                body = block.get("content")
                if isinstance(body, list):
                    body = " ".join(b.get("text", "") for b in body if isinstance(b, dict))
                results[block["tool_use_id"]] = (bool(block.get("is_error")), str(body or ""))


def describe(block):
    i = block.get("input", {})
    for key in ("command", "file_path", "pattern", "path"):
        if key in i:
            text = str(i[key]).replace("\n", " ⏎ ")
            return f"{key}={text[:300]}"
    return json.dumps(i)[:200]


lines = []
for n, cid in enumerate(order, 1):
    block = calls[cid]
    err, body = results.get(cid, (False, "(no result)"))
    first = " ".join(body.split())[:240]
    lines.append(f"{n:3d}. {block['name']} {describe(block)}\n     -> {'ERROR ' if err else ''}{first}")

open(f"{run_dir}/log.txt", "w").write("\n".join(lines) + "\n")
open(f"{run_dir}/report.md", "w").write((handback or last_text) + "\n")
json.dump({"tool_calls": len(order), "output_tokens": out_tokens, "input_tokens_total": in_tokens},
          open(f"{run_dir}/stats.json", "w"))
print(f"{run_dir.rsplit('/', 1)[-1]}: {len(order)} calls, {out_tokens} output tokens")
