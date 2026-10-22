"""The one home of real time in gates/: every wait that can end on time as well as on an event goes through a Clock."""

from collections.abc import Callable
from typing import Protocol

type Ready = Callable[[float | None], bool]


class Clock(Protocol):
    """A clock a wait that can end on time as well as on an event goes through."""

    def wait(self, ready: Ready, seconds: float | None) -> bool:
        """Wait through `ready` until the event comes or `seconds` pass on this clock, with no cap when None.

        True when the event came before `seconds` passed.
        """
        ...


class SystemClock:
    """Real time, the only real time in gates/."""

    def wait(self, ready: Ready, seconds: float | None) -> bool:
        """Hand `seconds` to `ready` as they are, and give its answer: True when the event came in time."""
        return ready(seconds)


SYSTEM: Clock = SystemClock()
