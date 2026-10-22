# Copyright 2026 oh shit, gorillas!
"""Red tests for the test-support capture helper.

Source: the capture design spec under docs/superpowers/specs/, its Modules and Decisions sections: each
of fds 1 and 2 points at a pipe of its own for the length of the call, so a write blocks as it would on a pipe, is never
cut and never fails for size; a call that raises propagates unchanged, as itself, and its `Output` is read as data
through `output_of(exc)`, not through an attribute on the exception, while `output_of` on an exception `captured` never
recorded raises `CaptureUnrecordedError` carrying that exception (decision 2). Once the call has ended, `captured`
keeps no bound of its own on a holder of fd 1 or 2: pytest-timeout is the one bound (the capture design's "A holder left
behind" bullet and decision 3), so no test here holds the fds past the call.

Order, decision 1: `.out` and `.err` hold each fd's lines exactly in the order written, and `.merged` holds every line of
both, each placed by the arrival of its first byte, so a line one stream interrupts mid-line is whole and placed where
it began. A write through this process's `sys.stdout` or `sys.stderr` is placed exactly; raw writes to the two fds, from
`os.write` or a child, with no stream write between them, may be merged in either fd's order. A write that works
uncaptured works captured, bytes that are not UTF-8 included.

Lines, the capture design's paragraph after the Modules bullets: "`_lines` is the one place captured bytes become lines.
It splits each fd's text at every `str.splitlines` boundary, each line keeping its line end", so the lines of each fd are
those `str.splitlines(keepends=True)` makes of what it was written.

Earlier source: the gates core design spec under docs/superpowers/specs/, section 3, the "capture.py" bullet: `captured(call)` returns a
`Captured` with `.result`, `.out`, `.err` and `.merged`; `.out` and `.err` are the lines written to fd 1 and fd 2 (and to
sys.stdout and sys.stderr), kept apart, and `.merged` is every line of both in the order written. It works in-process, at
the file-descriptor level, and everything is restored in `finally`, then its reader thread is stopped and joined, so
none of its threads is left running once it returns or raises. It sees writes to either Python stream in the order
made, direct fd writes, and a checker child's output.

Cleanup, the capture design's "Cleanup" bullet: on every exit path, an interrupt included, the `sys` streams are restored,
fds 1 and 2 are restored from saved duplicates, every fd capture opened is closed, since a `ResourceWarning` is an error,
and the reader is joined before `captured` returns or raises. A failure partway through setting up is an exit path too:
here it is the process running out of fds, which Python reports as `OSError` with errno `EMFILE` (`os.pipe`, `os.dup`).
The capture design's "Setup failure" bullet: after that same cleanup, `captured` raises `CaptureSetupError`, carrying the
errno and the step that failed, making a pipe (`pipe`), a dup (`dup`) or the reader thread (`reader`); no bare `OSError`
leaves the helper.
"""

import contextlib
import errno
import gc
import io
import itertools
import os
import resource
import subprocess
import sys
import threading
import warnings
from collections.abc import Callable
from pathlib import Path
from typing import TextIO

import pytest

from tests.support.capture import (
    CaptureSetupError,
    CaptureUnrecordedError,
    captured,
    output_of,
)

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


class BoomError(Exception):
    """Raised by a captured call to prove the exception propagates."""


class Halt(BaseException):
    """Raised by a captured call to prove an exception outside `Exception`, as an interrupt is, has its output read too."""


_MIB = 1024 * 1024

# A line one stream begins, the other stream writes a whole line, then the first stream ends its line.
_BEGUN = "begun on one stream, "
_WHOLE = "a whole line on the other stream\n"
_ENDED = "ended after the other stream's line\n"

