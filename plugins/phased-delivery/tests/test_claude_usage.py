import datetime
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "claude-usage.py"
HOUR = 60 * 60
DAY = 24 * HOUR
SETUP_HINT = "run any Claude Code request with a status line set up"


@pytest.mark.parametrize(
    "contents",
    [
        None,
        "invalid JSON",
        "{}",
        "null",
        '{"rate_limits": []}',
        '{"rate_limits": {"seven_day": null}}',
        '{"rate_limits": {"seven_day": {"resets_at": 0}}}',
        '{"rate_limits": {"seven_day": {"used_percentage": "20", "resets_at": 0}}}',
        '{"rate_limits": {"seven_day": {"used_percentage": 20, "resets_at": true}}}',
        '{"rate_limits": {"seven_day": {"used_percentage": 20, "resets_at": 1e100}}}',
    ],
)
def test_no_data(tmp_path, monkeypatch, contents):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    if contents is not None:
        (tmp_path / "claude-usage.json").write_text(contents, encoding="utf-8")

    result = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)

    assert result.returncode == 3
    assert result.stderr == ""
    assert len(result.stdout.splitlines()) == 1
    assert result.stdout.rstrip().endswith(SETUP_HINT)


@pytest.mark.parametrize(
    "windows, expected, descriptions, status",
    [
        ({"seven_day": (20, 3.5 * DAY)}, 0, ("weekly 20% used, 50% of window elapsed",), "on pace"),
        ({"seven_day": (50, 5 * DAY)}, 1, ("weekly 50% used, 29% of window elapsed",), "ahead of pace"),
        ({"five_hour": (85, HOUR)}, 1, ("5h window 85% used",), "ahead of pace"),
        ({"seven_day": (92, 5 * DAY)}, 2, ("weekly 92% used, 29% of window elapsed",), "nearly out"),
        ({"five_hour": (95, HOUR)}, 2, ("5h window 95% used",), "nearly out"),
        (
            {"seven_day": (90, 8 * DAY), "five_hour": (80, HOUR)},
            2,
            ("5h window 80% used", "weekly 90% used, 0% of window elapsed"),
            "nearly out",
        ),
        ({"five_hour": (12, HOUR), "seven_day": (99, -HOUR)}, 0, ("5h window 12% used",), "on pace"),
        ({"seven_day": (99, -HOUR)}, 3, (), "no active Claude usage windows"),
    ],
)
def test_usage(tmp_path, monkeypatch, windows, expected, descriptions, status):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    now = time.time()
    path = tmp_path / "claude-usage.json"
    path.write_text(
        json.dumps({"rate_limits": {
            key: {"used_percentage": used, "resets_at": now + remaining}
            for key, (used, remaining) in windows.items()
        }}),
        encoding="utf-8",
    )
    os.utime(path, (now - HOUR, now - HOUR))

    result = subprocess.run([sys.executable, SCRIPT], capture_output=True, text=True)

    assert result.returncode == expected
    assert result.stderr == ""
    assert len(result.stdout.splitlines()) == 1
    if expected == 3:
        assert result.stdout == f"{status}; {SETUP_HINT}\n"
    else:
        reset_times = (
            datetime.datetime.fromtimestamp(now + windows[key][1], datetime.timezone.utc)
            for key in ("five_hour", "seven_day")
            if key in windows and windows[key][1] > 0
        )
        parts = [
            f"{description} (resets {reset:%Y-%m-%d %H:%M} UTC)"
            for description, reset in zip(descriptions, reset_times)
        ]
        modified = datetime.datetime.fromtimestamp(path.stat().st_mtime, datetime.timezone.utc)
        assert result.stdout == "; ".join((*parts, f"as of {modified:%Y-%m-%d %H:%M} UTC", status)) + "\n"


def test_arguments(tmp_path, monkeypatch):
    monkeypatch.setenv("CLAUDE_CONFIG_DIR", str(tmp_path))
    result = subprocess.run([sys.executable, SCRIPT, "--help"], capture_output=True, text=True)

    assert result.returncode == 4
    assert result.stdout == ""
    assert "Usage: claude-usage.py" in result.stderr
