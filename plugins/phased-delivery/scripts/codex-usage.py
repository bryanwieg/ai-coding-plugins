#!/usr/bin/env python3
"""Report Codex plan usage from its newest local session log.

Usage: codex-usage.py [--max-window PCT] [--max-weekly PCT]

Codex has no usage command; each session it runs records its rate limits in
~/.codex/sessions (or $CODEX_HOME/sessions). The figures are as of the last
Codex request, not live.

Prints one line, then exits 0 when both limits are below the maximums
(defaults: 80% of the short window, 90% of the weekly one), 1 when either is
at or above, 2 when no usage data is found. A window that has reset since
the last Codex request counts as 0% used.
"""

import datetime
import glob
import json
import os
import sys
import time


def latest_limits():
    home = os.environ.get("CODEX_HOME") or os.path.expanduser("~/.codex")
    logs = sorted(glob.glob(os.path.join(home, "sessions", "*", "*", "*", "*.jsonl")),
                  key=os.path.getmtime, reverse=True)
    for path in logs:
        found = None
        with open(path) as log:
            for line in log:
                if '"rate_limits"' not in line:
                    continue
                found = find_key(json.loads(line), "rate_limits") or found
        if found:
            return found
    return None


def find_key(value, key):
    if isinstance(value, dict):
        if isinstance(value.get(key), dict):
            return value[key]
        children = value.values()
    elif isinstance(value, list):
        children = value
    else:
        return None
    for child in children:
        hit = find_key(child, key)
        if hit:
            return hit
    return None


def describe(name, window):
    resets = datetime.datetime.fromtimestamp(window["resets_at"], datetime.timezone.utc)
    return f"{name} {window['used_percent']:g}% used (resets {resets:%Y-%m-%d %H:%M} UTC)"


def main(argv):
    limits = {"--max-window": 80.0, "--max-weekly": 90.0}
    args = argv[1:]
    if len(args) % 2 or any(flag not in limits for flag in args[::2]):
        raise SystemExit(__doc__)
    for flag, value in zip(args[::2], args[1::2]):
        limits[flag] = float(value)
    found = latest_limits()
    if not found or not found.get("primary"):
        print("no Codex usage data found; run any Codex request first")
        return 2
    primary, weekly = found["primary"], found.get("secondary")
    now = time.time()
    parts = []
    over = False
    for name, window, maximum in (
        (f"{primary['window_minutes'] // 60}h window", primary, limits["--max-window"]),
        ("weekly", weekly, limits["--max-weekly"]),
    ):
        if not window:
            continue
        used = window["used_percent"]
        if window["resets_at"] <= now:
            parts.append(f"{name} reset since last Codex request")
            used = 0
        else:
            parts.append(describe(name, window))
        over = over or used >= maximum
    print("; ".join(parts) + ("; over the maximum" if over else "; room left"))
    return 1 if over else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
