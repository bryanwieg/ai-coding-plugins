import json
import os
from pathlib import Path
import subprocess
import sys

import pytest


TESTS = Path(__file__).resolve().parent
SCRIPTS = TESTS.parent / "scripts"
PROFILES = TESTS / "fixtures" / "profiles.json"
PLAN_DIR = "docs/plan"
PHASE = PLAN_DIR + "/01-demo"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

# One pair only, so a stage's ladder is used up by its first failed build.
AVAILABLE = {"tool": "claude-code", "subagent_model_choice": "allowed",
             "models": [{"id": "gpt-9-sol", "efforts": ["high"]}]}

PLAN = {"description": "Demo", "goal": "one and two exist.", "why": "w",
        "size": {"verdict": "full", "evidence": ["two stages"]},
        "outcomes": [{"id": "O1", "title": "one", "observable": "one exists", "how_to_check": "read it",
                      "sources": [{"doc": "spec", "section": "Goals", "quote": "one and two exist"}]}],
        "decisions": [], "existing": [],
        "phases": [{"phase": "01", "dir": "01-demo", "name": "Demo", "kind": "behaviour"}]}

PHASE_JSON = {"brief": {"role": "r", "why": "w", "how": "h", "before": "nothing.",
                        "after": "one and two exist.", "assumptions": [], "test_budget": "1 s", "notes": []},
              "record": {}}


def stage(title, order, path, tests=()):
    return {"brief": {"revision": 1, "title": title, "order": order, "lines": "under 30",
                      "files": [{"path": path, "action": "create", "role": "the file"}],
                      "provides": [], "uses": [], "goal": title,
                      "context": {"builds_on": [], "code_read": [], "design": []},
                      "behaviour": [], "external_inputs": [], "tests": list(tests), "done_when": ["it exists"],
                      "checks": [f"test -f {path}"], "out_of_scope": [],
                      "model_basis": dict.fromkeys("JFRCKPVS", 0)},
            "record": {}}


STAGES = {
    "01.1": stage("Write one", "first", "src/one.txt",
                  [{"test": "src/one.txt", "kind": "outcome", "action": "writes", "proves": "one exists",
                    "outcome": "O1"}]),
    "01.2": stage("Write two", "after 01.1", "src/two.txt"),
}

# fake claude steps
REVISED_NOTHING = {"report": "Nothing to change.\nResult: unchanged"}
BUILD_ONE = {"files": {"src/one.txt": "one\n"}, "report": "Wrote one.\nResult: done"}
BUILD_TWO = {"files": {"src/two.txt": "two\n"}, "report": "Wrote two.\nResult: done"}
FAILED_TWO = {"report": "Wrote two."}  # writes nothing, so the stage's check fails
REVIEW = {"files": {PHASE + "/review.json": json.dumps({"findings": [], "verdict": "ready"})},
          "report": "Reviewed."}


def raise_two(revision):
    return {"brief": {PHASE + "/01.2.json": {"revision": revision}}, "report": "Revised 01.2.\nResult: revised"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], env={**os.environ, **GIT_ENV},
                          capture_output=True, text=True, check=True).stdout


@pytest.fixture
def repo(tmp_path):
    """A git repository with one commit: a plan with one phase of two stages, each creating a file."""
    r = tmp_path / "repo"
    (r / "src").mkdir(parents=True)
    (r / PHASE).mkdir(parents=True)
    (r / "src/base.txt").write_text("base\n")
    (r / "spec.md").write_text("Goals: one and two exist.\n")
    files = {"plan.json": {**PLAN, "docs": {"spec": "spec.md"}}, "models-available.json": AVAILABLE,
             "01-demo/phase.json": PHASE_JSON, **{f"01-demo/{sid}.json": s for sid, s in STAGES.items()}}
    for name, data in files.items():
        (r / PLAN_DIR / name).write_text(json.dumps(data))
    subprocess.run([sys.executable, SCRIPTS / "select-models.py", r / PLAN_DIR / "models-available.json",
                    "--profiles", PROFILES, "--out", r / PLAN_DIR / "models.md"], check=True, capture_output=True)
    subprocess.run([sys.executable, SCRIPTS / "plan-check.py", r / PLAN_DIR, "--repo", r], check=True,
                   capture_output=True)
    git(r, "init", "-q")
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base")
    return r


