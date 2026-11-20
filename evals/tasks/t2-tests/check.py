"""Hidden checks for t2-tests (run by check.sh): the builder's tests pass on
the real script, then each planted bug (mutant) is applied alone to a copy
of select-models.py and the tests are run again; a mutant is killed when
any test fails or errors."""
import os
import sys

sys.path.insert(0, os.path.join(os.environ["KIT"], "lib"))
from checklib import RUN, SCRIPT, check, copy_repo, info, read, run_tests  # noqa: E402

TESTS = os.path.join("plugins", "phased-delivery", "tests")
NEW_TEST = os.path.join(TESTS, "test_select_models.py")

# (name, exact text in the base script, replacement)
MUTANTS = [
    ("effort_denial > becomes >=",
     "    if EFFORT_ORDER.index(effort) > EFFORT_ORDER.index(ceiling):\n",
     "    if EFFORT_ORDER.index(effort) >= EFFORT_ORDER.index(ceiling):\n"),
    ("match_model family check removed",
     "    if len(families) > 1:\n"
     "        return None, \"ambiguous: \" + \", \".join(sorted(partial)) + \"; add an explicit match\"\n",
     ""),
    ("normalize_effort returns None for empty",
     "effort.lower()) if effort else DEFAULT_EFFORT\n",
     "effort.lower()) if effort else None\n"),
    ("effort_denial unknown-level branch removed",
     "    if effort not in EFFORT_ORDER:\n"
     "        return f\"denied: unknown level, cannot confirm it is at or below {ceiling}\"\n",
     ""),
    ("match_model exact-match branch skipped",
     "    if len(exact) == 1:\n"
     "        return exact[0], \"exact name\"\n",
     ""),
]

if not check("test-file-exists", read(os.path.join(RUN, NEW_TEST)) is not None,
             f"{NEW_TEST} missing"):
    print("INFO mutants killed 0/5")
    sys.exit(0)

real = copy_repo(RUN, "real")
code, results, output = run_tests(os.path.join(real, TESTS))
new_ids = [t for t in results if ".test_select_models." in t or t.startswith("test_select_models.")]
info(f"tests run on real code: {len(results)} ({len(new_ids)} in test_select_models.py)")
check("green-on-real-code", code == 0 and len(new_ids) > 0,
      f"exit {code}; " + (", ".join(f"{t}={r}" for t, r in results.items() if r != "ok")
                          or output[-300:]))

killed = 0
for index, (name, old, new) in enumerate(MUTANTS, 1):
    copy = copy_repo(RUN, f"mutant{index}")
    script = os.path.join(copy, SCRIPT)
    source = read(script)
    if source.count(old) != 1:
        # The builder changed the script (also a scope failure); report it.
        info(f"mutant {index} ({name}): could not apply, target text not found once")
        continue
    with open(script, "w") as out:
        out.write(source.replace(old, new))
    code, results, _ = run_tests(os.path.join(copy, TESTS))
    caught = [t for t, r in results.items() if r != "ok"]
    is_killed = code != 0
    killed += is_killed
    info(f"mutant {index} ({name}): {'killed by ' + ', '.join(caught) if is_killed else 'survived'}")

print(f"INFO mutants killed {killed}/{len(MUTANTS)}")
check("mutants killed >= 3/5", killed >= 3, f"killed {killed}/{len(MUTANTS)}")
