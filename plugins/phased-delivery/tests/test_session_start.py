import datetime
import json
import os
from pathlib import Path
import subprocess

HOOK = Path(__file__).resolve().parents[1] / "hooks" / "session-start.sh"


def hook_context(tmp_path):
    """Run the hook outside any git repository with a stub `codex` that reports signed in."""
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "codex"
    stub.write_text("#!/bin/sh\nexit 0\n")
    stub.chmod(0o755)
    base = {k: v for k, v in os.environ.items() if k != "AI_CODEX"}
    result = subprocess.run(
        ["sh", str(HOOK)], cwd=tmp_path, capture_output=True, text=True, check=True,
        env={**base, "CLAUDE_CONFIG_DIR": str(tmp_path), "CODEX_HOME": str(tmp_path),
             "PATH": f"{bin_dir}{os.pathsep}{base['PATH']}"},
    )
    return json.loads(result.stdout)["hookSpecificOutput"]["additionalContext"]


def test_codex_off_line(tmp_path):
    today = datetime.date.today().isoformat()
    cache = tmp_path / "codex-availability.json"
    cache.write_text(json.dumps({"date": today, "on": False, "cause": "not signed in"}))
    off = hook_context(tmp_path)
    assert "Codex is off today" in off
    assert "do not consider Codex this session" in off
    assert "codex-usage.py --recheck" in off

    cache.write_text(json.dumps({"date": today, "on": True}))
    assert "Codex" not in hook_context(tmp_path)


def test_lists_phase_folders(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    (tmp_path / ".gitignore").write_text(".ai-scratchpad/\n")
    for where, name, status in (("docs/plans", "01-a", "planned"), ("docs/plans", "02-b", "built abc123"),
                                (".ai-scratchpad/plans", "01-c", "planned")):
        d = tmp_path / where / "x" / name
        d.mkdir(parents=True)
        (d / "phase.md").write_text(
            f"# Phase\n\nImplement with the implement-in-phases skill; do not build.\nStatus: {status}\n")
    context = hook_context(tmp_path)
    assert "- docs/plans/x/01-a/phase.md (planned)" in context
    assert "02-b" not in context
    assert "- .ai-scratchpad/plans/x/01-c/phase.md (planned)" in context  # ignored, still listed
