import os
import tempfile
from pathlib import Path

import pytest


def noexec(path):
    return bool(os.statvfs(path).f_flag & os.ST_NOEXEC)


def pytest_configure(config):
    # The tests put stub claude and codex scripts on PATH. On a noexec temp directory
    # (the ai-coding sandbox's /tmp) a stub cannot run and the real CLI answers instead,
    # so keep the temp files in the repository's ignored .pytest-tmp.
    if config.option.basetemp is None and noexec(tempfile.gettempdir()):
        config.option.basetemp = str(Path(__file__).parent / ".pytest-tmp")
        # and stop git there, so a test directory is never taken as part of this repository
        os.environ["GIT_CEILING_DIRECTORIES"] = config.option.basetemp
    base = Path(config.option.basetemp or tempfile.gettempdir())
    base.mkdir(parents=True, exist_ok=True)
    if noexec(base):
        raise pytest.UsageError(f"{base} is mounted noexec: pass --basetemp on a mount that can run files")
