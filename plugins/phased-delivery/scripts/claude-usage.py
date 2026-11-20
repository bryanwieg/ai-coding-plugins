#!/usr/bin/env python3
"""Report Claude plan usage from the saved status line JSON.

Usage: claude-usage.py

Reads claude-usage.json from $CLAUDE_CONFIG_DIR or ~/.claude. Prints one
line and exits 0 on pace, 1 ahead of pace, 2 nearly out, or 3 with no data.
Passing an argument prints this usage and exits 4.
"""

import datetime
import json
import os
import sys
import time


NEARLY_OUT = 90.0
AHEAD_POINTS = 10.0
FIVE_HOUR_AHEAD = 80.0


def describe(name, used, resets, elapsed):
    reset_time = datetime.datetime.fromtimestamp(resets, datetime.timezone.utc)
    pace = "" if elapsed is None else f", {elapsed:.0f}% of window elapsed"
    return f"{name} {used:g}% used{pace} (resets {reset_time:%Y-%m-%d %H:%M} UTC)"


def main(argv):
    if len(argv) > 1:
        print(__doc__, file=sys.stderr)
        return 4

    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    path = os.path.join(config_dir, "claude-usage.json")
    try:
        with open(path, encoding="utf-8") as saved:
            data = json.load(saved)
            modified = os.fstat(saved.fileno()).st_mtime

        limits = data.get("rate_limits") if isinstance(data, dict) else None
        if not isinstance(limits, dict):
            raise ValueError("missing or invalid rate_limits")

        now = time.time()
        windows = []
        for key, name, length in (
            ("five_hour", "5h window", 5 * 60 * 60),
            ("seven_day", "weekly", 7 * 24 * 60 * 60),
        ):
            if key not in limits:
                continue
            window = limits[key]
            if not isinstance(window, dict):
                raise ValueError(f"invalid {name} data")
            used, resets = window.get("used_percentage"), window.get("resets_at")
            if not (
                type(used) in (int, float) and 0 <= used <= 100
                and type(resets) in (int, float) and -float("inf") < resets < float("inf")
            ):
                raise ValueError(f"invalid {name} data")
            if resets <= now:
                continue

            if key == "seven_day":
                elapsed = min(100, max(0, 100 * (1 - (resets - now) / length)))
                ahead = used - elapsed >= AHEAD_POINTS
            else:
                elapsed = None
                ahead = used >= FIVE_HOUR_AHEAD
            level = 2 if used >= NEARLY_OUT else int(ahead)
            windows.append((describe(name, used, resets, elapsed), level))

        if not windows:
            raise ValueError("no active Claude usage windows")
        as_of = datetime.datetime.fromtimestamp(modified, datetime.timezone.utc)
    except FileNotFoundError:
        reason = "no saved Claude usage file"
    except (json.JSONDecodeError, UnicodeDecodeError, RecursionError):
        reason = "saved Claude usage file contains invalid JSON"
    except (OSError, OverflowError):
        reason = "unable to read Claude usage data"
    except ValueError as error:
        reason = str(error)
    else:
        descriptions, levels = zip(*windows)
        result = max(levels)
        status = ("on pace", "ahead of pace", "nearly out")[result]
        print("; ".join((*descriptions, f"as of {as_of:%Y-%m-%d %H:%M} UTC", status)))
        return result

    print(f"{reason}; run any Claude Code request with a status line set up")
    return 3


if __name__ == "__main__":
    sys.exit(main(sys.argv))
