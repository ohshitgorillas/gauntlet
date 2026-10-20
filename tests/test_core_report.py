"""Red tests for the gates core gate error and the exit code a run's outcome calls for.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "report.py: what a run prints and how it
exits": `GateError(report)` is an Exception whose report is printed as the checker's; an `Outcome` holds the run's
`Finding`, `Remark` and `Unfinished` lines and the gate's own notes; `exit_code(outcome)` is 2 on any Unfinished, else
1 on any Finding, else 0.

The count line and the empty run: the same section names `count_line(gate, findings, files)` and
`nothing_checked(gate, selects, given)`; their text is the quality-gates design spec's, "Gates", intro: "The count line
of a run whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where ... `finding(s)` and `file(s)`
are printed as written whatever N and M are", and "A gate given no Python file it checks makes an empty run: it prints
one line saying that nothing was checked, then the count line `<gate>: 0 finding(s) in 0 Python file(s)` as the last
line it prints". The words of the line saying nothing was checked are not written in the documents, so it is held only
to being one line that is no count line; what `selects` and `given` add to it is not pinned either.

Text that spans lines: the same section names `output_lines(text)`, "a checker's console output, one printed line per
str.splitlines line", and `one_line(text)`, "every str.splitlines break becomes a space". So every break str.splitlines
knows counts, `\\r\\n` as one break, and nothing else in a line is touched. The quality-gates design spec's "Tests" section
reads the same for a finding: "every line break in it replaced by a space".

What a finished run prints: the same section names `render(gate, outcome, files)`, "notes, lines in order, each
Unfinished text once per run, count line last"; a Finding is "One line, counted in N", a Remark is "printed, not
counted". So a Finding or Remark is one printed line, its breaks made spaces as `one_line` makes them, an Unfinished is
the printed lines of its whole text as `output_lines` splits them, and the count line names the files handed in and the
number of Findings. Which place a repeated Unfinished text keeps among other lines, and the order of two notes, are not
written, and no test here holds either.

The one writer: the same section names `write(lines, *, error=False)`, "the only writer: looks up sys.stdout/stderr at
call time, flushes". So the lines it is given are printed one per line, in order, each as given, a blank one as a blank
line, to whatever sys.stdout is when it is called, or sys.stderr when `error` is true, and are in that stream's file
once it returns. Printed one per line, each line ends with its own break, so lines from two calls never run together and
no line given prints nothing. What it does with a given line that holds a line break is not written, and no test here
holds it. That no other module writes is held by the structure test the same spec's section 3 names, not here.
"""

import io
import re
from contextlib import redirect_stderr, redirect_stdout

import pytest

from gates.core.report import (
    Finding,
    GateError,
    Outcome,
    Remark,
    Unfinished,
    count_line,
    exit_code,
    nothing_checked,
    one_line,
    output_lines,
    render,
    write,
)

REPORT = "mypy: cannot start: no such file or directory"
FINDING = "a.py:3:5: error: Name 'x' is not defined  [name-defined]"
REMARK = "a.py:3:5: note: See the mypy docs for name-defined"
UNFINISHED = "b.py: SyntaxWarning: invalid escape sequence"
SEED = "check_pytest: seed 1234"


