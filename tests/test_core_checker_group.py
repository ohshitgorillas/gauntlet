# Copyright 2026 oh shit, gorillas!
"""Red tests for the lifetime of a checker process: its own session, and the whole group killed at a timeout or interrupt.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`run(command)` starts the checker in its "own session; the whole group is killed at the timeout or on any interrupt", a
`Command` carries `timeout: float | None`, and `Completed` carries `timed_out: bool`.

A process in its own session leads it, so its session id is its own pid. The checker here starts a child of its own,
which stays in the checker's process group. That child holds a `Witness` FIFO (the `tests/support/lifeline.py`), writes a marker into it and then lives on a `Lifeline` the test releases only after
the FIFO's end; the checker lives on the same `Lifeline`, and both note their pids for the test's `Pids` to kill at
teardown. The test reads the FIFO to its end: the end comes only when every holder has closed it, so it comes before
the release only when the child is dead. A child the group kill missed holds the FIFO until pytest-timeout ends the
test.

The interrupt is a KeyboardInterrupt in the process that called `run`: the checker sends SIGINT to the test's own pid
once its child holds the FIFO. Whether `run` raises the interrupt again after it kills the group the documents do not
say, so a KeyboardInterrupt out of `run` is let through and nothing is claimed about it.

The time cap passes on the clock `run` is handed (tests/support/clock.py): a positive cap with
`VirtualClock(passes=...)` at it, against a checker a `Lifeline` holds, which is certainly alive at the clock's first
poll, so the cap passes at once in virtual time and `run` reports `timed_out`. In the timeout's group test the clock's
`after` is the checker's `Beacon`: the checker writes its line there once its child holds the FIFO, so
the cap passes only once the group is whole.
"""

import contextlib
import os
import sys
from pathlib import Path

from gates.core.checker import Command, Completed, run
from tests.support.clock import VirtualClock
from tests.support.lifeline import HOLD, WITNESS, Beacon, Lifeline, Pids, Witness

# A cap that passes only on the VirtualClock handed to run, which lets exactly this many seconds pass at its poll. It
# lies far past pytest-timeout's 30-second bound, so a run that sits the cap out in real time fails at that bound.
CAP = 3600.0

# The cap of the in-time and group-kill tests: it too passes only on the VirtualClock handed to run.
TIMEOUT = CAP

# Seconds a VirtualClock lets pass, short of the cap, while a checker that exits on its own has not yet exited.
SHORT = CAP / 2

EXIT_CODE = 3

HELD = b"held"

NO_TARGET = "0"

EXIT = "import sys\nsys.exit(int(sys.argv[1]))\n"

SESSION = "import os, sys\nsys.stdout.write(str(os.getsid(0) == os.getpid()))\n"

# Arguments: the FIFO, the pids file, the pid to interrupt or 0, the lifeline's read end, the child's code and, when
# given, a Beacon's write end, on which it writes a line once its child holds the FIFO and both pids are noted.
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
    "if len(sys.argv) > 6:\n"
    "    os.write(int(sys.argv[6]), b'whole\\n')\n"
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


def _run(cwd: Path, argv: tuple[str, ...], pass_fds: tuple[int, ...] = ()) -> Completed:
    return run(Command(argv=argv, cwd=cwd, pass_fds=pass_fds))


def _capped_run(
    cwd: Path, argv: tuple[str, ...], timeout: float, line: Lifeline, beacon: Beacon
) -> Completed:
    """Run the checker with a cap that passes on a VirtualClock at once, once the checker has written on its Beacon."""
    clock = VirtualClock(passes=timeout, after=beacon.seen)
    command = Command(
        argv=(*argv, str(beacon.write_fd)),
        cwd=cwd,
        timeout=timeout,
        pass_fds=(line.read_fd, beacon.write_fd),
    )
    return run(command, clock=clock)


def _group_run(
    tmp_path: Path, target: str, timeout: float | None, checker: str = CHECKER
) -> bytes:
    """Run the checker and its child through `run`, and read the FIFO the child held to its end."""
    with (
        Lifeline() as line,
        Pids(tmp_path / "pids.txt") as pids,
        Witness(tmp_path / "held.fifo") as witness,
        Beacon() as beacon,
    ):
        argv = _python(
            checker,
            str(witness.path),
            str(pids.path),
            target,
            str(line.read_fd),
            WITNESS,
        )
        with contextlib.suppress(KeyboardInterrupt):
            if timeout is None:
                _run(tmp_path, argv, (line.read_fd,))
            else:
                _capped_run(tmp_path, argv, timeout, line, beacon)
        return witness.ended()


def test_own_session(tmp_path: Path) -> None:
    """The checker starts in a session of its own, so its session id is its own pid."""
    assert _run(tmp_path, _python(SESSION)).stdout == "True"


def test_timed_out_on_the_clock_run_is_handed(tmp_path: Path) -> None:
    """A checker a Lifeline holds is still running when its cap passes on the clock `run` is handed: timed_out.

    The clock lets the cap pass at once in virtual time, and moves its `now` by the cap, only when `run` waits through
    it with the Command's timeout as the cap.
    """
    clock = VirtualClock(passes=CAP)
    with Lifeline() as line:
        command = Command(
            argv=_python(HOLD, str(line.read_fd)),
            cwd=tmp_path,
            timeout=CAP,
            pass_fds=(line.read_fd,),
        )
        completed = run(command, clock=clock)

    assert (completed.timed_out, clock.now) == (True, CAP)


def test_in_time(tmp_path: Path) -> None:
    """A checker that exits inside the Command's timeout is not timed_out, and keeps its own exit status."""
    command = Command(argv=_python(EXIT, str(EXIT_CODE)), cwd=tmp_path, timeout=TIMEOUT)
    completed = run(command, clock=VirtualClock(passes=SHORT))

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