# Text written to fd 1 through sys.stdout and to fd 2 directly, in two writes that cut "\r\n" between them, and the lines
# str.splitlines(keepends=True) makes of it: it ends a line at \n, \r, \r\n, \v, \f, \x1c, \x1d, \x1e, \x85,
# and \u2029, and keeps a last line that has no line end.
_SPLIT_HEAD = (
    "line feed\n"
    "carriage return\r"
    "both\r\n"
    "line tabulation\x0b"
    "form feed\x0c"
    "file separator\x1c"
    "group separator\x1d"
    "record separator\x1e"
    "next line\x85"
    "line separator\u2028"
    "paragraph separator\u2029"
    "both cut between writes\r"
)
_SPLIT_TAIL = "\nno line end"
_SPLIT_LINES = [
    "line feed\n",
    "carriage return\r",
    "both\r\n",
    "line tabulation\x0b",
    "form feed\x0c",
    "file separator\x1c",
    "group separator\x1d",
    "record separator\x1e",
    "next line\x85",
    "line separator\u2028",
    "paragraph separator\u2029",
    "both cut between writes\r\n",
    "no line end",
]

# Writes that work on an uncaptured terminal: text past ASCII, bytes through a stream's buffer, raw writes to a stream's
# fileno(), and UTF-8 characters whose bytes arrive in separate writes.
_NON_ASCII = "naïve café: ✓ 日本語 ünïcödé"
_BUFFER_OUT = "bytes through sys.stdout.buffer\n"
_BUFFER_ERR = "bytes through sys.stderr.buffer\n"
_FILENO_OUT = "raw write to sys.stdout.fileno()\n"
_FILENO_ERR = "raw write to sys.stderr.fileno()\n"
_SPLIT_CHARACTERS = "cut é, ✓ and 日本 byte by byte\n"
_NO_LINES: list[str] = []

# Lines around bytes that are not UTF-8: a stray continuation byte, a byte UTF-8 never uses, a lead byte with no
# continuation, and at the very end a lead byte and one continuation byte of a three-byte character with no line end.
_BEFORE_BAD = "before the bad bytes\n"
_BAD = b"bad: \x80\xff\xc3 end\n"
_AFTER_BAD = "after the bad bytes\n"
_CUT = b"cut: \xe2\x82"

# Lines a raising call writes through its Python streams, each with its line end.
_RAISED_OUT_ONE = "raised out one: sys.stdout\n"
_RAISED_ERR_ONE = "raised err one: sys.stderr\n"
_RAISED_OUT_TWO = "raised out two: sys.stdout again\n"
_RAISED_ERR_TWO = "raised err two: sys.stderr again\n"


def _fd_identity(fd: int) -> tuple[int, int]:
    status = os.fstat(fd)
    return (status.st_dev, status.st_ino)


def _bare(lines: list[str]) -> list[str]:
    return [line.rstrip("\n") for line in lines]


def _runs(
    lines: list[str], sizes: list[int], fd1_lines: list[str]
) -> list[tuple[list[str], list[str]]]:
    """Cut `lines` into consecutive runs of `sizes` lines, each run kept as its fd 1 lines and its fd 2 lines in order."""
    bounds = list(itertools.accumulate(sizes, initial=0))
    runs = [lines[start:end] for start, end in itertools.pairwise(bounds)]
    return [
        (
            [line for line in run if line in fd1_lines],
            [line for line in run if line not in fd1_lines],
        )
        for run in runs
    ]


def _write_non_ascii() -> None:
    sys.stdout.write(_NON_ASCII + "\n")


def _write_stdout_buffer() -> None:
    stdout: TextIO = sys.stdout
    stdout.buffer.write(_BUFFER_OUT.encode())
    stdout.flush()


def _write_stderr_buffer() -> None:
    stderr: TextIO = sys.stderr
    stderr.buffer.write(_BUFFER_ERR.encode())
    stderr.flush()


def _write_stream_filenos() -> None:
    stdout: TextIO = sys.stdout
    stderr: TextIO = sys.stderr
    os.write(stdout.fileno(), _FILENO_OUT.encode())
    os.write(stderr.fileno(), _FILENO_ERR.encode())