def drive(repo, steps, stall=None):
    """Run the driver on the phase with a fake claude that takes STEPS in order (a new list per run)."""
    tmp = repo.parent
    bin_dir = tmp / "bin"
    bin_dir.mkdir(exist_ok=True)
    stub = bin_dir / "claude"
    stub.write_text(f'#!/bin/sh\nexec sh "{TESTS / "fake-claude.sh"}" "$@"\n')
    stub.chmod(0o755)
    plan = tmp / "steps.json"
    plan.write_text(json.dumps(steps))
    Path(f"{plan}.calls").unlink(missing_ok=True)
    env = {**os.environ, **GIT_ENV, "PATH": f"{bin_dir}:{os.environ['PATH']}", "FAKE_CLAUDE_PLAN": str(plan)}
    if stall:
        env["CLAUDE_BUILD_STALL"] = str(stall)
    return subprocess.run([sys.executable, SCRIPTS / "run-phase.py", PHASE, "--profiles", PROFILES,
                           "--work", tmp / "work"], cwd=repo, env=env, capture_output=True, text=True)


def calls(repo):
    """How many times the last drive called claude."""
    path = repo.parent / "steps.json.calls"
    return len(path.read_text().splitlines()) if path.exists() else 0


def read(repo, name):
    return json.loads((repo / PHASE / name).read_text())


def halt(repo):
    found = read(repo, "phase.json")["record"].get("halt") or {}
    return found.get("reason"), found.get("stage")


def subjects(repo):
    return git(repo, "log", "--format=%s").splitlines()


def test_builds_phase(repo):
    result = drive(repo, [REVISED_NOTHING, BUILD_ONE, BUILD_TWO, REVIEW])
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls(repo) == 4
    assert "Status: built" in (repo / PHASE / "phase.md").read_text()
    assert any(s.startswith("01.1 Write one") for s in subjects(repo))
    assert any(s.startswith("01.2 Write two") for s in subjects(repo))
    assert git(repo, "status", "--porcelain") == ""
    assert "Codex: off (driver version 1)" in result.stdout
    # the live feed of each call, on stderr
    for line in ("[revise] thinking: fake thinking", "[build-01.1] Bash: true", "result: success, $0.01"):
        assert line in result.stderr, result.stderr


def test_plan_ignored_by_git(repo):
    # a plan kept out of the repository: stages are committed, the plan directory never is
    (repo / ".gitignore").write_text(PLAN_DIR + "/\n")
    git(repo, "rm", "-r", "-q", "--cached", PLAN_DIR)
    git(repo, "add", ".gitignore")
    git(repo, "commit", "-q", "-m", "ignore the plan")
    result = drive(repo, [REVISED_NOTHING, BUILD_ONE, BUILD_TWO, REVIEW])
    assert result.returncode == 0, result.stdout + result.stderr
    assert "Status: built" in (repo / PHASE / "phase.md").read_text()
    assert [s[:4] for s in subjects(repo)[:2]] == ["01.2", "01.1"]
    assert git(repo, "ls-files", PLAN_DIR) == ""
    assert git(repo, "status", "--porcelain") == ""


def test_rerun_of_built_phase(repo):
    drive(repo, [REVISED_NOTHING, BUILD_ONE, BUILD_TWO, REVIEW])
    head = git(repo, "rev-parse", "HEAD")
    result = drive(repo, [])
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls(repo) == 0
    assert git(repo, "rev-parse", "HEAD") == head
    assert git(repo, "status", "--porcelain") == ""
    assert "Halt: none" in result.stdout


