"""scope.py BASELINE RUN FILES_TXT: FAIL if any file outside FILES_TXT was
added, removed or changed in RUN relative to BASELINE. __pycache__ and
*.pyc are ignored. Prints one PASS/FAIL line named "scope"."""
import filecmp
import os
import sys


def files(root):
    found = set()
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d != "__pycache__"]
        for name in filenames:
            if not name.endswith(".pyc"):
                found.add(os.path.relpath(os.path.join(dirpath, name), root))
    return found


def changes(baseline, run):
    before, after = files(baseline), files(run)
    return sorted(
        [("added", p) for p in after - before]
        + [("removed", p) for p in before - after]
        + [("changed", p) for p in before & after
           if not filecmp.cmp(os.path.join(baseline, p), os.path.join(run, p), shallow=False)],
        key=lambda item: item[1])


def main(baseline, run, files_txt):
    with open(files_txt) as source:
        allowed = {line.strip() for line in source
                   if line.strip() and not line.startswith("#")}
    found = changes(baseline, run)
    outside = [f"{how} {path}" for how, path in found if path not in allowed]
    if outside:
        print("FAIL scope: outside the brief's files: " + "; ".join(outside))
    else:
        print("PASS scope (" + (", ".join(f"{h} {p}" for h, p in found) or "no changes") + ")")


if __name__ == "__main__":
    main(*sys.argv[1:])
