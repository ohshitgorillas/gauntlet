# Copyright 2026 oh shit, gorillas!
"""Red tests for the descriptors a checker process holds: those `Command.pass_fds` names stay open, every other is closed.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "checker.py: running a checker process",
which gives `Command(..., pass_fds: tuple[int, ...] = ())` and `def run(command: Command) -> Completed`; the behavior
held here is the owner's: `run` leaves open in the checker the file descriptors the Command's pass_fds names, and closes
every other descriptor of the running process.

Each descriptor here is opened by the test on a file of its own under `tmp_path`. A named descriptor is opened
non-inheritable, so only `pass_fds` can carry it into the checker; an unnamed one is made inheritable, so only `run`
closing it keeps it out. The checker is a Python child that probes each descriptor number it is given: it prints `open`
where that number holds the very file the test opened, by device and inode, and `closed` where the number holds nothing
or another file, so a number the child's own interpreter reuses is never read as the test's descriptor kept open.
Whether the checker's standard input, output and error count among "every other descriptor" the documents do not say,
so nothing is claimed about descriptors 0, 1 and 2.
"""

import contextlib
import os
import sys
from pathlib import Path

from gates.core.checker import Command, run

OPEN = "open"

CLOSED = "closed"

PROBE = (
    "import os, sys\n"
    "words = sys.argv[1:]\n"
    "verdicts = []\n"
    "for at in range(0, len(words), 3):\n"
    "    fd, device, inode = (int(word) for word in words[at:at + 3])\n"
    "    try:\n"
    "        seen = os.fstat(fd)\n"
    "    except OSError:\n"
    "        verdicts.append('closed')\n"
    "        continue\n"
    "    verdicts.append('open' if (seen.st_dev, seen.st_ino) == (device, inode) else 'closed')\n"
    "sys.stdout.write(' '.join(verdicts))\n"
)


def _open(
    stack: contextlib.ExitStack[bool | None],
    tmp_path: Path,
    name: str,
    *,
    inheritable: bool,
) -> int:
    """Open a file of the test's own read-only, closed again when the stack closes."""
    path = tmp_path / name
    path.write_text(name, encoding="utf-8")
    fd = os.open(path, os.O_RDONLY)
    stack.callback(os.close, fd)
    os.set_inheritable(fd, inheritable)
    return fd


def _identity(fd: int) -> tuple[str, str, str]:
    """Return the descriptor's number, then the device and inode of the file it holds, as the probe reads them."""
    status = os.fstat(fd)
    return (str(fd), str(status.st_dev), str(status.st_ino))


def _verdicts(
    tmp_path: Path, probed: tuple[int, ...], named: tuple[int, ...]
) -> list[str]:
    """Run the probe through `run` with `pass_fds=named`, and give back its verdict on each probed descriptor."""
    arguments = [word for fd in probed for word in _identity(fd)]
    command = Command(
        argv=(sys.executable, "-I", "-c", PROBE, *arguments),
        cwd=tmp_path,
        pass_fds=named,
    )
    return run(command).stdout.split()


def test_kept(tmp_path: Path) -> None:
    """A descriptor pass_fds names is open in the checker, holding the same file, though it is not inheritable."""
    with contextlib.ExitStack() as stack:
        named = _open(stack, tmp_path, "named.txt", inheritable=False)
        verdicts = _verdicts(tmp_path, (named,), (named,))

    assert verdicts == [OPEN]


def test_both(tmp_path: Path) -> None:
    """Every descriptor pass_fds names is open in the checker, the second as much as the first."""
    with contextlib.ExitStack() as stack:
        first = _open(stack, tmp_path, "first.txt", inheritable=False)
        second = _open(stack, tmp_path, "second.txt", inheritable=False)
        verdicts = _verdicts(tmp_path, (first, second), (first, second))

    assert verdicts == [OPEN, OPEN]


def test_closed(tmp_path: Path) -> None:
    """With pass_fds empty, a descriptor of the caller's that is inheritable is closed in the checker."""
    with contextlib.ExitStack() as stack:
        other = _open(stack, tmp_path, "other.txt", inheritable=True)
        verdicts = _verdicts(tmp_path, (other,), ())

    assert verdicts == [CLOSED]


def test_mixed(tmp_path: Path) -> None:
    """With pass_fds naming one descriptor, that one is open and an inheritable one it does not name is closed."""
    with contextlib.ExitStack() as stack:
        named = _open(stack, tmp_path, "named.txt", inheritable=False)
        other = _open(stack, tmp_path, "other.txt", inheritable=True)
        verdicts = _verdicts(tmp_path, (named, other), (named,))

    assert verdicts == [OPEN, CLOSED]
