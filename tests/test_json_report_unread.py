"""Red tests for what a gate prints when its checker gives no report the gate can read.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "A gate exits 0 with no
finding, 1 with one or more findings, and 2 when its checker could not finish; it prints each finding on its own line and
prints its count line on every run. The count line of a run whose checker finished reads `<gate>: N finding(s) in M
Python file(s)`, where `<gate>` is the name of the gate script without its extension and `finding(s)` and `file(s)` are
printed as written whatever N and M are, and it is the last line the run prints. A run whose checker could not finish
prints the same count line, in the same shape, as the last line it prints, after what the checker reported; a line
saying on how many files the checker could not finish, or that it gave no report the gate can read, is not a count line,
and no gate prints one."

The documents spell the count line of an unfinished run only by its shape, so N is held to any number and M to the
number of Python files the gate was given. They name no stream, so stdout and stderr are written into one buffer, which
keeps the order the lines were printed in. What the checker reported is its whole output, each of its lines printed as a
line of its own, in order and before the count line.
"""

import io
import re
from contextlib import redirect_stderr, redirect_stdout

import pytest

from gates.json_report import UnfinishedError, print_unread

CHECKER_STATUS = 3

GATES = [
    pytest.param("check_pyright", "pyright", id="pr"),
    pytest.param("check_mypy", "mypy", id="my"),
]

FILE_COUNTS = [
    pytest.param(1, id="one"),
    pytest.param(3, id="three"),
    pytest.param(12, id="twelve"),
]

OUTPUTS = [
    pytest.param("alpha failed hard\nbeta failed too\n", id="nl"),
    pytest.param("alpha failed hard\nbeta failed too", id="bare"),
    pytest.param("alpha failed hard\n\n    beta indented here\ngamma last line\n", id="blank"),
    pytest.param("only one line here", id="sole"),
]


def _printed(gate: str, checker: str, output: str, files: int) -> list[str]:
    """Run print_unread with stdout and stderr in one buffer; return every line it printed."""
    buffer = io.StringIO()
    unread = UnfinishedError(CHECKER_STATUS, output)
    with redirect_stdout(buffer), redirect_stderr(buffer):
        print_unread(gate, checker, unread, files)
    return buffer.getvalue().splitlines()


def _count_shape(gate: str, files: int) -> re.Pattern[str]:
    return re.compile(rf"{re.escape(gate)}: \d+ finding\(s\) in {files} Python file\(s\)")


def _last_is_count(lines: list[str], gate: str, files: int) -> list[bool]:
    """For the last printed line, as a list of at most one, whether it is the count line of this gate and file count."""
    shape = _count_shape(gate, files)
    return [shape.fullmatch(line) is not None for line in lines[-1:]]


def _framed(lines: list[str]) -> str:
    """Lines joined with a line break before, between and after each, so that a match is a match of whole lines."""
    return "\n" + "\n".join(lines) + "\n"


@pytest.mark.parametrize(("gate", "checker"), GATES)
@pytest.mark.parametrize("files", FILE_COUNTS)
def test_count(gate: str, checker: str, files: int) -> None:
    """The last line printed is the gate's count line, in the finished run's shape, counting the files given."""
    lines = _printed(gate, checker, "alpha failed hard\nbeta failed too\n", files)

    assert _last_is_count(lines, gate, files) == [True]


@pytest.mark.parametrize(("gate", "checker"), GATES)
@pytest.mark.parametrize("output", OUTPUTS)
def test_lines(gate: str, checker: str, output: str) -> None:
    """Every line of the checker's output is printed as a line of its own, in order, before the count line."""
    lines = _printed(gate, checker, output, 3)

    assert (_framed(output.splitlines()) in _framed(lines[:-1]), _last_is_count(lines, gate, 3)) == (True, [True])
