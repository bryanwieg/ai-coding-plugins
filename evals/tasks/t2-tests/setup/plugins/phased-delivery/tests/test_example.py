"""Tests for normalize() in scripts/select-models.py.

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


class NormalizeTest(unittest.TestCase):
    def test_lowercases_and_joins_words_with_hyphens(self):
        self.assertEqual(select_models.normalize("Claude Opus 5.5"), "claude-opus-5-5")

    def test_strips_separators_at_both_ends(self):
        self.assertEqual(select_models.normalize("  GPT (High) "), "gpt-high")


if __name__ == "__main__":
    unittest.main()
