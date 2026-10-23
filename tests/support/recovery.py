# Copyright 2026 oh shit, gorillas!
"""Literal executor replies and pipe-held observations of committed job states."""

import os
from collections.abc import Callable, Iterator, Sequence
from pathlib import Path

from gauntlet.core.records import (
    Effect,
    ExecutionAnswer,
    Reconciled,
    RecoveryPoint,
    RecoveryResult,
    State,
)
from gauntlet.seams.resume import Executor, resume
from tests.support.lifeline import CHUNK


class RepliesExhaustedError(Exception):
    """A literal reply stream ended, retaining every attempted call."""

    def __init__(self, seen: tuple[Effect, ...]) -> None:
        """Keep the call history at exhaustion."""
        self.seen = seen
        super().__init__("literal executor replies exhausted")


class Replies:
    """Return supplied records in independent prepare, execute and recover streams."""

    def __init__(
        self,
        values: Sequence[ExecutionAnswer],
        *,
        points: Sequence[RecoveryPoint] = (),
        recoveries: Sequence[RecoveryResult] = (),
    ) -> None:
        """Snapshot the supplied streams without interpreting any record."""
        self._values = iter(tuple(values))
        self._points = iter(tuple(points))
        self._recoveries = iter(tuple(recoveries))
        self._seen: list[Effect] = []

    def _next[T](self, effect: Effect, stream: Iterator[T]) -> T:
        self._seen.append(effect)
        try:
            return next(stream)
        except StopIteration:
            raise RepliesExhaustedError(self.seen) from None

    def prepare(self, effect: Effect, *, dispatch: int) -> RecoveryPoint:
        """Return the next literal point, irrespective of the requested dispatch."""
        del dispatch
        return self._next(effect, self._points)

    def __call__(self, effect: Effect, point: RecoveryPoint) -> ExecutionAnswer:
        """Return the next literal execution event."""
        del point
        return self._next(effect, self._values)

    def recover(self, effect: Effect, point: RecoveryPoint) -> RecoveryResult:
        """Return the next literal recovery result."""
        del point
        return self._next(effect, self._recoveries)

    @property
    def seen(self) -> tuple[Effect, ...]:
        """Return an immutable snapshot of calls across all three streams."""
        return tuple(self._seen)


def checkpoint_child(
    job: str,
    ready: int,
    release: int,
    replies: tuple[ExecutionAnswer, ...],
    *,
    checkpoint: str = "ready",
    points: tuple[RecoveryPoint, ...] = (),
    recoveries: tuple[RecoveryResult, ...] = (),
    run: Callable[[Executor], State] | None = None,
) -> None:
    """Announce a committed boundary and hold there until the parent releases us.

    Parents pass Beacon.write_fd and Lifeline.read_fd and own process cleanup.
    Points and recovery results are literal inputs just like execution replies.
    """
    if checkpoint not in {"ready", "started", "recovering", "completed"}:
        message = f"unknown checkpoint: {checkpoint}"
        raise ValueError(message)
    announced = False
    answered = False
    literal = Replies(replies, points=points, recoveries=recoveries)

    def hold(boundary: str) -> None:
        nonlocal announced
        if boundary == checkpoint and not announced:
            announced = True
            os.write(ready, boundary.encode("ascii") + b"\n")
            while os.read(release, CHUNK):
                pass

    class Observed:
        """Delegate literal replies after the driver's committed callback boundary."""

        def prepare(self, effect: Effect, *, dispatch: int) -> RecoveryPoint:
            """Observe prior completion and ready publication before preparation."""
            if answered:
                hold("completed")
            hold("ready")
            return literal.prepare(effect, dispatch=dispatch)

        def __call__(self, effect: Effect, point: RecoveryPoint) -> ExecutionAnswer:
            """Observe started publication before returning the literal answer."""
            nonlocal answered
            if answered:
                hold("completed")
            hold("started")
            result = literal(effect, point)
            answered = True
            return result

        def recover(self, effect: Effect, point: RecoveryPoint) -> RecoveryResult:
            """Observe recovering publication before the literal recovery reply."""
            nonlocal answered
            if answered:
                hold("completed")
            hold("recovering")
            result = literal.recover(effect, point)
            if isinstance(result, Reconciled):
                answered = True
            return result

    if run is None:
        resume(Path(job), execute=Observed())
    else:
        run(Observed())
    if answered:
        hold("completed")
