"""Red tests for the test-support capture helper.

Source: the gates core design spec under docs/superpowers/specs/, section 3, the "capture.py" bullet: `captured(call)` returns a
`Captured` with `.result` and `.lines`; it works in-process, at the file-descriptor level; fds 1 and 2 and sys.stdout and
sys.stderr all reach one file for the duration of the call, and everything is restored in `finally`. It sees writes to
either Python stream in the order made, direct fd writes, and a checker child's output.
"""

import os
import subprocess
import sys
from typing import TextIO

import pytest

from tests.support.capture import captured

_import_stdout = sys.__stdout__
_import_stderr = sys.__stderr__
assert _import_stdout is not None
assert _import_stderr is not None
IMPORT_STDOUT: TextIO = _import_stdout
IMPORT_STDERR: TextIO = _import_stderr

# A child process that inherits fds 1 and 2 and writes to each, through its own Python streams and directly.
_CHILD = (
    "import os, sys\n"
    "print('child: its sys.stdout', flush=True)\n"
    "print('child: its sys.stderr', file=sys.stderr, flush=True)\n"
    "os.write(1, b'child: its fd 1\\n')\n"
    "os.write(2, b'child: its fd 2\\n')\n"
)


class Boom(Exception):
    """Raised by a captured call to prove the exception propagates."""


def _fd_identity(fd: int) -> tuple[int, int]:
    status = os.fstat(fd)
    return (status.st_dev, status.st_ino)


def _bare(lines: list[str]) -> list[str]:
    return [line.rstrip("\n") for line in lines]


def test_captured_runs_the_call_in_this_interpreter_and_returns_its_result() -> None:
    effects: list[str] = []
    returned = object()

    def call() -> tuple[int, object]:
        effects.append("ran")
        return (os.getpid(), returned)

    result = captured(call).result

    assert result[0] == os.getpid()
    assert result[1] is returned
    assert effects == ["ran"]


def test_captured_sees_every_line_from_every_channel_in_the_order_written() -> None:
    def call() -> None:
        print("one: sys.stdout")
        print("two: sys.stderr", file=sys.stderr)
        IMPORT_STDOUT.write("three: stdout bound at import\n")
        IMPORT_STDOUT.flush()
        IMPORT_STDERR.write("four: stderr bound at import\n")
        IMPORT_STDERR.flush()
        os.write(1, b"five: fd 1\n")
        os.write(2, b"six: fd 2\n")
        subprocess.run([sys.executable, "-I", "-c", _CHILD], check=True, timeout=20)
        sys.stdout.write("seven: sys.stdout again\n")
        sys.stderr.write("eight: sys.stderr again\n")

    lines = captured(call).lines

    assert _bare(lines) == [
        "one: sys.stdout",
        "two: sys.stderr",
        "three: stdout bound at import",
        "four: stderr bound at import",
        "five: fd 1",
        "six: fd 2",
        "child: its sys.stdout",
        "child: its sys.stderr",
        "child: its fd 1",
        "child: its fd 2",
        "seven: sys.stdout again",
        "eight: sys.stderr again",
    ]


def test_captured_restores_fds_and_python_streams_after_the_call(capfd: pytest.CaptureFixture[str]) -> None:
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)

    def call() -> None:
        print("inside")
        os.write(2, b"inside fd 2\n")

    captured(call)

    assert sys.stdout is stdout_before
    assert sys.stderr is stderr_before
    assert _fd_identity(1) == fd1_before
    assert _fd_identity(2) == fd2_before
    capfd.readouterr()
    os.write(1, b"after fd 1\n")
    os.write(2, b"after fd 2\n")
    after = capfd.readouterr()
    assert after.out == "after fd 1\n"
    assert after.err == "after fd 2\n"


def test_captured_lets_the_exception_propagate_and_still_restores(capfd: pytest.CaptureFixture[str]) -> None:
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)

    def call() -> None:
        print("before the raise")
        os.write(1, b"fd 1 before the raise\n")
        raise Boom("raised inside the call")

    with pytest.raises(Boom, match="raised inside the call"):
        captured(call)

    assert sys.stdout is stdout_before
    assert sys.stderr is stderr_before
    assert _fd_identity(1) == fd1_before
    assert _fd_identity(2) == fd2_before
    capfd.readouterr()
    os.write(1, b"after fd 1\n")
    os.write(2, b"after fd 2\n")
    after = capfd.readouterr()
    assert after.out == "after fd 1\n"
    assert after.err == "after fd 2\n"
