#!/usr/bin/env python3
"""Report Codex plan usage from its newest local session log.

Usage: codex-usage.py [--max-window PCT] [--max-weekly PCT] [--recheck] [--record-off CAUSE]

Codex has no usage command; each session it runs records its rate limits in
~/.codex/sessions (or $CODEX_HOME/sessions). The figures are as of the last
Codex request, not live.

Prints one line, then exits 0 when both limits are below the maximums
(defaults: 80% of the short window, 90% of the weekly one), 1 when either is
at or above, 2 when no usage data is found. A window that has reset since
the last Codex request counts as 0% used.

Before reading usage it exits 3 when Codex is off (AI_CODEX=off) or not
installed, 4 when `codex login status` says it is not signed in, and 5 when
that check takes over 5 seconds (nothing cached).

Availability is cached for the local day in codex-availability.json in
$CLAUDE_CONFIG_DIR (or ~/.claude). While it says off, the script exits 3
without running codex; while it says on, it skips `codex login status`.
--recheck ignores the cache and checks again; --record-off CAUSE caches off
for today (after a failed build) and exits 3. AI_CODEX is never cached.
"""

import argparse
import datetime
import glob
import json
import os
import shutil
import subprocess
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


def cache_path():
    config_dir = os.environ.get("CLAUDE_CONFIG_DIR") or os.path.expanduser("~/.claude")
    return os.path.join(config_dir, "codex-availability.json")


def read_cache(today):
    """Today's cached availability, or None when missing, stale or malformed."""
    try:
        with open(cache_path(), encoding="utf-8") as saved:
            cache = json.load(saved)
    except (OSError, ValueError):
        return None
    if (not isinstance(cache, dict) or cache.get("date") != today
            or not isinstance(cache.get("on"), bool)):
        return None
    return cache


def write_cache(today, on, cause=None):
    entry = {"date": today, "on": on, **({} if on else {"cause": cause})}
    try:
        with open(cache_path(), "w", encoding="utf-8") as saved:
            json.dump(entry, saved)
    except OSError:
        pass  # an unwritable config folder only means the answer is not cached


def off_today(cause):
    print(f"Codex is off today: {cause} (cached; run codex-usage.py --recheck after fixing it)")
    return 3


def main(argv):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--max-window", type=float, default=80.0)
    parser.add_argument("--max-weekly", type=float, default=90.0)
    parser.add_argument("--recheck", action="store_true")
    parser.add_argument("--record-off", metavar="CAUSE")
    args = parser.parse_args(argv[1:])
    if os.environ.get("AI_CODEX") == "off":
        print("Codex is off (AI_CODEX=off)")
        return 3
    today = datetime.date.today().isoformat()
    if args.record_off is not None:
        write_cache(today, False, args.record_off)
        return off_today(args.record_off)
    cache = None if args.recheck else read_cache(today)
    if cache and not cache["on"]:
        return off_today(cache.get("cause", "cause not recorded"))
    if shutil.which("codex") is None:
        write_cache(today, False, "not installed")
        print("Codex is not installed")
        return 3
    if not cache:
        try:
            status = subprocess.run(["codex", "login", "status"], capture_output=True, timeout=5)
        except subprocess.TimeoutExpired:
            print("Codex check timed out: `codex login status` took over 5 seconds")
            return 5
        if status.returncode != 0:
            write_cache(today, False, "not signed in; run codex login --device-auth")
            print("Codex is not signed in; run: codex login --device-auth")
            return 4
        write_cache(today, True)
    found = latest_limits()
    if not found or not found.get("primary"):
        print("no Codex usage data found; run any Codex request first")
        return 2
    primary, weekly = found["primary"], found.get("secondary")
    now = time.time()
    parts = []
    over = False
    for name, window, maximum in (
        (f"{primary['window_minutes'] // 60}h window", primary, args.max_window),
        ("weekly", weekly, args.max_weekly),
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
