"""Red tests for the pyright gate on a file whose parse raises a warning.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates":
a warning raised while a gate parses a Python file is an error for that parse,
so its file is a file the checker did not finish: the gate prints the warning
as the checker's report and exits 2, prints its count line last in the shape
`<gate>: N finding(s) in M Python file(s)`, and exits 2 whatever it found in
the other files. The pinned Python is 3.12.

Each seeded source parses under the 3.12 grammar but makes the parse raise a
SyntaxWarning. The gate runs with warnings recorded and never printed around
it, so only what the gate prints itself reaches the captured output.
"""

import ast
import re
import warnings
from pathlib import Path

import pytest

from gates.check_pyright import main

INVALID_ESCAPE = 'PATTERN = "\\d"\n'

NUMBER_BEFORE_KEYWORD = "VALUE = 1if True else 2\n"

MISSING_PARAMETER_TYPE = "def double(value) -> int:\n    return value * 2\n"

PINNED = (3, 12)

ONE_FILE_COUNT_LINE = re.compile(r"check_pyright: \d+ finding\(s\) in 1 Python file\(s\)")

SOURCES = [
    pytest.param(INVALID_ESCAPE, id="invalid-escape"),
    pytest.param(NUMBER_BEFORE_KEYWORD, id="number-keyword"),
]


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _run(paths: list[Path]) -> int:
    with warnings.catch_warnings(record=True):
        warnings.simplefilter("always")
        return main(paths)


def _parse_warnings(path: Path) -> list[str]:
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        ast.parse(path.read_text(encoding="utf-8"), filename=str(path), feature_version=PINNED)
    return [str(warning.message) for warning in caught]


@pytest.mark.parametrize("source", SOURCES)
def test_parse_warning_exits_two(tmp_path: Path, source: str) -> None:
    """A file whose parse raises a warning is one the checker did not finish."""
    path = _seed(tmp_path, "seeded.py", source)

    assert _run([path]) == 2


@pytest.mark.parametrize("source", SOURCES)
def test_parse_warning_printed_as_report(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    """The gate prints the warning the parse raised as the checker's report."""
    path = _seed(tmp_path, "seeded.py", source)
    expected = _parse_warnings(path)

    _run([path])
    captured = capsys.readouterr()
    printed = captured.out + captured.err

    assert [message in printed for message in expected] == [True]


@pytest.mark.parametrize("source", SOURCES)
def test_parse_warning_count_line_last(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    """The warning comes first, then one count line, counting the one file given, last."""
    path = _seed(tmp_path, "seeded.py", source)
    expected = _parse_warnings(path)

    _run([path])
    lines = capsys.readouterr().out.rstrip("\n").split("\n")
    before = "\n".join(lines[:-1])
    counts = [line for line in lines if ONE_FILE_COUNT_LINE.fullmatch(line)]

    assert ([message in before for message in expected], counts) == ([True], [lines[-1]])


@pytest.mark.parametrize("source", SOURCES)
def test_parse_warning_exits_two_beside_finding(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], source: str
) -> None:
    """A warned file makes the run exit 2, and the other file's findings still print."""
    warned = _seed(tmp_path, "seeded.py", source)
    flawed = _seed(tmp_path, "flawed.py", MISSING_PARAMETER_TYPE)

    alone_code = _run([flawed])
    alone_findings = capsys.readouterr().out.rstrip("\n").split("\n")[:-1]
    mixed_code = _run([flawed, warned])
    mixed_lines = capsys.readouterr().out.rstrip("\n").split("\n")
    printed = [line in mixed_lines for line in alone_findings]

    assert (alone_code, len(printed) > 0, all(printed), mixed_code) == (1, True, True, 2)
