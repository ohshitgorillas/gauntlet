"""Red tests for the signals that end a process, met while `run` runs a checker: SIGHUP, SIGQUIT and SIGTERM.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`run(command)` starts the checker in its "own session; the whole group is killed at the timeout or on any interrupt".
An interrupt is any of the signals that end a process: a closing terminal's SIGHUP, the quit key's SIGQUIT, `kill`'s
SIGTERM and the interrupt key's SIGINT. Python answers SIGINT with KeyboardInterrupt, which
`test_core_checker_group.py` holds; the other three end the process by the OS default, which this file holds. The
group is killed first and the signal then takes its course, so the process that called `run` still ends by it.

A signal that ends the process would end pytest too, so `run` is called in a driver: a Python child the test starts,
which imports the core from the rootdir, sets the signal's action to the OS default, and calls `run` with the argv it is
given. As in the group tests, the checker starts a child of its own that holds a FIFO the test reads to its end; the
end comes promptly only when that child is dead; the test reads it once the checker has recorded its pids, its child
then holding the FIFO. The checker then sends the signal to the driver.

A signal that arrives once the checker has exited, while `run` reads its output files back, takes its course only once
`run` is done. The checker here makes a FIFO at its output path and exits; `run` then blocks reading it until the test
writes to it. The test sends SIGTERM while `run` blocks: the driver lives on until the test writes, then ends by SIGTERM.
"""

import contextlib
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

# How long the test waits for the FIFO's end, the driver's end, or the output FIFO to have its reader.
WAIT = 10.0

# How long the test sleeps between tries while it waits.
POLL = 0.05

# How long the driver must live on after SIGTERM while `run` reads its output.
HOLD = 0.5

HELD = b"held"

ALIVE = b" alive"

DRIVER = (
    "import signal, sys\n"
    "from pathlib import Path\n"
    "sys.path.insert(0, sys.argv[1])\n"
    "from gates.core.checker import Command, run\n"
    "signal.signal(int(sys.argv[2]), signal.SIG_DFL)\n"
    "output = Path(sys.argv[3])\n"
    "run(Command(argv=tuple(sys.argv[4:]), cwd=output.parent, outputs={'report': output}))\n"
)

GRANDCHILD = (
    "import os, sys, time\n"
    "held = os.open(sys.argv[1], os.O_WRONLY)\n"
    "os.write(held, b'held')\n"
    "print('ready', flush=True)\n"
    "time.sleep(40)\n"
)

CHECKER = (
    "import os, subprocess, sys, time\n"
    "fifo, pids, signum = sys.argv[1], sys.argv[2], int(sys.argv[3])\n"
    "child = subprocess.Popen(\n"
    "    [sys.executable, '-c', sys.argv[4], fifo],\n"
    "    stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,\n"
    ")\n"
    "child.stdout.readline()\n"
    "with open(pids, 'w', encoding='utf-8') as out:\n"
    "    out.write(f'{os.getpid()}\\n{child.pid}\\n')\n"
    "os.kill(os.getppid(), signum)\n"
    "time.sleep(20)\n"
)

MAKE_FIFO = "import os, sys\nos.mkfifo(sys.argv[1])\n"


def _driver(request: pytest.FixtureRequest, signum: int, output: Path, *argv: str) -> subprocess.Popen[bytes]:
    """Start the driver, which runs argv through `run` with output as its output file and signum at the OS default."""
    root = str(request.config.rootpath)
    return subprocess.Popen(
        [sys.executable, "-c", DRIVER, root, str(int(signum)), str(output), *argv],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


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


def _await_pids(pids: Path, driver: subprocess.Popen[bytes]) -> None:
    """Wait until the checker has recorded its pids, its child then holding the FIFO, or the driver has ended."""
    deadline = time.monotonic() + WAIT
    while not pids.exists() and driver.poll() is None and time.monotonic() < deadline:
        time.sleep(POLL)


def _ended(driver: subprocess.Popen[bytes]) -> int:
    """The driver's return code once it ends, killing it where it outlives WAIT seconds."""
    try:
        return driver.wait(WAIT)
    except subprocess.TimeoutExpired:
        driver.kill()
        return driver.wait()


@pytest.mark.parametrize("signum", [signal.SIGHUP, signal.SIGQUIT, signal.SIGTERM], ids=["hup", "quit", "term"])
def test_ending_signal_kills_group(request: pytest.FixtureRequest, tmp_path: Path, signum: signal.Signals) -> None:
    """A signal at the OS default kills the checker's whole group, then ends the process that called `run` by itself."""
    path = tmp_path / "held.fifo"
    pids = tmp_path / "pids.txt"
    os.mkfifo(path)
    fifo = os.open(path, os.O_RDONLY | os.O_NONBLOCK)
    try:
        argv = (sys.executable, "-c", CHECKER, str(path), str(pids), str(int(signum)), GRANDCHILD)
        driver = _driver(request, signum, tmp_path / "report.txt", *argv)
        _await_pids(pids, driver)
        held = _drain(fifo, pids)
    finally:
        os.close(fifo)

    assert (held, _ended(driver)) == (HELD, -signum)


def _writer(path: Path, driver: subprocess.Popen[bytes]) -> int:
    """Open the FIFO at path for writing once the driver has it open for reading, within WAIT seconds."""
    deadline = time.monotonic() + WAIT
    while True:
        try:
            return os.open(path, os.O_WRONLY | os.O_NONBLOCK)
        except OSError:
            if time.monotonic() >= deadline or driver.poll() is not None:
                raise
            time.sleep(POLL)


def test_signal_while_reading_outputs_waits_for_run(request: pytest.FixtureRequest, tmp_path: Path) -> None:
    """SIGTERM while `run` reads back an output leaves the driver alive until the read ends, then ends it by SIGTERM."""
    output = tmp_path / "report.fifo"
    driver = _driver(request, signal.SIGTERM, output, sys.executable, "-c", MAKE_FIFO, str(output))
    try:
        writer = _writer(output, driver)
        os.kill(driver.pid, signal.SIGTERM)
        time.sleep(HOLD)
        alive = driver.poll() is None
        with contextlib.suppress(BrokenPipeError):
            os.write(writer, b"report")
        os.close(writer)
    finally:
        status = _ended(driver)

    assert (alive, status) == (True, -signal.SIGTERM)
