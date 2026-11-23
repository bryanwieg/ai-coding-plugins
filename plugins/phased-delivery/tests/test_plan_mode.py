import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import pytest

SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "plan-mode.py"
spec = importlib.util.spec_from_file_location("plan_mode", SCRIPT)
plan_mode = importlib.util.module_from_spec(spec)
spec.loader.exec_module(plan_mode)
CASES = json.loads((Path(__file__).parent / "mode_cases.json").read_text())


@pytest.mark.parametrize("case", CASES, ids=[c["request"][:40] for c in CASES])
def test_calibration_cases(case):
    mode, total, _, _ = plan_mode.score(case["form"])
    assert mode == case["expected"], total


def run(tmp_path, form):
    (tmp_path / "app").mkdir(exist_ok=True)
    (tmp_path / "app" / "views.py").write_text("def login():\n    pass\n")
    (tmp_path / "docs.md").write_text("login\n")
    f = tmp_path / "form.json"
    f.write_text(json.dumps(form))
    p = subprocess.run([sys.executable, SCRIPT, str(f), "--repo", str(tmp_path)], capture_output=True, text=True)
    rows = [json.loads(x) for x in p.stdout.splitlines()]
    return p.returncode, rows[:-1], rows[-1]["summary"]


def form(**part):
    p = {"title": "login", "kind": "interface", "files": [{"path": "app/views.py", "action": "edit"}],
         "lines": 10, "reach": ["docs.md:1"], "search": "grep -rn login", "trust_boundary": False}
    p.update(part)
    return {"request": "r", "parts": [p], "open_questions": []}


def test_clean_form_scores(tmp_path):
    code, rows, s = run(tmp_path, form())
    assert code == 0 and rows == []
    assert s["mode"] == "direct" and s["total"] == 4 and s["parts"][0]["reach"] == 2


def test_open_questions_add(tmp_path):
    f = form()
    f["open_questions"] = ["which roles?"]
    assert run(tmp_path, f)[2]["mode"] == "quick"


@pytest.mark.parametrize("part, kind", [
    ({"files": [{"path": "app/nope.py", "action": "edit"}]}, "files"),
    ({"files": [{"path": "app/views.py", "action": "create"}]}, "files"),
    ({"reach": ["nope.md"]}, "reach"),
    ({"reach": ["docs.md:9"]}, "reach"),
    ({"reach": ["app/views.py:1"]}, "reach"),
    ({"search": " "}, "search"),
    ({"kind": "data"}, "schema"),
    ({"kind": "huge"}, "schema"),
])
def test_errors_withhold_mode(tmp_path, part, kind):
    code, rows, s = run(tmp_path, form(**part))
    assert code == 1 and s["mode"] is None
    assert kind in {r["kind"] for r in rows if r["level"] == "error"}, rows


def test_reach_ignored_for_internal(tmp_path):
    code, rows, s = run(tmp_path, form(kind="internal"))
    assert code == 0 and [r["kind"] for r in rows] == ["reach"] and s["parts"][0]["reach"] == 1


def test_existing_data_forces_full(tmp_path):
    assert run(tmp_path, form(kind="data", existing_data=True, reach=[]))[2]["mode"] == "full"