def test_gate_error_is_an_exception_that_carries_its_report() -> None:
    """Raise a GateError and catch it as an Exception whose message is the report it was given."""
    with pytest.raises(Exception, match=r"\A" + re.escape(REPORT) + r"\Z") as caught:
        raise GateError(REPORT)
    assert caught.type is GateError


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        pytest.param(Outcome(), 0, id="no-lines-is-0"),
        pytest.param(Outcome(notes=(SEED,)), 0, id="notes-only-is-0"),
        pytest.param(Outcome(lines=(Remark(REMARK),)), 0, id="remark-only-is-0"),
        pytest.param(Outcome(lines=(Remark(REMARK), Remark(REMARK))), 0, id="remarks-only-is-0"),
        pytest.param(Outcome(lines=(Finding(FINDING),)), 1, id="one-finding-is-1"),
        pytest.param(Outcome(lines=(Finding(FINDING), Finding(FINDING))), 1, id="two-findings-is-1"),
        pytest.param(Outcome(lines=(Remark(REMARK), Finding(FINDING))), 1, id="remark-then-finding-is-1"),
        pytest.param(Outcome(lines=(Finding(FINDING), Remark(REMARK))), 1, id="finding-then-remark-is-1"),
        pytest.param(Outcome(lines=(Finding(FINDING),), notes=(SEED,)), 1, id="finding-with-note-is-1"),
        pytest.param(Outcome(lines=(Unfinished(UNFINISHED),)), 2, id="one-unfinished-is-2"),
        pytest.param(Outcome(lines=(Unfinished(UNFINISHED),), notes=(SEED,)), 2, id="unfinished-with-note-is-2"),
        pytest.param(Outcome(lines=(Remark(REMARK), Unfinished(UNFINISHED))), 2, id="remark-then-unfinished-is-2"),
        pytest.param(Outcome(lines=(Finding(FINDING), Unfinished(UNFINISHED))), 2, id="finding-then-unfinished-is-2"),
        pytest.param(Outcome(lines=(Unfinished(UNFINISHED), Finding(FINDING))), 2, id="unfinished-then-finding-is-2"),
        pytest.param(
            Outcome(lines=(Finding(FINDING), Remark(REMARK), Unfinished(UNFINISHED), Finding(FINDING))),
            2,
            id="unfinished-among-findings-is-2",
        ),
    ],
)
def test_exit_code_is_2_on_any_unfinished_else_1_on_any_finding_else_0(outcome: Outcome, expected: int) -> None:
    """Take the exit code each outcome calls for."""
    assert exit_code(outcome) == expected


COUNT_SHAPE = re.compile(r".*: \d+ finding\(s\) in \d+ Python file\(s\)")


@pytest.mark.parametrize(
    ("gate", "findings", "files", "expected"),
    [
        pytest.param("check_mypy", 0, 1, "check_mypy: 0 finding(s) in 1 Python file(s)", id="0-1"),
        pytest.param("check_cast", 1, 1, "check_cast: 1 finding(s) in 1 Python file(s)", id="1-1"),
        pytest.param("check_pyright", 2, 3, "check_pyright: 2 finding(s) in 3 Python file(s)", id="2-3"),
        pytest.param("check_pytest", 3, 2, "check_pytest: 3 finding(s) in 2 Python file(s)", id="3-2"),
        pytest.param("check_mutation", 0, 0, "check_mutation: 0 finding(s) in 0 Python file(s)", id="0-0"),
        pytest.param(
            "check_suppressions", 12, 107, "check_suppressions: 12 finding(s) in 107 Python file(s)", id="12-107"
        ),
    ],
)
def test_count_line(gate: str, findings: int, files: int, expected: str) -> None:
    """The count line names the gate, then N and M, with `finding(s)` and `file(s)` as written whatever the numbers."""
    assert count_line(gate, findings, files) == expected


EMPTY_RUNS = [
    pytest.param("check_mypy", "Python file", 0, "check_mypy: 0 finding(s) in 0 Python file(s)", id="none"),
    pytest.param("check_cast", "Python file", 1, "check_cast: 0 finding(s) in 0 Python file(s)", id="one"),
    pytest.param("check_pytest", "test file", 3, "check_pytest: 0 finding(s) in 0 Python file(s)", id="test"),
    pytest.param(
        "check_mutation",
        "Python file that is not a test file",
        2,
        "check_mutation: 0 finding(s) in 0 Python file(s)",
        id="mut",
    ),
]


@pytest.mark.parametrize(("gate", "selects", "given", "count"), EMPTY_RUNS)
def test_empty_lines(gate: str, selects: str, given: int, count: str) -> None:
    """An empty run prints one line, then the count line for no finding in no Python file, last, whatever it was given."""
    assert nothing_checked(gate, selects, given)[1:] == [count]


