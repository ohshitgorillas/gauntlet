# Copyright 2026 oh shit, gorillas!
"""Red tests for the suppression gate on the gates core.

Source: the gates core design spec under docs/superpowers/specs/, section 2, "A gate on the core", the C4 row of
section 4 and the contract cases C3, C4, C5 and C11; the quality gates design spec, "Gates", intro, for the count line,
the exit status 2, the pin and the parse rules.

An empty run prints the nothing-checked line and the count line for no file, then exits 1. A file given twice is one
file in M. A warning raised while a file is parsed means the file was not finished: the warning prints as the report
of not finishing it, the run exits 2, and the file's own findings do not print. A missing pin prints an error naming the
key, then the count line, and exits 2. Findings print before the reports of files not finished, and the count line is
last.
"""

from collections.abc import Mapping, Sequence
from pathlib import Path

from gates.check_suppressions import GATE, main
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.project import scaffold

MARKED = "value = 1  # noqa\n"

CLEAN = "value = 1\n"

INVALID_ESCAPE = 'PATTERN = "\\d"  # noqa\n'

STRICT = '[tool.pyright]\ntypeCheckingMode = "strict"\n'


def _run(
    tmp_path: Path,
    files: Mapping[str, str],
    paths: Sequence[str],
    pyproject: str | None = None,
) -> tuple[int, list[str]]:
    """Run the gate over the named files of a scaffolded project; return its exit status and every line it printed."""
    project = scaffold(tmp_path, files, pyproject=pyproject)
    output = captured(
        lambda: run_gate(GATE, [tmp_path / name for name in paths], project=project)
    )
    return output.result, output.merged


def test_empty_run_prints_both_lines(tmp_path: Path) -> None:
    """A run with no Python file among the paths prints the nothing-checked line, then the count line, and exits 1."""
    note = tmp_path / "notes.txt"
    note.write_text("text\n", encoding="utf-8")

    output = captured(lambda: main([note]))

    assert (output.result, output.merged) == (
        1,
        [
            "check_suppressions: nothing checked: no Python file among the 1 file(s) given\n",
            "check_suppressions: 0 finding(s) in 0 Python file(s)\n",
        ],
    )


def test_a_file_given_twice_is_one_file(tmp_path: Path) -> None:
    """The same file named twice counts once in M and prints its finding once."""
    status, lines = _run(tmp_path, {"dirty.py": MARKED}, ["dirty.py", "dirty.py"])

    assert (status, lines) == (
        1,
        [
            f"{tmp_path / 'dirty.py'}:1: suppression comment `noqa`\n",
            "check_suppressions: 1 finding(s) in 1 Python file(s)\n",
        ],
    )


def test_a_parse_warning_ends_the_file_unfinished(tmp_path: Path) -> None:
    """A file whose parse raises a warning is not finished: the warning prints as its report, no finding of the file does, exit 2."""
    status, lines = _run(tmp_path, {"warned.py": INVALID_ESCAPE}, ["warned.py"])

    assert (
        status,
        len(lines),
        lines[0].startswith(f"{tmp_path / 'warned.py'}:1: SyntaxWarning: "),
        lines[-1],
    ) == (
        2,
        2,
        True,
        "check_suppressions: 0 finding(s) in 1 Python file(s)\n",
    )


def test_findings_print_before_the_unfinished_file(tmp_path: Path) -> None:
    """A finding of one file prints, then the report for the file not finished, then the count line, and the run exits 2."""
    status, lines = _run(
        tmp_path,
        {"warned.py": INVALID_ESCAPE, "dirty.py": MARKED},
        ["warned.py", "dirty.py"],
    )

    assert (status, lines[0], lines[-1], len(lines)) == (
        2,
        f"{tmp_path / 'dirty.py'}:1: suppression comment `noqa`\n",
        "check_suppressions: 1 finding(s) in 2 Python file(s)\n",
        3,
    )


def test_a_missing_pin_prints_an_error_naming_the_key_then_the_count_line(
    tmp_path: Path,
) -> None:
    """A project that pins no Python prints an error naming `pythonVersion`, then a count line for no finding, and exits 2."""
    status, lines = _run(tmp_path, {"clean.py": CLEAN}, ["clean.py"], pyproject=STRICT)

    assert (status, len(lines), "pythonVersion" in lines[0], lines[-1]) == (
        2,
        2,
        True,
        "check_suppressions: 0 finding(s) in 1 Python file(s)\n",
    )
