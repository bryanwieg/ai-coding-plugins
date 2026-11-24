import copy
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan-check.py"
spec = importlib.util.spec_from_file_location("plan_check", SCRIPT)
plan_check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan_check)

SPEC = "Users must log in. Five failed logins from one address within a minute get 429."
BASIS = {"J": 1, "F": 1, "R": 1, "C": 1, "K": 1, "P": 1, "V": 0, "S": 0}
P1 = "01-rate-limit/"

PLAN = {
    "description": "Login rate limit", "goal": "Limit failed logins.", "why": "Stop guessing.",
    "size": {"verdict": "full", "evidence": ["a shared contract changes"]},
    "outcomes": [{"id": "O1", "title": "limit", "observable": "the sixth failed login answers 429",
                  "how_to_check": "test client posts /login six times",
                  "sources": [{"doc": "spec", "section": "Goals", "quote": "Five failed logins from one address"}]}],
    "decisions": [{"id": "D1", "text": "Counts live in memory.", "reason": "single process", "phases": ["all"]}],
    "existing": [{"kind": "function", "name": "login", "shape": "login() -> Response", "path": "app/views.py"}],
    "phases": [{"phase": "01", "dir": "01-rate-limit", "name": "rate limit", "kind": "behaviour"}],
}

PHASE = {"brief": {"role": "r", "why": "w", "how": "h", "before": "No limit.", "after": "Logins are limited.",
                   "assumptions": [], "test_budget": "1 min", "notes": []},
         "record": {}}


def stage(title, order, lines, files, provides, uses, tests=()):
    return {"brief": {"revision": 1, "title": title, "order": order, "lines": lines, "files": files,
                      "provides": provides, "uses": uses, "goal": "g",
                      "context": {"builds_on": [], "code_read": [], "design": []},
                      "behaviour": [], "external_inputs": [], "tests": list(tests), "done_when": ["pytest passes"],
                      "checks": [], "out_of_scope": [], "model_basis": dict(BASIS)},
            "record": {}}


# the example plan: file path relative to the plan folder -> content
FILES = {
    "plan.json": PLAN,
    P1 + "phase.json": PHASE,
    P1 + "01.1.json": stage("limiter", "first", "30-150",
                            [{"path": "app/ratelimit.py", "action": "create", "role": "holds check_rate"}],
                            [{"kind": "function", "name": "check_rate", "shape": "check_rate(addr: str) -> bool",
                              "used_by": []}], []),
    P1 + "01.2.json": stage("wire it in", "after 01.1", "under 30",
                            [{"path": "app/views.py", "action": "edit", "role": "login calls check_rate"},
                             {"path": "tests/test_limit.py", "action": "create", "role": "the outcome test"}],
                            [], ["check_rate", "login"],
                            [{"test": "tests/test_limit.py::test_sixth", "kind": "outcome", "action": "writes",
                              "proves": "p", "outcome": "O1"}]),
}


def brief(f, sid):
    return f[f"{P1}{sid}.json"]["brief"]


def changed(change):
    f = copy.deepcopy(FILES)
    change(f)
    return f


def run(tmp_path, files=FILES, *extra):
    (tmp_path / "app").mkdir(exist_ok=True)
    (tmp_path / "app" / "views.py").write_text("def login():\n    return render()\n")
    (tmp_path / "spec.md").write_text(SPEC)
    for name, data in files.items():
        path = tmp_path / "plan" / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(data))
    p = subprocess.run([sys.executable, SCRIPT, str(tmp_path / "plan"), "--repo", str(tmp_path),
                        "--spec", str(tmp_path / "spec.md"), *extra], capture_output=True, text=True)
    rows = [json.loads(x) for x in p.stdout.splitlines()]
    return p.returncode, rows[:-1], rows[-1]["summary"]


def kinds(rows):
    return {x["kind"] for x in rows if x["level"] == "error"}


