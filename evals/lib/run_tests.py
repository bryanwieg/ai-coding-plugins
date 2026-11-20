"""run_tests.py START_DIR: discover unittest tests in START_DIR, print the
unittest output, then one JSON line {test id: ok|fail|error|skip}. Exit 0
only if at least one test ran and all passed."""
import io
import json
import sys
import unittest


class Recorder(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.outcomes = {}

    def addSuccess(self, test):
        super().addSuccess(test)
        self.outcomes[test.id()] = "ok"

    def addFailure(self, test, err):
        super().addFailure(test, err)
        self.outcomes[test.id()] = "fail"

    def addError(self, test, err):
        super().addError(test, err)
        self.outcomes[test.id()] = "error"

    def addSkip(self, test, reason):
        super().addSkip(test, reason)
        self.outcomes[test.id()] = "skip"


stream = io.StringIO()
suite = unittest.defaultTestLoader.discover(sys.argv[1], top_level_dir=sys.argv[1])
result = unittest.TextTestRunner(stream=stream, verbosity=2, resultclass=Recorder).run(suite)
# Import errors appear as failing _FailedTest cases and are recorded above.
sys.stdout.write(stream.getvalue())
print(json.dumps(result.outcomes))
sys.exit(0 if result.testsRun and result.wasSuccessful() else 1)
