"""Red tests for the lifetime of a checker process: its own session, and the whole group killed at a timeout or interrupt.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`run(command)` starts the checker in its "own session; the whole group is killed at the timeout or on any interrupt", a
`Command` carries `timeout: float | None`, and `Completed` carries `timed_out: bool`.

A process in its own session leads it, so its session id is its own pid. The checker here starts a child of its own,
which stays in the checker's process group. That child holds a `Witness` FIFO (the `tests/support/lifeline.py` module
of the no-wall-clock design spec), writes a marker into it and then lives on a `Lifeline` the test releases only after
the FIFO's end; the checker lives on the same `Lifeline`, and both note their pids for the test's `Pids` to kill at
teardown. The test reads the FIFO to its end: the end comes only when every holder has closed it, so it comes before
the release only when the child is dead. A child the group kill missed holds the FIFO until pytest-timeout ends the
test.

The interrupt is a KeyboardInterrupt in the process that called `run`: the checker sends SIGINT to the test's own pid
once its child holds the FIFO. Whether `run` raises the interrupt again after it kills the group the documents do not
say, so a KeyboardInterrupt out of `run` is let through and nothing is claimed about it.
"""

import contextlib
import os
import sys
from pathlib import Path

from gates.core.checker import Command, Completed, run
from tests.support.lifeline import WITNESS, Lifeline, Pids, Witness

# A timeout the checker's child opens the FIFO well inside.
TIMEOUT = 3.0

EXIT_CODE = 3

HELD = b"held"

NO_TARGET = "0"

EXIT = "import sys\nsys.exit(int(sys.argv[1]))\n"

SLEEPER = "import time\ntime.sleep(20)\n"

SESSION = "import os, sys\nsys.stdout.write(str(os.getsid(0) == os.getpid()))\n"

# Arguments: the FIFO, the pids file, the pid to interrupt or 0, the lifeline's read end, the child's code.
CHECKER = (
    "import os, signal, subprocess, sys\n"
    "fifo, pids, target, line = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4]\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[5], fifo, line],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, pass_fds=(int(line),),\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'w', encoding='utf-8') as out:\n"
    "    out.write(f'{os.getpid()}\\n{child.pid}\\n')\n"
    "if target:\n"
    "    os.kill(target, signal.SIGINT)\n"
    "while os.read(int(line), 65536):\n"
    "    pass\n"
)

LEAVER = (
    "import subprocess, sys\n"
    "fifo, pids, line = sys.argv[1], sys.argv[2], sys.argv[4]\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[5], fifo, line],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, pass_fds=(int(line),),\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'w', encoding='utf-8') as out:\n"
    "    out.write(f'{child.pid}\\n')\n"
)


def _python(code: str, *arguments: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code, *arguments)


def _run(cwd: Path, argv: tuple[str, ...], timeout: float | None = None, pass_fds: tuple[int, ...] = ()) -> Completed:
    return run(Command(argv=argv, cwd=cwd, timeout=timeout, pass_fds=pass_fds))


def _group_run(tmp_path: Path, target: str, timeout: float | None, checker: str = CHECKER) -> bytes:
    """Run the checker and its child through `run`, and read the FIFO the child held to its end."""
    with Lifeline() as line, Pids(tmp_path / "pids.txt") as pids, Witness(tmp_path / "held.fifo") as witness:
        argv = _python(checker, str(witness.path), str(pids.path), target, str(line.read_fd), WITNESS)
        with contextlib.suppress(KeyboardInterrupt):
            _run(tmp_path, argv, timeout, (line.read_fd,))
        return witness.ended()


def test_own_session(tmp_path: Path) -> None:
    """The checker starts in a session of its own, so its session id is its own pid."""
    assert _run(tmp_path, _python(SESSION)).stdout == "True"


def test_timed_out(tmp_path: Path) -> None:
    """A checker still running when the Command's timeout passes gives back a Completed that says timed_out."""
    assert _run(tmp_path, _python(SLEEPER), TIMEOUT).timed_out is True


def test_in_time(tmp_path: Path) -> None:
    """A checker that exits inside the Command's timeout is not timed_out, and keeps its own exit status."""
    completed = _run(tmp_path, _python(EXIT, str(EXIT_CODE)), TIMEOUT)

    assert (completed.timed_out, completed.status) == (False, EXIT_CODE)


def test_timeout_kills_group(tmp_path: Path) -> None:
    """At the timeout the whole group is killed: the checker's child, which held the FIFO, is dead when run returns."""
    assert _group_run(tmp_path, NO_TARGET, TIMEOUT) == HELD


def test_interrupt_kills_group(tmp_path: Path) -> None:
    """On an interrupt the whole group is killed: the checker's child, which held the FIFO, is dead after run."""
    assert _group_run(tmp_path, str(os.getpid()), None) == HELD


def test_normal_exit_kills_group(tmp_path: Path) -> None:
    """A checker that exits normally and leaves its child running: the child, which held the FIFO, is dead after run."""
    assert _group_run(tmp_path, NO_TARGET, None, LEAVER) == HELD
