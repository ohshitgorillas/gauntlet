# Copyright 2026 oh shit, gorillas!
"""Bound startup and nonblocking socket probes with one clock budget."""

import errno
import select
import socket
import time
from collections.abc import Callable
from pathlib import Path
from typing import Protocol

from gauntlet.core.errors import LaunchError

type Ready = Callable[[float | None], bool]


class Clock(Protocol):
    """Bound an event wait with an injectable clock."""

    def wait(self, ready: Ready, seconds: float | None) -> bool:
        """Wait for an event within the supplied budget."""
        ...


class SystemClock:
    """Use monotonic time for product event waits."""

    def wait(self, ready: Ready, seconds: float | None) -> bool:
        """Drive bounded event waits until readiness or expiry."""
        deadline = None if seconds is None else time.monotonic() + seconds
        while True:
            remaining = None if deadline is None else deadline - time.monotonic()
            if remaining is not None and remaining <= 0:
                return ready(0)
            if ready(remaining):
                return True


SYSTEM: Clock = SystemClock()


class SocketReadiness:
    """Probe local service sockets within their startup budget."""

    def __init__(self, *, clock: Clock = SYSTEM) -> None:
        """Use the caller's clock for every readiness wait."""
        self._clock = clock

    def unix(self, path: Path, *, seconds: int, start: Callable[[float], None]) -> None:
        """Await a Unix socket after starting its service."""
        self._wait(socket.AF_UNIX, str(path), seconds, start)

    def tcp(
        self, host: str, port: int, *, seconds: int, start: Callable[[float], None]
    ) -> None:
        """Await a TCP socket after starting its service."""
        self._wait(socket.AF_INET, (host, port), seconds, start)

    def _wait(
        self,
        family: int,
        address: str | tuple[str, int],
        seconds: int,
        start: Callable[[float], None],
    ) -> None:
        component = "readiness"
        deadline = time.monotonic() + seconds
        start(max(0.0, deadline - time.monotonic()))
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            raise LaunchError(component, "startup budget expired")

        def ready(cap: float | None) -> bool:
            return self._probe(family, address, cap)

        try:
            connected = self._clock.wait(ready, remaining)
        except OSError:
            raise LaunchError(component, "socket probe failed") from None
        if not connected:
            raise LaunchError(component, "startup budget expired")

    def _probe(
        self, family: int, address: str | tuple[str, int], cap: float | None
    ) -> bool:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.settimeout(0.0)
            status = probe.connect_ex(address)
            if status in (errno.EINPROGRESS, errno.EWOULDBLOCK, errno.EALREADY):
                waiter = select.poll()
                waiter.register(probe, select.POLLOUT)
                timeout = None if cap is None else int(cap * 1000)
                if not waiter.poll(timeout):
                    return False
                status = probe.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
            if status == 0:
                return True
            if status not in (errno.ECONNREFUSED, errno.ENOENT):
                raise OSError(status, "socket probe failed")
        # Refused endpoints have no pending event; bound the retry through the
        # clock's callback budget rather than spinning on an already ready fd.
        select.select([], [], [], 0.1 if cap is None else min(cap, 0.1))
        return False