@pytest.mark.parametrize(("gate", "selects", "given", "count"), EMPTY_RUNS)
def test_empty_count(gate: str, selects: str, given: int, count: str) -> None:
    """The line saying nothing was checked is no count line: of what an empty run prints, one line counts files."""
    assert [line for line in nothing_checked(gate, selects, given) if COUNT_SHAPE.fullmatch(line)] == [count]


@pytest.mark.parametrize(("gate", "selects", "given", "count"), EMPTY_RUNS)
def test_empty_whole(gate: str, selects: str, given: int, count: str) -> None:
    """Each of an empty run's lines is one whole printed line: none is empty and none holds a line break."""
    lines = nothing_checked(gate, selects, given)
    assert [piece for line in lines for piece in line.splitlines()] == [*lines[:1], count]


FIRST = 'a.py:3: error: Name "x" is not defined  [name-defined]'
SECOND = "Found 1 error in 1 file (checked 1 source file)"
BLANK = ""
INDENTED = "    x = undefined_name\t# the line it names  "

# Every line boundary str.splitlines knows, `\r\n` among them as one boundary. Ids stay short so that pytest's short
# summary line keeps the exception type in view.
BREAKS = [
    pytest.param("\n", id="lf"),
    pytest.param("\r\n", id="crlf"),
    pytest.param("\r", id="cr"),
    pytest.param("\v", id="vt"),
    pytest.param("\f", id="ff"),
    pytest.param("\x1c", id="fs"),
    pytest.param("\x1d", id="gs"),
    pytest.param("\x1e", id="rs"),
    pytest.param("\x85", id="nel"),
    pytest.param("\N{LINE SEPARATOR}", id="ls"),
    pytest.param("\N{PARAGRAPH SEPARATOR}", id="ps"),
]


@pytest.mark.parametrize("brk", BREAKS)
def test_split_at(brk: str) -> None:
    """output_lines: each line boundary str.splitlines knows ends one printed line of a checker's output."""
    assert output_lines(FIRST + brk + SECOND) == [FIRST, SECOND]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", [], id="empty"),
        pytest.param(FIRST, [FIRST], id="one"),
        pytest.param(FIRST + "\n", [FIRST], id="trailing"),
        pytest.param(FIRST + "\n" + SECOND + "\n", [FIRST, SECOND], id="two"),
        pytest.param(FIRST + "\n\n" + SECOND, [FIRST, BLANK, SECOND], id="blank"),
        pytest.param(FIRST + "\r\n\r\n" + SECOND, [FIRST, BLANK, SECOND], id="crlf-blank"),
        pytest.param("\n", [BLANK], id="lone"),
        pytest.param("\n" + FIRST, [BLANK, FIRST], id="leading"),
        pytest.param(INDENTED + "\n" + FIRST + "\n", [INDENTED, FIRST], id="indent"),
        pytest.param(FIRST + "\r" + SECOND + "\n", [FIRST, SECOND], id="mixed"),
    ],
)
def test_split(text: str, expected: list[str]) -> None:
    """output_lines: one printed line per str.splitlines line, in order, each as the checker wrote it.

    No output is no line; a trailing break adds no line; a blank line, a leading break and a lone break each give an
    empty line; indentation, tabs and trailing spaces stay.
    """
    assert output_lines(text) == expected


