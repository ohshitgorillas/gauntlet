"""Red tests for how a cast gate run whose checker did not finish on some file ends.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: a gate "exits 2 when its
checker could not finish" and "prints its count line on every run"; "The count line of a run whose checker finished
reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script without its extension";
"A run whose checker could not finish prints the same count line, in the same shape, as the last line it prints, after
what the checker reported; a line saying on how many files the checker could not finish, or that it gave no report the
gate can read, is not a count line, and no gate prints one."; and "A Python file the checker cannot read or cannot parse
is a file the checker did not finish: the gate prints what the checker reported for that file and exits 2, whatever it
found in the other files." The banned name comes from "Types", third bullet: "`typing.cast` is banned (ruff `TID251`)."
The gate script is the module `gates.check_cast`, so `<gate>` is `check_cast`.

The documents spell the count line of an unfinished run as the same count line a finished run prints, whose M counts the
Python files the gate takes, and the same paragraph's "counts them as M in its count line" names those files; so the
last line is held to that shape with any N and with M the number of Python files given, the unfinished file among them.
They do not spell the line no gate prints, so it is held by what makes it that line: a number of files. A
line counts files when it holds a number followed by `file`, `files` or `file(s)`, with `Python` between them or not; the
count line is one such line, so an unfinished run prints exactly one. They do not spell the checker's report either, so
a report is read only for the seeded file name and, on the same line, what only the checker's report on that file can
carry: for a syntax error, the seeded line of that error as the first number after the name; for a file no one may read,
the operating system's text for a denied read, `os.strerror(errno.EACCES)`, which no line of the gate's own that merely
names the file carries. The documents name no stream, so stdout and stderr go to one buffer while the gate
runs, which keeps the order the run printed its lines in. Each companion file is one the gate alone would pass, or fail
with one finding, placed before and after the unfinished file.

The test names and ids are kept short so that pytest's one-line summary has room to name the exception a test fails
with.
"""

import contextlib
import errno
import io
import os
import re
from collections.abc import Callable
from pathlib import Path

import pytest

from gates.check_cast import main

GATE = "check_cast"

UNFINISHED = 2

PERMISSION_DENIED = os.strerror(errno.EACCES)

FILE_COUNT = re.compile(r"\b\d+\s+(?:Python\s+)?file(?:s|\(s\))?(?!\w)", re.IGNORECASE)

BROKEN = "broken.py"

LOCKED = "locked.py"

UNPARSEABLE_ON_FIVE = "VALUE = 1\n\n\n\ndef broken(:\n    pass\n"

SYNTAX_LINE = 5

DIRTY = "import typing\n\nvalue = typing.cast(int, 1)\n"

CLEAN = "VALUE = 1\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _broken(tmp_path: Path) -> Path:
    """A file the checker cannot parse, its syntax error on line 5."""
    return _seed(tmp_path, BROKEN, UNPARSEABLE_ON_FIVE)


def _locked(tmp_path: Path) -> Path:
    """A file the checker cannot read: no one may read it."""
    locked = _seed(tmp_path, LOCKED, CLEAN)
    locked.chmod(0o000)
    return locked


def _syntax_alone(tmp_path: Path) -> list[Path]:
    return [_broken(tmp_path)]


def _clean_then_syntax(tmp_path: Path) -> list[Path]:
    return [_seed(tmp_path, "clean.py", CLEAN), _broken(tmp_path)]


def _syntax_then_clean(tmp_path: Path) -> list[Path]:
    return [_broken(tmp_path), _seed(tmp_path, "clean.py", CLEAN)]


def _dirty_then_syntax(tmp_path: Path) -> list[Path]:
    return [_seed(tmp_path, "dirty.py", DIRTY), _broken(tmp_path)]


def _syntax_then_dirty(tmp_path: Path) -> list[Path]:
    return [_broken(tmp_path), _seed(tmp_path, "dirty.py", DIRTY)]