def test_renders_layout(tmp_path):
    decoy = tmp_path / "plan" / ".plan" / "plan.json"
    decoy.parent.mkdir(parents=True)
    decoy.write_text("not json")
    code, rows, summary = run(tmp_path)
    assert code == 0, rows
    assert sorted(summary["rendered"]) == [P1 + "phase.md", "plan.md"]
    assert "[01 rate limit](01-rate-limit/phase.md)" in (tmp_path / "plan" / "plan.md").read_text()
    md = (tmp_path / "plan" / P1 / "phase.md").read_text()
    assert "# Phase 01: rate limit" in md
    assert "## 01.1 limiter" in md and "## 01.2 wire it in" in md
    assert "| 01.2 | g | middle | after 01.1 | planned |" in md
    assert "writes `tests/test_limit.py::test_sixth` (outcome): the sixth failed login answers 429" in md
    assert "- Counts live in memory. Reason: single process" in md
    assert "Model basis: J1 F1 R1 C1 K1 P1 V0 S0 = 6 -> middle" in md
    assert [p.name for p in decoy.parent.iterdir()] == ["plan.json"] and decoy.read_text() == "not json"


def test_outline_only_skips_phase_json(tmp_path):
    files = changed(lambda f: f.pop(P1 + "phase.json"))
    code, rows, summary = run(tmp_path, files, "--outline")
    assert code == 0 and summary["rendered"] == [], rows


@pytest.mark.parametrize("change, kind", [
    (lambda f: brief(f, "01.2")["uses"].append("check_limit"), "ref"),
    (lambda f: f["plan.json"]["existing"].append({**PLAN["existing"][0], "name": "check_rate"}), "registry"),
    (lambda f: brief(f, "01.2")["tests"].clear(), "coverage"),
    (lambda f: f["plan.json"]["outcomes"][0]["sources"][0].update(quote="Ten failed logins"), "quote"),
    (lambda f: brief(f, "01.2")["files"].append({"path": "app/nope.py", "action": "edit", "role": "r"}), "files"),
    (lambda f: (brief(f, "01.2")["uses"].remove("check_rate"),
                brief(f, "01.1")["provides"][0].update(used_by=["tests/test_limit.py"])), "internal"),
    (lambda f: brief(f, "01.1").update(order="after 01.2"), "order"),
    (lambda f: f["plan.json"]["existing"][0].update(path="app/gone.py"), "ref"),
    (lambda f: f["plan.json"]["decisions"][0].pop("reason"), "schema"),
])
def test_plan_errors(tmp_path, change, kind):
    code, rows, _ = run(tmp_path, changed(change))
    assert code == 1
    assert kind in kinds(rows), rows


@pytest.mark.parametrize("change, kind", [
    (lambda f: brief(f, "01.1")["provides"].append({"kind": "function", "name": "_prune", "shape": "_prune()",
                                                    "used_by": []}), "internal"),
    (lambda f: brief(f, "01.2")["context"]["design"].append({"doc": "spec", "section": "s",
                                                             "quote": "Admins skip limits"}), "quote"),
    (lambda f: brief(f, "01.2")["context"]["code_read"].append({"where": "app/views.py:1", "shows": "def logout",
                                                                "fact": "f"}), "cite"),
    (lambda f: brief(f, "01.2")["context"]["code_read"].append({"where": "app/views.py:9", "shows": "x",
                                                                "fact": "f"}), "cite"),
    (lambda f: f[P1 + "phase.json"]["brief"]["notes"].append("Follows D1."), "standalone"),
    (lambda f: f.update({P1 + "02.1.json": f[P1 + "01.2.json"]}), "id"),
    (lambda f: brief(f, "01.1")["provides"].clear(), "ref"),
    (lambda f: brief(f, "01.2")["tests"][0].pop("outcome"), "tests"),
])
def test_phase_errors_block_rendering(tmp_path, change, kind):
    code, rows, summary = run(tmp_path, changed(change))
    assert code == 1
    assert kind in kinds(rows), rows
    assert summary["rendered"] == []