def _write_split_characters() -> None:
    encoded = _SPLIT_CHARACTERS.encode()
    for start in range(len(encoded)):
        os.write(1, encoded[start : start + 1])


def test_captured_runs_the_call_in_this_interpreter_and_returns_its_result() -> None:
    """Verify captured runs the call in this interpreter and returns its result."""
    effects: list[str] = []
    returned = object()

    def call() -> tuple[int, object]:
        effects.append("ran")
        return (os.getpid(), returned)

    result = captured(call).result

    assert result[0] == os.getpid()
    assert result[1] is returned
    assert effects == ["ran"]


def test_captured_merges_every_channel_in_the_order_written_save_raw_writes_no_stream_write_parts() -> (
    None
):
    """Verify captured merges every channel in the order written save raw writes no stream write parts."""

    def call() -> None:
        sys.stdout.write("one: sys.stdout\n")
        sys.stderr.write("two: sys.stderr\n")
        IMPORT_STDOUT.write("three: stdout bound at import\n")
        IMPORT_STDOUT.flush()
        IMPORT_STDERR.write("four: stderr bound at import\n")
        IMPORT_STDERR.flush()
        os.write(1, b"five: fd 1\n")
        os.write(2, b"six: fd 2\n")
        sys.stdout.write("seven: sys.stdout between raw runs\n")
        subprocess.run([sys.executable, "-I", "-c", _CHILD], check=True)
        sys.stderr.write("eight: sys.stderr between raw runs\n")
        os.write(2, b"nine: fd 2 alone\n")
        sys.stdout.write("ten: sys.stdout last\n")

    capture = captured(call)
    out = _bare(capture.out)
    merged = _bare(capture.merged)

    assert (
        out,
        _bare(capture.err),
        len(merged),
        _runs(merged, [1, 1, 4, 1, 4, 1, 1, 1], out),
    ) == (
        [
            "one: sys.stdout",
            "three: stdout bound at import",
            "five: fd 1",
            "seven: sys.stdout between raw runs",
            "child: its sys.stdout",
            "child: its fd 1",
            "ten: sys.stdout last",
        ],
        [
            "two: sys.stderr",
            "four: stderr bound at import",
            "six: fd 2",
            "child: its sys.stderr",
            "child: its fd 2",
            "eight: sys.stderr between raw runs",
            "nine: fd 2 alone",
        ],
        14,
        [
            (["one: sys.stdout"], []),
            ([], ["two: sys.stderr"]),
            (
                ["three: stdout bound at import", "five: fd 1"],
                ["four: stderr bound at import", "six: fd 2"],
            ),
            (["seven: sys.stdout between raw runs"], []),
            (
                ["child: its sys.stdout", "child: its fd 1"],
                ["child: its sys.stderr", "child: its fd 2"],
            ),
            ([], ["eight: sys.stderr between raw runs"]),
            ([], ["nine: fd 2 alone"]),
            (["ten: sys.stdout last"], []),
        ],
    )


@pytest.mark.parametrize("interrupted", [1, 2])
def test_captured_keeps_a_line_another_stream_interrupts_mid_line_whole_and_placed_by_its_first_byte(
    interrupted: int,
) -> None:
    """Verify captured keeps a line another stream interrupts mid line whole and placed by its first byte."""

    def call() -> None:
        begun, other = (
            (sys.stdout, sys.stderr) if interrupted == 1 else (sys.stderr, sys.stdout)
        )
        begun.write(_BEGUN)
        begun.flush()
        other.write(_WHOLE)
        other.flush()
        begun.write(_ENDED)

    capture = captured(call)
    joined = _BEGUN + _ENDED
    views = ([joined], [_WHOLE]) if interrupted == 1 else ([_WHOLE], [joined])

    assert (capture.out, capture.err, capture.merged) == (*views, [joined, _WHOLE])


