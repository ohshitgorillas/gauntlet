# Copyright 2026 oh shit, gorillas!
"""An event paced Runner and worker wait, paired by each concurrent test.

Every submitted call starts before next_done releases calls.
Closing releases all blocked workers, including when the test's worker wait raises.

Tests prove in-process concurrency caps with Scripted and its own next_done, never timing-dependent overlap or
real-process rendezvous where run_gate's process and next_done arguments suffice. A test's own Runner contains no
timed wait, hold or poll, and the test never releases blocked calls itself.

A test hands Scripted as the plain name p, alongside next_done=p.next_done, to run_all as its first argument or to
Run and run_gate as process. The same pairing holds for dataclasses.replace when it supplies process.

Only test modules import Scripted; conftest.py and other support modules never do. Support modules never call
run_all, Run or run_gate. In a module importing Scripted, these names and dataclasses.replace appear only as imports
or direct call functions, never as values or partials, and no names are imported from another test file.
"""

import threading
from collections.abc import Callable, Collection, Mapping
from concurrent.futures import Future
from dataclasses import dataclass

from gates.core.checker import Command, Completed, first_done


class ReleasedError(Exception):
    """A call was released by closing its Scripted."""

    def __init__(self, name: str) -> None:
        """Initialize the seeded state."""
        self.name = name
        super().__init__(name)


def last_argument(command: Command) -> str:
    """Choose a step by the last argv word."""
    return command.argv[-1]


@dataclass(frozen=True)
class Step:
    """A reply and the calls that must finish before it."""

    reply: Completed | BaseException
    after: tuple[str, ...] = ()


class Scripted:
    """Hold calls until their paired next_done observes all workers under way."""

    def __init__(
        self,
        steps: Mapping[str, Step],
        *,
        key: Callable[[Command], str] = last_argument,
    ) -> None:
        """Initialize the seeded state."""
        self.steps = dict(steps)
        self.key = key
        self.called: list[str] = []
        self.finished: list[str] = []
        self.waiting = {name: threading.Event() for name in steps}
        self.peak = 0
        self._running = 0
        self._generation = 0
        self._closed = False
        self._condition = threading.Condition()
        self._futures: set[Future[Completed]] = set()

    def __call__(self, command: Command) -> Completed:
        """Return the reply for the supplied call."""
        name = self.key(command)
        with self._condition:
            self._check_open(name)
            step = self.steps[name]
            generation = self._generation
            self.called.append(name)
            self._running += 1
            self.peak = max(self.peak, self._running)
            self._condition.notify_all()
            try:
                while not self._closed and generation == self._generation:
                    self._condition.wait()
                self._check_open(name)
                for before in step.after:
                    if before not in self.finished:
                        self.waiting[name].set()
                        while not self._closed and before not in self.finished:
                            self._condition.wait()
                        self._check_open(name)
                if isinstance(step.reply, BaseException):
                    raise step.reply
                return step.reply
            finally:
                self._running -= 1
                self.finished.append(name)
                self._condition.notify_all()

    def _check_open(self, name: str) -> None:
        if self._closed:
            raise ReleasedError(name)

    def _ended(self, future: Future[Completed]) -> None:
        del future
        with self._condition:
            self._condition.notify_all()

    def next_done(
        self, running: Collection[Future[Completed]]
    ) -> set[Future[Completed]]:
        """Release the started calls together, then wait for a completed future."""
        try:
            with self._condition:
                if not self._closed:
                    for future in running:
                        if future not in self._futures:
                            self._futures.add(future)
                            future.add_done_callback(self._ended)
                    while self._running < sum(not future.done() for future in running):
                        self._check_open("next_done")
                        self._condition.wait()
                    self._check_open("next_done")
                    self._generation += 1
                    self._condition.notify_all()
            return first_done(running)
        except BaseException:
            self.close()
            raise

    def close(self) -> None:
        """Release every blocked call; subsequent calls fail immediately."""
        with self._condition:
            self._closed = True
            self._condition.notify_all()
