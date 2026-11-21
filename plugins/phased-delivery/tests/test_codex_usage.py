import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "codex-usage.py"


def run(tmp_path, stub_status=0, **env):
    """Run the script with only a stub `codex` (exiting stub_status) on PATH; None means no codex."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    if stub_status is not None:
        stub = bin_dir / "codex"
        stub.write_text('#!/bin/sh\nexit "$STUB_STATUS"\n')
        stub.chmod(0o755)
    base = {k: v for k, v in os.environ.items() if k != "AI_CODEX"}
    return subprocess.run(
        [sys.executable, SCRIPT],
        env={**base, "CODEX_HOME": str(tmp_path), "PATH": str(bin_dir),
             "STUB_STATUS": str(stub_status or 0), **env},
        capture_output=True, text=True,
    )


def write_log(tmp_path, primary_used=10, weekly_used=10, primary_reset=3600, weekly_reset=86400):
    now = time.time()
    limits = {
        "primary": {"used_percent": primary_used, "window_minutes": 300, "resets_at": now + primary_reset},
        "secondary": {"used_percent": weekly_used, "window_minutes": 10080, "resets_at": now + weekly_reset},
    }
    log = tmp_path / "sessions/2026/11/20/s.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"payload": {"rate_limits": limits}}) + "\n")


def test_no_sessions(tmp_path):
    assert run(tmp_path).returncode == 2


@pytest.mark.parametrize(
    "primary_used, weekly_used, primary_reset, weekly_reset, code, message",
    [
        (10, 10, 3600, 86400, 0, "room left"),
        (85, 10, 3600, 86400, 1, "over the maximum"),
        (10, 95, 3600, 86400, 1, "over the maximum"),
        (100, 10, -60, 86400, 0, "5h window reset since last Codex request"),
        (10, 100, 3600, -60, 0, "weekly reset since last Codex request"),
    ],
)
def test_usage_windows(tmp_path, primary_used, weekly_used, primary_reset, weekly_reset, code, message):
    write_log(tmp_path, primary_used, weekly_used, primary_reset, weekly_reset)
    result = run(tmp_path)
    assert result.returncode == code
    assert message in result.stdout


@pytest.mark.parametrize(
    "stub_status, env, code, message",
    [
        (0, {"AI_CODEX": "off"}, 3, "Codex is off (AI_CODEX=off)"),
        (None, {}, 3, "Codex is not installed"),
        (1, {}, 4, "Codex is not signed in; run: codex login --device-auth"),
        (0, {"AI_CODEX": "on"}, 0, "room left"),
    ],
)
def test_availability(tmp_path, stub_status, env, code, message):
    write_log(tmp_path)
    result = run(tmp_path, stub_status, **env)
    assert result.returncode == code
    assert result.stdout == message + "\n" if code else message in result.stdout
