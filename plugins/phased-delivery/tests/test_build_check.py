import json
import os
from pathlib import Path
import subprocess

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPTS / "build-check.py"
PHASE = "docs/plan/01-demo.md"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

PHASE_TEXT = """# Phase 01: Demo

Implement with the implement-in-phases skill; do not build from this file
without it. Model tiers map to models in [models.md](models.md).
Status: planned
Before: nothing.
After: a and b exist.

## Stages

| Stage | Goal | Tier | Order | Status |
| --- | --- | --- | --- | --- |
| 01.1 | Write a | middle | first | planned |
| 01.2 | Write b | small | after 01.1 | planned |

## Notes
none
"""

REVISION = {
    "phase": "01",
    "stages": [
        {"id": "01.1", "title": "Write a", "files": [{"path": "src/a.txt", "action": "edit"},
                                                    {"path": "src/done.txt", "action": "create"}],
         "checks": ["test -f src/done.txt"], "scores": "J1F1R0C0K0P0V0S0", "tier": "middle"},
        {"id": "01.2", "title": "Write b", "files": [{"path": "src/b.txt", "action": "edit"}],
         "checks": [], "scores": "J0F0R0C0K0P0V0S0", "tier": "small"},
    ],
    "assumptions": [],
    "adjustments": [],
}

REVIEW = {"findings": [], "verdict": "ready"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], env={**os.environ, **GIT_ENV},
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    """A git repository with one commit holding a phase file, its revision JSON and two stage files."""
    r = tmp_path / "repo"
    (r / "src").mkdir(parents=True)
    (r / "docs/plan/.build").mkdir(parents=True)
    (r / "src/a.txt").write_text("a\n")
    (r / "src/b.txt").write_text("b\n")
    (r / "src/other.txt").write_text("other\n")
    (r / PHASE).write_text(PHASE_TEXT)
    (r / "docs/plan/.build/01-revision.json").write_text(json.dumps(REVISION))
    git(r, "init", "-q")
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base")
    return r


def bc(repo, *args):
    return subprocess.run(["python3", str(SCRIPT), *args], cwd=repo, env={**os.environ, **GIT_ENV},
                          capture_output=True, text=True)


def record(repo, stage, model="opus", effort="high", code=0, tokens="1200", cost="0.40", *extra):
    return bc(repo, "record", PHASE, stage, "--tool", "claude-code", "--model", model, "--effort", effort,
              "--exit", str(code), "--tokens", tokens, "--cost", cost, *extra)


def build_a(repo):
    (repo / "src/a.txt").write_text("a2\n")
    (repo / "src/done.txt").write_text("done\n")


def message(repo, rev="HEAD"):
    return git(repo, "log", "-1", "--format=%B", rev)


def changed(repo, rev="HEAD"):
    return git(repo, "show", "--name-only", "--format=", rev).split()


def stats(repo):
    return subprocess.run(["sh", str(SCRIPTS / "stage-stats.sh"), "HEAD"], cwd=repo,
                          capture_output=True, text=True, check=True).stdout


def test_accepted_stage_commit(repo):
    assert bc(repo, "start", PHASE).returncode == 0
    build_a(repo)
    result = record(repo, "01.1", "opus", "high", 0, "1200", "0.40", "--tool-calls", "7")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["result"] == "accepted"
    done = bc(repo, "commit", PHASE, "01.1", "--extra-trailer", "Co-Authored-By: x <x@example.invalid>")
    assert done.returncode == 0, done.stderr
    assert sorted(changed(repo)) == ["src/a.txt", "src/done.txt"]
    msg = message(repo)
    assert msg.startswith("01.1 Write a")
    for line in ("Stage: 01.1", f"Plan: {PHASE}", "Tier: middle", "Tool: claude-code", "Model: opus",
                 "Effort: high", "Attempt: 1", "Tokens: 1200", "Cost: 0.40", "Tool-Calls: 7",
                 "Co-Authored-By: x <x@example.invalid>"):
        assert line in msg
    assert "| opus | high | claude-code | 1 | 1/1 |" in stats(repo)
    text = (repo / PHASE).read_text()
    assert "| 01.1 | Write a | middle | first | done |" in text
    assert "Status: in progress (stages done: 01.1)" in text


def test_outside_change_fails(repo):
    bc(repo, "start", PHASE)
    build_a(repo)
    (repo / "src/other.txt").write_text("changed\n")
    (repo / "src/__pycache__").mkdir()
    (repo / "src/__pycache__/x.pyc").write_text("cache")
    (repo / "src/b.txt").write_text("b2\n")  # stage 01.2 has no commit yet: not outside
    result = record(repo, "01.1")
    assert result.returncode == 1
    assert json.loads(result.stdout)["outside"] == ["src/other.txt"]


