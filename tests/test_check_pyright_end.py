"""Red tests for the count line of a pyright gate run whose checker could not finish.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "The count line of a run
whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script
without its extension and `finding(s)` and `file(s)` are printed as written whatever N and M are", and "A run whose
checker could not finish prints the same count line, in the same shape, as the last line it prints, after what the
checker reported; a line saying on how many files the checker could not finish is not a count line." The same
paragraph: "A Python file the checker cannot read or cannot parse is a file the checker did not finish: the gate prints
what the checker reported for that file and exits 2". The pyright gate is "Types", second bullet; its script is
`gates/check_pyright.py`, so `<gate>` is `check_pyright`.

The documents spell the count line of an unfinished run only by its shape, so the last line is held to that shape with
any N and M. They do not spell the checker's report, so what pyright reported is taken from pyright itself, run on the
same file: the message of each diagnostic its text output gives for that file, with the rule name it appends dropped,
since "Gate code" has a finding carry "the checker's whole message". Each such message, and the file's name, must be
printed before the count line, for the file pyright cannot parse and for the file it cannot read alike; pyright must
report at least one message on the file it cannot parse. The documents name no stream, so stdout and stderr are written
into one buffer, which keeps the order the run printed its lines in. Each companion file is one the gate alone would pass or
fail with a finding, placed before and after the unfinished file. The file name, test names and ids are kept short so
that pytest's one-line summary has room to name the exception a test fails with.
"""

import io
import re
import subprocess
import sys
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from gates.check_pyright import main

GATE = "check_pyright"

UNFINISHED = 2

COUNT_LINE_SHAPE = re.compile(rf"{GATE}: \d+ finding\(s\) in \d+ Python file\(s\)")

UNPARSEABLE = "def broken(:\n    return\n"

UNPARSEABLE_NAME = "broken.py"

UNREADABLE_NAME = "locked.py"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

ONE_FINDING = 'first_value: int = "alpha"\n'

LAYOUTS = [
    pytest.param(None, True, id="alone"),
    pytest.param(CLEAN, True, id="c1"),
    pytest.param(CLEAN, False, id="c2"),
    pytest.param(ONE_FINDING, True, id="f1"),
    pytest.param(ONE_FINDING, False, id="f2"),
]


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _layout(
    tmp_path: Path, broken: Path, companion: str | None, *, broken_first: bool
) -> list[Path]:
    """The unfinished file alone, or beside a companion file placed before or after it."""
    if companion is None:
        return [broken]
    other = _seed(tmp_path, "companion.py", companion)
    return [broken, other] if broken_first else [other, broken]


def _run(paths: list[Path]) -> tuple[int, list[str]]:
    """Run the gate with stdout and stderr in one buffer; return its exit status and every line it printed."""
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        status = main(paths)
    return status, buffer.getvalue().splitlines()


def _unparsed(
    tmp_path: Path, companion: str | None, *, broken_first: bool
) -> tuple[int, list[str]]:
    broken = _seed(tmp_path, UNPARSEABLE_NAME, UNPARSEABLE)
    return _run(_layout(tmp_path, broken, companion, broken_first=broken_first))


def _unread(
    tmp_path: Path, companion: str | None, *, broken_first: bool
) -> tuple[int, list[str]]:
    broken = _seed(tmp_path, UNREADABLE_NAME, CLEAN)
    broken.chmod(0o000)
    return _run(_layout(tmp_path, broken, companion, broken_first=broken_first))


def _shapes(lines: list[str]) -> list[bool]:
    """For the last printed line, as a list of at most one, whether it is in the count line's shape."""
    return [COUNT_LINE_SHAPE.fullmatch(line) is not None for line in lines[-1:]]


def _pyright_messages(path: Path) -> list[str]:
    """The message of each diagnostic pyright itself reports on one file, run on it alone, its rule name dropped."""
    command = [sys.executable, "-m", "pyright", str(path)]
    run = subprocess.run(command, capture_output=True, text=True, check=False)
    prefix = f"{path}:"
    messages: list[str] = []
    for line in run.stdout.splitlines():
        located = line.strip()
        if located.startswith(prefix):
            _, _, diagnostic = located.partition(" - ")
            _, _, message = diagnostic.partition(": ")
            messages.append(message.split(" (report")[0])
    return messages


def _missing(messages: list[str], lines: list[str]) -> list[str]:
    """Each message not found among the lines printed before the last one."""
    printed = "\n".join(lines[:-1])
    return [message for message in messages if message not in printed]


def _named(name: str, lines: list[str]) -> bool:
    """Whether the file's name appears among the lines printed before the last one."""
    return name in "\n".join(lines[:-1])


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unparsed(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """A run with a file pyright cannot parse exits 2 and ends on a count line in the finished run's shape."""
    status, lines = _unparsed(tmp_path, companion, broken_first=broken_first)

    assert (status, _shapes(lines)) == (UNFINISHED, [True])


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unread(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """A run with a file pyright cannot read exits 2 and ends on a count line in the finished run's shape."""
    status, lines = _unread(tmp_path, companion, broken_first=broken_first)

    assert (status, _shapes(lines)) == (UNFINISHED, [True])


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_report(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """What pyright reported on the unparsed file comes before the count line the run ends on."""
    status, lines = _unparsed(tmp_path, companion, broken_first=broken_first)
    reported = _pyright_messages(tmp_path / UNPARSEABLE_NAME)
    report = (
        len(reported) > 0,
        _named(UNPARSEABLE_NAME, lines),
        _missing(reported, lines),
    )

    assert (status, report, _shapes(lines)) == (UNFINISHED, (True, True, []), [True])


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unread_report(
    tmp_path: Path, companion: str | None, *, broken_first: bool
) -> None:
    """What pyright reported on the unread file comes before the count line the run ends on."""
    status, lines = _unread(tmp_path, companion, broken_first=broken_first)
    reported = _pyright_messages(tmp_path / UNREADABLE_NAME)
    report = (_named(UNREADABLE_NAME, lines), _missing(reported, lines))

    assert (status, report, _shapes(lines)) == (UNFINISHED, (True, []), [True])
