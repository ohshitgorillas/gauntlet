"""In-process capture of everything a call writes to file descriptors 1 and 2 and to sys.stdout and sys.stderr.

Design: the capture design spec under docs/superpowers/specs/. For the length of the call, fds 1 and 2 each point at the
write end of a pipe of their own, so a write to either fd, from this process or a child that inherits it, blocks as it
would on any pipe whose reader is alive, and is never cut or failed for size. A reader thread drains both read ends
while the call runs. sys.stdout and sys.stderr are text streams over fds 1 and 2 whose writes skip the pipes: each
first drains both pipes, then records its own bytes, so it is placed after every write that finished before it. Once
the call has ended, capture closes its write ends and the reader drains until both pipes reach end of file, with no bound
of its own: a holder of fd 1 or 2 is waited on until it closes them, and pytest-timeout is the one bound (capture design,
"A holder left behind" and decision 3).
"""

import bisect
import codecs
import contextlib
import io
import os
import select
import sys
import threading
from collections.abc import Buffer, Callable
from concurrent.futures import ThreadPoolExecutor
from types import TracebackType
from typing import Literal, override

_OUT, _ERR = "out", "err"
_READ_SIZE = 1 << 16


class Output:
    """The lines written to fd 1, to fd 2, and to both in the order of arrival; each line keeps its line end."""

    def __init__(self, out: list[str], err: list[str], merged: list[str]) -> None:
        self._out = list(out)
        self._err = list(err)
        self._merged = list(merged)

    @property
    def out(self) -> list[str]:
        return list(self._out)

    @property
    def err(self) -> list[str]:
        return list(self._err)

    @property
    def merged(self) -> list[str]:
        return list(self._merged)


class Captured[T](Output):
    """A call that returned: its result and its Output."""

    def __init__(self, result: T, output: Output) -> None:
        super().__init__(output.out, output.err, output.merged)
        self._result = result

    @property
    def result(self) -> T:
        return self._result


class CaptureSetupError(Exception):
    """Capture could not set up, so the call never ran."""

    errno: int | None
    step: Literal["pipe", "dup", "reader"]

    def __init__(self, errno: int | None, step: Literal["pipe", "dup", "reader"]) -> None:
        super().__init__(f"captured: could not set up: the {step} step failed, errno {errno}")
        self.errno = errno
        self.step = step


class CaptureUnrecordedError(Exception):
    """output_of was asked for an exception captured never recorded."""

    exc: BaseException

    def __init__(self, exc: BaseException) -> None:
        super().__init__(f"output_of: captured never recorded {exc!r}")
        self.exc = exc


# The key in a raised exception's own instance __dict__ that holds the Output of its call, for output_of alone
# (design decision 2).
_OUTPUT_KEY = "_tests_support_capture_output"


def _record(exc: BaseException, output: Output) -> None:
    """Keep `output` in `exc`'s own instance __dict__ under the one key output_of reads."""
    stash: dict[str, object] = exc.__dict__
    stash[_OUTPUT_KEY] = output


def _readable(fd: int) -> bool:
    """Whether a read of `fd` returns now, with bytes or at end of file, instead of blocking."""
    poller = select.poll()
    poller.register(fd, select.POLLIN)
    return bool(poller.poll(0))


