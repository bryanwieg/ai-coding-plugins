import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest


SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan-check.py"
SPEC = "Users must log in. Five failed logins from one address within a minute get 429."
BASIS = {"J": 1, "F": 1, "R": 1, "C": 1, "K": 1, "P": 1, "V": 0, "S": 0}

PLAN = {
    "size": {"verdict": "full", "evidence": ["a shared contract changes"]},
    "outcomes": [{"id": "O1", "title": "limit", "observable": "the sixth failed login answers 429",
                  "how_to_check": "test client posts /login six times",
                  "sources": [{"doc": "spec", "section": "Goals", "quote": "Five failed logins from one address"}]}],
    "decisions": [{"id": "D1", "text": "Counts live in memory.", "reason": "single process", "phases": ["all"]}],
    "contracts": [
        {"id": "C1", "kind": "function", "name": "check_rate", "shape": "check_rate(addr: str) -> bool",
         "provided_by": "01.1", "used_by": ["01.2"]},
        {"id": "C2", "kind": "function", "name": "login", "shape": "login() -> Response",
         "provided_by": "existing:app/views.py", "used_by": ["01.2"]}],
    "outcome_tests": [{"outcome": "O1", "test": "tests/test_limit.py::test_sixth", "written_in": "01.2",
                       "passes_from": "01.2"}],
    "phases": [{"phase": "01", "file": "01-rate-limit.md", "name": "rate limit", "kind": "behaviour", "stages": [
        {"id": "01.1", "title": "limiter", "files": [{"path": "app/ratelimit.py", "action": "create"}],
         "lines": "30-150", "provides": ["C1"], "uses": [], "order": "first"},
        {"id": "01.2", "title": "wire it in", "files": [{"path": "app/views.py", "action": "edit"},
                                                         {"path": "tests/test_limit.py", "action": "create"}],
         "lines": "under 30", "provides": [], "uses": ["C1", "C2"], "order": "after 01.1"}]}],
}


def stage(sid, files, contracts, **kw):
    return {"id": sid, "goal": "g", "context": {"builds_on": [], "code_read": [], "design": []},
            "contracts": contracts, "files": files, "behaviour": [], "external_inputs": [], "tests": [],
            "done_when": ["pytest passes"], "out_of_scope": [], "model_basis": dict(BASIS), **kw}


PHASE = {
    "before": "No limit.", "after": "Logins are limited.", "assumptions": [], "test_budget": "1 min",
    "stages": [
        stage("01.1", [{"path": "app/ratelimit.py", "action": "create", "role": "holds check_rate"}],
              [{"kind": "function", "name": "check_rate", "shape": "check_rate(addr: str) -> bool",
                "direction": "provides", "counterparts": ["01.2"]}]),
        stage("01.2", [{"path": "app/views.py", "action": "edit", "role": "login calls check_rate"},
                       {"path": "tests/test_limit.py", "action": "create", "role": "the outcome test"}],
              [{"kind": "function", "name": "check_rate", "shape": "check_rate(addr: str) -> bool",
                "direction": "uses", "counterparts": ["01.1"]}]),
    ],
    "notes": [],
}


def run(tmp_path, plan=PLAN, phase=PHASE, *extra):
    (tmp_path / "app").mkdir(exist_ok=True)
    (tmp_path / "app" / "views.py").write_text("def login():\n    return render()\n")
    (tmp_path / "spec.md").write_text(SPEC)
    d = tmp_path / "plan" / ".plan"
    d.mkdir(parents=True, exist_ok=True)
    (d / "plan.json").write_text(json.dumps(plan))
    if phase is not None:
        (d / "01.json").write_text(json.dumps(phase))
    p = subprocess.run([sys.executable, SCRIPT, str(tmp_path / "plan"), "--repo", str(tmp_path),
                        "--spec", str(tmp_path / "spec.md"), *extra], capture_output=True, text=True)
    rows = [json.loads(x) for x in p.stdout.splitlines()]
    return p.returncode, rows[:-1], rows[-1]["summary"]


def kinds(rows):
    return {x["kind"] for x in rows if x["level"] == "error"}


