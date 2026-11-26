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
                     ["| middle+", "opus", "high"], ["| top", "opus", "high"],
                     ["| top+", "opus", "high"]]

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
    assert claude["cap_usd"] == 0.25  # MIN_CAP_USD: at Haiku's input price it would be $0.01
    # F2 caps at high: small would be luna xhigh.
    assert pair(route(offered, "J0F2R0C0K0P0V0S0")) == ("terra", "low")
    # A top stage that is not among the hardest gets the pair one below top+ (astra high).
    assert pair(route(offered, "J1F2R1C1K0P2V2S0")) == ("sol", "medium")
    # F2 prefers the faster close pair: top+ (total 13) is astra high, sol high is faster.
    assert pair(route(offered, "J1F2R2C1K2P2V1S1")) == ("sol", "high")
    # J2 on a top+ stage moves up the model before the thinking level: nova low costs 1.33x astra high.
    assert pair(route(offered, "J2F1R1C2K2P2V1S0")) == ("nova", "low")
    # Risk moves one frontier pair up from the middle pick, terra high.
    assert pair(route(offered, "J1F1R0C0K1P0V0S0")) == ("sol", "low")
    # On a top stage, K1 does not step up to top+ (only K2 makes a stage top+).
    assert pair(route(offered, "J2F1R1C2K1P2V0S0")) == ("sol", "medium")
    # Without astra and sol high, J2 on top+ picks nova low, and a --up retry
    # after a failure moves on to nova medium.
    narrow = tmp_path / "narrow.json"
    narrow.write_text(json.dumps({**OFFERED, "models": [
        m if m["id"] != "gpt-9-sol" else {**m, "efforts": ["low", "medium"]}
        for m in OFFERED["models"] if m["id"] != "gpt-9-astra"]}))
    assert pair(route(narrow, "J2F1R1C2K2P2V1S0")) == ("nova", "low")
    assert pair(route(narrow, "J2F1R1C2K2P2V1S0", "--up", "1")) == ("nova", "medium")


def edited_profiles(tmp_path, changes):
    """The fixture profiles with some fields changed, keyed by (model, effort)."""
    data = json.loads(PROFILES.read_text())
    for row in data["pairs"] if "pairs" in data else data["profiles"]:
        row.update(changes.get((row["model"], row["effort"]), {}))
    path = tmp_path / "edited-profiles.json"
    path.write_text(json.dumps(data))
    return path


def test_route_premium_below_top(offered, tmp_path):
    # Two steps up from the middle+ pick, sol low, reach astra high (premium,
    # 58.5 for 300); the standard route reaches sol high (58.6 for 320), which
    # scores more, so astra is left out below top.
    up = route(offered, "J1F1R0C0K0P2V0S0", "--up", "2")
    assert pair(up) == ("sol", "high") and not up["premium"] and "below top" in up["why"]
    # Even a premium pair scoring better for less is left out: benchmark run cost
    # understates a premium pair's real spend.
    better = edited_profiles(tmp_path, {("GPT-9 Astra", "high"): {"intelligence": 59}})
    held = route(offered, "J1F1R0C0K0P2V0S0", "--up", "2", profiles=better)
    assert pair(held) == ("sol", "high") and not held["premium"]
    # When the standard pairs run out before a --up retry, the cheapest pair above
    # the standard pick is taken: --up 5 wants nova medium, past sol high, the
    # last standard pair, and gets nova low, the next pair up.
    short = route(offered, "J1F1R0C0K0P2V0S0", "--up", "5")
    assert pair(short) == ("nova", "low") and "--up retry" in short["why"]


