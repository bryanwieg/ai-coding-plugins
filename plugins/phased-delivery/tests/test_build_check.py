import json
import os
from pathlib import Path
import subprocess

import pytest


SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
SCRIPT = SCRIPTS / "build-check.py"
PLAN_DIR = "docs/plan"
PHASE = "docs/plan/01-demo"
PHASE_MD = PHASE + "/phase.md"
GIT_ENV = {"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.invalid",
           "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.invalid",
           "GIT_CONFIG_GLOBAL": os.devnull, "GIT_CONFIG_NOSYSTEM": "1"}

PLAN = {"description": "Demo", "goal": "a and b exist.", "why": "w",
        "size": {"verdict": "full", "evidence": ["two stages"]},
        "outcomes": [{"id": "O1", "title": "a", "observable": "a exists", "how_to_check": "read it",
                      "sources": [{"doc": "spec", "section": "Goals", "quote": "a and b exist"}]}],
        "decisions": [], "existing": [],
        "phases": [{"phase": "01", "dir": "01-demo", "name": "Demo", "kind": "behaviour"}]}

PHASE_JSON = {"brief": {"role": "r", "why": "w", "how": "h", "before": "nothing.", "after": "a and b exist.",
                        "assumptions": [], "test_budget": "1 s", "notes": []},
              "record": {}}


def stage(title, order, files, checks, basis, tests=()):
    return {"brief": {"revision": 1, "title": title, "order": order, "lines": "under 30", "files": files,
                      "provides": [], "uses": [], "goal": title,
                      "context": {"builds_on": [], "code_read": [], "design": []},
                      "behaviour": [], "external_inputs": [], "tests": list(tests), "done_when": ["it exists"],
                      "checks": checks, "out_of_scope": [],
                      "model_basis": {**dict.fromkeys("JFRCKPVS", 0), **basis}},
            "record": {}}


STAGES = {
    "01.1": stage("Write a", "first", [{"path": "src/a.txt", "action": "edit", "role": "a"},
                                       {"path": "src/done.txt", "action": "create", "role": "done"}],
                  ["test -f src/done.txt"], {"J": 1, "F": 1},
                  [{"test": "src/done.txt", "kind": "outcome", "action": "writes", "proves": "a exists",
                    "outcome": "O1"}]),
    "01.2": stage("Write b", "after 01.1", [{"path": "src/b.txt", "action": "edit", "role": "b"}], [], {}),
}

REVIEW = {"findings": [], "verdict": "ready"}


def git(repo, *args):
    return subprocess.run(["git", "-C", str(repo), *args], env={**os.environ, **GIT_ENV},
                          capture_output=True, text=True, check=True).stdout


def write_json(path, data):
    path.write_text(json.dumps(data))


@pytest.fixture
def repo(tmp_path):
    """A git repository with one commit holding a plan with one phase folder of two stage files."""
    r = tmp_path / "repo"
    (r / "src").mkdir(parents=True)
    (r / PHASE).mkdir(parents=True)
    (r / "src/a.txt").write_text("a\n")
    (r / "src/b.txt").write_text("b\n")
    (r / "src/other.txt").write_text("other\n")
    write_json(r / PLAN_DIR / "plan.json", PLAN)
    write_json(r / PHASE / "phase.json", PHASE_JSON)
    for sid, s in STAGES.items():
        write_json(r / PHASE / f"{sid}.json", s)
    git(r, "init", "-q")
    git(r, "add", ".")
    git(r, "commit", "-q", "-m", "base")
    return r


def stage_file(repo, sid):
    return json.loads((repo / PHASE / f"{sid}.json").read_text())


def edit_brief(repo, sid, **fields):
    s = stage_file(repo, sid)
    write_json(repo / PHASE / f"{sid}.json", {**s, "brief": {**s["brief"], **fields}})


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


def phase_md(repo):
    return (repo / PHASE_MD).read_text()


def test_accepted_stage_commit(repo):
    assert bc(repo, "start", PHASE).returncode == 0
    build_a(repo)
    result = record(repo, "01.1", "opus", "high", 0, "1200", "0.40", "--tool-calls", "7")
    assert result.returncode == 0, result.stdout + result.stderr
    assert json.loads(result.stdout)["result"] == "accepted"
    assert [x["result"] for x in stage_file(repo, "01.1")["record"]["attempts"]] == ["accepted"]
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
    text = phase_md(repo)
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
    bad = stage_file(repo, "01.1")
    del bad["brief"]["checks"]
    write_json(repo / PHASE / "01.1.json", bad)
    result = bc(repo, "start", PHASE)
    assert result.returncode == 1
    assert "checks" in result.stdout
    assert json.loads((repo / PHASE / "phase.json").read_text())["record"] == {}

    write_json(repo / PHASE / "01.1.json", STAGES["01.1"])
    assert bc(repo, "start", PHASE).returncode == 0
    head = git(repo, "rev-parse", "HEAD")
    review = {"findings": [{"type": "style", "severity": "blocking", "stage": "01.1", "file": "src/a.txt",
                            "line": 1, "evidence": "x", "action": "fix"}], "verdict": "not-ready"}
    write_json(repo / PHASE / "review.json", review)
    result = bc(repo, "finish", PHASE)
    assert result.returncode == 1
    assert "type" in result.stdout
    assert git(repo, "rev-parse", "HEAD") == head


