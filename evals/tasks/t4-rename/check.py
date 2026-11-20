"""Hidden checks for t4-rename (run by check.sh)."""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.environ["KIT"], "lib"))
from checklib import BASELINE, RUN, check, read  # noqa: E402
from scope import changes  # noqa: E402

DIR = os.path.join("plugins", "phased-delivery", "skills", "implement-in-phases")
OLD = os.path.join(DIR, "phase-reviewer.md")
NEW = os.path.join(DIR, "phase-review.md")
LINK = re.compile(r"\]\(([^)\s]+)\)")


def text_files(root):
    for dirpath, dirnames, filenames in os.walk(root):
        rel_dir = os.path.relpath(dirpath, root)
        dirnames[:] = [d for d in dirnames
                       if d != "__pycache__" and not (rel_dir == "." and d == "plan")]
        for name in filenames:
            path = os.path.join(dirpath, name)
            try:
                with open(path, encoding="utf-8") as source:
                    yield os.path.relpath(path, root), source.read()
            except (UnicodeDecodeError, OSError):
                continue


def broken_links(root):
    """Relative markdown links outside fenced code blocks that do not resolve."""
    broken = []
    for rel, text in text_files(root):
        if not rel.endswith(".md") or not (rel == "README.md" or rel.startswith("plugins" + os.sep)):
            continue
        fenced = False
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith("```"):
                fenced = not fenced
                continue
            if fenced:
                continue
            for target in LINK.findall(line):
                if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                    continue
                path = os.path.normpath(os.path.join(root, os.path.dirname(rel), target.split("#")[0]))
                if not os.path.exists(path):
                    broken.append(f"{rel}:{number} -> {target}")
    return broken


hits = [rel for rel, text in text_files(RUN) if "phase-reviewer" in text or "phase-reviewer" in rel]
check("old-name-absent", not hits, "found in " + ", ".join(hits))
check("old-file-removed", not os.path.exists(os.path.join(RUN, OLD)), f"{OLD} still exists")
old_text, new_text = read(os.path.join(BASELINE, OLD)), read(os.path.join(RUN, NEW))
check("new-file-identical", new_text == old_text,
      "missing" if new_text is None else "content differs from the old file")
base_broken = broken_links(BASELINE)
if base_broken:
    sys.exit("FAIL harness: baseline already has broken links: " + ", ".join(base_broken))
broken = broken_links(RUN)
check("links-resolve", not broken, ", ".join(broken))

# Every changed file other than the renamed one must equal the baseline once
# the new name is put back to the old one.
others = []
for how, path in changes(BASELINE, RUN):
    if path in (OLD, NEW):
        continue
    if how != "changed":
        others.append(f"{how} {path}")
        continue
    restored = read(os.path.join(RUN, path)).replace("phase-review.md", "phase-reviewer.md")
    if restored != read(os.path.join(BASELINE, path)):
        others.append(f"other edits in {path}")
check("only-reference-updates", not others, "; ".join(others))
check("skill-link-updated",
      "[phase-review.md](phase-review.md)" in (read(os.path.join(RUN, DIR, "SKILL.md")) or ""),
      "SKILL.md lacks [phase-review.md](phase-review.md)")
