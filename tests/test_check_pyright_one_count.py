"""Red tests for the one line that counts files in a pyright gate run whose checker could not finish.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "The count line of a run
whose checker finished reads `<gate>: N finding(s) in M Python file(s)`", and "A run whose checker could not finish
prints the same count line, in the same shape, as the last line it prints, after what the checker reported; a line
saying on how many files the checker could not finish, or that it gave no report the gate can read, is not a count
line, and no gate prints one." The same paragraph: "A Python file the checker cannot read or cannot parse is a file the
checker did not finish". The pyright gate is "Types", second bullet; its script is `gates/check_pyright.py`, so
`<gate>` is `check_pyright`.

The documents do not spell the line no gate prints, so it is held by what makes it that line: a number of files. A line
counts files when it holds a number followed by `file`, `files` or `file(s)`, with `Python` between them or not. The
count line is one such line, so an unfinished run prints exactly one, and it is the last line, in the count line's
shape. stdout and stderr are written into one buffer, since the documents name no stream. Each companion file is one
the gate alone would pass or fail with a finding, placed before and after the unfinished file. The ids are kept short
so that pytest's one-line summary has room to name the exception a test fails with.
"""

import io
import re
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from gates.check_pyright import main

GATE = "check_pyright"

UNFINISHED = 2

COUNT_LINE_SHAPE = re.compile(rf"{GATE}: \d+ finding\(s\) in \d+ Python file\(s\)")

FILE_COUNT = re.compile(r"\b\d+\s+(?:Python\s+)?file(?:s|\(s\))?(?!\w)", re.IGNORECASE)

UNPARSEABLE = "def broken(:\n    return\n"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

ONE_FINDING = 'first_value: int = "alpha"\n'

LAYOUTS = [
    pytest.param(None, True, id="a"),
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


def _counts(lines: list[str]) -> int:
    """How many printed lines count files."""
    return sum(1 for line in lines if FILE_COUNT.search(line) is not None)


def _shapes(lines: list[str]) -> list[bool]:
    """For the last printed line, as a list of at most one, whether it is in the count line's shape."""
    return [COUNT_LINE_SHAPE.fullmatch(line) is not None for line in lines[-1:]]


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unparsed(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """A run with a file pyright cannot parse counts files on one line only, the count line it ends on."""
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE)
    status, lines = _run(
        _layout(tmp_path, broken, companion, broken_first=broken_first)
    )

    assert (status, _counts(lines), _shapes(lines)) == (UNFINISHED, 1, [True])


@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_unread(tmp_path: Path, companion: str | None, *, broken_first: bool) -> None:
    """A run with a file pyright cannot read counts files on one line only, the count line it ends on."""
    broken = _seed(tmp_path, "locked.py", CLEAN)
    broken.chmod(0o000)
    status, lines = _run(
        _layout(tmp_path, broken, companion, broken_first=broken_first)
    )

    assert (status, _counts(lines), _shapes(lines)) == (UNFINISHED, 1, [True])
