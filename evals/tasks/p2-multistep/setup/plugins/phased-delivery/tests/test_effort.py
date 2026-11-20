"""Tests for normalize_effort() in scripts/select-models.py.

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

    def test_thinking_suffix(self):
        self.assertEqual(select_models.normalize_effort("high-thinking"), "highthinking")


if __name__ == "__main__":
    unittest.main()