@pytest.mark.parametrize("brk", BREAKS)
def test_join_at(brk: str) -> None:
    """one_line: each line boundary str.splitlines knows becomes one space, `\\r\\n` included as one."""
    assert one_line(FIRST + brk + SECOND) == FIRST + " " + SECOND


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        pytest.param("", "", id="empty"),
        pytest.param(FIRST, FIRST, id="one"),
        pytest.param(INDENTED, INDENTED, id="tab"),
        pytest.param(FIRST + "\n\n" + SECOND, FIRST + "  " + SECOND, id="two"),
        pytest.param(FIRST + "\r\n\r\n" + SECOND, FIRST + "  " + SECOND, id="crlf-two"),
        pytest.param(FIRST + "\n" + SECOND + "\n", FIRST + " " + SECOND + " ", id="trailing"),
        pytest.param("\n" + FIRST, " " + FIRST, id="leading"),
        pytest.param("\n", " ", id="lone"),
        pytest.param(INDENTED + "\n" + FIRST, INDENTED + " " + FIRST, id="indent"),
        pytest.param(
            FIRST + "\r" + SECOND + "\N{LINE SEPARATOR}" + FIRST, FIRST + " " + SECOND + " " + FIRST, id="mixed"
        ),
    ],
)
def test_join(text: str, expected: str) -> None:
    """one_line: every str.splitlines break becomes a space, and nothing else in the text changes.

    Two breaks are two spaces; a leading, trailing or lone break is a space too, since it is a break; tabs, indentation
    and the spaces at either end stay.
    """
    assert one_line(text) == expected


FAILED = "tests/test_a.py::test_x: assert 1 == 2"
TIMEOUT = "tests/test_b.py::test_y: Failed: Timeout >30.0s"
CRASH = "ERROR collecting tests/test_c.py"
CAUSE = "E   ModuleNotFoundError: No module named 'nope'"
OTHER = "tests/test_d.py: SyntaxWarning: invalid escape sequence"


