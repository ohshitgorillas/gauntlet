"""Red tests for an interrupt while `run_all` runs checkers in worker threads, and through `check_with`'s budget.

Source: the gates core design spec under docs/superpowers/specs/, decisions 26 and 27. While `run_all` runs, the main
thread answers the signals that end a process as `run` does; on any exception there, a signal's included, it kills the
process group of every checker `run` has started, in any thread, and not yet reaped, waits for every worker, puts the
handlers back, and only then do the exception and each signal take their course. `check_with` with a budget runs its
batches through `run_all`, so on an interrupt every running batch's process group is killed before it goes on.

Two checkers run at once. Each starts a child of its own that holds a FIFO the test reads to its end; the end comes
promptly only when both children are dead. The first checker marks a file once its child holds the FIFO; the second
marks that it started, waits for the first's mark, starts its child, then sends the signal to the process that called
`run_all`. A first checker that does not see the second start within 5 seconds marks the run serial. SIGINT is a
KeyboardInterrupt in pytest's own process. A signal that ends the process at the OS default would end pytest too, so
it is sent to a driver: a Python child that imports the core from the rootdir, sets the signal to the OS default, and
calls `run_all` with `run`.
"""

import contextlib
import os
import signal
import subprocess
import sys
import time
from collections.abc import Sequence
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed, run, run_all
from gates.core.project import Source
from gates.core.report import Line
from gates.core.runner import Run, Scratch, check_with
from tests.support.project import scaffold

# How long the test waits for the FIFO's end or the driver's end, and the second checker for the first one's mark.
WAIT = 10.0

# How long the test sleeps between tries while it waits.
POLL = 0.05

HELD = b"held"

ALIVE = b" alive"

GRANDCHILD = (
    "import os, sys, time\n"
    "held = os.open(sys.argv[1], os.O_WRONLY)\n"
    "os.write(held, b'held')\n"
    "print('ready', flush=True)\n"
    "time.sleep(40)\n"
)

CHECKER = (
    "import os, subprocess, sys, time\n"
    "fifo, pids, mark, signum, role = sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[6]\n"
    "def wait_for(path):\n"
    "    deadline = time.monotonic() + 5\n"
    "    while not os.path.exists(path) and time.monotonic() < deadline:\n"
    "        time.sleep(0.05)\n"
    "    return os.path.exists(path)\n"
    "if role == 'second':\n"
    "    open(mark + '.started', 'w').close()\n"
    "    wait_for(mark)\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[5], fifo],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'a', encoding='utf-8') as out:\n"
    "    out.write(f'{os.getpid()}\\n{child.pid}\\n')\n"
    "if role == 'first':\n"
    "    open(mark, 'w').close()\n"
    "    if not wait_for(mark + '.started'):\n"
    "        open(mark + '.serial', 'w').close()\n"
    "else:\n"
    "    os.kill(os.getppid(), signum)\n"
    "time.sleep(20)\n"
)

DRIVER = (
    "import signal, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "from gates.core.checker import Command, run, run_all\n"
    "signal.signal(int(sys.argv[2]), signal.SIG_DFL)\n"
    "argv = tuple(sys.argv[3:])\n"
    "commands = [Command(argv=(*argv, role), cwd=Path.cwd()) for role in ('first', 'second')]\n"
    "run_all(run, commands, 2)\n"
)


def _argv(tmp_path: Path, signum: int) -> tuple[str, ...]:
    """The checker's argv but its role: the FIFO, the pids file, the mark, the signal and the child's code."""
    return (
        sys.executable,
        "-c",
        CHECKER,
        str(tmp_path / "held.fifo"),
        str(tmp_path / "pids.txt"),
        str(tmp_path / "mark"),
        str(int(signum)),
        GRANDCHILD,
    )


def _commands(tmp_path: Path, signum: int) -> list[Command]:
    argv = _argv(tmp_path, signum)
    return [Command(argv=(*argv, role), cwd=tmp_path) for role in ("first", "second")]


def _kill_leftovers(pids: Path) -> None:
    """Kill, by the pids the checkers recorded, any checker or child that outlived the run."""
    if not pids.exists():
        return
    for pid in pids.read_text(encoding="utf-8").split():
        with contextlib.suppress(ProcessLookupError):
            os.kill(int(pid), signal.SIGKILL)


