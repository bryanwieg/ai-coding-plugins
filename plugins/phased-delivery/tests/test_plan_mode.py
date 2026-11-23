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
    f = case["form"]
    mode, total, _, _ = plan_mode.score(f["parts"], f["open_questions"], f["unresolved"])
    assert mode == case["expected"], total


def repo(tmp_path):
    (tmp_path / "app").mkdir(exist_ok=True)
    (tmp_path / "app" / "views.py").write_text("def login():\n    return check_rate(addr)\n")
    (tmp_path / "app" / "ratelimit.py").write_text("def check_rate(addr):\n    pass\n")
    (tmp_path / "docs.md").write_text("check_rate limits logins\n")
    (tmp_path / "logo.png").write_bytes(b"\x89PNG\0check_rate")
    (tmp_path / "plan").mkdir(exist_ok=True)
    (tmp_path / "plan" / "01-rate.md").write_text("# Phase 01: rate\n\nImplement with the implement-in-phases skill; check_rate\n")
    (tmp_path / "plan" / "models.md").write_text("check_rate\n")
    return tmp_path


def call(tmp_path, cmd, data):
    f = tmp_path / "in.json"
    f.write_text(json.dumps(data))
    p = subprocess.run([sys.executable, SCRIPT, cmd, str(f), "--repo", str(repo(tmp_path))],
                       capture_output=True, text=True)
    rows = [json.loads(x) for x in p.stdout.splitlines()]
    return p.returncode, rows[:-1], rows[-1]["summary"]


def test_locate_finds_mentions_and_names(tmp_path):
    code, rows, s = call(tmp_path, "locate", {"request": "r", "terms": ["CHECK_RATE", "ratelimit", "nothing"]})
    assert code == 0 and rows == []
    got = {x["term"]: x["files"] for x in s["located"]}
    assert got == {"CHECK_RATE": ["app/ratelimit.py", "app/views.py", "docs.md"],
                   "ratelimit": ["app/ratelimit.py"], "nothing": []}


def test_locate_limits_terms(tmp_path):
    code, rows, _ = call(tmp_path, "locate", {"request": "r", "terms": list("abcdef")})
    assert code == 1 and rows[0]["kind"] == "limit"


def form(**part):
    p = {"title": "rate", "kind": "interface", "files": [{"path": "app/ratelimit.py", "action": "edit"}],
         "lines": "under 30", "changes": ["check_rate"]}
    p.update(part)
    return {"request": "r", "opened": ["app/ratelimit.py"], "parts": [p], "unresolved": [], "open_questions": []}


def test_score_searches_reach_outside_the_part(tmp_path):
    code, rows, s = call(tmp_path, "score", form())
    assert code == 0 and rows == []
    assert s["parts"][0]["reach_files"] == ["app/views.py", "docs.md"]
    assert s["mode"] == "direct" and s["total"] == 3


def test_unresolved_makes_it_quick(tmp_path):
    f = form()
    f["unresolved"] = ["where sessions live"]
    s = call(tmp_path, "score", f)[2]
    assert s["mode"] == "quick" and s["total"] == 3


@pytest.mark.parametrize("change, kind", [
    (lambda f: f["parts"][0].update(files=[{"path": "app/nope.py", "action": "edit"}]), "files"),
    (lambda f: f["parts"][0].update(files=[{"path": "app/views.py", "action": "create"}]), "files"),
    (lambda f: f["parts"][0].update(changes=[]), "changes"),
    (lambda f: f["parts"][0].update(kind="data"), "schema"),
    (lambda f: f["parts"][0].update(lines=40), "schema"),
    (lambda f: f.update(opened=["docs.md"] * 6), "limit"),
    (lambda f: f.update(opened=["gone.py"]), "files"),
])
def test_errors_withhold_mode(tmp_path, change, kind):
    f = form()
    change(f)
    code, rows, s = call(tmp_path, "score", f)
    assert code == 1 and s["mode"] is None
    assert kind in {r["kind"] for r in rows if r["level"] == "error"}, rows


def test_changes_ignored_for_internal(tmp_path):
    code, rows, s = call(tmp_path, "score", form(kind="internal"))
    assert code == 0 and [r["kind"] for r in rows] == ["changes"] and s["parts"][0]["reach"] == 1


def test_existing_data_forces_full(tmp_path):
    assert call(tmp_path, "score", form(kind="data", existing_data=True))[2]["mode"] == "full"