def test_route_fable_limits(tmp_path):
    # A single 2 no longer makes a stage top: K2 at total 7 is middle+; a total of 9 is top.
    offered_path = tmp_path / "offered.json"
    offered_path.write_text(json.dumps(OFFERED))
    assert route(offered_path, "J1F1R1C1K2P1V0S0")["tier"] == "middle+"
    assert route(offered_path, "J2F1R1C2K0P2V1S0")["tier"] == "top"
    # Without sol and terra xhigh, the standard pairs end at the middle pick, terra
    # high, so the middle+ step would reach astra high, premium: terra high stays.
    narrow = tmp_path / "narrow.json"
    narrow.write_text(json.dumps({**OFFERED, "models": [
        m if m["id"] != "gpt-9-terra" else {**m, "efforts": ["low", "medium", "high"]}
        for m in OFFERED["models"] if m["id"] != "gpt-9-sol"]}))
    held = route(narrow, "J1F1R0C0K0P2V0S0")
    assert pair(held) == ("terra", "high") and "left out below top" in held["why"]
    # A --up retry after a failure still steps up to the premium pair.
    assert pair(route(narrow, "J1F1R0C0K0P2V0S0", "--up", "1")) == ("astra", "high")
    # The risk step is held the same way, and --up still steps.
    risk = route(narrow, "J1F1R0C0K1P0V0S0")
    assert pair(risk) == ("terra", "high") and "left out below top" in risk["why"]
    assert pair(route(narrow, "J1F1R0C0K1P0V0S0", "--up", "1")) == ("astra", "high")
    # A --down retry after a budget stop goes one pair below the held terra high.
    down = route(narrow, "J1F1R0C0K1P2V0S0", "--down", "1")
    assert pair(down) == ("terra", "low") and not down["premium"]
    # A premium pair barely costlier than terra high is still left out below top.
    near = edited_profiles(tmp_path, {("GPT-9 Astra", "high"): {"run_cost_usd": 91}})
    assert pair(route(narrow, "J1F1R0C0K0P2V0S0", profiles=near)) == ("terra", "high")


def test_route_pick_ceilings(tmp_path):
    # Fable above medium sets the best score the floors measure from but is never
    # picked: middle and top stay on Opus high, and only top+ and its reviews get
    # Fable, at low (within 3 points of medium), medium on a --up retry.
    available = tmp_path / "available.json"
    available.write_text(json.dumps({**json.loads(AVAILABLE.read_text()), "models": [
        {"id": m, "efforts": ["low", "medium", "high", "xhigh", "max"]}
        for m in ("fable", "opus", "sonnet", "haiku")]}))
    profiles = build_profiles(tmp_path, REPORT)
    for scores in ("J1F1R0C0K0P0V0S0", "J1F1R1C1K2P0V0S0", "J2F1R1C2K0P2V1S0"):
        assert pair(route(available, scores, profiles=profiles)) == ("opus", "high"), scores
    assert pair(route(available, "J0F0R0C0K0P0V0S0", "--review", profiles=profiles)) == ("opus", "high")
    hardest = "J1F2R2C2K2P2V1S1"
    assert pair(route(available, hardest, profiles=profiles)) == ("fable", "low")
    assert pair(route(available, hardest, "--review", profiles=profiles)) == ("fable", "low")
    assert pair(route(available, hardest, "--up", "3", profiles=profiles)) == ("fable", "medium")


def test_route_speed_gain(offered, tmp_path):
    # sol high at 45 is only 1.125x astra high's 40: under SPEED_GAIN, so F2 keeps astra.
    slow = edited_profiles(tmp_path, {("GPT-9 Sol", "high"): {"speed": 45}})
    assert pair(route(offered, "J1F2R2C1K2P2V1S1", profiles=slow)) == ("astra", "high")


def test_route_limits(offered):
    # One step below terra high: luna max is beaten by terra low, terra medium is low gain.
    down = route(offered, "J1F1R0C0K0P0V0S0", "--down", "1")
    assert pair(down) == ("terra", "low") and "--down 1" in down["why"]
    top_build = "J1F1R1C1K2P2V2S1"  # K2: top+
    assert route(offered, top_build)["premium"] and route(offered, top_build)["tier"] == "top+"
    over = route(offered, top_build, "--premium-spent", "10")
    assert pair(over) == ("sol", "high") and not over["premium"] and "budget" in over["why"]
    # a review runs on top, or on top+ when its scores are a top+ stage's; premium spend never limits it
    review = route(offered, "J1F1R0C0K0P0V0S0", "--review", "--premium-spent", "10")
    assert (pair(review), review["tier"]) == (("sol", "medium"), "top")
    hard = route(offered, top_build, "--review", "--premium-spent", "10")
    assert (pair(hard), hard["tier"], hard["premium"], hard["cap_usd"]) == (("astra", "high"), "top+", True, 10.0)
    # no caps or preferences shape a review: S2 and F2 do not move it, K2 below top does not make it top+
    assert pair(route(offered, "J0F2R2C0K2P0V0S2", "--review")) == ("sol", "medium")
    assert run("route", offered, "--scores", "J1F1R0C0K0P0V0S0", "--profiles", PROFILES,
               "--down", "-1").returncode == 2