def test_captured_splits_what_each_fd_was_written_into_lines_as_str_splitlines_does() -> (
    None
):
    """Capture design, the `_lines` paragraph: each fd's text splits at every `str.splitlines` boundary."""

    def call() -> None:
        sys.stdout.write(_SPLIT_HEAD)
        sys.stdout.flush()
        sys.stdout.write(_SPLIT_TAIL)
        os.write(2, _SPLIT_HEAD.encode())
        os.write(2, _SPLIT_TAIL.encode())

    capture = captured(call)

    assert (capture.out, capture.err) == (_SPLIT_LINES, _SPLIT_LINES)


@pytest.mark.parametrize(
    ("write", "views"),
    [
        pytest.param(
            _write_non_ascii,
            ([_NON_ASCII + "\n"], _NO_LINES),
            id="non-ASCII text through sys.stdout",
        ),
        pytest.param(
            _write_stdout_buffer,
            ([_BUFFER_OUT], _NO_LINES),
            id="bytes through sys.stdout.buffer",
        ),
        pytest.param(
            _write_stderr_buffer,
            (_NO_LINES, [_BUFFER_ERR]),
            id="bytes through sys.stderr.buffer",
        ),
        pytest.param(
            _write_stream_filenos,
            ([_FILENO_OUT], [_FILENO_ERR]),
            id="raw writes to the streams' filenos",
        ),
        pytest.param(
            _write_split_characters,
            ([_SPLIT_CHARACTERS], _NO_LINES),
            id="UTF-8 characters cut across writes",
        ),
    ],
)
def test_a_write_that_works_uncaptured_works_captured(
    write: Callable[[], None], views: tuple[list[str], list[str]]
) -> None:
    """Verify a write that works uncaptured works captured."""
    capture = captured(write)

    assert (capture.out, capture.err) == views


def test_bytes_that_are_not_utf_8_never_lose_the_capture() -> None:
    """Verify bytes that are not utf 8 never lose the capture."""
    returned = object()

    def call() -> object:
        os.write(1, _BEFORE_BAD.encode())
        os.write(1, _BAD)
        os.write(1, _AFTER_BAD.encode())
        os.write(1, _CUT)
        stderr: TextIO = sys.stderr
        stderr.buffer.write(_BEFORE_BAD.encode() + _BAD + _AFTER_BAD.encode())
        stderr.flush()
        return returned

    capture = captured(call)
    out, err = capture.out, capture.err

    assert (
        capture.result is returned,
        len(out),
        out[0],
        out[1][:5],
        out[1][-5:],
        out[2],
        out[3][:5],
        len(err),
        err[0],
        err[1][:5],
        err[1][-5:],
        err[2],
        capture.merged == out + err,
    ) == (
        True,
        4,
        _BEFORE_BAD,
        "bad: ",
        " end\n",
        _AFTER_BAD,
        "cut: ",
        3,
        _BEFORE_BAD,
        "bad: ",
        " end\n",
        _AFTER_BAD,
        True,
    )


