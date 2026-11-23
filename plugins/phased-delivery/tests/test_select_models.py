import copy
import json
from pathlib import Path
import subprocess
import sys

import pytest

PLUGIN = Path(__file__).resolve().parents[1]
SCRIPT = PLUGIN / "scripts" / "select-models.py"
# A frozen copy: the weekly refresh replaces model-report.json.
REPORT = json.loads((PLUGIN / "tests" / "fixtures" / "model-report-2026-11-21.json").read_text())
AVAILABLE = PLUGIN / "tests" / "fixtures" / "available-claude.json"
# Hand-built pairs, one routing rule visible in each; see the comments in the route tests.
PROFILES = PLUGIN / "tests" / "fixtures" / "profiles.json"
OFFERED = {"tool": "codex", "subagent_model_choice": "allowed",
           "models": [{"id": f"gpt-9-{name}", "efforts": ["low", "medium", "high", "xhigh", "max"]}
                      for name in ("luna", "terra", "sol", "astra", "nova")]}


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


@pytest.fixture
def offered(tmp_path):
    path = tmp_path / "available.json"
    path.write_text(json.dumps(OFFERED))
    return path


def route(available, scores, *options, profiles=PROFILES):
    result = run("route", available, "--scores", scores, "--profiles", profiles, *options)
    assert result.returncode == 0, result.stderr
    [line] = result.stdout.splitlines()
    return json.loads(line)


def pair(picked):
    return picked["model"].removeprefix("gpt-9-"), picked["effort"]


def test_route_frontier(offered):
    # Middle floor 51 (85% of 60): terra high is the cheapest pair meeting it.
    # terra medium, a low-gain step, would otherwise win the 3-point tie rule.
    middle = route(offered, "J1F1R0C0K0P0V0S0")
    assert {k: middle[k] for k in ("model", "effort", "tier", "premium", "score",
                                   "cap_tokens", "cap_usd")} == {
        "model": "gpt-9-terra", "effort": "high", "tier": "middle", "premium": False,
        "score": 51.2, "cap_tokens": 400000, "cap_usd": 0.8}
    # middle+ is the next frontier pair: terra xhigh scores just above terra
    # high but sol low beats it on both score and cost.
    assert pair(route(offered, "J1F1R0C0K0P2V0S0")) == ("sol", "low")


def test_route_stage_signals(offered, tmp_path):
    # Mechanical middle stage: terra high without the cap, sol low at medium or below.
    assert pair(route(offered, "J0F1R1C1K0P0V0S1")) == ("sol", "low")
    # Small mechanical stages keep higher levels: luna xhigh here, haiku high
    # on the committed data.
    assert pair(route(offered, "J0F1R1C0K0P0V0S0")) == ("luna", "xhigh")
    claude = route(AVAILABLE, "J0F1R1C0K0P0V0S0", profiles=build_profiles(tmp_path, REPORT))
    assert pair(claude) == ("haiku", "high")
    # F2 caps at high: small would be luna xhigh.
    assert pair(route(offered, "J0F2R0C0K0P0V0S0")) == ("terra", "low")
    # F2 prefers the faster close pair: top is astra high, sol high is faster.
    assert pair(route(offered, "J1F2R1C1K0P2V2S0")) == ("sol", "high")
    # J2 moves up the model before the thinking level: nova low costs 1.33x astra high.
    assert pair(route(offered, "J2F1R0C0K0P0V0S0")) == ("nova", "low")
    # Risk moves one frontier pair up from the middle pick, terra high.
    assert pair(route(offered, "J1F1R0C0K1P0V0S0")) == ("sol", "low")


def test_route_limits(offered):
    # One step below terra high: luna max is beaten by terra low, terra medium is low gain.
    down = route(offered, "J1F1R0C0K0P0V0S0", "--down", "1")
    assert pair(down) == ("terra", "low") and "--down 1" in down["why"]
    top_build = "J1F1R1C1K0P2V2S1"
    assert route(offered, top_build)["premium"]
    over = route(offered, top_build, "--premium-spent", "10")
    assert pair(over) == ("sol", "high") and not over["premium"] and "budget" in over["why"]
    review = route(offered, "J1F1R0C0K0P0V0S0", "--review", "--premium-spent", "10")
    assert (pair(review), review["tier"], review["premium"], review["cap_usd"]) == (
        ("astra", "high"), "top", True, 10.0)
    # a review ignores the stage's scores: no caps or preferences shape it
    assert pair(route(offered, "J0F2R2C0K2P0V0S2", "--review")) == ("astra", "high")