def _locked_alone(tmp_path: Path) -> list[Path]:
    return [_locked(tmp_path)]


def _dirty_then_locked(tmp_path: Path) -> list[Path]:
    return [_seed(tmp_path, "dirty.py", DIRTY), _locked(tmp_path)]


SEEDS = [
    pytest.param(_syntax_alone, BROKEN, SYNTAX_LINE, id="s"),
    pytest.param(_clean_then_syntax, BROKEN, SYNTAX_LINE, id="cs"),
    pytest.param(_syntax_then_clean, BROKEN, SYNTAX_LINE, id="sc"),
    pytest.param(_dirty_then_syntax, BROKEN, SYNTAX_LINE, id="ds"),
    pytest.param(_syntax_then_dirty, BROKEN, SYNTAX_LINE, id="sd"),
    pytest.param(_locked_alone, LOCKED, None, id="p"),
    pytest.param(_dirty_then_locked, LOCKED, None, id="dp"),
]

Seed = Callable[[Path], list[Path]]


def _run(paths: list[Path]) -> tuple[int, list[str]]:
    """Run the gate with stdout and stderr in one buffer; return its exit status and every line it printed."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        status = main(paths)
    return status, buffer.getvalue().splitlines()


def _shapes(lines: list[str], files: int) -> list[bool]:
    """For the last printed line, as a list of at most one, whether it is the count line with any N and M as `files`."""
    count_line = re.compile(rf"{GATE}: \d+ finding\(s\) in {files} Python file\(s\)")
    return [count_line.fullmatch(line) is not None for line in lines[-1:]]


def _counts(lines: list[str]) -> int:
    """How many printed lines count files."""
    return sum(1 for line in lines if FILE_COUNT.search(line) is not None)


def _first_number(text: str) -> int | None:
    """The first run of decimal digits in `text`, read as a number, or None where `text` holds no digit."""
    digits = ""
    for character in text:
        if character in "0123456789":
            digits += character
        elif digits:
            break
    return int(digits) if digits else None


def _reports(name: str, line_number: int | None, lines: list[str]) -> int:
    """How many lines name `name`, carrying `line_number`, where one is given, as the first number after that name, and
    the operating system's text for a denied read where none is."""
    return sum(
        1
        for line in lines
        if name in line
        and (
            PERMISSION_DENIED in line
            if line_number is None
            else _first_number(line.partition(name)[2]) == line_number
        )
    )


@pytest.mark.parametrize(("seed", "name", "line_number"), SEEDS)
def test_last(tmp_path: Path, seed: Seed, name: str, line_number: int | None) -> None:
    """An unfinished run exits 2 and the last line it prints is the count line, M counting every Python file given."""
    del name, line_number
    paths = seed(tmp_path)
    status, lines = _run(paths)

    assert (status, _shapes(lines, len(paths))) == (UNFINISHED, [True])


@pytest.mark.parametrize(("seed", "name", "line_number"), SEEDS)
def test_one(tmp_path: Path, seed: Seed, name: str, line_number: int | None) -> None:
    """An unfinished run exits 2 and counts files on one line only, the count line it ends on, never on a line of its own."""
    del name, line_number
    paths = seed(tmp_path)
    status, lines = _run(paths)

    assert (status, _counts(lines), _shapes(lines, len(paths))) == (UNFINISHED, 1, [True])


@pytest.mark.parametrize(("seed", "name", "line_number"), SEEDS)
def test_before(tmp_path: Path, seed: Seed, name: str, line_number: int | None) -> None:
    """The checker's report for the unfinished file comes before the count line that ends the run, and the run exits 2."""
    paths = seed(tmp_path)
    status, lines = _run(paths)

    assert (status, _reports(name, line_number, lines[:-1]) >= 1, _shapes(lines, len(paths))) == (
        UNFINISHED,
        True,
        [True],
    )
