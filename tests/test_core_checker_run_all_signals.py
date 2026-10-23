# Copyright 2026 oh shit, gorillas!
"""Red tests for an interrupt while `run_all` runs checkers in worker threads, and through `check_with`'s budget.

Source: the gates core design spec under docs/superpowers/specs/, decisions 26 and 27. While `run_all` runs, the main
thread answers the signals that end a process as `run` does; on any exception there, a signal's included, it kills the
process group of every checker `run` has started, in any thread, and not yet reaped, waits for every worker, puts the
handlers back, and only then do the exception and each signal take their course. `check_with` with a budget runs its
batches through `run_all`, so on an interrupt every running batch's process group is killed before it goes on.

Two checkers run at once. Each starts a child of its own that holds a `Witness` FIFO (`tests/support/lifeline.py`) and writes a marker into it; the test reads the FIFO to its end, which comes
only when every holder has closed it, so it comes promptly only when both children are dead. The checkers live on a
`Lifeline` the test never releases before the end, and their pids are noted for the test's `Pids` to kill at teardown.
The first checker, once its child holds the FIFO, opens a rendezvous FIFO to read and reads it to its end; the second
opens that FIFO to write, which returns only once the first is reading, writes a mark, starts its child, notes its pids,
writes a line on a `Beacon` and sends the signal to the process that called `run_all`. A first checker that reads no
mark from the second marks the run serial. SIGINT is a KeyboardInterrupt in pytest's own process. A signal that ends
the process at the OS default would end pytest too, so it is sent to a driver: a Python child that imports the core from
the rootdir, sets the signal to the OS default, and calls `run_all` with `run`; the test reads the FIFO once the second
checker has written its line on the `Beacon`.
"""

import contextlib
import os
import signal
import subprocess
import sys
from collections.abc import Generator, Sequence
from dataclasses import dataclass
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed, run, run_all
from gates.core.project import Source
from gates.core.report import Line
from gates.core.runner import Run, Scratch, check_with
from tests.support.lifeline import WITNESS, Beacon, Lifeline, Pids, Witness
from tests.support.project import scaffold

HELD = b"held"

# Arguments: the FIFO, the pids file, the mark path, the signal, the lifeline's read end, a Beacon's write end, the
# child's code and the role. The child holds the FIFO. The first checker notes its pids and reads the rendezvous FIFO
# `<mark>.started` to its end; the second opens it to write, which returns once the first reads, writes a mark, starts
# its child, notes its pids, writes a line on the Beacon and sends the signal. Both then live on the lifeline.
CHECKER = (
    "import os, subprocess, sys\n"
    "fifo, pids, mark, signum, line, beacon, role = (\n"
    "    sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4]), sys.argv[5], int(sys.argv[6]), sys.argv[8]\n"
    ")\n"
    "started = mark + '.started'\n"
    "if role == 'second':\n"
    "    with open(started, 'wb') as rendezvous:\n"
    "        rendezvous.write(b'started')\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[7], fifo, line],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, pass_fds=(int(line),),\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'a', encoding='utf-8') as out:\n"
    "    out.write(f'{os.getpid()}\\n{child.pid}\\n')\n"
    "if role == 'first':\n"
    "    with open(started, 'rb') as rendezvous:\n"
    "        if rendezvous.read() != b'started':\n"
    "            open(mark + '.serial', 'w').close()\n"
    "else:\n"
    "    os.write(beacon, b'whole\\n')\n"
    "    os.kill(os.getppid(), signum)\n"
    "while os.read(int(line), 65536):\n"
    "    pass\n"
)

# SIGQUIT at the OS default dumps core, and macOS then shows a crash dialog for every run. So the driver answers it with a
# Python handler that raises SystemExit with this code: `run` must kill the group, then let the handler take its course.
QUIT_EXIT = 7

# Arguments: the repository root, the signal, the file descriptors the checkers inherit (comma separated), then the
# checker's argv but its role.
DRIVER = (
    "import signal, sys\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from pathlib import Path\n"
    "from gates.core.checker import Command, run, run_all\n"
    "def quit_handler(signum, frame):\n"
    "    raise SystemExit(7)\n"
    "signal.signal(int(sys.argv[2]), quit_handler if int(sys.argv[2]) == signal.SIGQUIT else signal.SIG_DFL)\n"
    "fds = tuple(int(fd) for fd in sys.argv[3].split(','))\n"
    "argv = tuple(sys.argv[4:])\n"
    "commands = [Command(argv=(*argv, role), cwd=Path.cwd(), pass_fds=fds) for role in ('first', 'second')]\n"
    "run_all(run, commands, 2)\n"
)


@dataclass(frozen=True)
class Rig:
    """What the checkers hold: the Witness and Beacon the test reads, the checker's argv but its role, its inherited fds."""

    witness: Witness
    beacon: Beacon
    argv: tuple[str, ...]
    pass_fds: tuple[int, ...]


