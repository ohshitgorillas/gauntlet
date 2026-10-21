"""Red tests for the lifetime of a checker process: its own session, and the whole group killed at a timeout or interrupt.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`run(command)` starts the checker in its "own session; the whole group is killed at the timeout or on any interrupt", a
`Command` carries `timeout: float | None`, and `Completed` carries `timed_out: bool`.

A process in its own session leads it, so its session id is its own pid. The checker here starts a child of its own,
which stays in the checker's process group. That child opens a FIFO the test holds the read end of, writes a marker into
it and keeps it open for far longer than any test waits. The test reads the FIFO to its end: the end comes only when
every writer has closed it, so it comes promptly only when the child is dead. A child still holding it after the wait
is killed by the test, and the read gives back the marker followed by ALIVE.

The interrupt is a KeyboardInterrupt in the process that called `run`: the checker sends SIGINT to the test's own pid
once its child holds the FIFO. Whether `run` raises the interrupt again after it kills the group the documents do not
say, so a KeyboardInterrupt out of `run` is let through and nothing is claimed about it.
"""

import contextlib
import os
import signal
import sys
import time
from pathlib import Path

from gates.core.checker import Command, Completed, run

# A timeout the checker's child opens the FIFO well inside.
TIMEOUT = 3.0

# How long the test waits for the FIFO's end once `run` has returned.
WAIT = 5.0

# How long the test sleeps between reads of the FIFO while a writer holds it and has nothing new.
POLL = 0.05

EXIT_CODE = 3

HELD = b"held"

ALIVE = b" alive"

NO_TARGET = "0"

EXIT = "import sys\nsys.exit(int(sys.argv[1]))\n"

SLEEPER = "import time\ntime.sleep(20)\n"

SESSION = "import os, sys\nsys.stdout.write(str(os.getsid(0) == os.getpid()))\n"

GRANDCHILD = (
    "import os, sys, time\n"
    "held = os.open(sys.argv[1], os.O_WRONLY)\n"
    "os.write(held, b'held')\n"
    "print('ready', flush=True)\n"
    "time.sleep(40)\n"
)

CHECKER = (
    "import os, signal, subprocess, sys, time\n"
    "fifo, pids, target = sys.argv[1], sys.argv[2], int(sys.argv[3])\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[4], fifo],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'w', encoding='utf-8') as out:\n"
    "    out.write(f'{os.getpid()}\\n{child.pid}\\n')\n"
    "if target:\n"
    "    os.kill(target, signal.SIGINT)\n"
    "time.sleep(20)\n"
)

LEAVER = (
    "import subprocess, sys\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[4], sys.argv[1]],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,\n"
    ")\n"
    "child.stdout.readline()\n"
)


def _python(code: str, *arguments: str) -> tuple[str, ...]:
    return (sys.executable, "-c", code, *arguments)


def _run(cwd: Path, argv: tuple[str, ...], timeout: float | None = None) -> Completed:
    return run(Command(argv=argv, cwd=cwd, timeout=timeout))


def _kill_leftovers(pids: Path) -> None:
    """Kill, by the pids the checker recorded, the checker and its child where either outlived the run."""
    if not pids.exists():
        return
    for pid in pids.read_text(encoding="utf-8").split():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(pid), signal.SIGKILL)


def _drain(fifo: int, pids: Path) -> bytes:
    """Read the FIFO to its end: what the child wrote, then ALIVE where a writer still held it after WAIT seconds."""
    held = b""
    deadline = time.monotonic() + WAIT
    while True:
        try:
            chunk = os.read(fifo, 1024)
        except BlockingIOError:
            if time.monotonic() >= deadline:
                _kill_leftovers(pids)
                return held + ALIVE
            time.sleep(POLL)
            continue
        if not chunk:
            return held
        held += chunk
        deadline = time.monotonic() + WAIT


def _group_run(tmp_path: Path, target: str, timeout: float | None, checker: str = CHECKER) -> bytes:
    """Run the checker and its child through `run`, and read the FIFO the child held to its end."""
    path = tmp_path / "held.fifo"
    pids = tmp_path / "pids.txt"
    os.mkfifo(path)
    fifo = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        argv = _python(checker, str(path), str(pids), target, GRANDCHILD)
        with contextlib.suppress(KeyboardInterrupt):
            _run(tmp_path, argv, timeout)
        return _drain(fifo, pids)
    finally:
        os.close(fifo)


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
