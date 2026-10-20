"""In-process capture of everything a call writes to file descriptors 1 and 2 and to sys.stdout and sys.stderr.

Fds 1 and 2 are each pointed at their own bound Unix datagram socket, both connected to one receiving socket. Every
write to either fd, from this process or a child that inherits it, is one datagram queued on the receiver in the order
written and tagged with its sender's address, so the receiver knows both which fd wrote and in what order. A reader
thread drains the queue while the call runs, so the receive buffer holds only what has not been read yet. On macOS a
write that finds the 8 MiB queue full fails with ENOBUFS instead of waiting, and one write may carry at most 1 MiB.
"""

import bisect
import io
import os
import select
import socket
import sys
import tempfile
import threading
from collections.abc import Callable

_OUT, _ERR = "out", "err"
_CAPTURED = ((1, _OUT), (2, _ERR))
_DATAGRAM_LIMIT = 1 << 20
_RECEIVE_BUFFER = 1 << 23


class Captured[T]:
    """What `captured` saw: the call's return value and the lines it wrote to fd 1, to fd 2, and to both in the order written."""

    def __init__(self, result: T, out: list[str], err: list[str], merged: list[str]) -> None:
        self._result = result
        self._out = out
        self._err = err
        self._merged = merged

    @property
    def result(self) -> T:
        return self._result

    @property
    def out(self) -> list[str]:
        return list(self._out)

    @property
    def err(self) -> list[str]:
        return list(self._err)

    @property
    def merged(self) -> list[str]:
        return list(self._merged)


class _Reader:
    """Drains the receiving socket on its own thread until told to stop, keeping each datagram and the fd that sent it."""

    def __init__(self, sink: socket.socket, sources: dict[str, str]) -> None:
        self._sink = sink
        self._sources = sources
        self._stop_read, self._stop_write = os.pipe()
        self.chunks: list[tuple[str, bytes]] = []
        self.error: BaseException | None = None
        self._thread = threading.Thread(target=self._run, name="captured-reader")
        self._thread.start()

    def _run(self) -> None:
        try:
            poller = select.poll()
            poller.register(self._sink.fileno(), select.POLLIN)
            poller.register(self._stop_read, select.POLLIN)
            while True:
                ready = {fd for fd, _ in poller.poll()}
                if self._sink.fileno() in ready:
                    self._receive()
                elif self._stop_read in ready:
                    return
        except BaseException as error:
            self.error = error

    def _receive(self) -> None:
        received: tuple[bytes, list[tuple[int, int, bytes]], int, object] = self._sink.recvmsg(_DATAGRAM_LIMIT)
        data, _, flags, address = received
        if flags & socket.MSG_TRUNC or not isinstance(address, str) or address not in self._sources:
            raise OSError(f"captured: a datagram from {address!r} was cut short or came from an unknown sender")
        self.chunks.append((self._sources[address], data))

    def stop(self) -> None:
        """Every write is already queued; the reader empties the queue, then sees the stop and ends."""
        try:
            os.write(self._stop_write, b"\0")
            self._thread.join()
        finally:
            os.close(self._stop_read)
            os.close(self._stop_write)
        if self.error is not None:
            raise self.error


def _lines(chunks: list[tuple[str, bytes]], source: str) -> list[tuple[int, str]]:
    """The source's lines, each with the index in `chunks` of the datagram its first byte arrived in."""
    starts: list[int] = []
    indices: list[int] = []
    data = bytearray()
    for index, (sender, chunk) in enumerate(chunks):
        if sender == source:
            starts.append(len(data))
            indices.append(index)
            data += chunk
    lines: list[tuple[int, str]] = []
    offset = 0
    for line in bytes(data).splitlines(keepends=True):
        lines.append((indices[bisect.bisect_right(starts, offset) - 1], line.decode("utf-8")))
        offset += len(line)
    return lines


def _started(line: tuple[int, str]) -> int:
    return line[0]


def _flush_streams() -> None:
    for stream in (sys.stdout, sys.stderr, sys.__stdout__, sys.__stderr__):
        if stream is not None:
            stream.flush()


def _sender(directory: str, name: str, sink_path: str) -> socket.socket:
    sender = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    sender.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, _DATAGRAM_LIMIT)
    sender.bind(os.path.join(directory, name))
    sender.connect(sink_path)
    return sender


def _text_stream(sender: socket.socket) -> io.TextIOWrapper:
    return io.TextIOWrapper(open(os.dup(sender.fileno()), "wb", buffering=0), encoding="utf-8", write_through=True)


def captured[T](call: Callable[[], T]) -> Captured[T]:
    """Run `call` in this interpreter with fds 1 and 2 and sys.stdout and sys.stderr captured, restoring them afterwards."""
    with tempfile.TemporaryDirectory() as directory, socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as sink:
        sink_path = os.path.join(directory, "sink")
        sink.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, _RECEIVE_BUFFER)
        sink.bind(sink_path)
        senders = {name: _sender(directory, name, sink_path) for _, name in _CAPTURED}
        reader = _Reader(sink, {sender.getsockname(): name for name, sender in senders.items()})
        try:
            _flush_streams()
            saved_fds = [os.dup(fd) for fd, _ in _CAPTURED]
            saved_stdout, saved_stderr = sys.stdout, sys.stderr
            out_stream, err_stream = _text_stream(senders[_OUT]), _text_stream(senders[_ERR])
            try:
                for fd, name in _CAPTURED:
                    os.dup2(senders[name].fileno(), fd)
                sys.stdout, sys.stderr = out_stream, err_stream
                result = call()
            finally:
                _flush_streams()
                sys.stdout, sys.stderr = saved_stdout, saved_stderr
                for (fd, _), saved in zip(_CAPTURED, saved_fds, strict=True):
                    os.dup2(saved, fd)
                    os.close(saved)
                out_stream.close()
                err_stream.close()
        finally:
            try:
                reader.stop()
            finally:
                for sender in senders.values():
                    sender.close()
    out, err = _lines(reader.chunks, _OUT), _lines(reader.chunks, _ERR)
    merged = [line for _, line in sorted(out + err, key=_started)]
    return Captured(result, [line for _, line in out], [line for _, line in err], merged)
