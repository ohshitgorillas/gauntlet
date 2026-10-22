# Copyright 2026 oh shit, gorillas!
"""Red tests for the signals that end a process, met while `run` runs a checker: SIGHUP, SIGQUIT and SIGTERM.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`run(command)` starts the checker in its "own session; the whole group is killed at the timeout or on any interrupt".
An interrupt is any of the signals that end a process: a closing terminal's SIGHUP, the quit key's SIGQUIT, `kill`'s
SIGTERM and the interrupt key's SIGINT. Python answers SIGINT with KeyboardInterrupt, which
`test_core_checker_group.py` holds; the other three end the process by the OS default, which this file holds. The
group is killed first and the signal then takes its course, so the process that called `run` still ends by it.

A signal that ends the process would end pytest too, so `run` is called in a driver: a Python child the test starts,
which imports the core from the rootdir, sets the signal's action to the OS default, and calls `run` with the argv it is
given. As in the group tests, the checker starts a child of its own that holds a `Witness` FIFO (the
`tests/support/lifeline.py` module of the no-wall-clock design spec) and writes a marker into it; the test reads the
FIFO to its end, which comes only when every holder has closed it, so it comes promptly only when that child is dead.
The checker and its child live on a `Lifeline` the test never releases before the end. The test reads the FIFO once the
checker has written its line on a `Beacon`, after its child holds the FIFO and its pids are noted for the test's `Pids`
to kill at teardown. The checker then sends the signal to the driver.

A signal that arrives once the checker has exited, while `run` reads its output files back, takes its course only once
`run` is done (the no-wall-clock design spec, decision 5, and its `checker.py` section). The checker here writes its two
output files and exits. The driver hands `run` a reader that sends SIGTERM to its own process from inside the first read,
which delivers the signal before `kill` returns, and writes a line on its stdout from the next read, which it reaches only
when the signal was held past the first read and on through `run`'s reading. The test reads that line and the driver's
end: the line, then death by SIGTERM once `run` has returned.
"""

import signal
import subprocess
import sys
from pathlib import Path

import pytest

from tests.support.lifeline import WITNESS, Beacon, Lifeline, Pids, Witness

HELD = b"held"

# The line the reader writes once its own SIGTERM has been sent, reached only while `run` holds the signal.
READ_UNDER_SIGTERM = b"read under SIGTERM\n"

# SIGQUIT at the OS default dumps core, and macOS then shows a crash dialog for every run. So the driver answers it with a
# Python handler that raises SystemExit with this code: `run` must kill the group, then let the handler take its course.
QUIT_EXIT = 7

# Arguments: the repository root, the signal, the output path, the file descriptors the checker inherits (comma
# separated, or empty), then the checker's argv.
DRIVER = (
    "import signal, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from gates.core.checker import Command, run\n"
    "def quit_handler(signum, frame):\n"
    "    raise SystemExit(7)\n"
    "signal.signal(int(sys.argv[2]), quit_handler if int(sys.argv[2]) == signal.SIGQUIT else signal.SIG_DFL)\n"
    "output = Path(sys.argv[3])\n"
    "fds = tuple(int(fd) for fd in sys.argv[4].split(',') if fd)\n"
    "run(Command(argv=tuple(sys.argv[5:]), cwd=output.parent, outputs={'report': output}, pass_fds=fds))\n"
)

# Arguments: the FIFO, the pids file, the signal, the lifeline's read end, a Beacon's write end and the child's code.
# The child holds the FIFO; the checker notes its pids, writes a line on the Beacon, signals its parent and lives on.
CHECKER = (
    "import os, subprocess, sys\n"
    "fifo, pids, signum, line, beacon = sys.argv[1], sys.argv[2], int(sys.argv[3]), sys.argv[4], int(sys.argv[5])\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[6], fifo, line],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, pass_fds=(int(line),),\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'w', encoding='utf-8') as out:\n"
    "    out.write(f'{os.getpid()}\\n{child.pid}\\n')\n"
    "os.write(beacon, b'whole\\n')\n"
    "os.kill(os.getppid(), signum)\n"
    "while os.read(int(line), 65536):\n"
    "    pass\n"
)

# Arguments: the repository root, the two output paths, then the checker's argv. SIGTERM is at the OS default. The reader
# `run` is handed signals its own process with SIGTERM on its first read; on the next read, a later output read back
# while that signal is still pending, it writes READ_UNDER_SIGTERM on fd 1. Each read then reads its output back.
READING_DRIVER = (
    "import os, signal, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from gates.core.checker import Command, read_output, run\n"
    "signal.signal(signal.SIGTERM, signal.SIG_DFL)\n"
    "reads = []\n"
    "def reader(path):\n"
    "    if reads:\n"
    "        os.write(1, b'read under SIGTERM\\n')\n"
    "    else:\n"
    "        os.kill(os.getpid(), signal.SIGTERM)\n"
    "    reads.append(path)\n"
    "    return read_output(path)\n"
    "report, notes = Path(sys.argv[2]), Path(sys.argv[3])\n"
    "outputs = {'report': report, 'notes': notes}\n"
    "run(Command(argv=tuple(sys.argv[4:]), cwd=report.parent, outputs=outputs), read=reader)\n"
)

# Arguments: the output paths. The checker writes a report at each and exits.
WRITE_OUTPUT = (
    "import sys\n"
    "from pathlib import Path\n"
    "for name in sys.argv[1:]:\n"
    "    Path(name).write_text('report', encoding='utf-8')\n"
)


def _driver(
    request: pytest.FixtureRequest,
    signum: int,
    output: Path,
    *argv: str,
    fds: tuple[int, ...] = (),
) -> subprocess.Popen[bytes]:
    """Start the driver, which runs argv through `run` with output as its output file and signum at the OS default."""
    root = str(request.config.rootpath)
    return subprocess.Popen(
        [
            sys.executable,
            "-c",
            DRIVER,
            root,
            str(int(signum)),
            str(output),
            ",".join(str(fd) for fd in fds),
            *argv,
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        pass_fds=fds,
    )


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
def test_ending_signal_kills_group(
    request: pytest.FixtureRequest, tmp_path: Path, signum: signal.Signals, status: int
) -> None:
    """A signal kills the checker's whole group, then takes its course: SIGHUP and SIGTERM end the caller by themselves, SIGQUIT runs the caller's handler."""
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
            str(int(signum)),
            str(line.read_fd),
            str(beacon.write_fd),
            WITNESS,
        )
        driver = _driver(
            request,
            signum,
            tmp_path / "report.txt",
            *argv,
            fds=(line.read_fd, beacon.write_fd),
        )
        beacon.seen()
        held = witness.ended()

    assert (held, _ended(driver)) == (HELD, status)


def test_signal_while_reading_outputs_waits_for_run(
    request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    """SIGTERM sent from inside the first read of an output leaves the driver alive to write its line from the next read, then ends it once `run` returns."""
    report = tmp_path / "report.txt"
    notes = tmp_path / "notes.txt"
    driver = subprocess.Popen(
        [
            sys.executable,
            "-c",
            READING_DRIVER,
            str(request.config.rootpath),
            str(report),
            str(notes),
            sys.executable,
            "-c",
            WRITE_OUTPUT,
            str(report),
            str(notes),
        ],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
    )
    written, _ = driver.communicate()

    assert (written, driver.returncode) == (READ_UNDER_SIGTERM, -signal.SIGTERM)
