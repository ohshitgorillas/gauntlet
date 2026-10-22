"""Red tests for the cast gate's count line.

Source: the quality-gates design spec under docs/superpowers/specs/, "Gates", intro paragraph: "The count line of a run
whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the gate script
without its extension, and it is the last line the run prints." The banned name comes from "Types", third bullet:
"`typing.cast` is banned (ruff `TID251`)."

The gate script is the module `gates.check_cast`, so `<gate>` is `check_cast`. The same sentence says "`finding(s)` and
`file(s)` are printed as written whatever N and M are", so the last line is held to that one spelling, never to the
English singular or plural that agrees with the number.

The documents name no stream, so stdout and stderr are both sent to one buffer while the gate runs; that keeps the
order in which the run printed its lines, and "the last line the run prints" is the last line of that buffer.

The test names are kept short so that pytest's one-line summary has room to name the exception a test fails with.
"""

import contextlib
import io
from pathlib import Path

from gates.check_cast import main

GATE = "check_cast"

DIRTY_TWICE = (
    "import typing\n\nvalue = typing.cast(int, 1)\nother = typing.cast(int, 2)\n"
)

CLEAN = "VALUE = 1\n"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _last_lines(paths: list[Path]) -> list[str]:
    """Run the gate with stdout and stderr in one buffer and return its last line, as a list of at most one line."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        main(paths)
    return buffer.getvalue().splitlines()[-1:]


def _count_lines(findings: int, files: int) -> list[str]:
    """Return the count line as the documents write it, `finding(s)` and `file(s)` as written, as a list of one line."""
    return [f"{GATE}: {findings} finding(s) in {files} Python file(s)"]


def test_clean_last(tmp_path: Path) -> None:
    """A finished run over one clean Python file ends on the count line for no finding in one Python file."""
    clean = _seed(tmp_path, "clean.py", CLEAN)

    assert _last_lines([clean]) == _count_lines(0, 1)


def test_findings_last(tmp_path: Path) -> None:
    """A finished run with findings ends on the count line, after the findings, counting findings and every Python file checked.

    One file holds two uses of `typing.cast` and two files hold none: two findings in three Python files. A gate that
    counts files with a finding states 1 finding, and one that counts only those files states 1 Python file.
    """
    twice = _seed(tmp_path, "twice.py", DIRTY_TWICE)
    first_clean = _seed(tmp_path, "first_clean.py", CLEAN)
    second_clean = _seed(tmp_path, "second_clean.py", CLEAN)

    assert _last_lines([first_clean, twice, second_clean]) == _count_lines(2, 3)