class _Reader:
    """Drains the pipes' read ends on its own thread, keeping each chunk read and the fd it was written to.

    Every read happens under one lock, from the reader thread or from a stream write, so the chunks are kept in the order
    they were read, and each read is made only once the pipe is readable, so none blocks. The thread ends when both
    pipes reach end of file, or when the stop fd becomes readable; an exception it raises is raised again by `finish`.
    """

    def __init__(self, ends: dict[int, str], stop: tuple[int, int]) -> None:
        self._ends = ends
        self._stop_read, self._stop_write = stop
        self._lock = threading.RLock()
        self.chunks: list[tuple[str, bytes]] = []
        self._executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="captured-reader")
        try:
            self._done = self._executor.submit(self._run)
        except RuntimeError as error:
            raise CaptureSetupError(None, "reader") from error

    def _run(self) -> None:
        poller = select.poll()
        for end in self._ends:
            poller.register(end, select.POLLIN)
        poller.register(self._stop_read, select.POLLIN)
        open_ends = set(self._ends)
        while open_ends:
            ready = {fd for fd, _ in poller.poll()}
            if self._stop_read in ready:
                self._drain_all()
                return
            for end in ready & open_ends:
                with self._lock:
                    at_end = self._drain(end)
                if at_end:
                    open_ends.discard(end)
                    poller.unregister(end)

    def _drain(self, end: int) -> bool:
        """Read everything the pipe holds now; true once it has reached end of file. The lock is held."""
        while _readable(end):
            chunk = os.read(end, _READ_SIZE)
            if not chunk:
                return True
            self.chunks.append((self._ends[end], chunk))
        return False

    def _drain_all(self) -> None:
        with self._lock:
            for end in self._ends:
                self._drain(end)

    def place(self, source: str, data: bytes) -> None:
        """Record a stream write after every byte either pipe holds now, which every finished write has reached."""
        with self._lock:
            for end in self._ends:
                self._drain(end)
            if data:
                self.chunks.append((source, data))

    def finish(self) -> None:
        """Wait, with no bound, for both pipes to reach end of file, then join; a wait that is interrupted stops it first."""
        try:
            self._done.result()
        finally:
            if not self._done.done():
                os.write(self._stop_write, b"\0")
            self._executor.shutdown(wait=True)


class _Stream(io.RawIOBase):
    """The raw layer under a captured sys.stdout or sys.stderr: its fileno() is the captured fd, its writes are placed."""

    def __init__(self, fd: int, source: str, reader: _Reader) -> None:
        super().__init__()
        self._fd = fd
        self._source = source
        self._reader = reader

    @property
    def name(self) -> str:
        return f"<captured {self._source}>"

    @override
    def writable(self) -> bool:
        return True

    @override
    def fileno(self) -> int:
        return self._fd

    @override
    def write(self, data: Buffer, /) -> int:
        chunk = memoryview(data).tobytes()
        self._reader.place(self._source, chunk)
        return len(chunk)


def _text_stream(fd: int, source: str, reader: _Reader) -> io.TextIOWrapper:
    return io.TextIOWrapper(
        _Stream(fd, source, reader), encoding="utf-8", errors="backslashreplace", write_through=True
    )


def _lines(chunks: list[tuple[str, bytes]], source: str) -> list[tuple[int, str]]:
    """The source's lines, as str.splitlines makes them of its bytes decoded as UTF-8 with each bad byte replaced, each
    with the index in `chunks` of the chunk its first byte arrived in.

    A chunk read while the decoder holds the first bytes of a character starts one character later, since that
    character began in an earlier chunk.
    """
    decoder = codecs.getincrementaldecoder("utf-8")(errors="replace")
    starts: list[int] = []
    indices: list[int] = []
    parts: list[str] = []
    length = 0
    for index, (sender, chunk) in enumerate(chunks):
        if sender == source:
            pending, _ = decoder.getstate()
            starts.append(length + 1 if pending else length)
            indices.append(index)
            text = decoder.decode(chunk)
            parts.append(text)
            length += len(text)
    parts.append(decoder.decode(b"", final=True))
    lines: list[tuple[int, str]] = []
    offset = 0
    for line in "".join(parts).splitlines(keepends=True):
        lines.append((indices[bisect.bisect_right(starts, offset) - 1], line))
        offset += len(line)
    return lines


def _started(line: tuple[int, str]) -> int:
    return line[0]


