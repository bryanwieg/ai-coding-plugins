import json
import os
from pathlib import Path
import subprocess

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "codex-build.sh"

COMPLETED = {"type": "turn.completed", "usage": {"input_tokens": 100, "output_tokens": 5}}
# A lapsed subscription (plan_type "free"), captured 2026-11-22: the plan's models are refused.
REFUSED = "The 'gpt-6.2-sol' model is not supported when using Codex with a ChatGPT account."


def run(tmp_path, events):
    """Run the script with a stub `codex` that prints EVENTS as JSON lines."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    (tmp_path / "events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
    stub = bin_dir / "codex"
    stub.write_text(f'#!/bin/sh\ncat "{tmp_path / "events.jsonl"}"\n')
    stub.chmod(0o755)
    env = {**os.environ, "PATH": f"{bin_dir}:{os.environ['PATH']}"}
    env.pop("CODEX_BUILD_SANDBOX", None)
    return subprocess.run(
        ["sh", SCRIPT, str(tmp_path), str(tmp_path / "prompt.md"), "m", "low", str(tmp_path / "out")],
        env=env, capture_output=True, text=True,
    )


@pytest.mark.parametrize(
    "events, code, message",
    [
        ([{"type": "turn.started"}, COMPLETED], 0, "Tokens: 105"),
        ([{"type": "turn.started"}, {"type": "error", "message": REFUSED},
          {"type": "turn.failed", "error": {"message": REFUSED}}], 6, "not supported"),
        ([{"type": "turn.failed", "error": {"message": "You've hit your usage limit. Try again later."}}],
         7, "out of quota"),
        ([{"type": "turn.failed", "error": {"message": "You've hit your usage limit. Upgrade to Plus to continue."}}],
         6, "could not run a turn"),
    ],
)
def test_outcomes(tmp_path, events, code, message):
    result = run(tmp_path, events)
    assert result.returncode == code
    assert message in result.stdout + result.stderr