@pytest.mark.parametrize(
    ("gate", "outcome", "files", "expected"),
    [
        pytest.param(
            "check_pytest", Outcome(), 3, ["check_pytest: 0 finding(s) in 3 Python file(s)"], id="empty"
        ),
        pytest.param(
            "check_pytest",
            Outcome(notes=(SEED,)),
            1,
            [SEED, "check_pytest: 0 finding(s) in 1 Python file(s)"],
            id="note",
        ),
        pytest.param(
            "check_pytest",
            Outcome(lines=(Finding(FAILED),), notes=(SEED,)),
            1,
            [SEED, FAILED, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="note-first",
        ),
        pytest.param(
            "check_pytest",
            Outcome(lines=(Finding(TIMEOUT), Remark(REMARK), Finding(FAILED))),
            2,
            [TIMEOUT, REMARK, FAILED, "check_pytest: 2 finding(s) in 2 Python file(s)"],
            id="given-order",
        ),
        pytest.param(
            "check_pytest",
            Outcome(lines=(Remark(REMARK), Finding(FAILED))),
            1,
            [REMARK, FAILED, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="remark-first",
        ),
        pytest.param(
            "check_pytest",
            Outcome(lines=(Remark(REMARK), Remark(REMARK))),
            107,
            [REMARK, REMARK, "check_pytest: 0 finding(s) in 107 Python file(s)"],
            id="remarks",
        ),
        pytest.param(
            "check_pytest",
            Outcome(lines=(Finding(FAILED), Finding(FAILED))),
            1,
            [FAILED, FAILED, "check_pytest: 2 finding(s) in 1 Python file(s)"],
            id="twice",
        ),
        pytest.param(
            "check_pytest",
            Outcome(lines=(Finding(FAILED), Unfinished(UNFINISHED), Remark(REMARK)), notes=(SEED,)),
            2,
            [SEED, FAILED, UNFINISHED, REMARK, "check_pytest: 1 finding(s) in 2 Python file(s)"],
            id="between",
        ),
        pytest.param(
            "check_mypy",
            Outcome(lines=(Finding(FINDING),)),
            1,
            [FINDING, "check_mypy: 1 finding(s) in 1 Python file(s)"],
            id="gate-name",
        ),
    ],
)
def test_order(gate: str, outcome: Outcome, files: int, expected: list[str]) -> None:
    """render: the gate's notes first, then the run's lines in the order given, then the count line last.

    The count line counts the Findings, never a Remark or an Unfinished, in the files handed in, and is printed on
    every run, an outcome with no line included; a Finding given twice is two findings.
    """
    assert render(gate, outcome, files) == expected


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        pytest.param(
            Outcome(lines=(Finding(FAILED + "\n" + TIMEOUT),)),
            [FAILED + " " + TIMEOUT, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="lf",
        ),
        pytest.param(
            Outcome(lines=(Remark(REMARK + "\r\n" + REMARK),)),
            [REMARK + " " + REMARK, "check_pytest: 0 finding(s) in 1 Python file(s)"],
            id="crlf",
        ),
        pytest.param(
            Outcome(lines=(Finding(FAILED + "\n\n" + TIMEOUT),)),
            [FAILED + "  " + TIMEOUT, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="blank",
        ),
        pytest.param(
            Outcome(lines=(Finding(FAILED + "\N{LINE SEPARATOR}" + TIMEOUT),)),
            [FAILED + " " + TIMEOUT, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="ls",
        ),
        pytest.param(
            Outcome(lines=(Finding(FAILED + "\n" + TIMEOUT), Remark(REMARK + "\n" + REMARK)), notes=(SEED,)),
            [SEED, FAILED + " " + TIMEOUT, REMARK + " " + REMARK, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="both",
        ),
    ],
)
def test_one_line(outcome: Outcome, expected: list[str]) -> None:
    """render: a Finding or a Remark is exactly one printed line, each line break in its text made a space."""
    assert render("check_pytest", outcome, 1) == expected


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        pytest.param(
            Outcome(lines=(Unfinished(CRASH + "\n" + CAUSE + "\n"),)),
            [CRASH, CAUSE, "check_pytest: 0 finding(s) in 3 Python file(s)"],
            id="lf",
        ),
        pytest.param(
            Outcome(lines=(Unfinished(CRASH + "\n\n" + CAUSE),)),
            [CRASH, "", CAUSE, "check_pytest: 0 finding(s) in 3 Python file(s)"],
            id="blank",
        ),
        pytest.param(
            Outcome(lines=(Unfinished(CRASH + "\r\n" + CAUSE),)),
            [CRASH, CAUSE, "check_pytest: 0 finding(s) in 3 Python file(s)"],
            id="crlf",
        ),
        pytest.param(
            Outcome(lines=(Finding(FAILED), Unfinished(CRASH + "\n" + CAUSE), Finding(TIMEOUT)), notes=(SEED,)),
            [SEED, FAILED, CRASH, CAUSE, TIMEOUT, "check_pytest: 2 finding(s) in 3 Python file(s)"],
            id="between",
        ),
    ],
)
def test_whole(outcome: Outcome, expected: list[str]) -> None:
    """render: an Unfinished is printed as the printed lines of its whole text, in its place among the run's lines."""
    assert render("check_pytest", outcome, 3) == expected


@pytest.mark.parametrize(
    ("outcome", "expected"),
    [
        pytest.param(
            Outcome(lines=(Unfinished(UNFINISHED), Unfinished(UNFINISHED))),
            [UNFINISHED, "check_pytest: 0 finding(s) in 1 Python file(s)"],
            id="twice",
        ),
        pytest.param(
            Outcome(lines=(Unfinished(CRASH + "\n" + CAUSE), Unfinished(CRASH + "\n" + CAUSE))),
            [CRASH, CAUSE, "check_pytest: 0 finding(s) in 1 Python file(s)"],
            id="lines-twice",
        ),
        pytest.param(
            Outcome(lines=(Unfinished(UNFINISHED), Unfinished(UNFINISHED), Unfinished(UNFINISHED), Finding(FAILED))),
            [UNFINISHED, FAILED, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="thrice-first",
        ),
        pytest.param(
            Outcome(lines=(Finding(FAILED), Unfinished(UNFINISHED), Unfinished(UNFINISHED))),
            [FAILED, UNFINISHED, "check_pytest: 1 finding(s) in 1 Python file(s)"],
            id="twice-last",
        ),
        pytest.param(
            Outcome(lines=(Unfinished(UNFINISHED), Unfinished(OTHER))),
            [UNFINISHED, OTHER, "check_pytest: 0 finding(s) in 1 Python file(s)"],
            id="distinct",
        ),
    ],
)
def test_once(outcome: Outcome, expected: list[str]) -> None:
    """render: the same Unfinished text is printed once per run however often it occurs; distinct texts each print."""
    assert render("check_pytest", outcome, 1) == expected


COUNT = "check_pytest: 1 finding(s) in 1 Python file(s)"
# In the order a run prints them, which is neither sorted nor reversed.
PRINTED = (SEED, FAILED, COUNT)
PRINTED_TEXT = SEED + "\n" + FAILED + "\n" + COUNT + "\n"
KEPT = (CRASH, BLANK, INDENTED, CAUSE)
KEPT_TEXT = CRASH + "\n" + "\n" + INDENTED + "\n" + CAUSE + "\n"


def _buffered() -> tuple[io.TextIOWrapper, io.BytesIO]:
    """A text stream whose writes reach its bytes only when it is flushed."""
    raw = io.BytesIO()
    return io.TextIOWrapper(raw, encoding="utf-8", newline="\n"), raw


def test_write_stdout() -> None:
    """write: the lines given are printed one per line, in order, to the sys.stdout in place, and none to sys.stderr."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        write(list(PRINTED))
    assert (out.getvalue(), err.getvalue()) == (PRINTED_TEXT, "")


def test_write_stderr() -> None:
    """write: asked for the error stream, it prints the lines to the sys.stderr in place, and none to sys.stdout."""
    out, err = io.StringIO(), io.StringIO()
    with redirect_stdout(out), redirect_stderr(err):
        write(list(PRINTED), error=True)
    assert (out.getvalue(), err.getvalue()) == ("", PRINTED_TEXT)


def test_write_verbatim() -> None:
    """write: each line prints as given, a blank one as a blank line, indentation, tabs and trailing spaces kept."""
    out = io.StringIO()
    with redirect_stdout(out):
        write(list(KEPT))
    assert out.getvalue() == KEPT_TEXT


def test_write_none() -> None:
    """write: no line given prints nothing, not even a blank line, between the lines of the calls around it."""
    out = io.StringIO()
    with redirect_stdout(out):
        write([SEED])
        write([])
        write([FAILED])
    assert out.getvalue() == SEED + "\n" + FAILED + "\n"


def test_write_out_per_call() -> None:
    """write: each call prints to the sys.stdout in place at that call, not the one an earlier call found."""
    first, second = io.StringIO(), io.StringIO()
    with redirect_stdout(first):
        write([SEED])
    with redirect_stdout(second):
        write([FAILED])
    assert (first.getvalue(), second.getvalue()) == (SEED + "\n", FAILED + "\n")


def test_write_err_per_call() -> None:
    """write: each call asked for the error stream prints to the sys.stderr in place at that call."""
    first, second = io.StringIO(), io.StringIO()
    with redirect_stderr(first):
        write([SEED], error=True)
    with redirect_stderr(second):
        write([FAILED], error=True)
    assert (first.getvalue(), second.getvalue()) == (SEED + "\n", FAILED + "\n")


def test_write_flush_stdout() -> None:
    """write: the lines printed to sys.stdout are in its file once write returns, the stream flushed."""
    stream, raw = _buffered()
    with redirect_stdout(stream):
        write(list(PRINTED))
    assert raw.getvalue() == PRINTED_TEXT.encode()


def test_write_flush_stderr() -> None:
    """write: the lines printed to sys.stderr are in its file once write returns, the stream flushed."""
    stream, raw = _buffered()
    with redirect_stderr(stream):
        write(list(PRINTED), error=True)
    assert raw.getvalue() == PRINTED_TEXT.encode()