def test_captured_restores_fds_and_python_streams_after_the_call(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Verify captured restores fds and python streams after the call."""
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)
    threads_before = set(threading.enumerate())

    def call() -> None:
        sys.stdout.write("inside\n")
        os.write(2, b"inside fd 2\n")

    captured(call)

    assert set(threading.enumerate()) == threads_before
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


def test_captured_lets_the_exception_propagate_and_still_restores(
    capfd: pytest.CaptureFixture[str],
) -> None:
    """Verify captured lets the exception propagate and still restores."""
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)
    threads_before = set(threading.enumerate())

    def call() -> None:
        sys.stdout.write("before the raise\n")
        os.write(1, b"fd 1 before the raise\n")
        message = "raised inside the call"
        raise BoomError(message)

    with pytest.raises(BoomError, match="raised inside the call"):
        captured(call)

    assert set(threading.enumerate()) == threads_before
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


def test_captured_takes_a_write_far_past_a_mebibyte_whole_on_each_fd() -> None:
    """Verify captured takes a write far past a mebibyte whole on each fd."""
    stream_line = "s" * (4 * _MIB) + "\n"
    raw_line = "r" * (4 * _MIB) + "\n"

    def call() -> int:
        sys.stdout.write(stream_line)
        sys.stdout.flush()
        return os.write(2, raw_line.encode())

    capture = captured(call)

    assert (capture.result, capture.out, capture.err) == (
        len(raw_line),
        [stream_line],
        [raw_line],
    )


def test_captured_takes_a_childs_write_far_past_a_mebibyte_whole() -> None:
    """Verify captured takes a childs write far past a mebibyte whole."""
    size = 4 * _MIB
    child_line = "c" * size + "\n"
    child = f"import sys\nsys.stdout.buffer.write(b'c' * {size} + b'\\n')\nsys.stdout.flush()\n"

    def call() -> None:
        subprocess.run([sys.executable, "-I", "-c", child], check=True)

    assert captured(call).out == [child_line]


def test_captured_never_fails_a_write_while_more_is_written_than_the_reader_has_drained() -> (
    None
):
    """Verify captured never fails a write while more is written than the reader has drained."""
    out_lines = [f"out {index:06d} " + "o" * 4096 + "\n" for index in range(2048)]
    err_lines = [f"err {index:06d} " + "e" * 4096 + "\n" for index in range(2048)]

    def call() -> None:
        for out_line, err_line in zip(out_lines, err_lines, strict=True):
            os.write(1, out_line.encode())
            os.write(2, err_line.encode())

    capture = captured(call)

    assert (capture.out, capture.err) == (out_lines, err_lines)


@pytest.mark.parametrize("kind", [BoomError, Halt])
def test_output_of_reads_every_line_a_raising_call_wrote_from_its_exception(
    kind: type[BoomError | Halt],
) -> None:
    """Verify output of reads every line a raising call wrote from its exception."""

    def call() -> None:
        sys.stdout.write(_RAISED_OUT_ONE)
        sys.stderr.write(_RAISED_ERR_ONE)
        sys.stdout.write(_RAISED_OUT_TWO)
        sys.stderr.write(_RAISED_ERR_TWO)
        raise kind

    with pytest.raises(kind) as raised:
        captured(call)
    output = output_of(raised.value)

    assert (output.out, output.err, output.merged) == (
        [_RAISED_OUT_ONE, _RAISED_OUT_TWO],
        [_RAISED_ERR_ONE, _RAISED_ERR_TWO],
        [_RAISED_OUT_ONE, _RAISED_ERR_ONE, _RAISED_OUT_TWO, _RAISED_ERR_TWO],
    )


def test_a_raising_call_propagates_as_the_very_exception_it_raised() -> None:
    """Verify a raising call propagates as the very exception it raised."""
    thrown: list[BoomError] = []

    def call() -> None:
        sys.stdout.write(_RAISED_OUT_ONE)
        thrown.append(BoomError())
        raise thrown[0]

    with pytest.raises(BoomError) as raised:
        captured(call)

    assert (raised.value is thrown[0], output_of(raised.value).out) == (
        True,
        [_RAISED_OUT_ONE],
    )


@pytest.mark.parametrize(
    "kind",
    [
        pytest.param(ValueError, id="ValueError"),
        pytest.param(AssertionError, id="AssertionError"),
        pytest.param(KeyError, id="KeyError"),
        pytest.param(KeyboardInterrupt, id="KeyboardInterrupt, an interrupt"),
        pytest.param(SystemExit, id="SystemExit"),
    ],
)
def test_a_built_in_exception_a_call_raises_propagates_unchanged_with_every_line_it_wrote(
    kind: type[BaseException],
) -> None:
    """Verify a built in exception a call raises propagates unchanged with every line it wrote."""
    thrown: list[BaseException] = []

    def call() -> None:
        sys.stdout.write(_RAISED_OUT_ONE)
        sys.stderr.write(_RAISED_ERR_ONE)
        sys.stdout.write(_RAISED_OUT_TWO)
        sys.stderr.write(_RAISED_ERR_TWO)
        thrown.append(kind("raised as built"))
        raise thrown[0]

    with pytest.raises(kind) as raised:
        captured(call)
    output = output_of(raised.value)

    # An exception's repr is its class name and the repr of its args, so this holds the args without reading
    # BaseException.args, which is typed tuple[Any, ...].
    assert (
        raised.value is thrown[0],
        type(raised.value),
        repr(raised.value),
        output.out,
        output.err,
        output.merged,
    ) == (
        True,
        kind,
        repr(kind("raised as built")),
        [_RAISED_OUT_ONE, _RAISED_OUT_TWO],
        [_RAISED_ERR_ONE, _RAISED_ERR_TWO],
        [_RAISED_OUT_ONE, _RAISED_ERR_ONE, _RAISED_OUT_TWO, _RAISED_ERR_TWO],
    )


def _never_left_captured() -> BaseException:
    """Return an exception a captured call raised and caught itself, so it never left `captured`."""
    caught: list[BoomError] = []

    def raise_boom() -> None:
        raise BoomError

    def call() -> None:
        try:
            raise_boom()
        except BoomError as error:
            caught.append(error)

    captured(call)
    return caught[0]


@pytest.mark.parametrize(
    "unrecorded",
    [
        pytest.param(BoomError, id="never passed through captured"),
        pytest.param(
            _never_left_captured, id="raised and caught inside a captured call"
        ),
    ],
)
def test_output_of_an_exception_captured_never_recorded_raises_its_own_error_carrying_it(
    unrecorded: Callable[[], BaseException],
) -> None:
    """Verify output of an exception captured never recorded raises its own error carrying it."""
    exc = unrecorded()

    with pytest.raises(CaptureUnrecordedError) as raised:
        output_of(exc)

    assert raised.value.exc is exc


# Lines a call writes before it leaves `captured` one way or another, and a line a later capture writes.
_PATH_OUT = "written to fd 1 before the call ends\n"
_PATH_ERR = "written to fd 2 before the call ends\n"
_LATER_OUT = "written by a later capture\n"


class Interrupt(KeyboardInterrupt):
    """Raised by a captured call as an interrupt is, a `KeyboardInterrupt`, to prove cleanup on an interrupt."""


def _open_fds() -> set[int]:
    """Every fd open in this process, the one that lists them excluded."""
    open_fds: set[int] = set()
    for path in Path("/dev/fd").iterdir():
        fd = int(path.name)
        try:
            os.fstat(fd)
        except OSError:
            continue
        open_fds.add(fd)
    return open_fds


def _nth_free_fd(open_fds: set[int], count: int) -> int:
    """Return the fd number below which exactly `count` fd numbers are free."""
    free = (fd for fd in itertools.count() if fd not in open_fds)
    return next(itertools.islice(free, count, None))


def _write_both() -> None:
    sys.stdout.write(_PATH_OUT)
    os.write(2, _PATH_ERR.encode())


def _write_later() -> None:
    sys.stdout.write(_LATER_OUT)


def _write_then_raise() -> None:
    _write_both()
    raise BoomError


def _write_then_interrupt() -> None:
    _write_both()
    raise Interrupt


def _returned() -> list[str]:
    return captured(_write_both).out


def _raised() -> list[str]:
    try:
        captured(_write_then_raise)
    except BoomError as error:
        return output_of(error).out
    return _NO_LINES


def _interrupted() -> list[str]:
    try:
        captured(_write_then_interrupt)
    except Interrupt as error:
        return output_of(error).out
    return _NO_LINES


# Each way out of `captured`, run to its end, and the fd 1 lines it hands back.
_EXIT_PATHS = [
    pytest.param(_returned, [_PATH_OUT], id="the call returned"),
    pytest.param(_raised, [_PATH_OUT], id="the call raised"),
    pytest.param(_interrupted, [_PATH_OUT], id="the call was interrupted"),
]


@pytest.mark.parametrize(("leave", "out"), _EXIT_PATHS)
def test_every_fd_captured_opens_is_closed_on_every_exit_path(
    leave: Callable[[], list[str]], out: list[str]
) -> None:
    """Verify every fd captured opens is closed on every exit path."""
    gc.collect()
    fds_before = _open_fds()

    left = leave()

    assert (left, _open_fds()) == (out, fds_before)


@pytest.mark.parametrize(("leave", "out"), _EXIT_PATHS)
def test_captured_leaves_nothing_behind_that_warns_when_it_is_collected(
    leave: Callable[[], list[str]], out: list[str]
) -> None:
    """Verify captured leaves nothing behind that warns when it is collected."""
    gc.collect()
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        left = leave()
        gc.collect()

    assert (left, [str(warning.message) for warning in caught]) == (out, [])


def test_an_interrupted_call_restores_fds_streams_and_threads() -> None:
    """Verify an interrupted call restores fds streams and threads."""
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)
    threads_before = set(threading.enumerate())

    with pytest.raises(Interrupt):
        captured(_write_then_interrupt)

    assert (
        set(threading.enumerate()),
        sys.stdout,
        sys.stderr,
        _fd_identity(1),
        _fd_identity(2),
    ) == (threads_before, stdout_before, stderr_before, fd1_before, fd2_before)


def test_captured_restores_fds_and_streams_the_call_itself_replaced() -> None:
    """Verify captured restores fds and streams the call itself replaced."""
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)

    def call() -> None:
        replaced = contextlib.ExitStack()
        replaced.enter_context(contextlib.redirect_stdout(io.StringIO()))
        replaced.enter_context(contextlib.redirect_stderr(io.StringIO()))
        null = os.open(os.devnull, os.O_WRONLY)
        os.dup2(null, 1)
        os.dup2(null, 2)
        os.close(null)

    captured(call)

    assert (sys.stdout, sys.stderr, _fd_identity(1), _fd_identity(2)) == (
        stdout_before,
        stderr_before,
        fd1_before,
        fd2_before,
    )


@pytest.mark.parametrize(
    "free",
    [
        pytest.param(0, id="no fd free"),
        pytest.param(1, id="one fd free"),
        pytest.param(2, id="two fds free"),
        pytest.param(3, id="three fds free"),
        pytest.param(4, id="four fds free"),
    ],
)
def test_a_failure_partway_through_setting_up_raises_its_own_error_and_leaves_nothing_behind(
    free: int,
) -> None:
    """Verify a failure partway through setting up raises its own error and leaves nothing behind."""
    gc.collect()
    stdout_before, stderr_before = sys.stdout, sys.stderr
    fd1_before, fd2_before = _fd_identity(1), _fd_identity(2)
    threads_before = set(threading.enumerate())
    fds_before = _open_fds()
    soft, hard = resource.getrlimit(resource.RLIMIT_NOFILE)
    resource.setrlimit(resource.RLIMIT_NOFILE, (_nth_free_fd(fds_before, free), hard))
    try:
        with pytest.raises(CaptureSetupError) as raised:
            captured(_write_both)
    finally:
        resource.setrlimit(resource.RLIMIT_NOFILE, (soft, hard))
    after = (
        raised.value.errno,
        # Running out of fds fails a step that opens one; the design names no order among the steps.
        raised.value.step in {"pipe", "dup"},
        set(threading.enumerate()),
        sys.stdout,
        sys.stderr,
        _fd_identity(1),
        _fd_identity(2),
        _open_fds(),
    )

    later = captured(_write_later).out

    assert (after, later) == (
        (
            errno.EMFILE,
            True,
            threads_before,
            stdout_before,
            stderr_before,
            fd1_before,
            fd2_before,
            fds_before,
        ),
        [_LATER_OUT],
    )
