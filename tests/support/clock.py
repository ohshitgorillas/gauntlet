# Copyright 2026 oh shit, gorillas!
"""A virtual clock: the one Clock a test hands to code that waits on time.

Its time moves only as the test sets it, and it never hands a Ready a positive number, so no wait on it reads or
waits on real time. A wait polls the caller's event first, with `ready(0)`. When the event has not come and `passes`
reaches the cap, `after` runs, when it is set, and the event is polled again with `ready(0)`; when it has still not
come, the cap passes at once in virtual time: `now` moves by the cap and the wait reports False. Otherwise `passes`
seconds pass, when it is set, and the wait ends on the event alone, through `ready(None)`. A still `VirtualClock()`
never lets a cap pass. `after` blocks, with no timeout, until the event the test proves against has come, so the cap
passes only once that event has come.

Tests use VirtualClock instead of defining their own fake clock. They assert now only when an event's state at the
first poll is certain. They prove absence through an event or an injected fake, never by waiting to see nothing happen.

A test's positive cap runs on VirtualClock. Only tests/test_core_clock_real_time.py waits on SystemClock, in one test
with a cap of a few hundredths of a second, passed as seconds, and a total wait well under a tenth of a second.

A red step and its build run back to back, with no intervening step, and land together with their stub in one commit.

A builder needing a wait these shared homes do not provide stops and reports it instead of writing another wait.
"""

from collections.abc import Callable

from gates.core.clock import Ready


class VirtualClock:
    """A Clock whose time moves only as the test sets it."""

    now: float

    def __init__(
        self, *, passes: float | None = None, after: Callable[[], object] | None = None
    ) -> None:
        """Initialize the seeded state."""
        self.now = 0.0
        self._passes = passes
        self._after = after

    def wait(self, ready: Ready, seconds: float | None) -> bool:
        """Return true when the event came before `seconds` passed on this clock; None: no cap."""
        if ready(0):
            return True
        if self._passes is None:
            return ready(None)
        if seconds is not None and self._passes >= seconds:
            if self._after is not None:
                self._after()
            if ready(0):
                return True
            self.now += seconds
            return False
        self.now += self._passes
        return ready(None)