def _drain(fifo: int, pids: Path) -> bytes:
    """Read the FIFO to its end: what the children wrote, then ALIVE where a writer still held it after WAIT seconds."""
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
        if not chunk and held:
            return held
        if not chunk:
            if time.monotonic() >= deadline:
                return held
            time.sleep(POLL)
            continue
        held += chunk
        deadline = time.monotonic() + WAIT


def _serial(tmp_path: Path) -> bool:
    """Whether the first checker marked the run serial: it did not see the second start while it ran."""
    return (tmp_path / "mark.serial").exists()


def _open_fifo(tmp_path: Path) -> int:
    path = tmp_path / "held.fifo"
    os.mkfifo(path)
    return os.open(path, os.O_RDONLY | os.O_NONBLOCK)


def test_interrupt_kills_every_group(tmp_path: Path) -> None:
    """A KeyboardInterrupt while two checkers run kills both their groups, then goes on out of run_all."""
    fifo = _open_fifo(tmp_path)
    try:
        with pytest.raises(KeyboardInterrupt):
            run_all(run, _commands(tmp_path, signal.SIGINT), 2)
        held = _drain(fifo, tmp_path / "pids.txt")
    finally:
        os.close(fifo)
        _kill_leftovers(tmp_path / "pids.txt")

    assert (held, _serial(tmp_path)) == (HELD + HELD, False)


def test_handlers_put_back_after_interrupt(tmp_path: Path) -> None:
    """After an interrupt goes on out of run_all, the handlers in place before it are back."""
    before = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)
    fifo = _open_fifo(tmp_path)
    try:
        with pytest.raises(KeyboardInterrupt):
            run_all(run, _commands(tmp_path, signal.SIGINT), 2)
        _drain(fifo, tmp_path / "pids.txt")
    finally:
        os.close(fifo)
        _kill_leftovers(tmp_path / "pids.txt")

    assert (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)) == before


def _ended(driver: subprocess.Popen[bytes]) -> int:
    """The driver's return code once it ends, killing it where it outlives WAIT seconds."""
    try:
        return driver.wait(WAIT)
    except subprocess.TimeoutExpired:
        driver.kill()
        return driver.wait()


@pytest.mark.parametrize("signum", [signal.SIGHUP, signal.SIGQUIT, signal.SIGTERM], ids=["hup", "quit", "term"])
def test_ending_signal_kills_every_group(
    request: pytest.FixtureRequest, tmp_path: Path, signum: signal.Signals
) -> None:
    """A signal at the OS default kills both checkers' groups, then ends the process that called run_all by itself."""
    fifo = _open_fifo(tmp_path)
    try:
        driver = subprocess.Popen(
            [sys.executable, "-c", DRIVER, str(request.config.rootpath), str(int(signum)), *_argv(tmp_path, signum)],
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        held = _drain(fifo, tmp_path / "pids.txt")
    finally:
        os.close(fifo)
        _kill_leftovers(tmp_path / "pids.txt")

    assert (held, _serial(tmp_path), _ended(driver)) == (HELD + HELD, False, -signum)


class Held:
    """A checker with one batch per source, each batch a held checker whose role is the source's name."""

    stopped: frozenset[int] = frozenset()

    def __init__(self, tmp_path: Path) -> None:
        self.argv = _argv(tmp_path, signal.SIGINT)

    def batches(self, run: Run) -> list[list[Source]]:
        return [[source] for source in run.sources]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        return Command(argv=(*self.argv, batch[0].given.name), cwd=run.project.root)

    def read(self, completed: Completed) -> list[str]:
        return []

    def expected_status(self, report: list[str]) -> int:
        return 0

    def lines(self, report: list[str], batch: Sequence[Source], *, stopped: bool) -> list[Line]:
        return []


def test_check_with_interrupt_kills_every_batch(tmp_path: Path) -> None:
    """A KeyboardInterrupt while a budgeted check runs two batches kills both their groups, then goes on."""
    project = scaffold(tmp_path / "project", {"first": "", "second": ""})
    sources = tuple(Source(given=Path(name), absolute=project.root / name) for name in ("first", "second"))
    check = check_with(Held(tmp_path), budget=lambda: 2)
    fifo = _open_fifo(tmp_path)
    try:
        with pytest.raises(KeyboardInterrupt):
            check(Run(project=project, sources=sources, scratch=Scratch(tmp_path), process=run))
        held = _drain(fifo, tmp_path / "pids.txt")
    finally:
        os.close(fifo)
        _kill_leftovers(tmp_path / "pids.txt")

    assert (held, _serial(tmp_path)) == (HELD + HELD, False)
