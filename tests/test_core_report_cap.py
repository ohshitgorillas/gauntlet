"""Red tests for the line naming a checker's time cap and the pair a capped checker's run gives.

Source: the gates core design spec under docs/superpowers/specs/, section 1, "report.py: what a run prints and how it
exits": `time_cap(checker, seconds)` is "decision 22's line naming the cap, its one home (decision 29)", and
`timed_out(output, checker, seconds)` is "a checker its cap ended: its whole output, then time_cap". Decision 22 gives
the line's words, "the gate's own line `the checker <argv[0]> ran past its time cap of <timeout> seconds`", after "an
Unfinished of the checker's whole output"; decision 29 makes `time_cap` the one home of that line and `timed_out` the
one home of the pair, "its whole output then that line", and writes the mutation gate's call as `time_cap(argv[0], 600)`.

So `time_cap` fills the checker as given, a path included, and the seconds into that line, "seconds" printed as written;
`timed_out` gives an Unfinished of the output as given, nothing cut from it, then an Unfinished of that line. How a
number of seconds with a fraction, or a float with none, is printed is not written, so only whole seconds are held.
"""

import pytest

from gates.core.report import Unfinished, time_cap, timed_out

MUTMUT_CAP = "the checker mutmut ran past its time cap of 600 seconds"
PYTEST_CAP = "the checker pytest ran past its time cap of 30 seconds"
PATH_CAP = "the checker /opt/venv/bin/mypy ran past its time cap of 1 seconds"
LONG_CAP = "the checker ruff ran past its time cap of 86400 seconds"

GENERATING = "Generating mutants\n    done in 412ms\n"
COLLECTING = "============ test session starts ============\r\ncollecting ... \r\n"
NO_BREAK = "running 3 checks"
BLANKS = "\n\nTraceback (most recent call last):\n\n"


@pytest.mark.parametrize(
    ("checker", "seconds", "expected"),
    [
        pytest.param("mutmut", 600, MUTMUT_CAP, id="mut"),
        pytest.param("pytest", 30, PYTEST_CAP, id="pyt"),
        pytest.param("/opt/venv/bin/mypy", 1, PATH_CAP, id="path"),
        pytest.param("ruff", 86400, LONG_CAP, id="day"),
    ],
)
def test_time_cap(checker: str, seconds: float, expected: str) -> None:
    """time_cap: the line names the checker as given and its cap in seconds, in decision 22's words."""
    assert time_cap(checker, seconds) == expected


@pytest.mark.parametrize(
    ("output", "checker", "seconds", "expected"),
    [
        pytest.param(
            GENERATING,
            "mutmut",
            600,
            (Unfinished(GENERATING), Unfinished(MUTMUT_CAP)),
            id="mut",
        ),
        pytest.param(
            COLLECTING,
            "pytest",
            30,
            (Unfinished(COLLECTING), Unfinished(PYTEST_CAP)),
            id="crlf",
        ),
        pytest.param(
            NO_BREAK,
            "/opt/venv/bin/mypy",
            1,
            (Unfinished(NO_BREAK), Unfinished(PATH_CAP)),
            id="path",
        ),
        pytest.param(
            BLANKS, "ruff", 86400, (Unfinished(BLANKS), Unfinished(LONG_CAP)), id="blnk"
        ),
        pytest.param(
            "", "mutmut", 600, (Unfinished(""), Unfinished(MUTMUT_CAP)), id="none"
        ),
    ],
)
def test_timed_out(
    output: str, checker: str, seconds: float, expected: tuple[Unfinished, Unfinished]
) -> None:
    """timed_out: an Unfinished of the checker's whole output as given, then an Unfinished of its cap line."""
    assert timed_out(output, checker, seconds) == expected