def _output(chunks: list[tuple[str, bytes]]) -> Output:
    out, err = _lines(chunks, _OUT), _lines(chunks, _ERR)
    merged = [line for _, line in sorted(out + err, key=_started)]
    return Output([line for _, line in out], [line for _, line in err], merged)


def _flush_streams() -> None:
    for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
        if stream is not None:
            stream.flush()


def _pipe(owned: list[int]) -> tuple[int, int]:
    try:
        read_end, write_end = os.pipe()
    except OSError as error:
        raise CaptureSetupError(error.errno, "pipe") from error
    owned.extend((read_end, write_end))
    return read_end, write_end


def _dup(owned: list[int], fd: int) -> int:
    try:
        duplicate = os.dup(fd)
    except OSError as error:
        raise CaptureSetupError(error.errno, "dup") from error
    owned.append(duplicate)
    return duplicate


def _close(owned: list[int], fd: int) -> None:
    owned.remove(fd)
    os.close(fd)


def _close_all(owned: list[int]) -> None:
    while owned:
        os.close(owned.pop())


class _Capture:
    """One capture, set up when made: its saved fds, its pipes and its reader, cleaned up as the `with` block ends.

    A failure while it sets up closes every fd it opened before it raises. The call's exception leaves the `with` block
    as itself; the cleanup only records the Output against it.
    """

    def __init__(self) -> None:
        self._owned: list[int] = []
        self.output = Output([], [], [])
        with contextlib.ExitStack() as undo:
            undo.callback(_close_all, self._owned)
            self._saved = (_dup(self._owned, 1), _dup(self._owned, 2))
            out_read, out_write = _pipe(self._owned)
            err_read, err_write = _pipe(self._owned)
            stop = _pipe(self._owned)
            self._writes = (out_write, err_write)
            self._reader = _Reader({out_read: _OUT, err_read: _ERR}, stop)
            undo.pop_all()

    def __enter__(self) -> "_Capture":
        return self

    def run[T](self, call: Callable[[], T]) -> T:
        """Run `call` with fds 1 and 2 on the pipes' write ends and the sys streams over them, all restored afterwards."""
        out_stream, err_stream = _text_stream(1, _OUT, self._reader), _text_stream(2, _ERR, self._reader)
        stdout_before, stderr_before = sys.stdout, sys.stderr
        try:
            for fd, write_end in zip((1, 2), self._writes, strict=True):
                os.dup2(write_end, fd)
                _close(self._owned, write_end)
            sys.stdout, sys.stderr = out_stream, err_stream
            return call()
        finally:
            try:
                _flush_streams()
            finally:
                sys.stdout, sys.stderr = stdout_before, stderr_before
                for fd, duplicate in zip((1, 2), self._saved, strict=True):
                    os.dup2(duplicate, fd)
                out_stream.close()
                err_stream.close()

    def __exit__(
        self,
        kind: type[BaseException] | None,
        raised: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        try:
            self._reader.finish()
        finally:
            _close_all(self._owned)
        self.output = _output(self._reader.chunks)
        if raised is not None:
            _record(raised, self.output)


def captured[T](call: Callable[[], T]) -> Captured[T]:
    """Run `call` in this interpreter with fds 1 and 2 and sys.stdout and sys.stderr captured, restoring them afterwards.

    A call that raised propagates as itself, and output_of reads its Output. Once the call has ended, this blocks until
    fds 1 and 2 reach end of file; pytest-timeout is the one bound. A failure while capture sets up raises
    CaptureSetupError, after the same cleanup, and the call never runs.
    """
    _flush_streams()
    with _Capture() as capture:
        result = capture.run(call)
    return Captured(result, capture.output)


def output_of(exc: BaseException) -> Output:
    """The Output read while the call that raised `exc` ran; CaptureUnrecordedError for an `exc` captured never recorded."""
    stash: dict[str, object] = exc.__dict__
    output = stash.get(_OUTPUT_KEY)
    if not isinstance(output, Output):
        raise CaptureUnrecordedError(exc)
    return output
