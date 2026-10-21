"""Tests for the test-support lifeline: child processes held, met and ended by pipes.

Source: the no-wall-clock design spec under docs/superpowers/specs/, the `tests/support/lifeline.py` module. A
`Lifeline` is a pipe whose write end only the test holds, so a child reading its read end to EOF lives until `release`;
`release` closes the write end and a second call does nothing; leaving it releases, then closes the read end. A
`Witness` makes a FIFO and opens its read end without blocking; every process that opens it to write is a holder, and
`ended`, called after every holder's ready line, blocks until every holder has closed it and returns what they wrote.
`ready(fd)` blocks until a child writes one line on fd and returns it, b"" when every writer closed first. `Pids` gives
the pids children note in its file and SIGKILLs each at teardown, passing over a ProcessLookupError. `HOLD` writes a
ready line to fd 1, then reads the fd its first argument names to EOF and exits 0; `WITNESS` opens the FIFO its first
argument names to write, writes a mark and a ready line, then holds on the fd its second argument names; `MEET` opens
the FIFO its first argument names for reading or writing as its second says, and returns once the other side has
opened it. Every wait here is on a pipe or FIFO, with no timeout: pytest-timeout is the one bound on a test that hangs,
and each child a test starts is killed at its teardown, so a failing test leaves none blocked.
"""

import contextlib
import errno
import os
import signal
import stat
import subprocess
import sys
from collections.abc import Generator
from pathlib import Path

import pytest

from tests.support.lifeline import HOLD, MEET, WITNESS, Lifeline, Pids, Witness, ready

READY = b"ready\n"

MARK = b"held"

# More bytes than a pipe or FIFO buffers, so a writer of them blocks until its reader has taken all but the last.
LATE = b"late" * 262144

# A holder that opens the FIFO at argv[1] to write and writes its ready line, then reads fd argv[2] to EOF, and only
# then writes LATE into the FIFO and closes it.
LATE_HOLDER = (
    "import os, sys\n"
    "witness = os.fdopen(os.open(sys.argv[1], os.O_WRONLY), 'wb')\n"
    "os.write(1, b'ready\\n')\n"
    "while os.read(int(sys.argv[2]), 65536):\n"
    "    pass\n"
    "witness.write(b'late' * 262144)\n"
    "witness.close()\n"
)


