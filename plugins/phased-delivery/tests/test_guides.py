import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GUIDE = ROOT / "skills" / "plan-in-phases" / "model-selection.md"
DRIVER = ROOT / "scripts" / "run-phase.py"


def test_model_selection_leaves_the_loop_to_the_driver():
    text = " ".join(GUIDE.read_text().split())
    session_loop = ["the implementer runs", "re-scores at", "At dispatch, re-score",
                    "retry it with `route --down", "rerun it with `route --up",
                    "**Stop and report:**", "stop and report, with the cause", "review pending"]
    assert [p for p in session_loop if p in text] == []
    named = set(re.findall(r"`([a-z]+-[a-z-]+)`", text)) & {"models-stale", "revise-capped", "builder-stopped"}
    halts = set(re.findall(r'"([a-z]+-[a-z-]+)"', DRIVER.read_text()))
    assert named == {"models-stale", "revise-capped", "builder-stopped"} <= halts
