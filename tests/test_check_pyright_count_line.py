"""Red tests for the pyright gate's count line.

Source: the quality gates design spec under docs/superpowers/specs/, "Gates", intro paragraph:
"it prints each finding on its own line and prints its count line on every run. The count line
of a run whose checker finished reads `<gate>: N finding(s) in M Python file(s)`, where `<gate>`
is the name of the gate script without its extension, and it is the last line the run prints."
The pyright gate is "Types", second bullet; its script is `gates/check_pyright.py`, so `<gate>`
is `check_pyright`. The template's `finding(s)` and `file(s)` are read as literal text.

The documents name no stream, so stdout and stderr are written into one buffer, which keeps
the order the run printed its lines in.
"""

import io
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

from gates.check_pyright import main

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

ONE_FINDING = 'first_value: int = "alpha"\n'

TWO_FINDINGS = 'first_value: int = "alpha"\nsecond_value: int = "beta"\n'


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _last_line(paths: list[Path]) -> str:
    buffer = io.StringIO()
    with redirect_stdout(buffer), redirect_stderr(buffer):
        main(paths)
    lines = buffer.getvalue().splitlines()
    return lines[-1] if lines else ""


def test_count_line_clean_file(tmp_path: Path) -> None:
    """A finished run over one clean file ends on a count of zero findings in one file."""
    path = _seed(tmp_path, "seeded.py", CLEAN)

    assert _last_line([path]) == "check_pyright: 0 finding(s) in 1 Python file(s)"


def test_count_line_counts_files(tmp_path: Path) -> None:
    """M is the number of Python files the run checked."""
    first = _seed(tmp_path, "first.py", CLEAN)
    second = _seed(tmp_path, "second.py", CLEAN)

    assert _last_line([first, second]) == "check_pyright: 0 finding(s) in 2 Python file(s)"


def test_count_line_after_finding(tmp_path: Path) -> None:
    """A run with a finding prints the finding first and ends on the count line."""
    path = _seed(tmp_path, "seeded.py", ONE_FINDING)

    assert _last_line([path]) == "check_pyright: 1 finding(s) in 1 Python file(s)"


def test_count_line_counts_findings(tmp_path: Path) -> None:
    """N is the number of findings, not the number of files holding one."""
    path = _seed(tmp_path, "seeded.py", TWO_FINDINGS)

    assert _last_line([path]) == "check_pyright: 2 finding(s) in 1 Python file(s)"