def test_failed_check_then_retry(repo):
    bc(repo, "start", PHASE)
    (repo / "src/a.txt").write_text("a2\n")
    first = record(repo, "01.1", "haiku", "high", 0, "500", "0.10")
    assert first.returncode == 1
    assert json.loads(first.stdout)["checks"] == [{"cmd": "test -f src/done.txt", "exit": 1}]
    (repo / "src/done.txt").write_text("done\n")
    second = record(repo, "01.1", "opus", "medium", 0, "900", "0.30")
    assert second.returncode == 0
    assert bc(repo, "commit", PHASE, "01.1").returncode == 0
    msg = message(repo)
    assert "Attempt: 2" in msg
    assert "Earlier-Attempt: haiku high 500 check failed" in msg


def test_can_try_refuses_repeat(repo):
    bc(repo, "start", PHASE)
    (repo / "src/a.txt").write_text("a2\n")
    assert record(repo, "01.1", "opus", "high").returncode == 1
    assert record(repo, "01.1", "sonnet", "high", 1, "unknown", "unknown").returncode == 4
    assert bc(repo, "can-try", PHASE, "01.1", "opus", "high").returncode == 1
    assert bc(repo, "can-try", PHASE, "01.1", "sonnet", "high").returncode == 0
    assert bc(repo, "can-try", PHASE, "01.1", "fable", "low").returncode == 0


def test_premium_spend(repo):
    bc(repo, "start", PHASE)
    build_a(repo)
    record(repo, "01.1", "fable", "low", 0, "800", "1.25", "--premium")
    record(repo, "review", "fable", "high", 0, "unknown", "unknown", "--cap", "3.00", "--premium")
    record(repo, "01.2", "opus", "high", 0, "100", "2.00")
    result = bc(repo, "spend", PHASE)
    assert result.stdout.strip() == "4.25"


def test_preexisting_edits_left_alone(repo):
    (repo / "src/other.txt").write_text("mine\n")
    bc(repo, "start", PHASE)
    build_a(repo)
    assert record(repo, "01.1").returncode == 0
    assert bc(repo, "commit", PHASE, "01.1").returncode == 0
    assert "src/other.txt" not in changed(repo)
    assert " M src/other.txt" in git(repo, "status", "--porcelain")


def test_invalid_json_refused(repo):
    bad = json.loads(json.dumps(REVISION))
    del bad["stages"][0]["checks"]
    (repo / "docs/plan/.build/01-revision.json").write_text(json.dumps(bad))
    result = bc(repo, "start", PHASE)
    assert result.returncode == 1
    assert "checks" in result.stdout
    assert not (repo / "docs/plan/.build/01-ledger.json").exists()

    (repo / "docs/plan/.build/01-revision.json").write_text(json.dumps(REVISION))
    assert bc(repo, "start", PHASE).returncode == 0
    head = git(repo, "rev-parse", "HEAD")
    review = {"findings": [{"type": "style", "severity": "blocking", "stage": "01.1", "file": "src/a.txt",
                            "line": 1, "evidence": "x", "action": "fix"}], "verdict": "not-ready"}
    (repo / "docs/plan/.build/01-review.json").write_text(json.dumps(review))
    result = bc(repo, "finish", PHASE)
    assert result.returncode == 1
    assert "type" in result.stdout
    assert git(repo, "rev-parse", "HEAD") == head


def test_finish_phase(repo):
    bc(repo, "start", PHASE)
    build_a(repo)
    record(repo, "01.1")
    bc(repo, "commit", PHASE, "01.1")
    (repo / "docs/plan/.build/01-review.json").write_text(json.dumps(REVIEW))
    assert bc(repo, "finish", PHASE).returncode == 1  # 01.2 has no commit
    (repo / "src/b.txt").write_text("b2\n")
    record(repo, "01.2", "haiku", "high")
    bc(repo, "commit", PHASE, "01.2")
    stage_commit = git(repo, "rev-parse", "--short", "HEAD").strip()
    result = bc(repo, "finish", PHASE)
    assert result.returncode == 0, result.stdout + result.stderr
    assert f"Status: built {stage_commit}" in (repo / PHASE).read_text()
    assert f"Phase: {PHASE}" in message(repo)
    assert set(changed(repo)) >= {PHASE, "docs/plan/.build/01-ledger.json", "docs/plan/.build/01-review.json"}
    assert git(repo, "status", "--porcelain") == ""


def test_fix_commit(repo):
    bc(repo, "start", PHASE)
    build_a(repo)
    record(repo, "01.1")
    bc(repo, "commit", PHASE, "01.1")
    (repo / "src/a.txt").write_text("a3\n")
    assert record(repo, "01.1", "sonnet", "medium", 0, "300", "0.05", "--fix").returncode == 0
    assert bc(repo, "commit", PHASE, "01.1").returncode == 0
    msg = message(repo)
    assert "Fixes-Stage: 01.1" in msg and "Stage: 01.1\n" not in msg.replace("Fixes-Stage", "")
    assert "| opus | high | claude-code | 1 | 1/1 | 0/1 | 0 | 1 |" in stats(repo)
