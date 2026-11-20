"""Tests for normalize_effort(), match_model() and effort_denial() in
scripts/select-models.py.

Run from the repository root:
  python3 -m unittest discover -s plugins/phased-delivery/tests
"""
import importlib.util
import os
import unittest

# The script's file name has a hyphen, so it is loaded by path.
SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                      "..", "scripts", "select-models.py")
spec = importlib.util.spec_from_file_location("select_models", SCRIPT)
select_models = importlib.util.module_from_spec(spec)
spec.loader.exec_module(select_models)


class NormalizeEffortTest(unittest.TestCase):
    def test_lowercases(self):
        self.assertEqual(select_models.normalize_effort("High"), "high")

    def test_removes_punctuation(self):
        self.assertEqual(select_models.normalize_effort("x-high"), "xhigh")

    def test_empty_is_default(self):
        self.assertEqual(select_models.normalize_effort(""), select_models.DEFAULT_EFFORT)

    def test_none_is_default(self):
        self.assertEqual(select_models.normalize_effort(None), select_models.DEFAULT_EFFORT)


class MatchModelTest(unittest.TestCase):
    def test_explicit(self):
        bases = {"Claude Opus 5": {"released": "2026-01-01"}}
        self.assertEqual(select_models.match_model({"id": "x", "match": "Claude Opus 5"}, bases),
                         ("Claude Opus 5", "explicit"))

    def test_explicit_name_missing(self):
        bases = {"Claude Opus 5": {"released": "2026-01-01"}}
        name, _ = select_models.match_model({"id": "x", "match": "Nope"}, bases)
        self.assertIsNone(name)

    def test_exact_name(self):
        bases = {"Claude Opus 5": {"released": "2026-01-01"},
                 "Claude Opus 5 Mini": {"released": "2026-01-01"}}
        self.assertEqual(select_models.match_model({"id": "claude-opus-5"}, bases),
                         ("Claude Opus 5", "exact name"))

    def test_alias_picks_newest_release(self):
        bases = {"Claude Opus 4": {"released": "2025-05-01"},
                 "Claude Opus 5": {"released": "2026-05-01"}}
        self.assertEqual(select_models.match_model({"id": "opus"}, bases),
                         ("Claude Opus 5", "alias: newest release containing the name"))

    def test_ambiguous_across_families(self):
        bases = {"Claude Opus 5": {"released": "2026-01-01"},
                 "Claude Sonnet 5": {"released": "2026-02-01"}}
        name, reason = select_models.match_model({"id": "claude"}, bases)
        self.assertIsNone(name)
        self.assertTrue(reason.startswith("ambiguous"))

    def test_no_match(self):
        bases = {"Claude Opus 5": {"released": "2026-01-01"}}
        self.assertEqual(select_models.match_model({"id": "gemini"}, bases),
                         (None, "no report model matches the name"))


class EffortDenialTest(unittest.TestCase):
    def test_no_ceiling_allows_anything(self):
        self.assertIsNone(select_models.effort_denial("max", None))

    def test_default_effort_allowed(self):
        self.assertIsNone(select_models.effort_denial(select_models.DEFAULT_EFFORT, "low"))

    def test_at_ceiling_allowed(self):
        self.assertIsNone(select_models.effort_denial("high", "high"))

    def test_below_ceiling_allowed(self):
        self.assertIsNone(select_models.effort_denial("low", "high"))

    def test_above_ceiling_denied(self):
        self.assertIn("above", select_models.effort_denial("xhigh", "high"))

    def test_unknown_level_denied(self):
        self.assertIn("unknown level", select_models.effort_denial("turbo", "high"))


if __name__ == "__main__":
    unittest.main()
