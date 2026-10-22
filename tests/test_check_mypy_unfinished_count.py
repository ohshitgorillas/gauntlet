# Copyright 2026 oh shit, gorillas!
"""Red tests for the count line of a mypy gate run whose checker could not finish.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "The count line of a run whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script without its extension and `finding(s)` and `file(s)` are printed as written whatever N and M are", and "A run whose checker could not finish prints the same count line, in the same shape, as the last line it prints, after what the checker reported; a line saying on how many files the checker could not finish, or that it gave no report the gate can read, is not a count line, and no gate prints one." The same paragraph: "A Python file the checker cannot read or cannot parse is a file the checker did not finish: the gate prints what the checker reported for that file and exits 2, whatever it found in the other files." The mypy gate is "Types", first bullet; its script is `gates/check_mypy.py`, so `<gate>` is `check_mypy`.

The documents spell the count line of an unfinished run as the same count line a finished run prints, whose M counts the Python files the gate takes, and the same paragraph's "counts them as M in its count line" names those files; so the last line is held to that shape with any N and with M the number of Python files given, the unfinished file among them. They do not spell the checker's report, so it is read only for the name of the file the checker did not finish, on a line printed before the count line, and, on that same line, what only the checker's report on that file can carry: for the file mypy cannot parse, the seeded line of its syntax error, line 3, as the first number after the name; for the file no one may read, the operating system's text for a denied read, `os.strerror(errno.EACCES)`. A command line or a list of the given paths that merely names the file carries neither. The documents name no stream, so stdout and stderr are written into one buffer, which keeps the order the run printed its lines in. Each companion file is one the gate alone would pass, or fail with a finding, placed before and after the unfinished file.

Each case id is a letter for the unfinished file, `p` for one mypy cannot parse and `r` for one it cannot read, then the layout: `a` for the file alone, `c` for a clean companion and `f` for a companion with one finding, `1` for the unfinished file first and `2` for it last. The ids and the test name are kept short so that pytest's one-line summary has room to name the exception a test fails with.
"""

import errno
import io
import os
import re
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

import pytest

from gates.check_mypy import main

GATE = "check_mypy"

UNFINISHED = 2

UNPARSEABLE = "count: int = 1\n\ndef broken(:\n"

SYNTAX_LINE = 3

PERMISSION_DENIED = os.strerror(errno.EACCES)

UNPARSEABLE_NAME = "broken.py"

UNREADABLE_NAME = "locked.py"

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

ONE_FINDING = 'first_value: int = "alpha"\n'

CASES = [
    pytest.param(UNPARSEABLE_NAME, None, True, id="pa"),
    pytest.param(UNPARSEABLE_NAME, CLEAN, True, id="pc1"),
    pytest.param(UNPARSEABLE_NAME, CLEAN, False, id="pc2"),
    pytest.param(UNPARSEABLE_NAME, ONE_FINDING, True, id="pf1"),
    pytest.param(UNPARSEABLE_NAME, ONE_FINDING, False, id="pf2"),
    pytest.param(UNREADABLE_NAME, None, True, id="ra"),
    pytest.param(UNREADABLE_NAME, CLEAN, True, id="rc1"),
    pytest.param(UNREADABLE_NAME, CLEAN, False, id="rc2"),
    pytest.param(UNREADABLE_NAME, ONE_FINDING, True, id="rf1"),
    pytest.param(UNREADABLE_NAME, ONE_FINDING, False, id="rf2"),
]


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _unfinished(tmp_path: Path, name: str) -> Path:
    """Return the file mypy cannot parse, or a well-typed file no one may read."""
    if name == UNPARSEABLE_NAME:
        return _seed(tmp_path, name, UNPARSEABLE)
    path = _seed(tmp_path, name, CLEAN)
    path.chmod(0o000)
    return path


def _layout(
    tmp_path: Path, unfinished: Path, companion: str | None, *, unfinished_first: bool
) -> list[Path]:
    """Return the unfinished file alone, or beside a companion file placed before or after it."""
    if companion is None:
        return [unfinished]
    other = _seed(tmp_path, "companion.py", companion)
    return [unfinished, other] if unfinished_first else [other, unfinished]


def _run(paths: list[Path]) -> tuple[int, list[str]]:
    """Run the gate with stdout and stderr in one buffer; return its exit status and every line it printed."""
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        status = main(paths)
    return status, buffer.getvalue().splitlines()


def _first_number(text: str) -> int | None:
    """Return the first run of decimal digits in `text`, read as a number, or None where `text` holds no digit."""
    digits = ""
    for character in text:
        if character in "0123456789":
            digits += character
        elif digits:
            break
    return int(digits) if digits else None


def _is_report(line: str, name: str) -> bool:
    """Whether `line` names `name` and carries what mypy's report on that file does: the syntax error's line as the first number after the name, or the text of a denied read."""
    if name not in line:
        return False
    if name == UNPARSEABLE_NAME:
        return _first_number(line.partition(name)[2]) == SYNTAX_LINE
    return PERMISSION_DENIED in line


def _outcome(
    status: int, lines: list[str], name: str, files: int
) -> tuple[int, bool, list[bool]]:
    """Return the exit status; whether mypy's report on `name` is on a line printed before the last; and, for the last line, as a list of at most one, whether it is the count line with any N and M as `files`."""
    reported = any(_is_report(line, name) for line in lines[:-1])
    count_line = re.compile(rf"{GATE}: \d+ finding\(s\) in {files} Python file\(s\)")
    shapes = [count_line.fullmatch(line) is not None for line in lines[-1:]]
    return status, reported, shapes


@pytest.mark.parametrize(("name", "companion", "unfinished_first"), CASES)
def test_end(
    tmp_path: Path, name: str, companion: str | None, *, unfinished_first: bool
) -> None:
    """A run with a file mypy cannot parse or read prints mypy's report on it, then ends on the finished run's count line, M counting every Python file given, and exits 2."""
    unfinished = _unfinished(tmp_path, name)
    paths = _layout(tmp_path, unfinished, companion, unfinished_first=unfinished_first)
    status, lines = _run(paths)

    assert _outcome(status, lines, name, len(paths)) == (UNFINISHED, True, [True])
