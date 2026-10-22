"""Red tests for the cast gate on a Python file its checker cannot parse.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "A Python file the
checker cannot read or cannot parse is a file the checker did not finish: the gate prints what the checker reported for
that file and exits 2, whatever it found in the other files." The same paragraph: "A gate exits 0 with no finding, 1
with one or more findings, and 2 when its checker could not finish." The banned name comes from "Types", third bullet:
"`typing.cast` is banned (ruff `TID251`)."

A file that is not valid Python syntax is a file the checker cannot parse. The documents name no stream, so stdout and
stderr are read together. The documents do not spell the checker's report, so a report is read only for the seeded file
name and, after it on the same line, the seeded line of its syntax error, in whatever form the gate prints them.

The test names are kept short so that pytest's one-line summary has room to name the exception a test fails with.
"""

from pathlib import Path

import pytest

from gates.check_cast import main

UNPARSEABLE = "def broken(:\n    pass\n"

UNPARSEABLE_ON_FIVE = "VALUE = 1\n\n\n\ndef broken(:\n    pass\n"

SYNTAX_LINE = 5

UNPARSEABLE_WITH_CAST = (
    "import typing\n\nvalue = typing.cast(int, 1)\n\ndef broken(:\n    pass\n"
)

DIRTY = "import typing\n\nvalue = typing.cast(int, 1)\n"

CLEAN = "VALUE = 1\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _lines(paths: list[Path], capsys: pytest.CaptureFixture[str]) -> list[str]:
    main(paths)
    captured = capsys.readouterr()
    return (captured.out + captured.err).splitlines()


def _first_number(text: str) -> int | None:
    """The first run of decimal digits in `text`, read as a number, or None where `text` holds no digit."""
    digits = ""
    for character in text:
        if character in "0123456789":
            digits += character
        elif digits:
            break
    return int(digits) if digits else None


def _lines_placing(name: str, line_number: int, lines: list[str]) -> int:
    """How many lines name `name` and carry `line_number` as the first number printed after that name."""
    return sum(
        1
        for line in lines
        if name in line and _first_number(line.partition(name)[2]) == line_number
    )


def test_broken_alone(tmp_path: Path) -> None:
    """A run over one file the checker cannot parse did not finish, so the gate exits 2, not 1 as for a finding."""
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE)

    assert main([broken]) == 2


def test_broken_clean(tmp_path: Path) -> None:
    """A clean file beside an unparseable one does not make the run finished: the gate exits 2, not 0."""
    clean = _seed(tmp_path, "clean.py", CLEAN)
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE)

    assert main([clean, broken]) == 2


def test_dirty_broken(tmp_path: Path) -> None:
    """A finding in another file listed first does not outrank the unfinished file: the gate exits 2, not 1."""
    dirty = _seed(tmp_path, "dirty.py", DIRTY)
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE)

    assert main([dirty, broken]) == 2


def test_broken_dirty(tmp_path: Path) -> None:
    """A finding in another file listed last does not outrank the unfinished file: the gate exits 2, not 1."""
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE)
    dirty = _seed(tmp_path, "dirty.py", DIRTY)

    assert main([broken, dirty]) == 2


def test_broken_cast(tmp_path: Path) -> None:
    """A file the checker cannot parse is unfinished even where it also holds a use of `typing.cast`: the gate exits 2."""
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE_WITH_CAST)

    assert main([broken]) == 2


def test_broken_shown(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """The gate prints what the checker reported for the unparseable file, so a line names that file and its error's line.

    A clean file sits beside it, so a gate that prints nothing for the unfinished file names no file at all, and a gate
    that drops the checker's report for a line of its own naming the file does not place the error on its seeded line.
    """
    clean = _seed(tmp_path, "clean.py", CLEAN)
    broken = _seed(tmp_path, "broken.py", UNPARSEABLE_ON_FIVE)

    assert (
        _lines_placing("broken.py", SYNTAX_LINE, _lines([clean, broken], capsys)) >= 1
    )
