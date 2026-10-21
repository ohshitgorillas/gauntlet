"""A Runner for concurrent tests: each Command's reply chosen by its last argument, with an order the calls finish in.

Design: the gates-core design spec under docs/superpowers/specs/, decisions 26 and 27. FakeRunner replies in call
order, which threads make arbitrary, so this runner keys each reply by the Command's last argument. A step may wait,
up to WAIT seconds, for other names to finish first; a wait that runs out raises AssertionError. A step's reply is a
Completed to return or an exception to raise. The runner keeps the names it was called with, the names that finished,
and the most calls it saw running at once. A step may also hold its call for a moment, so calls that can overlap do.
"""

import threading
from collections.abc import Mapping
from dataclasses import dataclass

from gates.core.checker import Command, Completed

# How long a step waits for the names it must finish after.
WAIT = 5.0


@dataclass(frozen=True)
class Step:
    """One name's reply: what it returns or raises, the names it finishes after, and how long it holds its call."""

    reply: Completed | BaseException
    after: tuple[str, ...] = ()
    hold: float = 0.0


class Scripted:
    """A Runner whose replies are keyed by each Command's last argument, safe to call from many threads."""

    def __init__(self, steps: Mapping[str, Step]) -> None:
        self.steps = dict(steps)
        self.called: list[str] = []
        self.finished: list[str] = []
        self.peak = 0
        self._running = 0
        self._lock = threading.Lock()
        self._done = {name: threading.Event() for name in steps}

    def __call__(self, command: Command) -> Completed:
        name = command.argv[-1]
        step = self.steps[name]
        with self._lock:
            self.called.append(name)
            self._running += 1
            self.peak = max(self.peak, self._running)
        try:
            for before in step.after:
                if not self._done[before].wait(WAIT):
                    raise AssertionError(f"{name} waited past {WAIT} seconds for {before} to finish")
            if step.hold:
                threading.Event().wait(step.hold)
            if isinstance(step.reply, BaseException):
                raise step.reply
            return step.reply
        finally:
            with self._lock:
                self._running -= 1
                self.finished.append(name)
            self._done[name].set()
