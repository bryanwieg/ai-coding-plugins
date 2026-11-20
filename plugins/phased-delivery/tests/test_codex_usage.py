import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "codex-usage.py"


def test_no_sessions(tmp_path):
    result = subprocess.run([sys.executable, SCRIPT], env={**os.environ, "CODEX_HOME": str(tmp_path)})
    assert result.returncode == 2


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
    now = time.time()
    limits = {
        "primary": {"used_percent": primary_used, "window_minutes": 300, "resets_at": now + primary_reset},
        "secondary": {"used_percent": weekly_used, "window_minutes": 10080, "resets_at": now + weekly_reset},
    }
    log = tmp_path / "sessions/2026/11/20/s.jsonl"
    log.parent.mkdir(parents=True)
    log.write_text(json.dumps({"payload": {"rate_limits": limits}}) + "\n")

    result = subprocess.run(
        [sys.executable, SCRIPT], env={**os.environ, "CODEX_HOME": str(tmp_path)},
        capture_output=True, text=True,
    )
    assert result.returncode == code
    assert message in result.stdout
