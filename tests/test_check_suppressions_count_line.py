"""Red tests for the suppression gate's count line.

Source: the quality gates design spec, "Gates" intro: the count line of a run whose checker finished reads
`<gate>: N finding(s) in M Python file(s)`, where `<gate>` is the name of the
gate script without its extension, and it is the last line the run prints.

The documents name no stream, so stdout and stderr are sent to one buffer while the gate runs; that keeps the order in
which the run printed its lines, and "the last line the run prints" is the last line of that buffer.
"""

import contextlib
import io
from pathlib import Path

from gates.check_suppressions import main

GATE = "check_suppressions"


def _seed(tmp_path: Path, name: str, source: str) -> Path:
    path = tmp_path / name
    path.write_text(source, encoding="utf-8")
    return path


def _count_line(findings: int, files: int) -> str:
    return f"{GATE}: {findings} finding(s) in {files} Python file(s)"


def _last_lines(paths: list[Path]) -> list[str]:
    """Run the gate with stdout and stderr in one buffer and return its last line, as a list of at most one line."""
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer), contextlib.redirect_stderr(buffer):
        main(paths)
    return buffer.getvalue().splitlines()[-1:]


def test_clean_run_ends_with_zero_finding_count_line(tmp_path: Path) -> None:
    path = _seed(tmp_path, "clean.py", "value = 1\n")
    expected = _count_line(0, 1)

    assert _last_lines([path]) == [expected]


def test_run_with_findings_ends_with_count_line_after_findings(tmp_path: Path) -> None:
    dirty = _seed(
        tmp_path, "dirty.py", "first = 1  # noqa\nsecond = 2  # pragma: no cover\n"
    )
    clean = _seed(tmp_path, "clean.py", "value = 1\n")
    expected = _count_line(2, 2)

    assert _last_lines([dirty, clean]) == [expected]


def test_count_line_counts_only_python_files(tmp_path: Path) -> None:
    source = _seed(tmp_path, "module.py", "value = 1\n")
    windowed = _seed(tmp_path, "window.pyw", "value = 1\n")
    expected = _count_line(0, 1)

    assert _last_lines([source, windowed]) == [expected]
