# Copyright 2026 oh shit, gorillas!
"""Red tests for the mypy gate's stderr: a stop prints it as unfinished, a finish prints it again as remarks.

Source: the C3 review's findings 1 and 2, as the owner ruled them. On a stop (mypy's exit 2), mypy's stderr, when not
empty, is printed as Unfinished alongside the records, so an INTERNAL ERROR crash is visible. On a finished check,
mypy's stderr, when not empty, is printed again as Remark lines, as the old gate echoed it. Empty stderr adds no line.

The mypy runs below are answered by canned replies, and the warm run before each is answered by exit 0 with no output.
"""

import json
from collections.abc import Sequence
from pathlib import Path

from gates.check_mypy import GATE
from gates.core.checker import Command, Completed
from gates.core.runner import run_gate
from tests.support.capture import captured
from tests.support.fake import FakeRunner, completed
from tests.support.project import scaffold

CLEAN = "def double(value: int) -> int:\n    return value * 2\n"

MESSAGE = 'Incompatible return value type (got "str", expected "int")'

CRASH = "here.py:1: error: INTERNAL ERROR -- Please try using mypy master on GitHub:\n"

REPORT_BUG = "Please report a bug at https://github.com/python/mypy/issues\n"

PLUGIN_WARNING = "plugin: hook message while analysing here.py\n"

COUNT_ONE = "check_mypy: 0 finding(s) in 1 Python file(s)\n"

COUNT_ONE_FOUND = "check_mypy: 1 finding(s) in 1 Python file(s)\n"

# The warm run's reply: exit 0 and nothing printed.
WARM = completed(0)


class CacheLeavingRunner:
    """A Runner that leaves a file in each empty directory under the scratch root, then gives the next canned reply."""

    def __init__(self, scratch: Path, replies: Sequence[Completed]) -> None:
        """Initialize the seeded state."""
        self.scratch = scratch
        self.replies = FakeRunner(replies)

    def __call__(self, command: Command) -> Completed:
        """Return the reply for the supplied call."""
        for directory in list(self.scratch.rglob("*")):
            if directory.is_dir() and not any(directory.iterdir()):
                (directory / "cache.json").write_text("{}\n", encoding="utf-8")
        return self.replies(command)


def _record(file: Path) -> str:
    """One record of mypy's `--output json` report, in the given file, on its own line."""
    entry: dict[str, object] = {
        "file": str(file),
        "line": 2,
        "column": 4,
        "message": MESSAGE,
        "hint": None,
        "code": "return-value",
        "severity": "error",
    }
    return json.dumps(entry) + "\n"


def _run(tmp_path: Path, reply: Completed) -> tuple[int, list[str]]:
    """Run the gate over one file of a scaffolded project: the warm, then one mypy run answered by `reply`."""
    project = scaffold(tmp_path / "project", {"here.py": CLEAN})
    scratch = tmp_path / "scratch"
    scratch.mkdir()
    runner = CacheLeavingRunner(scratch, [WARM, reply])
    output = captured(
        lambda: run_gate(
            GATE,
            [project.root / "here.py"],
            project=project,
            process=runner,
            scratch_root=scratch,
        )
    )
    return output.result, output.merged


def test_a_stop_prints_its_stderr_as_unfinished_beside_the_records(
    tmp_path: Path,
) -> None:
    """A stop that read a record and wrote to stderr prints the record, then the stderr's lines, then the count; exit 2."""
    record = _record(tmp_path / "project" / "here.py")

    status, lines = _run(tmp_path, completed(2, record, CRASH + REPORT_BUG))

    assert (status, [line for line in lines if MESSAGE not in line]) == (
        2,
        [CRASH, REPORT_BUG, COUNT_ONE],
    )
    assert sum(MESSAGE in line for line in lines) == 1


def test_a_stop_with_no_stderr_prints_only_its_records(tmp_path: Path) -> None:
    """A stop whose stderr is empty adds no line: the record, then the count line, exit 2."""
    here = tmp_path / "project" / "here.py"
    record = _record(here)

    status, lines = _run(tmp_path, completed(2, record))

    assert (status, len(lines), lines[-1]) == (2, 2, COUNT_ONE)
    assert (MESSAGE in lines[0], str(here) in lines[0]) == (True, True)


def test_a_finish_prints_its_stderr_again_as_remarks(tmp_path: Path) -> None:
    """A finished check that wrote to stderr prints each of its lines, then the count line; remarks count no finding."""
    status, lines = _run(tmp_path, completed(0, "", PLUGIN_WARNING + REPORT_BUG))

    assert (status, lines) == (0, [PLUGIN_WARNING, REPORT_BUG, COUNT_ONE])


def test_a_finish_with_a_finding_prints_its_stderr_as_remarks_beside_it(
    tmp_path: Path,
) -> None:
    """A finished check with a finding and stderr text counts the finding only, and exits 1 with the stderr remarks printed."""
    record = _record(tmp_path / "project" / "here.py")

    status, lines = _run(tmp_path, completed(1, record, PLUGIN_WARNING))

    assert (status, PLUGIN_WARNING in lines, lines[-1]) == (1, True, COUNT_ONE_FOUND)


def test_a_finish_with_no_stderr_prints_nothing_more(tmp_path: Path) -> None:
    """A finished check whose stderr is empty adds no line: the count line alone, exit 0."""
    status, lines = _run(tmp_path, completed(0))

    assert (status, lines) == (0, [COUNT_ONE])