def plan(tmp_path, stages, contracts, phases=1):
    d = repo(tmp_path) / "docs" / "plan" / ".plan"
    d.mkdir(parents=True, exist_ok=True)
    ph = [{"phase": f"{i + 1:02}", "stages": stages if i == 0 else stages[:1]} for i in range(phases)]
    (d / "plan.json").write_text(json.dumps({"contracts": contracts, "phases": ph}))
    p = subprocess.run([sys.executable, SCRIPT, "rescore", str(d.parent), "--repo", str(tmp_path)],
                       capture_output=True, text=True)
    return p.returncode, json.loads(p.stdout)["summary"] if p.stdout else None


def st(sid, files, provides=(), lines="30-150"):
    return {"id": sid, "title": "t", "files": [{"path": f, "action": a} for f, a in files],
            "lines": lines, "provides": list(provides), "uses": [], "order": "first"}


def test_rescore_kinds_and_reach(tmp_path):
    code, s = plan(tmp_path, [
        st("01.1", [("app/new.py", "create")]),
        st("01.2", [("app/ratelimit.py", "edit")]),
        st("01.3", [("app/views.py", "edit")], ["C2"], "under 30")],
        [{"id": "C1", "name": "check_rate", "provided_by": "existing:app/ratelimit.py", "used_by": ["01.3"]},
         {"id": "C2", "name": "login_page", "provided_by": "01.3", "used_by": ["user"]}])
    assert code == 0
    assert [p["kind"] for p in s["parts"]] == ["new", "interface", "interface"]
    assert s["parts"][1]["reach_files"] == ["app/views.py", "docs.md"]
    assert s["parts"][2]["reach_files"] == ["user"]
    assert s["mode"] == "quick" and s["total"] == 1 + 6 + 3


def test_rescore_structure_forces_full(tmp_path):
    stages = [st(f"01.{i}", [(f"app/f{i}.py", "create")], lines="under 30") for i in range(1, 5)]
    assert plan(tmp_path, stages, [])[1]["mode"] == "full"
    assert plan(tmp_path, stages[:1], [], phases=2)[1]["mode"] == "full"
    assert plan(tmp_path, stages[:1], [])[1]["mode"] == "direct"


def test_rescore_without_plan(tmp_path):
    p = subprocess.run([sys.executable, SCRIPT, "rescore", str(tmp_path / "nope")], capture_output=True, text=True)
    assert p.returncode == 2


def sketch(**part):
    f = form(**part)
    f["opened"] = []
    return f


def test_sketch_decides_direct_without_reading(tmp_path):
    code, rows, s = call(tmp_path, "sketch", sketch(kind="internal", changes=[], files=[]))
    assert code == 0 and s["mode"] == "direct" and (s["low"], s["high"]) == (1, 1)


def test_sketch_without_paths_spans_reach(tmp_path):
    s = call(tmp_path, "sketch", sketch(files=[], lines="30-150"))[2]
    # check_rate is in 3 files (its own among them): reach 1 to 1.5, 2x2 -> 4 to 6
    assert s["mode"] is None and (s["low"], s["high"]) == (4, 6)


def test_sketch_with_paths_uses_found_reach(tmp_path):
    s = call(tmp_path, "sketch", sketch())[2]
    assert s["mode"] == "direct" and (s["low"], s["high"]) == (3, 3)


def test_sketch_unsure_lines_span_sizes(tmp_path):
    s = call(tmp_path, "sketch", sketch(kind="internal", changes=[], lines="unsure"))[2]
    assert s["mode"] is None and (s["low"], s["high"]) == (1, 5)
    s = call(tmp_path, "sketch", sketch(kind="architecture", changes=["check_rate"], lines="unsure"))[2]
    assert s["mode"] is None and (s["low"], s["high"]) == (4.5, 22.5)


def test_sketch_unresolved_is_undecided_unless_full(tmp_path):
    f = sketch(kind="internal", changes=[])
    f["unresolved"] = ["where sessions live"]
    assert call(tmp_path, "sketch", f)[2]["mode"] is None
    f["parts"][0].update(kind="data", existing_data=True, changes=["check_rate"])
    assert call(tmp_path, "sketch", f)[2]["mode"] == "full"


def test_sketch_rules(tmp_path):
    f = sketch()
    f["opened"] = ["docs.md"]
    assert call(tmp_path, "sketch", f)[0] == 1
    assert call(tmp_path, "sketch", sketch(files=[{"path": "app/nope.py", "action": "edit"}]))[0] == 1
    code, rows, _ = call(tmp_path, "score", form(files=[], lines="unsure"))
    assert code == 1 and {"files", "lines"} <= {r["kind"] for r in rows}
