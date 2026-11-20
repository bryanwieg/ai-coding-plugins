"""Hidden checks for p2-multistep (run by check.sh), one group per brief step."""
import ast
import os
import re
import shutil
import sys

sys.path.insert(0, os.path.join(os.environ["KIT"], "lib"))
from checklib import (BASELINE, RUN, SCRIPT, check, copy_repo, first_diff, info,  # noqa: E402
                      load_module, read, run_tests, select)

PLUGIN = os.path.join("plugins", "phased-delivery")
TESTS = os.path.join(PLUGIN, "tests")
TEST_FILE = os.path.join(TESTS, "test_effort.py")
GUIDE = os.path.join(PLUGIN, "skills", "plan-in-phases", "model-selection.md")
SENTENCE = ('Effort names are compared ignoring case and punctuation, and a trailing word '
            '"thinking" is dropped, so `High thinking` counts as `high`.')
ANCHOR = "the `efforts` it accepts."
ORIGINAL_TESTS = {"test_lowercases", "test_removes_punctuation", "test_empty_is_default",
                  "test_thinking_suffix"}
CASES = {"high-thinking": "high", "xhigh thinking": "xhigh", "High_Thinking": "high",
         "x-high": "xhigh", "High": "high", "highthinking": "highthinking",
         "": "default", None: "default"}


def squash(text):
    return re.sub(r"\s+", " ", text or "").strip()


# Step 1: behavior of normalize_effort.
try:
    module = load_module(os.path.join(RUN, SCRIPT))
    wrong = {k: module.normalize_effort(k) for k in CASES if module.normalize_effort(k) != CASES[k]}
    check("step 1 normalize_effort", not wrong,
          ", ".join(f"{k!r} -> {v!r} (want {CASES[k]!r})" for k, v in wrong.items()))
except Exception as error:  # the builder's script may not import
    module = None
    check("step 1 normalize_effort", False, f"{type(error).__name__}: {error}")

# Step 2: docstring.
doc = getattr(getattr(module, "normalize_effort", None), "__doc__", None)
check("step 2 docstring", bool(doc) and "thinking" in doc.lower(), f"docstring {doc!r}")

# Step 3: the guide sentence, in place, and nothing else changed.
run_guide, base_guide = squash(read(os.path.join(RUN, GUIDE))), squash(read(os.path.join(BASELINE, GUIDE)))
want_guide = base_guide.replace(ANCHOR, ANCHOR + " " + SENTENCE, 1)
check("step 3 model-selection sentence", run_guide == want_guide,
      "sentence missing" if squash(SENTENCE) not in run_guide
      else "sentence present but placed elsewhere or other text changed: "
      + first_diff(run_guide.replace(". ", ".\n"), want_guide.replace(". ", ".\n")))

# Step 4 (running the tests) leaves nothing in the files.
info("step 4 (run the tests) is not visible in files; grade it from the tool log")

# Steps 5 and 6: the test file, judged by running it against the new and
# the old script.
test_source = read(os.path.join(RUN, TEST_FILE))
methods = {}
if test_source is not None:
    try:
        for node in ast.walk(ast.parse(test_source)):
            if isinstance(node, ast.FunctionDef) and node.name.startswith("test"):
                methods[node.name] = ast.get_source_segment(test_source, node)
    except SyntaxError as error:
        check("test file parses", False, str(error))

new_copy = copy_repo(RUN, "new")
code_new, on_new, out_new = run_tests(os.path.join(new_copy, TESTS))
old_copy = copy_repo(BASELINE, "old")
if test_source is not None:
    shutil.copy(os.path.join(RUN, TEST_FILE), os.path.join(old_copy, TEST_FILE))
code_old, on_old, _ = run_tests(os.path.join(old_copy, TESTS))
outcome = lambda results, name: next((r for t, r in results.items() if t.endswith("." + name)), "missing")

check("step 5 original tests kept", ORIGINAL_TESTS <= set(methods),
      "missing " + ", ".join(sorted(ORIGINAL_TESTS - set(methods))))
check("step 5 test_thinking_suffix updated",
      outcome(on_new, "test_thinking_suffix") == "ok"
      and outcome(on_old, "test_thinking_suffix") != "ok"
      and '"high"' in (methods.get("test_thinking_suffix") or "").replace("'", '"'),
      f"new code: {outcome(on_new, 'test_thinking_suffix')}, "
      f"old code: {outcome(on_old, 'test_thinking_suffix')} (want ok / not ok)")

added = sorted(set(methods) - ORIGINAL_TESTS)
check("step 6 exactly one new test", len(added) == 1, f"new test methods: {added}")
xhigh = [m for m in added if "xhigh thinking" in methods[m]]
check("step 6 xhigh thinking test",
      len(xhigh) == 1 and outcome(on_new, xhigh[0]) == "ok" and outcome(on_old, xhigh[0]) != "ok",
      f"tests mentioning 'xhigh thinking': {xhigh}"
      + (f"; new code: {outcome(on_new, xhigh[0])}, old code: {outcome(on_old, xhigh[0])}" if xhigh else ""))

check("tests green", code_new == 0,
      ", ".join(f"{t}={r}" for t, r in on_new.items() if r != "ok") or out_new[-300:])

code, base_out, _ = select(BASELINE)
code, out, err = select(RUN)
check("output unchanged", code == 0 and out == base_out,
      f"exit {code}: {err.strip()[-200:]}" if code else first_diff(out, base_out))
