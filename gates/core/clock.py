"""The one home of real time in gates/: every wait that can end on time as well as on an event goes through a Clock."""

from collections.abc import Callable
from typing import Protocol

type Ready = Callable[[float | None], bool]


class Clock(Protocol):
    def wait(self, ready: Ready, seconds: float | None) -> bool:
        raise NotImplementedError


class SystemClock:
    def wait(self, ready: Ready, seconds: float | None) -> bool:
        raise NotImplementedError


SYSTEM: Clock = SystemClock()