def test_clean_plan_renders(tmp_path):
    code, rows, summary = run(tmp_path)
    assert code == 0, rows
    assert summary["rendered"] == ["01-rate-limit.md"]
    md = (tmp_path / "plan" / "01-rate-limit.md").read_text()
    assert "# Phase 01: rate limit" in md
    assert "| 01.2 | g | middle | after 01.1 | planned |" in md
    assert "writes `tests/test_limit.py::test_sixth` (outcome): the sixth failed login answers 429" in md
    assert "- Counts live in memory. Reason: single process" in md
    assert "Model basis: J1 F1 R1 C1 K1 P1 V0 S0 = 6 -> middle" in md


def test_outline_only_skips_phase_json(tmp_path):
    code, rows, summary = run(tmp_path, PLAN, None, "--outline")
    assert code == 0 and summary["rendered"] == []


def broken_plan(change):
    p = copy.deepcopy(PLAN)
    change(p)
    return p


@pytest.mark.parametrize("change, kind", [
    (lambda p: p["contracts"][0]["used_by"].append("01.9"), "ref"),
    (lambda p: p["phases"][0]["stages"][1]["uses"].remove("C1"), "registry"),
    (lambda p: p["outcome_tests"].clear(), "coverage"),
    (lambda p: p["outcomes"][0]["sources"][0].update(quote="Ten failed logins"), "quote"),
    (lambda p: p["phases"][0]["stages"][1]["files"].append({"path": "app/nope.py", "action": "edit"}), "files"),
    (lambda p: p["contracts"][0].update(used_by=["tests/test_limit.py"]), "internal"),
    (lambda p: p["phases"][0]["stages"][0].update(order="after 01.2"), "order"),
    (lambda p: p["contracts"][1].update(provided_by="existing:app/gone.py"), "ref"),
    (lambda p: p["decisions"][0].pop("reason"), "schema"),
])
def test_plan_errors(tmp_path, change, kind):
    code, rows, _ = run(tmp_path, broken_plan(change), PHASE, "--outline")
    assert code == 1
    assert kind in kinds(rows), rows


def broken_phase(change):
    d = copy.deepcopy(PHASE)
    change(d)
    return d


@pytest.mark.parametrize("change, kind", [
    (lambda d: d["stages"][0]["contracts"].append({"kind": "function", "name": "_prune", "shape": "_prune()",
                                                   "direction": "provides", "counterparts": ["01.1"]}), "internal"),
    (lambda d: d["stages"][1]["context"]["design"].append({"doc": "spec", "section": "s", "quote": "Admins skip limits"}), "quote"),
    (lambda d: d["stages"][1]["context"]["code_read"].append({"where": "app/views.py:1", "shows": "def logout", "fact": "f"}), "cite"),
    (lambda d: d["stages"][1]["context"]["code_read"].append({"where": "app/views.py:9", "shows": "x", "fact": "f"}), "cite"),
    (lambda d: d["notes"].append("Follows C1."), "standalone"),
    (lambda d: d["stages"][0]["files"].pop(), "plan"),
    (lambda d: d["stages"][0]["contracts"].clear(), "plan"),
    (lambda d: d["stages"][1]["tests"].append({"test": "tests/test_limit.py::test_sixth", "kind": "outcome",
                                               "action": "writes", "proves": "p"}), "tests"),
])
def test_phase_errors_block_rendering(tmp_path, change, kind):
    code, rows, summary = run(tmp_path, PLAN, broken_phase(change))
    assert code == 1
    assert kind in kinds(rows), rows
    assert summary["rendered"] == []


def test_code_in_prose_is_a_warning(tmp_path):
    d = broken_phase(lambda d: d["stages"][1]["behaviour"].append(
        {"given": "five failures", "when": "a sixth", "then": "`if n == 5 return False`"}))
    code, rows, summary = run(tmp_path, PLAN, d)
    assert code == 0
    assert [x["kind"] for x in rows] == ["code"] and rows[0]["level"] == "warning"


def test_valid_citation_passes(tmp_path):
    d = broken_phase(lambda d: d["stages"][1]["context"]["code_read"].append(
        {"where": "app/views.py:1-2", "shows": "def login", "fact": "the login view"}))
    assert run(tmp_path, PLAN, d)[0] == 0


def test_quick_plan_renders_size(tmp_path):
    p = broken_plan(lambda p: p["size"].update(verdict="quick", evidence=["total 6: one interface part"]))
    code, rows, _ = run(tmp_path, p, PHASE)
    assert code == 0, rows
    assert "## Size\n\nQuick plan:\n- total 6: one interface part" in (tmp_path / "plan" / "01-rate-limit.md").read_text()
