"""Helpers for the per-task check.py scripts (run from check.sh, which
exports KIT, RUN, WORK, BASELINE and TODAY)."""
import importlib.util
import json
import os
import shutil
import subprocess
import sys

PLUGIN = os.path.join("plugins", "phased-delivery")
SCRIPT = os.path.join(PLUGIN, "scripts", "select-models.py")
REPORT = os.path.join(PLUGIN, "model-report.json")
KIT = os.environ["KIT"]
RUN = os.environ["RUN"]
WORK = os.environ["WORK"]
BASELINE = os.environ["BASELINE"]
TODAY = os.environ["TODAY"]
FIXTURE = os.path.join(KIT, "fixtures", "live-claude.json")


def check(name, ok, detail=""):
    """Print one PASS/FAIL line; the detail is flattened to one line."""
    flat = " / ".join(part.strip() for part in str(detail).splitlines() if part.strip())
    print(f"PASS {name}" if ok else f"FAIL {name}: {flat[-400:]}")
    return ok


def info(text):
    print(f"INFO {text}")


def select(repo, *args, report=None, available=FIXTURE):
    """Run repo's select-models.py; return (exit code, stdout, stderr)."""
    cmd = [sys.executable, "-B", os.path.join(repo, SCRIPT), available,
           "--report", report or os.path.join(repo, REPORT), "--today", TODAY, *args]
    try:
        done = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return 124, "", "timeout"
    return done.returncode, done.stdout, done.stderr


def load_module(path, name="select_models_under_check"):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def copy_repo(src, name):
    """Copy a repo into WORK/name (so tests never write into the run repo)."""
    dest = os.path.join(WORK, name)
    shutil.copytree(src, dest, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    return dest


def run_tests(start_dir, timeout=180):
    """Discover and run unittest tests in a subprocess; return
    (returncode, {test id: ok|fail|error|skip}, raw output)."""
    runner = os.path.join(KIT, "lib", "run_tests.py")
    try:
        done = subprocess.run([sys.executable, "-B", runner, start_dir],
                              capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return 124, {}, "timeout"
    try:
        results = json.loads(done.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        results = {}
    return done.returncode, results, done.stdout + done.stderr


def first_diff(got, expected):
    gl, el = got.splitlines(), expected.splitlines()
    for i, (g, e) in enumerate(zip(gl, el)):
        if g != e:
            return f"line {i + 1}: got {g!r}, expected {e!r}"
    return f"{len(gl)} lines, expected {len(el)}"


def read(path):
    try:
        with open(path) as source:
            return source.read()
    except OSError:
        return None