def test_finish_phase(repo):
    bc(repo, "start", PHASE)
    build_a(repo)
    record(repo, "01.1")
    bc(repo, "commit", PHASE, "01.1")
    write_json(repo / PHASE / "review.json", REVIEW)
    assert bc(repo, "finish", PHASE).returncode == 1  # 01.2 has no commit
    (repo / "src/b.txt").write_text("b2\n")
    record(repo, "01.2", "haiku", "high")
    bc(repo, "commit", PHASE, "01.2")
    stage_commit = git(repo, "rev-parse", "--short", "HEAD").strip()
    result = bc(repo, "finish", PHASE)
    assert result.returncode == 0, result.stdout + result.stderr
    text = phase_md(repo)
    assert f"Status: built {stage_commit}" in text
    assert "| 01.1 | Write a | middle | first | done |" in text and "| 01.2 | Write b | small | after 01.1 | done |" in text
    assert f"Phase: {PHASE}" in message(repo)
    assert set(changed(repo)) >= {PHASE_MD, f"{PHASE}/phase.json", f"{PHASE}/01.1.json", f"{PHASE}/review.json",
                                   f"{PLAN_DIR}/plan.md"}
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
    # a raised revision reopens the stage; its rebuild is a fix, with a changed file and then with none
    for revision, content in ((2, "a4\n"), (3, None)):
        edit_brief(repo, "01.1", revision=revision, goal=f"Write a, revision {revision}")
        if content:
            (repo / "src/a.txt").write_text(content)
        assert record(repo, "01.1", "sonnet", "medium", 0, "300", "0.05", "--fix").returncode == 0
        assert bc(repo, "commit", PHASE, "01.1").returncode == 0
        assert "Fixes-Stage: 01.1" in message(repo)
        assert changed(repo) == (["src/a.txt"] if content else [])
        assert f"| 01.1 | Write a, revision {revision} | middle | first | done |" in phase_md(repo)


def test_rename_from_outside_fails(repo):
    bc(repo, "start", PHASE)
    (repo / "src/a.txt").write_text("a2\n")
    git(repo, "mv", "src/other.txt", "src/done.txt")  # into a stage file
    result = record(repo, "01.1")
    assert result.returncode == 1
    assert "src/other.txt" in json.loads(result.stdout)["outside"]


def test_reject_budget_stop_then_retry(repo):
    bc(repo, "start", PHASE)
    (repo / "src/other.txt").write_text("stray\n")
    stopped = record(repo, "01.1", "haiku", "high", 8, "400", "0.25")
    assert stopped.returncode == 3
    assert json.loads(stopped.stdout)["outside"] == ["src/other.txt"]
    git(repo, "checkout", "src/other.txt")
    build_a(repo)
    assert record(repo, "01.1", "sonnet", "high").returncode == 0
    assert bc(repo, "reject", PHASE, "01.1", "tests check nothing\nsee diff").returncode == 0
    assert bc(repo, "commit", PHASE, "01.1").returncode == 1
    assert record(repo, "01.1", "opus", "high").returncode == 0
    assert bc(repo, "commit", PHASE, "01.1").returncode == 0
    msg = message(repo)
    assert "Attempt: 3" in msg
    assert "Earlier-Attempt: haiku high 400 budget reached" in msg
    assert "Earlier-Attempt: sonnet high 1200 tests check nothing see diff" in msg
    assert "1 accepted stages" in stats(repo)


def test_revision_resets_ladder(repo):
    def plan_check():
        result = subprocess.run(["python3", str(SCRIPTS / "plan-check.py"), PLAN_DIR], cwd=repo,
                                capture_output=True, text=True)
        rows = [json.loads(x) for x in result.stdout.splitlines()[:-1]]
        return result.returncode, [x["kind"] for x in rows if x["level"] == "error"]

    bc(repo, "start", PHASE)
    (repo / "src/a.txt").write_text("a2\n")
    assert record(repo, "01.1", "opus", "high").returncode == 1
    assert bc(repo, "can-try", PHASE, "01.1", "opus", "high").returncode == 1
    assert plan_check() == (0, [])
    edit_brief(repo, "01.1", goal="Write a, edited")
    assert plan_check() == (1, ["revision"])
    attempts = stage_file(repo, "01.1")["record"]["attempts"]
    assert record(repo, "01.1", "sonnet", "high").returncode == 5
    assert stage_file(repo, "01.1")["record"]["attempts"] == attempts
    edit_brief(repo, "01.1", revision=2)
    assert plan_check() == (0, [])
    assert bc(repo, "can-try", PHASE, "01.1", "opus", "high").returncode == 0


def test_orchestrator_needs_session_only(repo):
    bc(repo, "start", PHASE)
    (repo / "src/b.txt").write_text("b2\n")
    refused = record(repo, "01.2", "orchestrator", "high")
    assert refused.returncode == 2 and "session_only" in refused.stderr
    assert "attempts" not in stage_file(repo, "01.2")["record"]
    edit_brief(repo, "01.2", session_only=True)
    accepted = record(repo, "01.2", "orchestrator", "high")
    assert accepted.returncode == 0, accepted.stdout + accepted.stderr
    assert [x["model"] for x in stage_file(repo, "01.2")["record"]["attempts"]] == ["orchestrator"]
