"""Red tests for the cast gate on the gates core.

Source: the gates core design spec under docs/superpowers/specs/, section 2, "A gate on the core", and decision 2
(iii) and (iv); the quality gates design spec, "Gates", intro, for the count line and the exit status 2.

An empty run prints the nothing-checked line and the count line for no file, then exits 1. A file given twice is one
file in M. A checker run counts as finished only when its exit status is the one its report calls for: ruff exits 1
with a finding and 0 with none, so an exit 0 over a report that holds a finding is not a finished run. A checker whose
output holds no report the gate can read ends the run unfinished, printing the checker's whole output, then the count
line; one that ran past its time cap adds the gate's own line naming the cap between them. The gate runs ruff with no
cache and no `noqa`, in the project's directory, with the project's own settings file.
"""

import json
from collections.abc import Mapping
from pathlib import Path

from gates.check_cast import GATE, main
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

DIRTY = "import typing\n\nvalue = typing.cast(int, 1)\n"

CLEAN = "VALUE = 1\n"

ENTRY = {
    "code": "TID251",
    "message": "`typing.cast` is banned",
    "filename": "dirty.py",
    "location": {"row": 3, "column": 9},
}

FINDING_LINE = "dirty.py:3:9: TID251 `typing.cast` is banned\n"


def _report(*entries: Mapping[str, object]) -> str:
    return json.dumps(entries)


def test_empty_run_prints_both_lines(tmp_path: Path) -> None:
    """A run with no Python file among the paths prints the nothing-checked line, then the count line, and exits 1."""
    note = tmp_path / "notes.txt"
    note.write_text("text\n", encoding="utf-8")

    output = captured(lambda: main([note]))

    assert (output.result, output.merged) == (
        1,
        [
            "check_cast: nothing checked: no Python file among the 1 file(s) given\n",
            "check_cast: 0 finding(s) in 0 Python file(s)\n",
        ],
    )


def test_a_file_given_twice_is_one_file(tmp_path: Path) -> None:
    """The same file named twice counts once in M."""
    path = tmp_path / "clean.py"
    path.write_text(CLEAN, encoding="utf-8")

    output = captured(lambda: main([path, path]))

    assert (output.result, output.merged) == (
        0,
        ["check_cast: 0 finding(s) in 1 Python file(s)\n"],
    )


def test_findings_print_with_the_count_line(tmp_path: Path) -> None:
    """A report with one TID251 entry prints that finding's line, then the count line, and exits 1."""
    project = scaffold(tmp_path, {"dirty.py": DIRTY})
    fake = FakeRunner([completed(1, _report(ENTRY))])

    output = captured(
        lambda: run_gate(GATE, [tmp_path / "dirty.py"], project=project, process=fake)
    )

    assert (output.result, output.merged) == (
        1,
        [FINDING_LINE, "check_cast: 1 finding(s) in 1 Python file(s)\n"],
    )


def test_other_rules_are_not_findings(tmp_path: Path) -> None:
    """An entry of another rule is no finding of this gate: the run is clean."""
    project = scaffold(tmp_path, {"clean.py": CLEAN})
    other = {**ENTRY, "code": "E501"}
    fake = FakeRunner([completed(1, _report(other))])

    output = captured(
        lambda: run_gate(GATE, [tmp_path / "clean.py"], project=project, process=fake)
    )

    assert (output.result, output.merged) == (
        0,
        ["check_cast: 0 finding(s) in 1 Python file(s)\n"],
    )


def test_unfinished_entries_follow_the_findings(tmp_path: Path) -> None:
    """A file ruff could not parse is printed after the findings, the run exits 2, and the count line ends it."""
    project = scaffold(tmp_path, {"dirty.py": DIRTY, "broken.py": "def broken(:\n"})
    broken = {
        "code": "invalid-syntax",
        "message": "Expected a parameter",
        "filename": "broken.py",
        "location": {"row": 1, "column": 12},
    }
    fake = FakeRunner([completed(1, _report(ENTRY, broken))])
    paths = [tmp_path / "dirty.py", tmp_path / "broken.py"]

    output = captured(lambda: run_gate(GATE, paths, project=project, process=fake))

    assert (output.result, output.merged) == (
        2,
        [
            FINDING_LINE,
            "broken.py:1:12: invalid-syntax Expected a parameter\n",
            "check_cast: 1 finding(s) in 2 Python file(s)\n",
        ],
    )


def test_exit_zero_over_a_finding_is_unfinished(tmp_path: Path) -> None:
    """Ruff exits 1 with a finding, so an exit 0 over a report that holds one is no finished run: exit 2."""
    project = scaffold(tmp_path, {"dirty.py": DIRTY})
    fake = FakeRunner([completed(0, _report(ENTRY))])

    output = captured(
        lambda: run_gate(GATE, [tmp_path / "dirty.py"], project=project, process=fake)
    )

    assert (output.result, output.merged) == (
        2,
        [_report(ENTRY) + "\n", "check_cast: 0 finding(s) in 1 Python file(s)\n"],
    )


def test_unreadable_report_prints_the_whole_output(tmp_path: Path) -> None:
    """Output that is no JSON report ends the run at exit 2: the checker's output line by line, then the count line."""
    project = scaffold(tmp_path, {"clean.py": CLEAN})
    fake = FakeRunner([completed(1, "garbage\n", "No module named ruff\n")])

    output = captured(
        lambda: run_gate(GATE, [tmp_path / "clean.py"], project=project, process=fake)
    )

    assert (output.result, output.merged) == (
        2,
        [
            "garbage\n",
            "No module named ruff\n",
            "check_cast: 0 finding(s) in 1 Python file(s)\n",
        ],
    )


def test_a_report_of_another_shape_is_unreadable(tmp_path: Path) -> None:
    """A JSON list whose entry lacks a field the gate reads is no report it can read: exit 2."""
    project = scaffold(tmp_path, {"clean.py": CLEAN})
    entry = {
        "code": None,
        "message": "m",
        "filename": "clean.py",
        "location": {"row": 1, "column": 1},
    }
    fake = FakeRunner([completed(1, _report(entry))])

    output = captured(
        lambda: run_gate(GATE, [tmp_path / "clean.py"], project=project, process=fake)
    )

    assert (output.result, output.merged) == (
        2,
        [_report(entry) + "\n", "check_cast: 0 finding(s) in 1 Python file(s)\n"],
    )


def test_ruff_runs_in_the_project_without_cache_or_noqa(tmp_path: Path) -> None:
    """The command runs from the project's root, takes its settings file, and turns off the cache and `noqa`."""
    project = scaffold(tmp_path, {"clean.py": CLEAN})
    fake = FakeRunner([completed(0, "[]")])

    captured(
        lambda: run_gate(GATE, [tmp_path / "clean.py"], project=project, process=fake)
    )

    (command,) = fake.commands
    argv = command.argv
    assert (command.cwd, "--no-cache" in argv, "--ignore-noqa" in argv) == (
        tmp_path,
        True,
        True,
    )
    assert argv[argv.index("--config") + 1] == str(project.config)
    assert argv[-1] == str(tmp_path / "clean.py")
