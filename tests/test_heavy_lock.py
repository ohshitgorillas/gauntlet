# Copyright 2026 oh shit, gorillas!
"""Red tests for the host-safety wrapper whose lock cannot be taken.

Source: the agents design spec under docs/superpowers/specs/, "Decisions", the bullet on heavy runs: "given `--lock
<path>` before its command, it locks that path instead". "Given `--lock` with an empty path, it prints its usage and
exits 2; where its lock's path cannot be opened or locked, the run is never made: the wrapper prints why and exits 2."
The wrapper "reads its arguments through `parser()`, an argparse parser", so its usage is argparse's, which begins
`usage:`.

A lock path is made one no process can open whoever runs it and whatever the wrapper does first: a path under a regular
file, which no directory can be made at either, and a path whose last name is longer than any file name the host allows.
The command each run is given notes a word in a log, so a run made shows in the log. Every run is given `--lock` with a
path under the test's temporary directory, or an empty one, and never takes the default, since this suite's own run
already holds it.
"""

import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

HEAVY_MODULE = "gates.heavy"

REPO_ROOT = Path(__file__).parents[1]

BLOCKED = 2

RAN = "ran"

USAGE = "usage:"

NOTE = "import sys\nwith open(sys.argv[1], 'a', encoding='utf-8') as log:\n    log.write(sys.argv[2] + '\\n')\n"

# Longer than the 255 bytes a file name may hold on macOS and Linux.
LONG_NAME = "l" * 300

EMPTY_LOCK = [["--lock", ""], ["--lock="]]


def _lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines() if path.exists() else []


def _under_file(tmp_path: Path) -> Path:
    """Create a lock path whose parent is a regular file."""
    parent = tmp_path / "file"
    parent.write_text("", encoding="utf-8")
    return parent / "heavy.lock"


def _too_long(tmp_path: Path) -> Path:
    """Create a lock path whose name is longer than the host allows a file name."""
    return tmp_path / LONG_NAME


def _wrapper(options: list[str], log: Path) -> subprocess.CompletedProcess[str]:
    """Run the wrapper with options before a command that notes RAN in log, from the repository root, to its end.

    The child imports the wrapper module when the command runs.
    """
    line = [
        sys.executable,
        "-m",
        HEAVY_MODULE,
        *options,
        sys.executable,
        "-c",
        NOTE,
        str(log),
        RAN,
    ]
    return subprocess.run(
        line, cwd=REPO_ROOT, check=False, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    "unopenable", [_under_file, _too_long], ids=["under-file", "too-long"]
)
def test_unopenable_lock(tmp_path: Path, unopenable: Callable[[Path], Path]) -> None:
    """Where the path given by --lock cannot be opened, the wrapper never runs its command and exits 2."""
    log = tmp_path / "log"

    result = _wrapper(["--lock", str(unopenable(tmp_path))], log)

    assert (result.returncode, _lines(log)) == (BLOCKED, [])


@pytest.mark.parametrize("options", EMPTY_LOCK, ids=["separate", "joined"])
def test_empty_lock(tmp_path: Path, options: list[str]) -> None:
    """Given --lock with an empty path, the wrapper prints its usage and exits 2."""
    result = _wrapper(options, tmp_path / "log")

    assert (result.returncode, USAGE in result.stdout + result.stderr) == (
        BLOCKED,
        True,
    )
