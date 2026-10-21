"""Red tests for a Command run with capture off: the checker writes straight to the run's own fds 1 and 2.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process",
which gives `Command(..., capture: bool = True, ...)` and says: "`capture=False` lets the checker inherit the run's own
fds 1 and 2 and write straight to them; `Completed.stdout` and `.stderr` come back `""`."

The run's own fds 1 and 2 are read through `captured` of `tests/support/capture.py`, which for the length of the call
points each at a pipe of its own and keeps what a child that inherits them writes there. A checker that inherits them
holds those very pipes, so the device and inode of its fds 1 and 2 are the ones the run holds while it runs; a checker
whose output `run` relays through pipes of its own holds others. What the checker writes to its stdout reaches fd 1 alone
and what it writes to its stderr reaches fd 2 alone, and the Completed holds neither.
"""

import os
import sys
from pathlib import Path

from gates.core.checker import Command, Completed, run
from tests.support.capture import captured

OUT = "check: on stdout\n"

ERR = "check: on stderr\n"

STATUS = 5

BOTH = (
    "import sys\n"
    "sys.stdout.write(sys.argv[1])\n"
    "sys.stdout.flush()\n"
    "sys.stderr.write(sys.argv[2])\n"
    "sys.stderr.flush()\n"
    "sys.exit(int(sys.argv[3]))\n"
)

HOLDS = (
    "import os, sys\n"
    "words = [str(value) for fd in (1, 2) for value in (os.fstat(fd).st_dev, os.fstat(fd).st_ino)]\n"
    "with open(sys.argv[1], 'w', encoding='utf-8') as out:\n"
    "    out.write(' '.join(words))\n"
)


def _uncaptured(tmp_path: Path, *argv: str) -> Completed:
    """Run argv in tmp_path through `run` with capture off."""
    return run(Command(argv=argv, cwd=tmp_path, capture=False))


def _writer(tmp_path: Path) -> Completed:
    """Run, with capture off, a checker that writes OUT to its stdout and ERR to its stderr and exits STATUS."""
    return _uncaptured(tmp_path, sys.executable, "-I", "-c", BOTH, OUT, ERR, str(STATUS))


def _held(tmp_path: Path) -> tuple[list[str], list[str]]:
    """The device and inode of fds 1 and 2, as the run holds them and as the checker it starts with capture off does."""
    report = tmp_path / "held.txt"
    own = [str(value) for fd in (1, 2) for value in (os.fstat(fd).st_dev, os.fstat(fd).st_ino)]
    _uncaptured(tmp_path, sys.executable, "-I", "-c", HOLDS, str(report))
    return own, report.read_text(encoding="utf-8").split()


def test_stdout_reaches_fd_one(tmp_path: Path) -> None:
    """What the checker writes to its stdout is written to the run's own fd 1."""
    assert captured(lambda: _writer(tmp_path)).out == [OUT]


def test_stderr_reaches_fd_two(tmp_path: Path) -> None:
    """What the checker writes to its stderr is written to the run's own fd 2."""
    assert captured(lambda: _writer(tmp_path)).err == [ERR]


def test_completed_streams_empty(tmp_path: Path) -> None:
    """The Completed of a checker that wrote to both streams has stdout and stderr empty, beside its own status."""
    done = captured(lambda: _writer(tmp_path)).result
    assert (done.status, done.stdout, done.stderr) == (STATUS, "", "")


def test_inherits_own_fds(tmp_path: Path) -> None:
    """The checker's fds 1 and 2 are the very files the run's own fds 1 and 2 hold, not pipes `run` relays through."""
    own, seen = captured(lambda: _held(tmp_path)).result
    assert seen == own
