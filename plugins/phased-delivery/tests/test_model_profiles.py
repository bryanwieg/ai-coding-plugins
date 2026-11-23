import copy
import json
from pathlib import Path
import subprocess
import sys


PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "scripts" / "select-models.py"
# A frozen copy: the weekly refresh replaces model-report.json.
REPORT = json.loads((PLUGIN / "tests" / "fixtures" / "model-report-2026-11-21.json").read_text())


def profiles(tmp_path, report):
    """Run `profiles` on report into tmp_path; return (exit code, file text or None)."""
    source = tmp_path / "report.json"
    source.write_text(json.dumps(report))
    result = subprocess.run([sys.executable, SCRIPT, "profiles", source, tmp_path],
                            capture_output=True, text=True)
    out = tmp_path / "model-profiles.json"
    return result.returncode, out.read_text() if out.exists() else None


def row(model, effort, score, cost, price_out=10):
    return {"creator": "Anthropic", "model": model, "effort": effort,
            "name": f"{model} ({effort})", "released": "2026-01-01",
            "intelligence_index": score, "engineering_index": None,
            "benchmark_run_cost_usd": cost, "price_in_per_1m_usd": 1,
            "price_out_per_1m_usd": price_out, "output_tokens_per_second": 50}


def test_refresh_only_on_model_or_price_change(tmp_path):
    assert profiles(tmp_path, REPORT)[0] == 0
    code, built = profiles(tmp_path, REPORT)
    assert code == 1

    rescored = copy.deepcopy(REPORT)
    for r in rescored["rows"]:
        if r["intelligence_index"] is not None:
            r["intelligence_index"] += 1
            r["benchmark_run_cost_usd"] *= 2
    assert profiles(tmp_path, rescored) == (1, built)

    dropped = {**REPORT, "rows": REPORT["rows"][1:]}
    added = {**REPORT, "rows": REPORT["rows"] + [row("Claude New", "high", None, None)]}
    repriced = copy.deepcopy(REPORT)
    repriced["rows"][-1]["price_out_per_1m_usd"] = 99
    first_score = copy.deepcopy(REPORT)
    first_score["rows"][0]["intelligence_index"] = 10
    for changed in [dropped, added, repriced, first_score]:
        code, text = profiles(tmp_path, changed)
        assert code == 0 and text != built
        assert profiles(tmp_path, REPORT)[0] == 0  # back to the committed report

    # a report the code cannot handle must not read as "unchanged" (exit 1)
    bad = copy.deepcopy(REPORT)
    bad["rows"][0]["effort"] = 5
    assert profiles(tmp_path, bad)[0] == 2


def test_derived_properties(tmp_path):
    report = {"checked": "2026-11-21", "attribution": "test", "rows": [
        row("M", "low", 30, 100),
        row("M", "medium", None, 150),
        row("M", "high", 40, 200, price_out=30),
        row("M", "xhigh", 41, 400, price_out=None),
        row("M", "non-reasoning", 20, 50),
    ]}
    assert profiles(tmp_path, report)[0] == 0
    pairs = {p["effort"]: p for p in json.loads((tmp_path / "model-profiles.json").read_text())["pairs"]}
    derived = {effort: (p["gain_from_lower"], p["cost_ratio_from_lower"], p["low_gain"], p["premium"])
               for effort, p in pairs.items()}
    assert derived == {
        "low": (None, None, False, False),           # lowest level
        "medium": (None, None, False, False),        # no score
        "high": (None, None, False, True),           # lower level has no score; price 30 is premium
        "xhigh": (1, 2.0, True, False),              # 1 point for 2x cost; missing price not premium
        "nonreasoning": (None, None, False, False),  # outside EFFORT_ORDER
    }