def test_code_in_prose_is_a_warning(tmp_path):
    files = changed(lambda f: brief(f, "01.2")["behaviour"].append(
        {"given": "five failures", "when": "a sixth", "then": "`if n == 5 return False`"}))
    code, rows, summary = run(tmp_path, files)
    assert code == 0
    assert [x["kind"] for x in rows] == ["code"] and rows[0]["level"] == "warning"


def test_valid_citation_passes(tmp_path):
    files = changed(lambda f: brief(f, "01.2")["context"]["code_read"].append(
        {"where": "app/views.py:1-2", "shows": "def login", "fact": "the login view"}))
    assert run(tmp_path, files)[0] == 0


def test_quick_plan_renders_size(tmp_path):
    files = changed(lambda f: f["plan.json"]["size"].update(verdict="quick", evidence=["total 6: one interface part"]))
    code, rows, _ = run(tmp_path, files)
    assert code == 0, rows
    assert "## Size\n\nQuick plan:\n- total 6: one interface part" in (tmp_path / "plan" / P1 / "phase.md").read_text()


def test_brief_change_needs_revision(tmp_path):
    # build-check.py writes `revisions` only from phase 03, so the record is written by hand here
    built = changed(lambda f: f[P1 + "01.1.json"]["record"].update(
        revisions={"1": plan_check.brief_hash(brief(f, "01.1"))}))
    assert run(tmp_path, built)[0] == 0
    edited = copy.deepcopy(built)
    brief(edited, "01.1")["goal"] = "g2"
    code, rows, _ = run(tmp_path, edited)
    assert code == 1 and [x["where"] for x in rows if x["kind"] == "revision"] == ["01.1"], rows
    raised = copy.deepcopy(edited)
    brief(raised, "01.1")["revision"] = 2
    assert run(tmp_path, raised)[0] == 0
    lowered = copy.deepcopy(raised)
    lowered[P1 + "01.1.json"]["record"]["revisions"]["2"] = plan_check.brief_hash(brief(raised, "01.1"))
    brief(lowered, "01.1")["revision"] = 1
    assert "revision" in kinds(run(tmp_path, lowered)[1])


STALE = {"where": "app/views.py:1", "shows": "def logout", "fact": "f"}


def test_repository_checks_skip_done_stages(tmp_path):
    def change(f):
        f[P1 + "01.1.json"]["record"]["commit"] = "abc1234"
        brief(f, "01.1")["context"]["code_read"].append(STALE)
        brief(f, "01.2")["context"]["code_read"].append(STALE)
    (tmp_path / "app").mkdir()
    (tmp_path / "app" / "ratelimit.py").write_text("")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "test_limit.py").write_text("")
    code, rows, _ = run(tmp_path, changed(change))
    assert code == 1
    assert {(x["where"].split("/")[0], x["kind"]) for x in rows if x["level"] == "error"} == {
        ("01.2", "files"), ("01.2", "cite")}, rows


def test_phase_scopes_repository_checks(tmp_path):
    P2 = "02-more/"

    def change(f):
        f["plan.json"]["phases"].append({"phase": "02", "dir": "02-more", "name": "more", "kind": "behaviour"})
        for sid in ("01.1", "01.2"):
            f[f"{P1}{sid}.json"]["record"]["commit"] = "abc1234"
        f[P1 + "phase.json"]["record"]["built"] = "abc1234"
        f[P2 + "phase.json"] = PHASE
        f[P2 + "02.1.json"] = stage("more", "after 01.2", "under 30",
                                    [{"path": "app/views.py", "action": "edit", "role": "r"}], [], ["login"])
        f[P2 + "02.1.json"]["brief"]["context"]["code_read"].append(STALE)
    files = changed(change)
    assert run(tmp_path, files, "--phase", "01")[0] == 0
    code, rows, _ = run(tmp_path, files, "--phase", "02")
    assert code == 1 and kinds(rows) == {"cite"}, rows
