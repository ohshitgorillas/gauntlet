"""In-process capture of everything a call writes to file descriptors 1 and 2 and to sys.stdout and sys.stderr."""

import io
import os
import sys
import tempfile
from collections.abc import Callable

_CAPTURED_FDS = (1, 2)


class Captured[T]:
    """What `captured` saw: the call's return value and every output line, in the order written."""

    def __init__(self, result: T, lines: list[str]) -> None:
        self._result = result
        self._lines = lines

    @property
    def result(self) -> T:
        return self._result

    @property
    def lines(self) -> list[str]:
        return list(self._lines)


def _flush_streams() -> None:
    for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
        if stream is not None:
            stream.flush()


def captured[T](call: Callable[[], T]) -> Captured[T]:
    """Run `call` in this interpreter with fds 1 and 2 and sys.stdout and sys.stderr captured, restoring them afterwards."""
    with tempfile.TemporaryFile() as sink:
        _flush_streams()
        saved_fds = [os.dup(fd) for fd in _CAPTURED_FDS]
        saved_stdout, saved_stderr = sys.stdout, sys.stderr
        wrapper = io.TextIOWrapper(
            open(os.dup(sink.fileno()), "wb", buffering=0), encoding="utf-8", write_through=True
        )
        try:
            for fd in _CAPTURED_FDS:
                os.dup2(sink.fileno(), fd)
            sys.stdout = sys.stderr = wrapper
            result = call()
        finally:
            _flush_streams()
            sys.stdout, sys.stderr = saved_stdout, saved_stderr
            for fd, saved in zip(_CAPTURED_FDS, saved_fds, strict=True):
                os.dup2(saved, fd)
                os.close(saved)
            wrapper.close()
        sink.seek(0)
        lines = sink.read().decode("utf-8").splitlines(keepends=True)
    return Captured(result, lines)
