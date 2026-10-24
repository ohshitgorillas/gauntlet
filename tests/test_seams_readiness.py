# Copyright 2026 oh shit, gorillas!
"""Socket startup contracts from M2 launcher design, Order 3b."""

import socket
import time
from collections.abc import Callable
from errno import EACCES
from pathlib import Path

import pytest

from gauntlet.seams.readiness import SocketReadiness
from tests.support.clock import VirtualClock


def _invoke(
    readiness: SocketReadiness,
    address: Path | tuple[str, int],
    start: Callable[[float], None],
) -> None:
    if isinstance(address, Path):
        readiness.unix(address, seconds=10, start=start)
    else:
        readiness.tcp(*address, seconds=10, start=start)


def _listener(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, unix: bool
) -> tuple[socket.socket, Path | tuple[str, int]]:
    monkeypatch.chdir(tmp_path)
    listener = socket.socket(socket.AF_UNIX if unix else socket.AF_INET)
    if unix:
        address = Path("ready.sock")
        listener.bind(str(address))
        return listener, address
    listener.bind(("127.0.0.1", 0))
    bound: object = listener.getsockname()
    match bound:
        case (str() as host, int() as port):
            return listener, (host, port)
        case _:
            listener.close()
            raise AssertionError(bound)


def _probes(monkeypatch: pytest.MonkeyPatch) -> list[socket.socket]:
    opened: list[socket.socket] = []

    class Probe(socket.socket):
        def __init__(
            self,
            family: int = socket.AF_INET,
            kind: int = socket.SOCK_STREAM,
            proto: int = 0,
            fileno: int | None = None,
        ) -> None:
            super().__init__(family, kind, proto, fileno)
            opened.append(self)

    monkeypatch.setattr(socket, "socket", Probe)
    return opened


# Returning before connection, omitting start, or leaking the probe breaks this.
@pytest.mark.parametrize("unix", [True, False], ids=["unix", "tcp"])
def test_ready(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, unix: bool) -> None:
    """Start the service before probing and close a successful probe."""
    listener, address = _listener(tmp_path, monkeypatch, unix=unix)
    clock = VirtualClock()
    monkeypatch.setattr(time, "monotonic", lambda: clock.now)
    opened = _probes(monkeypatch)
    budgets: list[float] = []

    def start(seconds: float) -> None:
        budgets.append(seconds)
        listener.listen()

    with listener:
        _invoke(SocketReadiness(clock=clock), address, start)
        listener.settimeout(None)
        connection, _ = listener.accept()
        connection.close()
    assert budgets == [10.0]
    assert opened
    assert all(probe.fileno() == -1 for probe in opened)


# Accepting a ready socket after start exhausted the deadline breaks this.
@pytest.mark.parametrize("unix", [True, False], ids=["unix", "tcp"])
def test_expiry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, unix: bool) -> None:
    """Startup cannot buy another deadline even when the service is listening."""
    listener, address = _listener(tmp_path, monkeypatch, unix=unix)
    clock = VirtualClock(passes=20)
    monkeypatch.setattr(time, "monotonic", lambda: clock.now)
    opened = _probes(monkeypatch)

    def start(seconds: float) -> None:
        clock.now += seconds
        listener.listen()

    with listener:
        readiness = SocketReadiness(clock=clock)
        with pytest.raises(Exception, match=r"\S") as caught:
            _invoke(readiness, address, start)
    assert type(caught.value).__name__ == "LaunchError"
    assert (clock.now,) == (10.0,)
    assert all(probe.fileno() == -1 for probe in opened)


# Retrying a permanent socket failure or leaking its probe breaks this.
@pytest.mark.parametrize("unix", [True, False], ids=["unix", "tcp"])
def test_denied(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, unix: bool) -> None:
    """A denied connection becomes a safe LaunchError and closes its probe."""
    listener, address = _listener(tmp_path, monkeypatch, unix=unix)
    clock = VirtualClock(passes=20)
    monkeypatch.setattr(time, "monotonic", lambda: clock.now)
    opened = _probes(monkeypatch)

    def denied(_self: socket.socket, _address: object) -> int:
        raise PermissionError(EACCES, "private-socket-detail")

    monkeypatch.setattr(socket.socket, "connect", denied)
    monkeypatch.setattr(socket.socket, "connect_ex", denied)
    with listener:
        readiness = SocketReadiness(clock=clock)
        with pytest.raises(Exception, match=r"\S") as caught:
            _invoke(readiness, address, lambda _seconds: None)
    assert type(caught.value).__name__ == "LaunchError"
    assert "private-socket-detail" not in str(caught.value)
    assert opened
    assert all(probe.fileno() == -1 for probe in opened)


# Resetting the timeout after start spends thirteen seconds instead of ten.
@pytest.mark.parametrize("unix", [True, False], ids=["unix", "tcp"])
def test_budget(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, unix: bool) -> None:
    """An unavailable socket has only the seven seconds left after startup."""
    listener, address = _listener(tmp_path, monkeypatch, unix=unix)
    clock = VirtualClock(passes=20)
    monkeypatch.setattr(time, "monotonic", lambda: clock.now)
    opened = _probes(monkeypatch)
    budgets: list[float] = []

    def start(seconds: float) -> None:
        budgets.append(seconds)
        clock.now += 3

    with listener:
        readiness = SocketReadiness(clock=clock)
        with pytest.raises(Exception, match=r"\S") as caught:
            _invoke(readiness, address, start)
    assert type(caught.value).__name__ == "LaunchError"
    assert budgets == [10.0]
    assert (clock.now,) == (10.0,)
    assert opened
    assert all(probe.fileno() == -1 for probe in opened)
