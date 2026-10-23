# Copyright 2026 oh shit, gorillas!
"""Red tests for the wrapper's wait on a lock another holder has.

Source: gates/heavy.py and the agents design's bullet on heavy runs: "`acquire` asks for the lock without blocking first; when
another process holds it, it writes `WAITING`, the one line `heavy: waiting for the lock <path>`, on the stream it is
handed, then blocks until it gets the lock". Its stub: `acquire(handle, lock, err)`, "LOCK_EX | LOCK_NB on handle
first; when refused, writes WAITING for lock and a line end on err, then blocks on LOCK_EX".

The test calls `acquire` in its own thread. It holds the lock on a second handle and hands `acquire` a stream whose
`write` closes that handle, so the line is the event that releases the lock, with no clock and no second process.
flock locks belong to each open of the file, so a second open in this process is refused as another process would be.
"""

import fcntl
import io
from pathlib import Path
from typing import IO, override

from gates import heavy

WAITING_LINE = "heavy: waiting for the lock {path}\n"


class _Releasing(io.StringIO):
    """A stream that keeps what is written to it and closes the lock's holder at the first write."""

    def __init__(self, holder: IO[str]) -> None:
        super().__init__()
        self.holder = holder

    @override
    def write(self, s: str, /) -> int:
        self.holder.close()
        return super().write(s)


def _held_elsewhere(lock: Path) -> bool:
    """Whether a fresh open of lock is refused the lock at once."""
    with lock.open("a", encoding="utf-8") as probe:
        try:
            fcntl.flock(probe, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return True
        return False


def _acquire_refused(lock: Path) -> tuple[str, bool, bool]:
    """Call acquire on lock while a second handle holds it.

    Returns what it wrote, whether the lock was then held, and whether it was still held once the handle given to
    acquire was closed: a lock held on that handle, and on no other open, is free again at its close.
    """
    holder = lock.open("a", encoding="utf-8")
    fcntl.flock(holder, fcntl.LOCK_EX)
    err = _Releasing(holder)
    with lock.open("a", encoding="utf-8") as handle:
        try:
            heavy.acquire(handle, lock, err)
        finally:
            holder.close()
        held = _held_elsewhere(lock)
    return err.getvalue(), held, _held_elsewhere(lock)


def test_refused_writes_waiting_line(tmp_path: Path) -> None:
    """Refused the lock at once, acquire writes the one line WAITING for its path, and a line end, on its stream.

    Breaks when: acquire blocks on the lock without writing, or writes another line, or writes it more than once.
    """
    lock = tmp_path / "heavy.lock"

    written, _held, _held_after_close = _acquire_refused(lock)

    assert written == WAITING_LINE.format(path=lock)


def test_refused_then_takes_lock(tmp_path: Path) -> None:
    """Refused the lock at once, acquire returns only once it holds the lock on the handle it is given.

    Breaks when: acquire returns after writing the line without taking the lock, or takes it on an open of its own
    instead of on the handle it is given.
    """
    lock = tmp_path / "heavy.lock"

    _written, held, held_after_close = _acquire_refused(lock)

    assert held is True
    assert held_after_close is False