@contextlib.contextmanager
def _rig(tmp_path: Path, signum: int) -> Generator[Rig]:
    """Everything the two checkers hold, closed and their leftovers killed by pid at the end."""
    os.mkfifo(tmp_path / "mark.started")
    with (
        Lifeline() as line,
        Pids(tmp_path / "pids.txt") as pids,
        Witness(tmp_path / "held.fifo") as witness,
        Beacon() as beacon,
    ):
        argv = (
            sys.executable,
            "-c",
            CHECKER,
            str(witness.path),
            str(pids.path),
            str(tmp_path / "mark"),
            str(int(signum)),
            str(line.read_fd),
            str(beacon.write_fd),
            WITNESS,
        )
        yield Rig(witness, beacon, argv, (line.read_fd, beacon.write_fd))


def _commands(tmp_path: Path, rig: Rig) -> list[Command]:
    return [
        Command(argv=(*rig.argv, role), cwd=tmp_path, pass_fds=rig.pass_fds)
        for role in ("first", "second")
    ]


def _serial(tmp_path: Path) -> bool:
    """Whether the first checker marked the run serial: it did not see the second start while it ran."""
    return (tmp_path / "mark.serial").exists()


def test_interrupt_kills_every_group(tmp_path: Path) -> None:
    """A KeyboardInterrupt while two checkers run kills both their groups, then goes on out of run_all."""
    with _rig(tmp_path, signal.SIGINT) as rig:
        with pytest.raises(KeyboardInterrupt):
            run_all(run, _commands(tmp_path, rig), 2)
        held = rig.witness.ended()

    assert (held, _serial(tmp_path)) == (HELD + HELD, False)


def test_handlers_put_back_after_interrupt(tmp_path: Path) -> None:
    """After an interrupt goes on out of run_all, the handlers in place before it are back."""
    before = signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)
    with _rig(tmp_path, signal.SIGINT) as rig:
        with pytest.raises(KeyboardInterrupt):
            run_all(run, _commands(tmp_path, rig), 2)
        rig.witness.ended()

    assert (signal.getsignal(signal.SIGTERM), signal.getsignal(signal.SIGINT)) == before


def _ended(driver: subprocess.Popen[bytes]) -> int:
    """Return the driver's return code once it ends."""
    return driver.wait()


@pytest.mark.parametrize(
    ("signum", "status"),
    [
        (signal.SIGHUP, -signal.SIGHUP),
        (signal.SIGQUIT, QUIT_EXIT),
        (signal.SIGTERM, -signal.SIGTERM),
    ],
    ids=["hup", "quit", "term"],
)
def test_ending_signal_kills_every_group(
    request: pytest.FixtureRequest, tmp_path: Path, signum: signal.Signals, status: int
) -> None:
    """A signal kills both checkers' groups, then takes its course: SIGHUP and SIGTERM end the caller, SIGQUIT runs its handler."""
    with _rig(tmp_path, signum) as rig:
        driver = subprocess.Popen(
            [
                sys.executable,
                "-c",
                DRIVER,
                str(request.config.rootpath),
                str(int(signum)),
                ",".join(str(fd) for fd in rig.pass_fds),
                *rig.argv,
            ],
            cwd=tmp_path,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            pass_fds=rig.pass_fds,
        )
        rig.beacon.seen()
        held = rig.witness.ended()

    assert (held, _serial(tmp_path), _ended(driver)) == (HELD + HELD, False, status)


class Held:
    """A checker with one batch per source, each batch a held checker whose role is the source's name."""

    stopped: frozenset[int] = frozenset()

    def __init__(self, rig: Rig) -> None:
        """Initialize the seeded state."""
        self.argv = rig.argv
        self.pass_fds = rig.pass_fds

    def batches(self, run: Run) -> list[list[Source]]:
        """Return batches."""
        return [[source] for source in run.sources]

    def command(self, run: Run, batch: Sequence[Source]) -> Command:
        """Return command."""
        return Command(
            argv=(*self.argv, batch[0].given.name),
            cwd=run.project.root,
            pass_fds=self.pass_fds,
        )

    def read(self, completed: Completed) -> list[str]:
        """Return read."""
        del completed
        return []

    def expected_status(self, report: list[str]) -> int:
        """Return expected status."""
        del report
        return 0

    def lines(
        self, report: list[str], batch: Sequence[Source], *, stopped: bool
    ) -> list[Line]:
        """Return lines."""
        del report, batch, stopped
        return []


def test_check_with_interrupt_kills_every_batch(tmp_path: Path) -> None:
    """A KeyboardInterrupt while a budgeted check runs two batches kills both their groups, then goes on."""
    project = scaffold(tmp_path / "project", {"first": "", "second": ""})
    sources = tuple(
        Source(given=Path(name), absolute=project.root / name)
        for name in ("first", "second")
    )
    with _rig(tmp_path, signal.SIGINT) as rig:
        check = check_with(Held(rig), budget=lambda: 2)
        with pytest.raises(KeyboardInterrupt):
            check(
                Run(
                    project=project,
                    sources=sources,
                    scratch=Scratch(tmp_path),
                    process=run,
                )
            )
        held = rig.witness.ended()

    assert (held, _serial(tmp_path)) == (HELD + HELD, False)