@contextlib.contextmanager
def _child(code: str, *arguments: str, fds: tuple[int, ...] = ()) -> Generator[subprocess.Popen[bytes]]:
    """Run child code with its stdout on a pipe and the given fds passed to it; killed at teardown."""
    child = subprocess.Popen(
        [sys.executable, "-c", code, *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        pass_fds=fds,
    )
    try:
        yield child
    finally:
        child.kill()
        child.wait()
        if child.stdout is not None:
            child.stdout.close()


def _ready(child: subprocess.Popen[bytes]) -> bytes:
    """The first line the child writes on its stdout."""
    assert child.stdout is not None
    return ready(child.stdout.fileno())


def _taken(fd: int, data: bytes) -> int:
    """How many bytes of data blocking writes to fd got in before every reader of it had closed."""
    taken = 0
    with contextlib.suppress(BrokenPipeError):
        while taken < len(data):
            taken += os.write(fd, data[taken:])
    return taken


def test_a_held_child_writes_its_ready_line_and_exits_0_once_released() -> None:
    with Lifeline() as line, _child(HOLD, str(line.read_fd), fds=(line.read_fd,)) as child:
        first = _ready(child)
        line.release()
        status = child.wait()

    assert (first, status) == (READY, 0)


def test_a_held_child_reads_its_fd_until_the_writer_closes_it_and_then_exits_0() -> None:
    read_fd, write_fd = os.pipe()
    with _child(HOLD, str(read_fd), fds=(read_fd,)) as child:
        os.close(read_fd)
        try:
            first = _ready(child)
            taken = _taken(write_fd, LATE)
        finally:
            os.close(write_fd)
        status = child.wait()

    assert (first, taken, status) == (READY, len(LATE), 0)


def test_leaving_a_lifeline_releases_its_child() -> None:
    line = Lifeline()
    with _child(HOLD, str(line.read_fd), fds=(line.read_fd,)) as child:
        with line:
            first = _ready(child)
        status = child.wait()

    assert (first, status) == (READY, 0)


def test_a_second_release_does_nothing(tmp_path: Path) -> None:
    other = tmp_path / "other.txt"
    other.write_text("other", encoding="utf-8")
    with Lifeline() as line:
        line.release()
        fd = os.open(other, os.O_RDONLY)
        try:
            line.release()
            kept = os.read(fd, 16)
        finally:
            os.close(fd)

    assert kept == b"other"


def test_leaving_a_lifeline_closes_its_read_end() -> None:
    with Lifeline() as line:
        read_fd = line.read_fd
    with pytest.raises(OSError) as raised:
        os.fstat(read_fd)

    assert raised.value.errno == errno.EBADF


def test_a_witness_is_a_fifo_at_its_path(tmp_path: Path) -> None:
    path = tmp_path / "witness.fifo"
    with Witness(path) as witness:
        mode = path.stat().st_mode

    assert (witness.path, stat.S_ISFIFO(mode)) == (path, True)


def test_ended_gives_back_what_every_holder_wrote_once_each_has_closed(tmp_path: Path) -> None:
    with (
        Lifeline() as line,
        Witness(tmp_path / "witness.fifo") as witness,
        _child(WITNESS, str(witness.path), str(line.read_fd), fds=(line.read_fd,)) as first,
        _child(WITNESS, str(witness.path), str(line.read_fd), fds=(line.read_fd,)) as second,
    ):
        lines = (_ready(first), _ready(second))
        line.release()
        written = witness.ended()
        statuses = (first.wait(), second.wait())

    assert (lines, written, statuses) == ((READY, READY), MARK + MARK, (0, 0))


def test_ended_reads_on_until_a_holder_writing_after_its_release_has_closed(tmp_path: Path) -> None:
    with (
        Lifeline() as line,
        Witness(tmp_path / "witness.fifo") as witness,
        _child(LATE_HOLDER, str(witness.path), str(line.read_fd), fds=(line.read_fd,)) as holder,
    ):
        first = _ready(holder)
        line.release()
        written = witness.ended()
        status = holder.wait()

    assert (first, written, status) == (READY, LATE, 0)


def test_ready_gives_back_one_line_at_a_time() -> None:
    read_fd, write_fd = os.pipe()
    try:
        os.write(write_fd, b"one\ntwo\n")
        lines = (ready(read_fd), ready(read_fd))
    finally:
        os.close(read_fd)
        os.close(write_fd)

    assert lines == (b"one\n", b"two\n")


def test_ready_gives_back_nothing_when_every_writer_closed_first() -> None:
    read_fd, write_fd = os.pipe()
    os.close(write_fd)
    try:
        line = ready(read_fd)
    finally:
        os.close(read_fd)

    assert line == b""


def test_no_pids_noted_before_the_file_is_written(tmp_path: Path) -> None:
    with Pids(tmp_path / "pids.txt") as pids:
        noted = pids.noted()

    assert noted == []


def test_pids_gives_back_the_pids_noted_in_its_file(tmp_path: Path) -> None:
    path = tmp_path / "pids.txt"
    pids = Pids(path)
    path.write_text("1\n2\n", encoding="utf-8")

    assert (pids.path, pids.noted()) == (path, [1, 2])


def test_pids_kills_each_noted_pid_passing_over_one_already_gone(tmp_path: Path) -> None:
    path = tmp_path / "pids.txt"
    with _child("pass\n") as gone:
        gone.wait()
    with Lifeline() as line, _child(HOLD, str(line.read_fd), fds=(line.read_fd,)) as held:
        first = _ready(held)
        with Pids(path):
            path.write_text(f"{gone.pid}\n{held.pid}\n", encoding="utf-8")
        line.release()
        status = held.wait()

    assert (first, status) == (READY, -signal.SIGKILL)


@pytest.mark.parametrize(
    ("side", "flags"),
    [
        pytest.param("read", os.O_WRONLY, id="child reads"),
        pytest.param("write", os.O_RDONLY, id="child writes"),
    ],
)
def test_meet_returns_once_the_other_side_has_opened_the_fifo(tmp_path: Path, side: str, flags: int) -> None:
    path = tmp_path / "meet.fifo"
    os.mkfifo(path)
    with _child(MEET, str(path), side) as child:
        fd = os.open(path, flags)
        try:
            status = child.wait()
        finally:
            os.close(fd)

    assert status == 0
