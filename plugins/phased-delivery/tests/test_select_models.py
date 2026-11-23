import copy
import json
from pathlib import Path
import subprocess
import sys


PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "scripts" / "select-models.py"
REPORT = json.loads((PLUGIN / "model-report.json").read_text())
AVAILABLE = PLUGIN.parents[1] / "docs" / "plans" / "model-profiles" / "models-available.json"


def run(*args):
    return subprocess.run([sys.executable, SCRIPT, *args], capture_output=True, text=True)


def build_profiles(tmp_path, report):
    source = tmp_path / "report.json"
    source.write_text(json.dumps(report))
    assert run("profiles", source, tmp_path).returncode == 0
    return tmp_path / "model-profiles.json"


def test_any_age_and_check(tmp_path):
    profiles = build_profiles(tmp_path, {**REPORT, "checked": "2020-01-01"})
    fingerprint = json.loads(profiles.read_text())["fingerprint"]
    models_md = tmp_path / "models.md"
    result = run(AVAILABLE, "--profiles", profiles, "--out", models_md, "--today", "2026-11-23")
    assert result.returncode == 0, result.stderr
    text = models_md.read_text()
    assert f"Profiles: {fingerprint} (data checked 2020-01-01); {REPORT['attribution']}" in text
    tiers = [line.split(" | ")[:3] for line in text.splitlines() if line.startswith("| ")][2:]
    assert tiers == [["| small", "haiku", "high"], ["| middle", "opus", "medium"],
                     ["| middle+", "opus", "high"], ["| top", "opus", "high"]]

    assert run("check", models_md, "--profiles", profiles).returncode == 0
    repriced = copy.deepcopy(REPORT)
    repriced["rows"][0]["price_out_per_1m_usd"] = 99
    build_profiles(tmp_path, repriced)
    assert run("check", models_md, "--profiles", profiles).returncode == 1
    models_md.write_text(text.replace("Profiles:", "Report:"))
    build_profiles(tmp_path, REPORT)
    assert run("check", models_md, "--profiles", profiles).returncode == 1
