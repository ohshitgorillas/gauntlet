# Copyright 2026 oh shit, gorillas!
"""Red tests for the signal handlers `run` leaves alone: off the main thread, and for a signal that was ignored.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process":
`run(command)` kills the checker's group "on any interrupt". Python allows handlers only in the main thread, so `run`
called from another thread still runs the checker and gives back its Completed. A signal the caller ignores stays
ignored: the checker sends SIGHUP to the process that called `run`, which ends no run and no test, and after `run` the
signal is still ignored.
"""

import signal
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from gates.core.checker import Command, run

EXIT = "import sys\nsys.exit(int(sys.argv[1]))\n"

HANG_UP = "import os, signal\nos.kill(os.getppid(), signal.SIGHUP)\n"

CODE = 5


def test_run_off_the_main_thread(tmp_path: Path) -> None:
    """`run` called from a thread other than the main one runs the checker and gives back its Completed."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        completed = pool.submit(
            run, Command(argv=(sys.executable, "-c", EXIT, str(CODE)), cwd=tmp_path)
        ).result()

    assert completed.status == CODE


def test_ignored_signal_stays_ignored(tmp_path: Path) -> None:
    """A signal ignored before `run` does not end the run when the checker sends it, and is still ignored after."""
    before = signal.signal(signal.SIGHUP, signal.SIG_IGN)
    try:
        completed = run(Command(argv=(sys.executable, "-c", HANG_UP), cwd=tmp_path))
        after = signal.getsignal(signal.SIGHUP)
    finally:
        signal.signal(signal.SIGHUP, before)

    assert (completed.status, after) == (0, signal.SIG_IGN)
