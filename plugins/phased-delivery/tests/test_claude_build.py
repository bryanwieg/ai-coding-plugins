import json
import os
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "claude-build.sh"

USAGE = {"input_tokens": 100, "output_tokens": 5, "cache_read_input_tokens": 1000,
         "cache_creation_input_tokens": 20}
BUILT = {"type": "result", "subtype": "success", "result": "Built it.", "usage": USAGE,
         "total_cost_usd": 0.1234}
# A real budget stop (2026-11-23) reports zero usage and the counts under modelUsage.
CAPPED = {"type": "result", "subtype": "error_max_budget_usd", "total_cost_usd": 0.5,
          "usage": {k: 0 for k in USAGE},
          "modelUsage": {"claude-haiku-5-5": {"inputTokens": 2, "outputTokens": 188,
                                              "cacheReadInputTokens": 12427,
                                              "cacheCreationInputTokens": 9070}}}


def run(tmp_path, events, code=0, permissions=None):
    """Run the script with a stub `claude` that records its arguments and prints EVENTS."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "events.jsonl").write_text("not json\n" + "".join(json.dumps(e) + "\n" for e in events))
    (tmp_path / "prompt.md").write_text("Build stage 03.1.")
    stub = bin_dir / "claude"
    stub.write_text(f'#!/bin/sh\nprintf "%s\\n" "$@" > "{tmp_path / "args.txt"}"\n'
                    f'echo "claude failed" >&2\ncat "{tmp_path / "events.jsonl"}"\nexit {code}\n')
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    env.pop("CLAUDE_BUILD_PERMISSIONS", None)
    if permissions:
        env["CLAUDE_BUILD_PERMISSIONS"] = permissions
    return subprocess.run(
        ["sh", SCRIPT, str(tmp_path), str(tmp_path / "prompt.md"), "opus", "high", "2.5", str(tmp_path / "out")],
        env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize(
    "events, status, code, message",
    [
        ([{"type": "system"}, BUILT], 0, 0, "Tokens: 1125\nCost: 0.12"),
        ([CAPPED], 1, 8, "Tokens: 21687"),
        ([{"type": "system"}], 0, 1, "claude failed"),
        ([], 3, 3, "Tokens: unknown\nCost: unknown"),
        # an error result is never "built", even when claude exits 0
        ([{**BUILT, "subtype": "error_during_execution", "is_error": True}], 0, 1, "error result"),
    ],
)
def test_outcomes(tmp_path, events, status, code, message):
    result = run(tmp_path, events, status)
    assert result.returncode == code
    assert message in result.stdout + result.stderr
    args = (tmp_path / "args.txt").read_text().splitlines()
    assert args[:2] == ["-p", "Build stage 03.1."]
    for flag, value in [("--model", "opus"), ("--effort", "high"), ("--max-budget-usd", "2.5"),
                        ("--permission-mode", "acceptEdits"), ("--output-format", "stream-json"),
                        ("--settings", '{"enabledPlugins":{"phased-delivery@ai-coding-plugins":false}}')]:
        assert args[args.index(flag) + 1] == value
    assert "--no-session-persistence" in args
    if events and events[-1] is BUILT:
        assert (tmp_path / "out" / "report.md").read_text() == "Built it."


def test_permissions_setting(tmp_path):
    result = run(tmp_path, [BUILT], permissions="bypassPermissions")
    args = (tmp_path / "args.txt").read_text().splitlines()
    assert result.returncode == 0 and args[args.index("--permission-mode") + 1] == "bypassPermissions"
    other = tmp_path / "other"
    other.mkdir()
    assert run(other, [BUILT], permissions="default").returncode == 2
    assert not (other / "args.txt").exists()  # refused before running claude
