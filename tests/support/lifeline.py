"""Child processes held, met and ended by pipes: every wait a test makes on a real process.

Design: the no-wall-clock design spec under docs/superpowers/specs/, the `tests/support/lifeline.py` module. Each wait
is an event on a pipe or FIFO, blocked on with no timeout: pytest-timeout is the one bound on a test that hangs. A
`Lifeline` is a pipe whose write end only the test holds, so a child reading its read end to end of file lives until
the test releases it. A `Witness` is a FIFO the test reads; every process that opens it to write is a holder, and its
end of file comes only when every holder has closed it. `Pids` kills, by pid, the pids children note in a file.

The child code is run as `python -c <code> <arguments>`. `HOLD` writes the ready line `ready` to fd 1 and then reads
the fd its first argument names to its end. `WITNESS` opens the FIFO its first argument names to write, writes the
mark `held` into it, writes the ready line and then holds on the fd its second argument names. `MEET` opens the FIFO
its first argument names for reading (`read`) or writing (`write`), as its second argument says; a FIFO's open blocks
until both ends are open, so it returns once the other side has opened it.
"""

import contextlib
import os
import signal
from pathlib import Path
from typing import Self

# The size of each read the helpers make.
CHUNK = 65536

HOLD = "import os, sys\nos.write(1, b'ready\\n')\nwhile os.read(int(sys.argv[1]), 65536):\n    pass\n"

WITNESS = (
    "import os, sys\n"
    "witness = os.open(sys.argv[1], os.O_WRONLY)\n"
    "os.write(witness, b'held')\n"
    "os.write(1, b'ready\\n')\n"
    "while os.read(int(sys.argv[2]), 65536):\n"
    "    pass\n"
)

MEET = "import os, sys\nos.open(sys.argv[1], os.O_RDONLY if sys.argv[2] == 'read' else os.O_WRONLY)\n"


class Lifeline:
    """A pipe whose write end only the test holds; a child reading its read end to EOF lives until release."""

    read_fd: int

    def __init__(self) -> None:
        self.read_fd, write_fd = os.pipe()
        self._write_fd: int | None = write_fd

    def release(self) -> None:
        """Close the write end; a second call does nothing."""
        if self._write_fd is not None:
            os.close(self._write_fd)
            self._write_fd = None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        """Release, then close the read end."""
        self.release()
        os.close(self.read_fd)


class Witness:
    """A FIFO the test reads; every process that opens it to write is a holder."""

    path: Path

    def __init__(self, path: Path) -> None:
        """Make the FIFO and open its read end without blocking."""
        self.path = path
        os.mkfifo(path)
        self._fd = os.open(path, os.O_RDONLY | os.O_NONBLOCK)

    def ended(self) -> bytes:
        """Called after every holder's ready line: block, with no deadline, until every holder has closed it."""
        os.set_blocking(self._fd, True)
        written = b""
        while chunk := os.read(self._fd, CHUNK):
            written += chunk
        return written

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        os.close(self._fd)


def ready(fd: int) -> bytes:
    """Block until a child writes one line on fd and return it; b"" when every writer closed first."""
    line = b""
    while not line.endswith(b"\n"):
        byte = os.read(fd, 1)
        if not byte:
            break
        line += byte
    return line


class Pids:
    """The pids children note in a file, killed by pid at teardown."""

    path: Path

    def __init__(self, path: Path) -> None:
        self.path = path

    def noted(self) -> list[int]:
        """The pids noted in the file, one word each; none when no child has written it."""
        if not self.path.exists():
            return []
        return [int(word) for word in self.path.read_text(encoding="utf-8").split()]

    def __enter__(self) -> Self:
        return self

    def __exit__(self, *exc: object) -> None:
        """SIGKILL each noted pid; a ProcessLookupError is passed over."""
        for pid in self.noted():
            with contextlib.suppress(ProcessLookupError):
                os.kill(pid, signal.SIGKILL)
