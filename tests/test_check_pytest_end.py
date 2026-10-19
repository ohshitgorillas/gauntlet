"""Red tests for how a pytest gate run whose checker did not finish on a test file ends.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "The count line of a run
whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script
without its extension and `finding(s)` and `file(s)` are printed as written whatever N and M are", and "A run whose
checker could not finish prints the same count line, in the same shape, as the last line it prints, after what the
checker reported; a line saying on how many files the checker could not finish, or that it gave no report the gate can
read, is not a count line, and no gate prints one." The same paragraph: "A Python file the checker cannot read or cannot
parse is a file the checker did not finish: the gate prints what the checker reported for that file and exits 2,
whatever it found in the other files." The "Tests" section, "pytest strictness" bullet: "Anything that stops pytest
before or during collection is a run the checker did not finish, exit 2, with pytest's own error printed and the count
line still printed: a collection error". The gate's script is `gates/check_pytest.py`, so `<gate>` is `check_pytest`.

The documents spell the count line of an unfinished run only by its shape, so the last line is held to that shape with
any N and M. They do not spell the line no gate prints, so it is held by what makes it that line: a number of files. A
line counts files when it holds a number followed by `file`, `files` or `file(s)`, with `Python` between them or not;
the count line is one such line, so an unfinished run prints exactly one. They do not spell pytest's report, so it is
read only for the name of the test file pytest did not finish, on a line printed before the count line, and, on a line
printed before the count line, what only pytest's own error on that file can carry: the `SyntaxError` Python raises on
the file it cannot parse, the seeded module name whose import fails, and for the file no one may read the operating
system's text for a denied read, `os.strerror(errno.EACCES)`. An argument list that merely names the file carries none.

The unfinished test file is one pytest cannot parse, one it cannot read, or one whose import fails at collection. Each
companion test file is one the gate alone would pass or fail with a finding, given before and after the unfinished one.
The gate runs in a child interpreter whose stdout and stderr share one unbuffered pipe, so the lines come back in the
order the run printed them whichever stream or process printed them. Test names and ids are kept short so that each
line of pytest's short summary names its exception.
"""

import errno
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from gates.check_pytest import main

REPO_ROOT = Path(__file__).parents[1]

CHILD = (
    "import sys\n"
    "from pathlib import Path\n\n"
    f"from {main.__module__} import {main.__name__}\n\n"
    f"sys.exit({main.__name__}([Path(arg) for arg in sys.argv[1:]]))\n"
)

GATE = "check_pytest"

UNFINISHED = 2

COUNT_LINE_SHAPE = re.compile(rf"{GATE}: \d+ finding\(s\) in \d+ Python file\(s\)")

FILE_COUNT = re.compile(r"\b\d+\s+(?:Python\s+)?file(?:s|\(s\))?(?!\w)", re.IGNORECASE)

BROKEN_NAME = "test_broken.py"

PASSING = "def test_seeded():\n    pass\n"

CALL_FAILS = "def test_seeded():\n    raise ValueError('SeededFailure')\n"

UNPARSEABLE = "def test_seeded(:\n    pass\n"

MISSING_IMPORT = "import seededmissingmodule\n\n\ndef test_seeded():\n    pass\n"

MISSING_MODULE = "seededmissingmodule"

SYNTAX_ERROR = "SyntaxError"

PERMISSION_DENIED = os.strerror(errno.EACCES)

KINDS = [
    pytest.param(UNPARSEABLE, False, id="syn"),
    pytest.param(PASSING, True, id="perm"),
    pytest.param(MISSING_IMPORT, False, id="imp"),
]

LAYOUTS = [
    pytest.param(None, True, id="a"),
    pytest.param(PASSING, True, id="c1"),
    pytest.param(PASSING, False, id="c2"),
    pytest.param(CALL_FAILS, True, id="f1"),
    pytest.param(CALL_FAILS, False, id="f2"),
]


def _seed(root: Path, relative: str, source: str) -> Path:
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def _paths(root: Path, source: str, companion: str | None, *, locked: bool, broken_first: bool) -> list[Path]:
    """The unfinished test file alone, or beside a companion test file given before or after it."""
    broken = _seed(root, f"tests/{BROKEN_NAME}", source)
    if locked:
        broken.chmod(0o000)
    if companion is None:
        return [broken]
    other = _seed(root, "tests/test_companion.py", companion)
    return [broken, other] if broken_first else [other, broken]


def _run(paths: list[Path]) -> tuple[int, list[str]]:
    """Run the gate in a child with stdout and stderr in one pipe; return its exit status and every line it printed."""
    command = ["/usr/bin/env", "PYTHONUNBUFFERED=1", sys.executable, "-c", CHILD, *map(str, paths)]
    result = subprocess.run(  # A child interpreter keeps the gate's stdout and stderr in one ordered buffer.
        command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        check=False,
    )
    return result.returncode, result.stdout.splitlines()


def _counts(lines: list[str]) -> int:
    """How many printed lines count files."""
    return sum(1 for line in lines if FILE_COUNT.search(line) is not None)


def _shapes(lines: list[str]) -> list[bool]:
    """For the last printed line, as a list of at most one, whether it is in the count line's shape."""
    return [COUNT_LINE_SHAPE.fullmatch(line) is not None for line in lines[-1:]]


@pytest.mark.parametrize(("source", "locked"), KINDS)
@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_one(tmp_path: Path, source: str, companion: str | None, *, locked: bool, broken_first: bool) -> None:
    """An unfinished run exits 2 and counts files on one line only, the count line in its shape it ends on."""
    paths = _paths(tmp_path, source, companion, locked=locked, broken_first=broken_first)

    status, lines = _run(paths)

    assert (status, _counts(lines), _shapes(lines)) == (UNFINISHED, 1, [True])


def _evidence(source: str, *, locked: bool) -> str:
    """What only pytest's own error on the unfinished test file carries: a denied read, a syntax error, or the missing module."""
    if locked:
        return PERMISSION_DENIED
    return SYNTAX_ERROR if source == UNPARSEABLE else MISSING_MODULE


@pytest.mark.parametrize(("source", "locked"), KINDS)
@pytest.mark.parametrize(("companion", "broken_first"), LAYOUTS)
def test_report(tmp_path: Path, source: str, companion: str | None, *, locked: bool, broken_first: bool) -> None:
    """What pytest reported on the unfinished test file, which names it and carries its error, comes before the count line the run ends on."""
    paths = _paths(tmp_path, source, companion, locked=locked, broken_first=broken_first)

    status, lines = _run(paths)

    before = "\n".join(lines[:-1])
    assert (status, BROKEN_NAME in before, _evidence(source, locked=locked) in before, _shapes(lines)) == (
        UNFINISHED,
        True,
        True,
        [True],
    )