def test_revise_then_halt(repo):
    steps = [REVISED_NOTHING, BUILD_ONE, FAILED_TWO, raise_two(2), FAILED_TWO, raise_two(3), FAILED_TWO]
    result = drive(repo, steps)
    assert result.returncode == 10, result.stdout + result.stderr
    assert calls(repo) == len(steps)
    assert halt(repo) == ("revise-capped", "01.2")
    assert read(repo, "01.1.json")["record"]["commit"]
    two = read(repo, "01.2.json")
    assert two["brief"]["revision"] == 3 and not two["record"].get("commit")
    assert [x["result"] for x in two["record"]["attempts"]] == ["failed"] * 3
    assert "Halt: revise-capped at build 01.2" in result.stdout


def test_resume_after_halt(repo):
    # claude exits 3 after writing the file: an error that is not the model's
    first = drive(repo, [REVISED_NOTHING, {**BUILD_ONE, "exit": 3}])
    assert first.returncode == 10, first.stdout + first.stderr
    assert halt(repo) == ("build-error", "01.1")
    assert not (repo / "src/one.txt").exists()  # restored, so the rerun starts from a clean tree
    # the rerun does not revise again, builds 01.1 and halts at 01.2, before any review
    second = drive(repo, [BUILD_ONE, {**BUILD_TWO, "exit": 3}])
    assert second.returncode == 10, second.stdout + second.stderr
    assert calls(repo) == 2
    assert halt(repo) == ("build-error", "01.2")
    assert read(repo, "01.1.json")["record"]["commit"]
    assert not read(repo, "01.2.json")["record"].get("commit")


def test_refused_commit_rejects_attempt(repo):
    # 01.1 edits a committed one.txt to what it already holds, so the commit finds no changed files
    (repo / "src/one.txt").write_text("one\n")
    one = read(repo, "01.1.json")
    one["brief"]["files"][0]["action"] = "edit"
    (repo / PHASE / "01.1.json").write_text(json.dumps(one))
    git(repo, "add", ".")
    git(repo, "commit", "-q", "-m", "one")
    result = drive(repo, [REVISED_NOTHING, BUILD_ONE])
    assert result.returncode == 10, result.stdout + result.stderr
    assert halt(repo) == ("build-error", "01.1")
    attempt = read(repo, "01.1.json")["record"]["attempts"][-1]
    assert attempt["result"] == "rejected" and "no changed files" in attempt["why"]


def test_build_adding_plan_file_is_undone(repo):
    added = {**BUILD_ONE["files"], PHASE + "/01.3.json": "{}"}
    result = drive(repo, [REVISED_NOTHING, {**BUILD_ONE, "files": added}, REVISED_NOTHING])
    assert result.returncode == 10, result.stdout + result.stderr
    assert not (repo / PHASE / "01.3.json").exists()
    assert halt(repo) == ("revise-capped", "01.1")  # the retry's only pair is used up, so it revises
    attempt = read(repo, "01.1.json")["record"]["attempts"][-1]
    assert (attempt["result"], attempt["why"]) == ("rejected", "edited the plan")


def test_stalled_call_is_undone_and_run_again(repo):
    result = drive(repo, [REVISED_NOTHING, {**BUILD_ONE, "sleep": 6}, BUILD_ONE, BUILD_TWO, REVIEW], stall=2)
    assert result.returncode == 0, result.stdout + result.stderr
    assert calls(repo) == 5
    assert len(read(repo, "01.1.json")["record"]["attempts"]) == 1  # the stall is not a try of the pair


def test_second_stall_halts(repo):
    stalled = {**BUILD_ONE, "sleep": 6}
    result = drive(repo, [REVISED_NOTHING, stalled, stalled], stall=2)
    assert result.returncode == 10, result.stdout + result.stderr
    assert halt(repo) == ("stalled", "01.1")
    assert not (repo / "src/one.txt").exists()
    assert not read(repo, "01.1.json")["record"].get("attempts")
