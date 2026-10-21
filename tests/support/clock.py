"""A virtual clock: the one Clock a test hands to code that waits on time.

Design: the no-wall-clock design spec under docs/superpowers/specs/, the `tests/support/clock.py` module, decisions 6
and 14. Its time moves only as the test sets it, and it never hands a Ready a positive number, so no wait on it reads or
waits on real time. A wait polls the caller's event first, with `ready(0)`. When the event has not come and `passes`
reaches the cap, `after` runs, when it is set, and the event is polled again with `ready(0)`; when it has still not
come, the cap passes at once in virtual time: `now` moves by the cap and the wait reports False. Otherwise `passes`
seconds pass, when it is set, and the wait ends on the event alone, through `ready(None)`. A still `VirtualClock()`
never lets a cap pass. `after` blocks, with no timeout, until the event the test proves against has come, so the cap
passes only once that event has come.
"""

from collections.abc import Callable

from gates.core.clock import Ready


class VirtualClock:
    """A Clock whose time moves only as the test sets it."""

    now: float

    def __init__(self, *, passes: float | None = None, after: Callable[[], object] | None = None) -> None:
        self.now = 0.0
        self._passes = passes
        self._after = after

    def wait(self, ready: Ready, seconds: float | None) -> bool:
        """True when the event came before `seconds` passed on this clock; None: no cap."""
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
