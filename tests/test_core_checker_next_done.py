# Copyright 2026 oh shit, gorillas!
"""Red tests for the waits `run_all` makes on its workers: each one through the `next_done` it is handed.

Source: gates/core/checker.py: `run_all(process, commands, cap, *, next_done=first_done)` makes every wait on its workers, the wait for one
to end included, through its `next_done` keyword, and never looks at its Runner to find a wait. The gates core design
spec's decision 26: it takes the next Command only when fewer than `cap` are running, and a `NextDone` blocks until at
least one future in `running` is done and gives back the done ones.

Each checker here is a real child run through `run`, held by a `Lifeline` of its own (`tests/support/lifeline.py`), so it is certainly still running until the test lets it go. The test's
`next_done` notes how many workers each call is handed, lets the next held checker go, and answers with `first_done`.
With a cap of 1 and two Commands, `run_all` can take the second only after the first has ended, and can return only
after the second has ended, so it must wait twice, each time on one worker. Code that waits on its own leaves the first
checker held; it fails at pytest-timeout's bound, and the cleanup's kill ends the checker.

The gates core design spec's decision 26 also puts the cleanup's wait
through `next_done`: on any exception in a wait, `run_all` waits through `next_done` until no worker is running, and
only then does the exception take its course. The test's `next_done` raises at its first call, with one worker running,
and answers with `first_done` after that; the cleanup must hand that same worker to it once more. The worker runs its
checker through a `Lingering` Runner, which returns only once the test's `next_done` lets it go at the cleanup's call,
so the worker is certainly still running when the cleanup looks for running workers, whatever the kill has ended.

The cleanup has no poll (decision 26 of the gates core design): while it waits,
each checker `run` starts is killed as it is added to the live set. The test's `next_done` raises at its first call,
with its checker held, and at the cleanup's call runs through `run` a second checker its own `Lifeline` holds; `run`
returns only because that checker is killed as it is added. The first worker runs through a `Lingering` Runner too, so
it is still running past the cleanup's kill and the cleanup's call is certain. A shell reports a process a signal ended
as 128 plus the signal number (POSIX, "Exit Status for Commands"), so the checker comes back with a status above 128,
not timed out.

Each test lets its `Lingering` go on the way out whatever happens, so code that never makes the cleanup's call fails at
pytest-timeout's bound and leaves no worker blocked.
"""

import sys
import threading
from collections.abc import Collection, Sequence
from concurrent.futures import Future
from pathlib import Path

import pytest

from gates.core.checker import Command, Completed, first_done, run, run_all
from tests.support.lifeline import HOLD, Lifeline


class Noting:
    """A next_done that notes how many workers each call is handed, lets the next held checker go, then first_done."""

    noted: list[int]

    def __init__(self, lines: Sequence[Lifeline]) -> None:
        """Initialize the seeded state."""
        self.noted = []
        self._lines = list(lines)

    def __call__(
        self, running: Collection[Future[Completed]]
    ) -> set[Future[Completed]]:
        """Return the reply for the supplied call."""
        self.noted.append(len(running))
        if self._lines:
            self._lines.pop(0).release()
        return first_done(running)


class StalledError(Exception):
    """The exception the test's next_done raises in run_all's first wait."""


class Lingering:
    """A Runner around run whose call, once run has returned, blocks with no timeout until the test lets it go."""

    def __init__(self) -> None:
        """Initialize the seeded state."""
        self._let_go = threading.Event()

    def __call__(self, command: Command) -> Completed:
        """Return the reply for the supplied call."""
        completed = run(command)
        self._let_go.wait()
        return completed

    def release(self) -> None:
        """Let every call go, the ones blocked now and every later one; a second call does nothing."""
        self._let_go.set()


class Stalling:
    """A next_done noting the workers each call is handed: the first lets the checker go and raises, later ones let.

    the Runner go.
    """

    handed: list[frozenset[Future[Completed]]]

    def __init__(self, line: Lifeline, process: Lingering) -> None:
        """Initialize the seeded state."""
        self.handed = []
        self._line = line
        self._process = process

    def __call__(
        self, running: Collection[Future[Completed]]
    ) -> set[Future[Completed]]:
        """Return the reply for the supplied call."""
        self.handed.append(frozenset(running))
        if len(self.handed) == 1:
            self._line.release()
            raise StalledError
        self._process.release()
        return first_done(running)


class Adding:
    """A next_done that raises StalledError at its first call; at each later one it runs a held checker through run, then.

    lets the Runner go.
    """

    completed: list[Completed]

    def __init__(
        self, cwd: Path, lines: tuple[Lifeline, Lifeline], process: Lingering
    ) -> None:
        """Initialize the seeded state."""
        self.completed = []
        self._calls = 0
        self._cwd = cwd
        self._first, self._second = lines
        self._process = process

    def __call__(
        self, running: Collection[Future[Completed]]
    ) -> set[Future[Completed]]:
        """Return the reply for the supplied call."""
        self._calls += 1
        if self._calls == 1:
            raise StalledError
        try:
            self.completed.append(run(_held(self._cwd, self._second)))
        finally:
            self._first.release()
            self._second.release()
            self._process.release()
        return first_done(running)


# A shell reports a process a signal ended as 128 plus the signal number.
SIGNAL_FLOOR = 128


def _held(cwd: Path, line: Lifeline) -> Command:
    """Return a checker that lives until its Lifeline is let go."""
    return Command(
        argv=(sys.executable, "-c", HOLD, str(line.read_fd)),
        cwd=cwd,
        pass_fds=(line.read_fd,),
    )


def test_waits_for_a_worker_through_next_done(tmp_path: Path) -> None:
    """With a cap of 1, each wait for the one running worker to end is a call to the next_done run_all is handed."""
    with Lifeline() as first, Lifeline() as second:
        next_done = Noting([first, second])

        results = run_all(
            run,
            [_held(tmp_path, first), _held(tmp_path, second)],
            1,
            next_done=next_done,
        )

    assert (next_done.noted, len(results)) == ([1, 1], 2)


def test_cleanup(tmp_path: Path) -> None:
    """An exception in run_all's wait goes on only after the cleanup has waited for the worker through that next_done."""
    # Breaks when the cleanup does not wait through next_done: the worker, held in its Runner, keeps the test until
    # pytest-timeout's bound, or the cleanup hands next_done other workers than the one running.
    process = Lingering()
    with Lifeline() as line:
        next_done = Stalling(line, process)

        try:
            with pytest.raises(StalledError):
                run_all(process, [_held(tmp_path, line)], 1, next_done=next_done)
        finally:
            process.release()

    first = next_done.handed[0]
    assert (next_done.handed, len(first)) == ([first, first], 1)


def test_kill_add(tmp_path: Path) -> None:
    """A checker run starts from inside the cleanup's wait is killed as it is added, so run gives it back killed."""
    # Breaks when `_Live.add` drops the kill while the cleanup lasts (run then holds the test to pytest-timeout's bound),
    # when the cleanup does not wait through next_done (the first worker, held in its Runner, keeps the test until that
    # bound and nothing is run), or when the kill is not reported as a signal's.
    process = Lingering()
    with Lifeline() as first, Lifeline() as second:
        next_done = Adding(tmp_path, (first, second), process)

        try:
            with pytest.raises(StalledError):
                run_all(process, [_held(tmp_path, first)], 1, next_done=next_done)
        finally:
            process.release()

    killed = [
        (completed.status > SIGNAL_FLOOR, completed.timed_out)
        for completed in next_done.completed
    ]
    assert killed == [(True, False)]
